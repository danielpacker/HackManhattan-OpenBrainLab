#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Puzzlebox Productions, LLC (2010-2011)
#
# This code is released under the GNU Pulic License (GPL) version 2
# For more information please refer to http://www.gnu.org/copyleft/gpl.html

import Puzzlebox.Synapse.Configuration as configuration
import Puzzlebox.Synapse.Interface as tgInterface
import sys

if configuration.ENABLE_PYSIDE:
	try:
		import PySide as PyQt4
		from PySide import QtCore, QtGui
	except:
		print "ERROR: Exception importing PySide:",
		print e
		configuration.ENABLE_PYSIDE = False
	else:
		print "INFO: [Synapse:synapse-gui] Using PySide module"

if not configuration.ENABLE_PYSIDE:
	print "INFO: [Synapse:synapse-gui] Using PyQt4 module"
	from PyQt4 import QtCore, QtGui


log = None
app = QtGui.QApplication(sys.argv)
window = tgInterface.QtUI(log, configuration.DEBUG)
window.show()
sys.exit(app.exec_())