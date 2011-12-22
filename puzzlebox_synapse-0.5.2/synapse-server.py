#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Puzzlebox Productions, LLC (2010-2011)
#
# This code is released under the GNU Pulic License (GPL) version 2
# For more information please refer to http://www.gnu.org/copyleft/gpl.html

import Puzzlebox.Synapse.Server as tgServer
import Puzzlebox.Synapse.Configuration as tgConf

import sys, signal

try:
	import PySide as PyQt4
	from PySide import QtCore
except:
	print "Using PyQt4 module"
	from PyQt4 import QtCore
else:
	print "Using PySide module"

DEBUG = 1

# Perform correct KeyboardInterrupt handling
signal.signal(signal.SIGINT, signal.SIG_DFL)
log = None

server_interface = tgConf.THINKGEAR_SERVER_INTERFACE
server_port = tgConf.THINKGEAR_SERVER_PORT
device_address = tgConf.THINKGEAR_DEVICE_SERIAL_PORT
device_id = tgConf.THINKGEAR_DEVICE_ID

for each in sys.argv:
	if each.startswith("--interface="):
		server_interface = each[ len("--interface="): ]
	if each.startswith("--port="):
		server_port = each[ len("--port="): ]
	if each.startswith("--device="):
		device_address = each[ len("--device="): ]
	if each.startswith("--debug="):
		DEBUG = int (each[ len("--debug="): ] )
	if each.startswith("--id="):
		device_id = int (each[ len("--id="): ] )

app = QtCore.QCoreApplication(sys.argv)
server = tgServer.ThinkgearServer(log, server_interface, server_port, device_address, device_id, emulate_headset_data = tgConf.THINKGEAR_ENABLE_SIMULATE_HEADSET_DATA, DEBUG=DEBUG)
server.start()
sys.exit(app.exec_())