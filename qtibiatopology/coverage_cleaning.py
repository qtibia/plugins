# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QTIBIA Topology - Coverage Cleaning Plugin
                                 A QGIS plugin
 Clean polygon coverages using PostGIS ST_CoverageClean
                              -------------------
        begin                : 2026-01-05
        copyright            : (C) 2026 by QTIBIA Engineering
        email                : tudor.barascu@qtibia.ro
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt5.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QAction, QInputDialog, QMessageBox, QDialog,
                              QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                              QDoubleSpinBox, QComboBox, QCheckBox, QPushButton,
                              QGroupBox, QFormLayout)
import os.path

from qgis.core import (QgsProject, QgsFeature, QgsGeometry, Qgis,
                       QgsWkbTypes, QgsVectorLayer, QgsMessageLog)
import psycopg


def log_message(message, level=Qgis.Info, verbose=True):
    """Log message to QGIS log panel and Python console."""
    # Set verbose=False in production for better performance
    if verbose:
        QgsMessageLog.logMessage(message, 'Coverage Cleaning', level)
        print(f"[Coverage Cleaning] {message}")


def ewkb_to_geom(ewkb_str):
    """Convert EWKB hex string from PostGIS to QgsGeometry."""
    if ewkb_str is None:
        return QgsGeometry()
    # get type + flags
    header = ewkb_str[2:10]
    has_srid = int(header[6], 16) & 2 > 0
    if has_srid:
        # remove srid flag
        header = header[:6] + "%X" % (int(header[6], 16) ^ 2) + header[7]
        # remove srid
        ewkb_str = ewkb_str[:2] + header + ewkb_str[18:]
    w = bytes.fromhex(ewkb_str)
    g = QgsGeometry()
    g.fromWkb(w)
    return g


class CoverageCleaningSettingsDialog(QDialog):
    """Settings dialog for Coverage Cleaning plugin."""

    def __init__(self, plugin, parent=None):
        super().__init__(parent)
        self.plugin = plugin
        self.setWindowTitle("Coverage Cleaning - Settings")
        self.setMinimumWidth(500)
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout()

        # Database settings group
        db_group = QGroupBox("Database Connection")
        db_layout = QFormLayout()

        self.pg_service_edit = QLineEdit()
        self.pg_service_edit.setPlaceholderText("cadastru_999")
        db_layout.addRow("pg_service:", self.pg_service_edit)

        db_group.setLayout(db_layout)
        layout.addWidget(db_group)

        # Cleaning parameters group
        params_group = QGroupBox("Cleaning Parameters")
        params_layout = QFormLayout()

        self.gap_tolerance_spin = QDoubleSpinBox()
        self.gap_tolerance_spin.setDecimals(4)
        self.gap_tolerance_spin.setRange(0.0, 1000000.0)
        self.gap_tolerance_spin.setSingleStep(0.01)
        self.gap_tolerance_spin.setSuffix(" map units")
        params_layout.addRow("Gap Maximum Width:", self.gap_tolerance_spin)

        self.snapping_distance_spin = QDoubleSpinBox()
        self.snapping_distance_spin.setDecimals(4)
        self.snapping_distance_spin.setRange(-1.0, 1000000.0)
        self.snapping_distance_spin.setSingleStep(0.01)
        self.snapping_distance_spin.setSuffix(" (-1=auto, 0=disabled)")
        params_layout.addRow("Snapping Distance:", self.snapping_distance_spin)

        self.merge_strategy_combo = QComboBox()
        self.merge_strategy_combo.addItems([
            "MERGE_LONGEST_BORDER - Longest common border (recommended)",
            "MERGE_MAX_AREA - Maximum area",
            "MERGE_MIN_AREA - Minimum area",
            "MERGE_MIN_INDEX - Smallest input index"
        ])
        params_layout.addRow("Overlap Merge Strategy:", self.merge_strategy_combo)

        params_group.setLayout(params_layout)
        layout.addWidget(params_group)

        # Performance settings group
        perf_group = QGroupBox("Performance")
        perf_layout = QVBoxLayout()

        self.verbose_logging_check = QCheckBox("Enable verbose logging (slower but detailed)")
        perf_layout.addWidget(self.verbose_logging_check)

        perf_group.setLayout(perf_layout)
        layout.addWidget(perf_group)

        # Buttons
        button_layout = QHBoxLayout()
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_and_close)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)

        button_layout.addStretch()
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def load_settings(self):
        """Load settings from plugin."""
        self.pg_service_edit.setText(self.plugin.pg_service)
        self.gap_tolerance_spin.setValue(self.plugin.gap_tolerance)
        self.snapping_distance_spin.setValue(self.plugin.snapping_distance)

        # Set merge strategy combo
        strategies = ["MERGE_LONGEST_BORDER", "MERGE_MAX_AREA", "MERGE_MIN_AREA", "MERGE_MIN_INDEX"]
        if self.plugin.merge_strategy in strategies:
            self.merge_strategy_combo.setCurrentIndex(strategies.index(self.plugin.merge_strategy))

        self.verbose_logging_check.setChecked(self.plugin.verbose_logging)

    def save_and_close(self):
        """Save settings to plugin and close dialog."""
        self.plugin.pg_service = self.pg_service_edit.text()
        self.plugin.gap_tolerance = self.gap_tolerance_spin.value()
        self.plugin.snapping_distance = self.snapping_distance_spin.value()

        # Extract strategy key from combo text
        strategy_text = self.merge_strategy_combo.currentText()
        self.plugin.merge_strategy = strategy_text.split(" - ")[0]

        self.plugin.verbose_logging = self.verbose_logging_check.isChecked()

        # Save to QSettings for persistence
        self.plugin.save_settings()

        self.accept()


class CoverageCleaningPlugin:
    """QGIS Plugin Implementation for Coverage Cleaning."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # Store reference to the map canvas
        self.canvas = self.iface.mapCanvas()
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'CoverageCleaningPlugin_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Load settings from QSettings or use defaults
        self.settings = QSettings("QTIBIA", "CoverageCleaning")
        self.pg_service = self.settings.value("pg_service", "cadastru_999")
        self.gap_tolerance = float(self.settings.value("gap_tolerance", 0.01))
        self.snapping_distance = float(self.settings.value("snapping_distance", -1))
        self.merge_strategy = self.settings.value("merge_strategy", "MERGE_LONGEST_BORDER")
        self.verbose_logging = self.settings.value("verbose_logging", True, type=bool)

    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        :param message: String for translation.
        :type message: str, QString
        :returns: Translated version of message.
        :rtype: QString
        """
        return QCoreApplication.translate('CoverageCleaningPlugin', message)

    def save_settings(self):
        """Save current settings to QSettings for persistence."""
        self.settings.setValue("pg_service", self.pg_service)
        self.settings.setValue("gap_tolerance", self.gap_tolerance)
        self.settings.setValue("snapping_distance", self.snapping_distance)
        self.settings.setValue("merge_strategy", self.merge_strategy)
        self.settings.setValue("verbose_logging", self.verbose_logging)
        log_message("Settings saved")

    def show_settings_dialog(self):
        """Show the settings dialog."""
        dialog = CoverageCleaningSettingsDialog(self, self.iface.mainWindow())
        dialog.exec_()

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        # Set up icon
        icon_path = os.path.join(self.plugin_dir, 'icon.svg')
        icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()

        # Main action - Clean Coverage
        self.action = QAction(
            icon,
            'Clean Coverage',
            self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)

        # Settings action
        self.settings_action = QAction(
            'Coverage Cleaning Settings',
            self.iface.mainWindow())
        self.settings_action.triggered.connect(self.show_settings_dialog)

        # Add to Vector menu
        self.iface.addPluginToVectorMenu('&QTIBIA Topology', self.action)
        self.iface.addPluginToVectorMenu('&QTIBIA Topology', self.settings_action)

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        self.iface.removeToolBarIcon(self.action)
        self.iface.removePluginVectorMenu('&QTIBIA Topology', self.action)
        self.iface.removePluginVectorMenu('&QTIBIA Topology', self.settings_action)
        del self.action
        del self.settings_action

    def run(self):
        """Run the coverage cleaning process on selected features."""

        log_message("=== Coverage Cleaning Started ===")

        # Get the active layer
        layer = self.iface.activeLayer()

        log_message(f"Active layer: {layer.name() if layer else 'None'}")

        if not layer:
            self.iface.messageBar().pushMessage(
                "Error", "No active layer selected",
                Qgis.Critical, duration=3)
            return

        if not isinstance(layer, QgsVectorLayer):
            self.iface.messageBar().pushMessage(
                "Error", "Active layer is not a vector layer",
                Qgis.Critical, duration=3)
            return

        # Check if layer geometry is polygon
        geom_type = layer.geometryType()
        if geom_type != QgsWkbTypes.PolygonGeometry:
            self.iface.messageBar().pushMessage(
                "Error", "Layer must contain polygon geometries",
                Qgis.Critical, duration=3)
            return

        # Get selected features
        selected_features = layer.selectedFeatures()

        log_message(f"Selected features count: {len(selected_features)}")

        if len(selected_features) < 2:
            self.iface.messageBar().pushMessage(
                "Error", "Please select at least 2 features to clean coverage",
                Qgis.Warning, duration=3)
            return

        # Use saved settings
        log_message(f"Using settings: tolerance={self.gap_tolerance}, snapping={self.snapping_distance}, pg_service={self.pg_service}, strategy={self.merge_strategy}")

        # Start editing on the layer
        if not layer.isEditable():
            log_message("Starting edit mode on layer")
            layer.startEditing()
        else:
            log_message("Layer already in edit mode")

        # Process the coverage cleaning
        try:
            log_message("Calling clean_coverage()...")
            cleaned_geoms = self.clean_coverage(selected_features, self.gap_tolerance, self.snapping_distance, self.merge_strategy)

            if cleaned_geoms:
                log_message(f"Received {len(cleaned_geoms)} cleaned geometries")
                # Update features with cleaned geometries only if they changed
                changed_count = 0
                for idx, (feature, clean_geom) in enumerate(zip(selected_features, cleaned_geoms)):
                    original_geom = feature.geometry()
                    # Check if geometry actually changed
                    if not original_geom.equals(clean_geom):
                        if self.verbose_logging:
                            log_message(f"Feature {idx} (ID: {feature.id()}) geometry changed", verbose=True)
                        layer.changeGeometry(feature.id(), clean_geom)
                        changed_count += 1
                    else:
                        if self.verbose_logging:
                            log_message(f"Feature {idx} (ID: {feature.id()}) geometry unchanged", verbose=True)

                log_message(f"Total changed: {changed_count} of {len(selected_features)}")

                if changed_count > 0:
                    self.iface.messageBar().pushMessage(
                        "Success",
                        f"Coverage cleaned: {changed_count} of {len(selected_features)} features modified (in edit buffer, not committed)",
                        Qgis.Success, duration=5)
                else:
                    self.iface.messageBar().pushMessage(
                        "Info",
                        f"Coverage already clean: no changes needed for {len(selected_features)} features",
                        Qgis.Info, duration=3)

        except Exception as e:
            log_message(f"ERROR: {str(e)}", Qgis.Critical)
            self.iface.messageBar().pushMessage(
                "Error",
                f"Coverage cleaning failed: {str(e)}",
                Qgis.Critical, duration=5)

    def clean_coverage(self, features, gap_tolerance, snapping_distance, merge_strategy):
        """Clean coverage using PostGIS ST_CoverageClean.

        :param features: List of QgsFeature objects
        :param gap_tolerance: Maximum gap width to clean
        :param snapping_distance: Snapping distance (-1=auto, 0=disabled, >0=custom)
        :param merge_strategy: Strategy for merging overlaps
        :return: List of cleaned QgsGeometry objects in same order
        """

        log_message(f"clean_coverage() called with {len(features)} features, tolerance={gap_tolerance}, snapping={snapping_distance}, strategy={merge_strategy}",
                    verbose=self.verbose_logging)

        # Connect to PostGIS using psycopg3
        try:
            log_message(f"Connecting to PostgreSQL using service: {self.pg_service}",
                        verbose=self.verbose_logging)
            with psycopg.connect(f"service={self.pg_service}") as conn:
                log_message("Connected successfully", verbose=self.verbose_logging)
                with conn.cursor() as cur:
                    # Create a temporary table to hold the geometries with their order
                    log_message("Creating temporary table coverage_input", verbose=self.verbose_logging)
                    cur.execute("""
                        CREATE TEMP TABLE coverage_input (
                            feature_order INTEGER PRIMARY KEY,
                            geom geometry
                        )
                    """)

                    # Prepare batch insert data - use WKB (binary) for better performance
                    log_message(f"Preparing {len(features)} geometries for batch insert",
                                verbose=self.verbose_logging)
                    batch_data = []
                    for idx, feature in enumerate(features):
                        geom = feature.geometry()
                        # Use WKB (binary format) instead of WKT for better performance
                        # Convert QByteArray to Python bytes for psycopg3
                        wkb = bytes(geom.asWkb())
                        batch_data.append((idx, wkb))
                        if self.verbose_logging:
                            log_message(f"  Feature {idx}: WKB prepared ({len(wkb)} bytes)",
                                        verbose=True)

                    # Batch insert using executemany for better performance
                    log_message(f"Batch inserting {len(batch_data)} geometries",
                                verbose=self.verbose_logging)
                    cur.executemany(
                        """INSERT INTO coverage_input (feature_order, geom)
                           VALUES (%s, ST_GeomFromWKB(%s))""",
                        batch_data
                    )

                    log_message("Geometries inserted (commit deferred)", verbose=self.verbose_logging)

                    # Clean the coverage using ST_CoverageClean
                    # ST_CoverageClean is a WINDOW FUNCTION that requires OVER () clause
                    # It processes all geometries in the window and returns cleaned versions
                    sql = f"""
                        SELECT
                            feature_order,
                            ST_AsEWKB(
                                ST_CoverageClean(
                                    geom,
                                    {gap_tolerance},
                                    {snapping_distance},
                                    '{merge_strategy}'
                                ) OVER ()
                            ) as geom
                        FROM coverage_input
                        ORDER BY feature_order
                    """
                    if self.verbose_logging:
                        log_message(f"Executing ST_CoverageClean query:\n{sql}", verbose=True)
                    else:
                        log_message("Executing ST_CoverageClean...", verbose=True)

                    cur.execute(sql)

                    results = cur.fetchall()
                    log_message(f"Query returned {len(results)} results", verbose=self.verbose_logging)

                    # Convert results to QgsGeometry in original feature order
                    log_message("Converting results to QgsGeometry objects", verbose=self.verbose_logging)
                    cleaned_geoms = []
                    for idx, row in enumerate(results):
                        geom_ewkb = row[1]
                        if isinstance(geom_ewkb, bytes):
                            geom_ewkb = geom_ewkb.hex()
                        cleaned_geom = ewkb_to_geom(geom_ewkb)
                        cleaned_geoms.append(cleaned_geom)
                        if self.verbose_logging:
                            log_message(f"  Result {idx}: EWKB converted to QgsGeometry", verbose=True)

                    # Clean up - don't need explicit DROP, temp table will be dropped at session end
                    # But we'll do it anyway for cleanliness
                    log_message("Cleanup complete", verbose=self.verbose_logging)

                    log_message(f"Returning {len(cleaned_geoms)} cleaned geometries",
                                verbose=self.verbose_logging)
                    return cleaned_geoms

        except Exception as e:
            log_message(f"Database operation failed: {str(e)}", Qgis.Critical, verbose=True)
            raise Exception(f"Database operation failed: {str(e)}")
