# encoding: utf-8
#-----------------------------------------------------------
# Copyright (C) 2015 Martin Dobias, Tudor Bărăscu
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
# http://doc.qt.io/qt-5.9/qmessagebox.html


# from PyQt5.QtWidgets import *
from qgis.PyQt.QtWidgets import *


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
        QMessageBox.information(None, 'Minimal Plugin 01', 'Execute something useful..')
