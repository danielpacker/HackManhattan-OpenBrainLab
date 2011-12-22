#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Puzzlebox Productions, LLC (2010)
#
# This code is released under the GNU Pulic License (GPL) version 2
# For more information please refer to http://www.gnu.org/copyleft/gpl.html

import Puzzlebox.Synapse.Protocol as tgProtocol
import Puzzlebox.Synapse.Configuration as tgConf
import signal, sys

try:
	import PySide as PyQt4
	from PySide import QtCore
except:
	print "Using PyQt4 module"
	from PyQt4 import QtCore
else:
	print "Using PySide module"

signal.signal(signal.SIGINT, signal.SIG_DFL)

log = None
DEBUG = 2

device_address = None

for each in sys.argv:
	if each.startswith("--device="):
		device_address = each[ len("--device="): ]

if device_address == None:
	if tgConf.THINKGEAR_DEVICE_BLUETOOTH_ADDRESS == '':
		device_address = tgConf.THINKGEAR_DEVICE_SERIAL_PORT
	else:
		device_address = tgConf.THINKGEAR_DEVICE_BLUETOOTH_ADDRESS
	
app = QtCore.QCoreApplication(sys.argv)
serial_device = tgProtocol.SerialDevice(log, device_address, DEBUG=DEBUG)
protocol = tgProtocol.ProtocolHandler(log, serial_device, DEBUG=DEBUG)
protocol.start()
serial_device.run()