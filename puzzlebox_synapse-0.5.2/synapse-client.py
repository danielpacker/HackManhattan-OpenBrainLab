#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Puzzlebox Productions, LLC (2010)
#
# This code is released under the GNU Pulic License (GPL) version 2
# For more information please refer to http://www.gnu.org/copyleft/gpl.html

import Puzzlebox.Synapse.Client as tgClient
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


signal.signal(signal.SIGINT, signal.SIG_DFL)
log = None
DEBUG = 1
command_parameters = sys.argv[1:]

server_host = tgConf.THINKGEAR_SERVER_HOST
server_port = tgConf.THINKGEAR_SERVER_PORT

for each in sys.argv:
	if each.startswith("--host="):
		server_host = each[ len("--host="): ]
	if each.startswith("--port="):
		server_port = each[ len("--port="): ]
		try:
			server_port = int(server_port)
		except:
			pass

app = QtCore.QCoreApplication(sys.argv)
client = tgClient.CLIClient(log, command_parameters, server_host, server_port, DEBUG=DEBUG)
sys.exit(app.exec_())