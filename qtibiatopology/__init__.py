# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QTIBIA Topology - Coverage Cleaning Plugin
                                 A QGIS plugin
 Clean polygon coverages using PostGIS ST_CoverageClean
 Generated for QTIBIA Engineering
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
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load CoverageCleaningPlugin class from file coverage_cleaning.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    from .coverage_cleaning import CoverageCleaningPlugin
    return CoverageCleaningPlugin(iface)
