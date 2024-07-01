# encoding: utf-8
#-----------------------------------------------------------
# Copyright (C) 2018 Tudor Bărăscu
#-----------------------------------------------------------
# Licensed under the terms of GNU GPL 2
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#---------------------------------------------------------------------

# https://qgis.org/api/classQgisInterface.html
# http://doc.qt.io/qt-5.9/qaction-members.html
# https://qgis.org/api/classQgsDataSourceUri.html
# http://doc.qt.io/qt-5.9/qmessagebox.html

from qgis.PyQt.QtWidgets import *
from qgis.core import QgsDataSourceUri, QgsVectorLayer

def classFactory(iface):
    return MinimalPlugin(iface)

class MinimalPlugin:
    def __init__(self, iface):
        self.iface = iface

    def initGui(self):
        self.action = QAction('Execute action!', self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        self.iface.removeToolBarIcon(self.action)
        del self.action

    def run(self):
        uri = QgsDataSourceUri()
        uri.setConnection("workshop.qcooperative.net", "5437", "workshop", "qcooperative", "qcooperative")
        uri.setDataSource("tudor", "countries", "geom")

        vl = QgsVectorLayer(uri.uri(), "countries", "postgres")

        if not vl.isValid():
            QMessageBox.critical(None, "Plugin minimal 02", "failed to load buildings!")

        else:
            count = 0

            for feature in vl.getFeatures():
                count += 1

            QMessageBox.information(None, "Plugin minimal 02", "No. of countries: " + str(count))
