# -*- coding: utf-8 -*-

# Copyright Puzzlebox Productions, LLC (2010-2011)
#
# This code is released under the GNU Pulic License (GPL) version 2
# For more information please refer to http://www.gnu.org/copyleft/gpl.html

# Old Class Names:
#       puzzlebox_synapse_interface = QtUI

__changelog__ = """\
Last Update: 2011.12.07
"""

__todo__ = """
- update configuration.ini file with settings entered into interface
"""

### IMPORTS ###
import os, sys, time
import simplejson as json


import Configuration as configuration

if configuration.ENABLE_PYSIDE:
	try:
		import PySide as PyQt4
		from PySide import QtCore, QtGui, QtNetwork
	except Exception, e:
		print "ERROR: Exception importing PySide:",
		print e
		configuration.ENABLE_PYSIDE = False
	else:
		print "INFO: [Synapse:Interface] Using PySide module"

if not configuration.ENABLE_PYSIDE:
	print "INFO: [Synapse:Interface] Using PyQt4 module"
	from PyQt4 import QtCore, QtGui, QtNetwork


try:
	from Interface_Plot import *
	MATPLOTLIB_AVAILABLE = True
except Exception, e:
	print "ERROR: Exception importing Interface_Plot:",
	print e
	MATPLOTLIB_AVAILABLE = False


if (sys.platform != 'win32'):
	import bluetooth
	DEFAULT_IMAGE_PATH = '/usr/share/puzzlebox_synapse/images'
else:
	import _winreg as winreg
	import itertools
	import re
	import serial
	DEFAULT_IMAGE_PATH = 'images'


try:
	import cPickle as pickle
except:
	import pickle

# from puzzlebox_synapse_interface_design import Ui_Form
from Interface_Design import Ui_Form as Design

#import Configuration as configuration
import Server as synapse_server
import Client as thinkgear_client
#import puzzlebox_logger


#####################################################################
# Globals
#####################################################################

DEBUG = configuration.DEBUG

THINKGEAR_SERVER_HOST = configuration.THINKGEAR_SERVER_HOST
THINKGEAR_SERVER_PORT = configuration.THINKGEAR_SERVER_PORT

THINKGEAR_EEG_POWER_BAND_ORDER = configuration.THINKGEAR_EEG_POWER_BAND_ORDER

THINKGEAR_EMULATION_MAX_ESENSE_VALUE = \
	configuration.THINKGEAR_EMULATION_MAX_ESENSE_VALUE
THINKGEAR_EMULATION_MAX_EEG_POWER_VALUE = \
	configuration.THINKGEAR_EMULATION_MAX_EEG_POWER_VALUE

PATH_TO_HCITOOL = '/usr/bin/hcitool'

#UPDATE_INTERFACE_VIA_TIMER = True # Alternative is to establish a
                                  ## ThinkGear Connect client which
                                  ## updates the interface on demand
                                  ## as packets are received

UPDATE_INTERFACE_VIA_TIMER = False

#INTERFACE_UPDATE_FREQUENCY = (1 / 512) * 1000 # ms (512 Hz)
INTERFACE_UPDATE_FREQUENCY = 1000 # ms

INTERFACE_RAW_EEG_UPDATE_FREQUENCY = 512

PACKET_MINIMUM_TIME_DIFFERENCE_THRESHOLD = 0.75


#####################################################################
# Classes
#####################################################################

class QtUI(QtGui.QWidget, Design):
	
	def __init__(self, log, server=None, DEBUG=DEBUG, parent = None):
		
		self.log = log
		self.DEBUG = DEBUG
		self.parent=parent
		
		if self.parent == None:
			QtGui.QWidget.__init__(self, parent)
			self.setupUi(self)
		
			self.configureSettings()
			self.connectWidgets()
		
		self.name = "Synapse Interface"
		
		self.thinkGearConnectServer = None
		self.thinkgearConnectClient = None
		
		self.maxEEGPower = THINKGEAR_EMULATION_MAX_EEG_POWER_VALUE
		
		self.debug_console_buffer = ''
		
		self.packets = {}
		self.packets['rawEeg'] = []
		self.packets['signals'] = []
		
		self.customDataHeaders = []
		
		if UPDATE_INTERFACE_VIA_TIMER:
			self.updateInterfaceTimer = QtCore.QTimer()
			QtCore.QObject.connect(self.updateInterfaceTimer, \
				                    QtCore.SIGNAL("timeout()"), \
				                    self.updateInterface)
		
		if (sys.platform == 'win32'):
			self.homepath = os.path.join( \
			   os.environ['HOMEDRIVE'], \
			   os.environ['HOMEPATH'], \
			   'Desktop')
		else:
			self.homepath = os.environ['HOME']
		
		if not os.path.exists(self.homepath):
			self.homepath = os.getcwd()
		
		
		self.activePlugins = []
	
	
	##################################################################
	
	def configureSettings(self):
		
		# Synapse Interface
		image_path = "puzzlebox.ico"
		if not os.path.exists(image_path):
			image_path = os.path.join(DEFAULT_IMAGE_PATH, image_path)
		
		if os.path.exists(image_path):
			icon = QtGui.QIcon()
			icon.addPixmap(QtGui.QPixmap(image_path), \
				            QtGui.QIcon.Normal, \
				            QtGui.QIcon.Off)
			self.setWindowIcon(icon)
		
		image_path = "puzzlebox_logo.png"
		if not os.path.exists(image_path):
			image_path = os.path.join(DEFAULT_IMAGE_PATH, image_path)
		if os.path.exists(image_path):
			self.labelPuzzleboxIcon.setPixmap(QtGui.QPixmap(image_path))
		
		
		if configuration.INTERFACE_TAB_POSITION == 'South':
			self.tabWidget.setTabPosition(QtGui.QTabWidget.South)
		else:
			self.tabWidget.setTabPosition(QtGui.QTabWidget.North)
		
		
		# ThinkGear Device
		self.updateThinkGearDevices()
		
		
		# ThinkGear Connect Server
		self.textLabelBluetoothStatus.setText("Status: Disconnected")
		
		# Display Host for ThinkGear Connect Socket Server
		self.lineEditThinkGearHost.setText(THINKGEAR_SERVER_HOST)
		
		# Display Port for ThinkGear Connect Socket Server
		self.lineEditThinkGearPort.setText('%i' % THINKGEAR_SERVER_PORT)
		
		
		# ThinkgGear Progress Bars
		self.progressBarEEGDelta.setMaximum(THINKGEAR_EMULATION_MAX_EEG_POWER_VALUE)
		self.progressBarEEGTheta.setMaximum(THINKGEAR_EMULATION_MAX_EEG_POWER_VALUE)
		self.progressBarEEGLowAlpha.setMaximum(THINKGEAR_EMULATION_MAX_EEG_POWER_VALUE)
		self.progressBarEEGHighAlpha.setMaximum(THINKGEAR_EMULATION_MAX_EEG_POWER_VALUE)
		self.progressBarEEGLowBeta.setMaximum(THINKGEAR_EMULATION_MAX_EEG_POWER_VALUE)
		self.progressBarEEGHighBeta.setMaximum(THINKGEAR_EMULATION_MAX_EEG_POWER_VALUE)
		self.progressBarEEGLowGamma.setMaximum(THINKGEAR_EMULATION_MAX_EEG_POWER_VALUE)
		self.progressBarEEGMidGamma.setMaximum(THINKGEAR_EMULATION_MAX_EEG_POWER_VALUE)
		
		self.progressBarAttention.setMaximum(THINKGEAR_EMULATION_MAX_ESENSE_VALUE)
		self.progressBarMeditation.setMaximum(THINKGEAR_EMULATION_MAX_ESENSE_VALUE)
		
		self.progressBarSignalContactQuality.setMaximum(200)
		
		
		if MATPLOTLIB_AVAILABLE:
			self.rawEEGMatplot = rawEEGMatplotlibCanvas( \
			                        self.tabEEGSignals, \
			                        width=8, \
			                        height=4, \
			                        dpi=100, \
			                        title='Raw EEG Waves')
			self.chartEEGMatplot = chartEEGMatplotlibCanvas( \
			                        self.tabCharts, \
			                        width=8, \
			                        height=4, \
			                        dpi=100, \
			                        title='EEG Brain Signals')
		
		else:
			self.tabWidget.removeTab(self.tabWidget.indexOf(self.tabEEGSignals))
			self.tabWidget.removeTab(self.tabWidget.indexOf(self.tabCharts))
	
	
	##################################################################
	
	def connectWidgets(self):
		
		self.connect(self.pushButtonBluetoothSearch, \
			          QtCore.SIGNAL("clicked()"), \
			          self.updateThinkGearDevices)
		
		self.connect(self.pushButtonBluetoothConnect, \
			          QtCore.SIGNAL("clicked()"), \
			          self.connectToThinkGearDevice)
		
		self.connect(self.pushButtonThinkGearConnect, \
			          QtCore.SIGNAL("clicked()"), \
			          self.startThinkGearConnectServer)
		
		self.connect(self.pushButtonSave, \
			          QtCore.SIGNAL("clicked()"), \
			          self.saveData)
		
		self.connect(self.pushButtonExport, \
			          QtCore.SIGNAL("clicked()"), \
			          self.exportData)
		
		self.connect(self.pushButtonReset, \
			          QtCore.SIGNAL("clicked()"), \
			          self.resetData)
	
	
	##################################################################
	
	def connectToThinkGearDevice(self):
		
		device_selection = self.comboBoxDeviceSelect.currentText()
		
		self.disconnect(self.pushButtonBluetoothConnect, \
			             QtCore.SIGNAL("clicked()"), \
			             self.connectToThinkGearDevice)
		
		self.connect(self.pushButtonBluetoothConnect, \
			          QtCore.SIGNAL("clicked()"), \
			          self.disconnectFromThinkGearDevice)
		
		self.textLabelBluetoothStatus.setText("Status: Connected")
		
		self.pushButtonBluetoothSearch.setEnabled(False)
		
		self.pushButtonBluetoothConnect.setText('Disconnect')
		self.pushButtonBluetoothConnect.setChecked(True)
		
		self.comboBoxDeviceSelect.setEnabled(False)
		self.comboBoxEEGHeadsetModel.setEnabled(False)
	
	
	##################################################################
	
	def disconnectFromThinkGearDevice(self):
		
		self.disconnect(self.pushButtonBluetoothConnect, \
			             QtCore.SIGNAL("clicked()"), \
			             self.disconnectFromThinkGearDevice)
		
		self.connect(self.pushButtonBluetoothConnect, \
			          QtCore.SIGNAL("clicked()"), \
			          self.connectToThinkGearDevice)
		
		self.textLabelBluetoothStatus.setText("Status: Disconnected")
		
		self.pushButtonBluetoothSearch.setEnabled(True)
		
		self.pushButtonBluetoothConnect.setText('Connect')
		self.pushButtonBluetoothConnect.setChecked(False)
		
		self.comboBoxDeviceSelect.setEnabled(True)
		self.comboBoxEEGHeadsetModel.setEnabled(True)
		
		
		self.progressBarEEGDelta.setValue(0)
		self.progressBarEEGTheta.setValue(0)
		self.progressBarEEGLowAlpha.setValue(0)
		self.progressBarEEGHighAlpha.setValue(0)
		self.progressBarEEGLowBeta.setValue(0)
		self.progressBarEEGHighBeta.setValue(0)
		self.progressBarEEGLowGamma.setValue(0)
		self.progressBarEEGMidGamma.setValue(0)
		
		self.progressBarAttention.setValue(0)
		self.progressBarMeditation.setValue(0)
		
		self.progressBarSignalContactQuality.setValue(0)
		
		self.maxEEGPower = THINKGEAR_EMULATION_MAX_EEG_POWER_VALUE
		
		# In case the user connects to a MindSet, then disconnects
		# and re-connects to a MindSet Emulator,
		# we need to reset the max power values
		self.progressBarEEGDelta.setMaximum(self.maxEEGPower)
		self.progressBarEEGTheta.setMaximum(self.maxEEGPower)
		self.progressBarEEGLowAlpha.setMaximum(self.maxEEGPower)
		self.progressBarEEGHighAlpha.setMaximum(self.maxEEGPower)
		self.progressBarEEGLowBeta.setMaximum(self.maxEEGPower)
		self.progressBarEEGHighBeta.setMaximum(self.maxEEGPower)
		self.progressBarEEGLowGamma.setMaximum(self.maxEEGPower)
		self.progressBarEEGMidGamma.setMaximum(self.maxEEGPower)
	
	
	##################################################################
	
	def startThinkGearConnectServer(self):
		
		# Ensure EEG device is connected first
		
		if not self.pushButtonBluetoothConnect.isChecked():
			self.connectToThinkGearDevice()
		
		
		self.pushButtonBluetoothSearch.setEnabled(False)
		self.pushButtonBluetoothConnect.setEnabled(False)
		
		server_interface = str(self.lineEditThinkGearHost.text())
		server_port = int(self.lineEditThinkGearPort.text())
		device_address = str(self.comboBoxDeviceSelect.currentText())
		emulate_headset_data = (device_address == 'ThinkGear Emulator')
		
		
		self.thinkGearConnectServer = \
			synapse_server.ThinkgearServer( \
				self.log, \
				server_interface=server_interface, \
				server_port=server_port, \
				device_address=device_address, \
				device_model=None, \
				emulate_headset_data=emulate_headset_data, \
				DEBUG=DEBUG, \
				parent=self)
		
		#self.connect(self.thinkGearConnectServer, \
		             #QtCore.SIGNAL("sendPacket()"), \
		             #self.thinkGearConnectServer.sendPacketQueue)
		
		self.thinkGearConnectServer.start()
		
		
		if UPDATE_INTERFACE_VIA_TIMER:
			self.updateInterfaceTimer.start(INTERFACE_UPDATE_FREQUENCY)
		
		else:
			self.thinkgearConnectClient = \
				thinkgear_client.QtClient( \
					self.log, \
					server_host=server_interface, \
					server_port=server_port, \
					DEBUG=0, \
					parent=self)
			
			self.thinkgearConnectClient.start()
		
		
		self.disconnect(self.pushButtonThinkGearConnect, \
			             QtCore.SIGNAL("clicked()"), \
			             self.startThinkGearConnectServer)
		
		self.connect(self.pushButtonThinkGearConnect, \
			          QtCore.SIGNAL("clicked()"), \
			          self.stopThinkGearConnectServer)
		
		self.lineEditThinkGearHost.setEnabled(False)
		self.lineEditThinkGearPort.setEnabled(False)
		
		self.pushButtonThinkGearConnect.setText('Stop')
	
	
	##################################################################
	
	def stopThinkGearConnectServer(self):
		
		if UPDATE_INTERFACE_VIA_TIMER:
			self.updateInterfaceTimer.stop()
		else:
			try:
				self.thinkgearConnectClient.disconnectFromHost()
			except Exception, e:
				if self.DEBUG:
					print "Call failed to self.thinkgearConnectClient.disconnectFromHost():",
					print e
			
			try:
				self.thinkGearConnectServer.exitThread()
			except Exception, e:
				if self.DEBUG:
					print "Call failed to self.thinkGearConnectServer.exitThread():",
					print e
		
		self.disconnect(self.pushButtonThinkGearConnect, \
		                QtCore.SIGNAL("clicked()"), \
		                self.stopThinkGearConnectServer)
		
		self.connect(self.pushButtonThinkGearConnect, \
			          QtCore.SIGNAL("clicked()"), \
			          self.startThinkGearConnectServer)
		
		self.lineEditThinkGearHost.setEnabled(True)
		self.lineEditThinkGearPort.setEnabled(True)
		
		self.pushButtonThinkGearConnect.setText('Start')
		
		#self.pushButtonBluetoothSearch.setEnabled(True)
		self.pushButtonBluetoothConnect.setEnabled(True)
		
		self.pushButtonThinkGearConnect.setChecked(False)
	
	
	##################################################################
	
	def updateInterface(self):
		
		if not self.thinkGearConnectServer.emulate_headset_data:
			self.processPacketThinkGear( \
				self.thinkGearConnectServer.protocol.data_packet)
	
	
	##################################################################
	
	def processPacketThinkGear(self, packet):
		
		if self.DEBUG > 2:
			print packet
		
		
		if ('rawEeg' in packet.keys()):
			self.packets['rawEeg'].append(packet['rawEeg'])
			value = packet['rawEeg']
			if MATPLOTLIB_AVAILABLE and \
				(self.tabWidget.currentIndex() == \
				 self.tabWidget.indexOf(self.tabEEGSignals)):
				self.rawEEGMatplot.update_figure(value)
			return
		else:
			self.packets['signals'].append(packet)
		
		
		if ('poorSignalLevel' in packet.keys()):
			value = 200 - packet['poorSignalLevel']
			self.progressBarSignalContactQuality.setValue(value)
			self.textEditDebugConsole.append("")
			try:
				(date, localtime) = self.parseTimeStamp(packet['timestamp'])
				self.textEditDebugConsole.append("Timestamp: %s %s" % (date, localtime))
			except:
				pass
			self.textEditDebugConsole.append("poorSignalLevel: %i" % \
			                                 packet['poorSignalLevel'])
		
		
		if ('eSense' in packet.keys()):
			
			if ('attention' in packet['eSense'].keys()):
				value = packet['eSense']['attention']
				self.progressBarAttention.setValue(value)
				self.textEditDebugConsole.append("eSense attention: %i" % value)
			
			if ('meditation' in packet['eSense'].keys()):
				value = packet['eSense']['meditation']
				self.progressBarMeditation.setValue(value)
				self.textEditDebugConsole.append("eSense meditation: %i" % value)
			
			
			if MATPLOTLIB_AVAILABLE:
				self.chartEEGMatplot.update_values('eSense', packet['eSense'])
				if (self.tabWidget.currentIndex() == \
				    self.tabWidget.indexOf(self.tabCharts)):
					self.chartEEGMatplot.update_figure('eSense', packet['eSense'])
		
		
		if ('eegPower' in packet.keys()):
			
			# If we are not emulating packets we'll set the maximum EEG Power value
			# threshold to the default (or maximum value found within this packet)
			if not self.thinkGearConnectServer.emulate_headset_data:
				self.maxEEGPower = THINKGEAR_EMULATION_MAX_EEG_POWER_VALUE
			
			for value in packet['eegPower'].keys():
				if packet['eegPower'][value] > self.maxEEGPower:
					self.maxEEGPower = packet['eegPower'][value]
			
			
			if ('delta' in packet['eegPower'].keys()):
				value = packet['eegPower']['delta']
				self.progressBarEEGDelta.setMaximum(self.maxEEGPower)
				self.progressBarEEGDelta.setValue(value)
				self.textEditDebugConsole.append("delta: %i" % value)
			
			if ('theta' in packet['eegPower'].keys()):
				value = packet['eegPower']['theta']
				self.progressBarEEGTheta.setMaximum(self.maxEEGPower)
				self.progressBarEEGTheta.setValue(value)
				self.textEditDebugConsole.append("theta: %i" % value)
			
			if ('lowAlpha' in packet['eegPower'].keys()):
				value = packet['eegPower']['lowAlpha']
				self.progressBarEEGLowAlpha.setMaximum(self.maxEEGPower)
				self.progressBarEEGLowAlpha.setValue(value)
				self.textEditDebugConsole.append("lowAlpha: %i" % value)
			
			if ('highAlpha' in packet['eegPower'].keys()):
				value = packet['eegPower']['highAlpha']
				self.progressBarEEGHighAlpha.setMaximum(self.maxEEGPower)
				self.progressBarEEGHighAlpha.setValue(value)
				self.textEditDebugConsole.append("highAlpha: %i" % value)
			
			if ('lowBeta' in packet['eegPower'].keys()):
				value = packet['eegPower']['lowBeta']
				self.progressBarEEGLowBeta.setMaximum(self.maxEEGPower)
				self.progressBarEEGLowBeta.setValue(value)
				self.textEditDebugConsole.append("lowBeta: %i" % value)
			
			if ('highBeta' in packet['eegPower'].keys()):
				value = packet['eegPower']['highBeta']
				self.progressBarEEGHighBeta.setMaximum(self.maxEEGPower)
				self.progressBarEEGHighBeta.setValue(value)
				self.textEditDebugConsole.append("highBeta: %i" % value)
			
			if ('lowGamma' in packet['eegPower'].keys()):
				value = packet['eegPower']['lowGamma']
				self.progressBarEEGLowGamma.setMaximum(self.maxEEGPower)
				self.progressBarEEGLowGamma.setValue(value)
				self.textEditDebugConsole.append("lowGamma: %i" % value)
			
			if ('highGamma' in packet['eegPower'].keys()):
				value = packet['eegPower']['highGamma']
				self.progressBarEEGMidGamma.setMaximum(self.maxEEGPower)
				self.progressBarEEGMidGamma.setValue(value)
				self.textEditDebugConsole.append("highGamma: %i" % value)
			
			
			if MATPLOTLIB_AVAILABLE:
				self.chartEEGMatplot.update_values('eegPower', packet['eegPower'])
				if (self.tabWidget.currentIndex() == \
				    self.tabWidget.indexOf(self.tabCharts)):
					self.chartEEGMatplot.update_figure('eegPower', packet['eegPower'])
		
		
		if ((self.thinkGearConnectServer.protocol != None) and
		    (self.tabWidget.currentIndex() == \
		     self.tabWidget.indexOf(self.tabControlPanel))):
			
			self.updateProfileSessionStatus()
	
	
	##################################################################
	
	def updateProfileSessionStatus(self, source=None, target=None):
		
		session_time = self.calculateSessionTime()
		
		if source == None:
			if self.parent == None:
				source = self
			else:
				source = self.parent
		
		if target == None:
			if self.parent == None:
				target = self
			else:
				target = self.parent
		
		target.textLabelSessionTime.setText(session_time)
		
		try:
			target.textLabelPacketsReceived.setText( "%i" % \
				source.thinkGearConnectServer.protocol.packet_count)
		except:
			pass
		
		try:
			target.textLabelPacketsDropped.setText( "%i" % \
				source.thinkGearConnectServer.protocol.bad_packets)
		except:
			pass
	
	
	##################################################################
	
	def calculateSessionTime(self):
		
		if self.parent == None:
			server = self.thinkGearConnectServer
		else:
			server = self.parent.thinkGearConnectServer
		
		session_time = time.time() - \
			server.protocol.session_start_timestamp
		
		session_time = int(session_time)
		
		session_time = self.convert_seconds_to_datetime(session_time)
		
		return(session_time)
	
	
	##################################################################
	
	def enumerateSerialPorts(self):
		
		""" Uses the Win32 registry to return an
		iterator of serial (COM) ports
		existing on this computer.
		
		from http://eli.thegreenplace.net/2009/07/31/listing-all-serial-ports-on-windows-with-python/
		"""
	 
		path = 'HARDWARE\\DEVICEMAP\\SERIALCOMM'
		try:
			key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)
		except WindowsError:
			#raise IterationError
			return
		
		for i in itertools.count():
			try:
				val = winreg.EnumValue(key, i)
				yield str(val[1])
			except EnvironmentError:
				break
	
	
	##################################################################
	
	def fullPortName(self, portname):
		
		""" Given a port-name (of the form COM7,
		COM12, CNCA0, etc.) returns a full
		name suitable for opening with the
		Serial class.
		"""
		
		m = re.match('^COM(\d+)$', portname)
		if m and int(m.group(1)) < 10:
			return portname
		
		return '\\\\.\\' + portname
	
	
	##################################################################
	
	def searchForSerialDevices(self, devices=[]):
		
		if (sys.platform == 'win32'):
			
			for portname in self.enumerateSerialPorts():
				
				if portname not in devices:
					#portname = self.fullPortName(portname)
					devices.append(portname)
		
		else:
			
			if os.path.exists('/dev/ttyUSB0'):
				devices.append('/dev/ttyUSB0')
			if os.path.exists('/dev/ttyUSB1'):
				devices.append('/dev/ttyUSB1')
			if os.path.exists('/dev/ttyUSB2'):
				devices.append('/dev/ttyUSB2')
			if os.path.exists('/dev/ttyUSB3'):
				devices.append('/dev/ttyUSB3')
			if os.path.exists('/dev/ttyUSB4'):
				devices.append('/dev/ttyUSB4')
			if os.path.exists('/dev/ttyUSB5'):
				devices.append('/dev/ttyUSB5')
			if os.path.exists('/dev/ttyUSB6'):
				devices.append('/dev/ttyUSB6')
			if os.path.exists('/dev/ttyUSB7'):
				devices.append('/dev/ttyUSB7')
			if os.path.exists('/dev/ttyUSB8'):
				devices.append('/dev/ttyUSB8')
			if os.path.exists('/dev/ttyUSB9'):
				devices.append('/dev/ttyUSB9')
			
			if os.path.exists('/dev/ttyACM0'):
				devices.append('/dev/ttyACM0')
			if os.path.exists('/dev/ttyACM1'):
				devices.append('/dev/ttyACM1')
			if os.path.exists('/dev/ttyACM2'):
				devices.append('/dev/ttyACM2')
			if os.path.exists('/dev/ttyACM3'):
				devices.append('/dev/ttyACM3')
			if os.path.exists('/dev/ttyACM4'):
				devices.append('/dev/ttyACM4')
		
		
		return(devices)
	
	
	##################################################################
	
	def hcitoolScanForRemoteDevices(self, thinkgear_devices=[]):
		
		bluetooth_devices = []
		
		#command = '%s scan 2> /dev/null' % PATH_TO_HCITOOL
		command = '%s scan' % PATH_TO_HCITOOL
		
		if self.DEBUG > 1:
			print 'INFO: Calling "%s"' % command 
		
		output = os.popen(command, 'r')
		
		for line in output.readlines():
			line = line.strip()
			if line == '' or line == 'Scanning ...':
				continue
			elif self.DEBUG > 1:
				print line
			try:
				address = line.split('\t')[0]
			except:
				pass
			else:
				bluetooth_devices.append(address)
		
		
		for address in bluetooth_devices:
			
			command = '%s name %s' % (PATH_TO_HCITOOL, address)
			
			if self.DEBUG:
				print 'INFO: Calling "%s"' % command
			
			output = os.popen(command, 'r')
			
			for line in output.readlines():
				line = line.strip()
				if line == '':
					continue
				elif self.DEBUG:
					print '\t',
					print line
				
				device_name = line.strip()
			
				if ((device_name == 'MindSet' or device_name == 'MindWave Mobile') and \
					(address not in thinkgear_devices)):
					thinkgear_devices.append(address)
		
		
		return (thinkgear_devices)
	
	
	##################################################################
	
	def hcitoolGetActiveConnections(self, thinkgear_devices=[]):
		
		bluetooth_devices = []
		
		#command = '%s con 2> /dev/null' % PATH_TO_HCITOOL
		command = '%s con' % PATH_TO_HCITOOL
		
		if self.DEBUG > 1:
			print 'INFO: Calling "%s"' % command 
		
		output = os.popen(command, 'r')
		
		for line in output.readlines():
			line = line.strip()
			if line == '' or line == 'Connections:':
				continue
			elif self.DEBUG > 1:
				print line
			try:
				address = line.split(' ')[2]
			except:
				pass
			else:
				bluetooth_devices.append(address)
		
		
		for address in bluetooth_devices:
			
			command = '%s name %s' % (PATH_TO_HCITOOL, address)
			
			if self.DEBUG:
				print 'INFO: Calling "%s":' % command
			
			output = os.popen(command, 'r')
			
			for line in output.readlines():
				line = line.strip()
				if line == '':
					continue
				elif self.DEBUG:
					print '\t',
					print line
				
				device_name = line.strip()
			
				if ((device_name == 'MindSet' or device_name == 'MindWave Mobile') and \
					(address not in thinkgear_devices)):
					thinkgear_devices.append(address)
		
		
		return (thinkgear_devices)
	
	
	##################################################################
	
	def searchForThinkGearDevices(self):
		
		enable_hcitool = configuration.ENABLE_HCITOOL
		
		thinkgear_devices = []
		
		#self.pushButtonBluetoothSearch.setText('Searching')
		
		if (sys.platform != 'win32'):
			
			# Bluetooth module doesn't compile properly under WindowsError
			
			bluetooth_devices = []
			
			if not enable_hcitool:
				
				try:
					
					if self.DEBUG:
						print "INFO: Searching for Bluetooth devices using PyBluez module"
					
					bluetooth_devices = bluetooth.discover_devices( \
					                       duration=5, \
					                       flush_cache=True, \
					                       lookup_names=False)
					
					for address in bluetooth_devices:
						device_name = bluetooth.lookup_name(address)
						if ((device_name == 'MindSet' or device_name == 'MindWave Mobile') and \
							(address not in thinkgear_devices)):
							thinkgear_devices.append(address)
					
					
					# There is an issue under recent released of Linux
					# in which already-connected Bluetooth ThinkGear devices
					# are not appearing in a bluetooth device scan. However,
					# using "hcitool" connected devices can be listed correctly.
					# There does not appear to be an equivalent PyBluez feature.
					# (http://pybluez.googlecode.com/svn/www/docs-0.7/index.html)
					
					if thinkgear_devices == []:
						if self.DEBUG:
							print "INFO: No devices found through PyBluez module. Falling back to hcitool."
						thinkgear_devices = self.hcitoolGetActiveConnections(thinkgear_devices)
				
				
				except Exception, e:
					if self.DEBUG:
						print "ERROR: Exception calling Python Bluetooth module. (Is PyBluez installed?):"
						print e
					
					enable_hcitool = True
			
			
			if enable_hcitool:
				
				thinkgear_devices = self.hcitoolScanForRemoteDevices(thinkgear_devices)
				thinkgear_devices = self.hcitoolGetActiveConnections(thinkgear_devices)
			
			
			if self.DEBUG > 2:
				print "Bluetooth ThinkGear devices found:",
				print thinkgear_devices
		
		
		thinkgear_devices = self.searchForSerialDevices(thinkgear_devices)
		
		
		if self.DEBUG:
			print "ThinkGear devices found:",
			print thinkgear_devices
		
		
		return(thinkgear_devices)
	
	
	##################################################################
	
	def updateThinkGearDevices(self):
		
		devices = self.searchForThinkGearDevices()
		
		#if self.parent == None:
			#self.comboBoxDeviceSelect.clear()
		#else:
			#self.parent.comboBoxDeviceSelect.clear()
		
		self.comboBoxDeviceSelect.clear()
		devices.insert(0, 'ThinkGear Emulator')
		
		for device in devices:
			self.comboBoxDeviceSelect.addItem(device)
	
	
	##################################################################
	
	def collectData(self, source=None, target=None):
		
		if source == None:
			if self.parent == None:
				source = self
			else:
				source = self.parent
		
		if target == None:
			if self.parent == None:
				target = self
			else:
				target = self.parent
		
		data = {}
		
		data['rawEeg'] = source.packets['rawEeg']
		data['signals'] = source.packets['signals']
		
		data['sessionTime'] = self.calculateSessionTime()
		
		data['profileName'] = str(target.lineEditSessionProfile.text())
		
		return(data)
	
	
	##################################################################
	
	def parseTimeStamp(self, timestamp, local_version=False, truncate_time_zone=False):
		
		try:
			decimal = '%f' % timestamp
			decimal = decimal.split('.')[1]
		except:
			decimal = '0'
		
		localtime = time.localtime(timestamp)
		
		if local_version:
			date = time.strftime('%x', localtime)
			localtime = time.strftime('%X', localtime)
		
		elif truncate_time_zone:
			date = time.strftime('%Y-%m-%d', localtime)
			localtime = time.strftime('%H:%M:%S', localtime)
			localtime = '%s.%s' % (localtime, decimal[:3])
		
		else:
			date = time.strftime('%Y-%m-%d', localtime)
			localtime = time.strftime('%H:%M:%S', localtime)
			localtime = '%s.%s %s' % (localtime, decimal, \
			               time.strftime('%Z', time.localtime(timestamp)))
		
		
		return(date, localtime)
	
	
	##################################################################
	
	def saveData(self, source=None, target=None):
		
		if source == None:
			if self.parent == None:
				source = self
			else:
				source = self.parent
		
		if target == None:
			if self.parent == None:
				target = self
			else:
				target = self.parent
		
		data = self.collectData(source=source, target=target)
		
		(date, localtime) = self.parseTimeStamp(time.time())
		
		default_filename = '%s %s.synapse' % (date, \
		                      target.lineEditSessionProfile.text())
		                      
		default_filename = os.path.join(self.homepath, default_filename)
		
		output_file = QtGui.QFileDialog.getSaveFileName(parent=target, \
		                 caption="Save Session Data to File", \
		                 dir=default_filename, \
		                 filter="Puzzlebox Synapse Data File (*.synapse)")
		
		try:
			output_file = output_file[0]
		except:
			output_file = ''
		
		if output_file == '':
			return
		
		file = open(str(output_file), 'w')
		pickle.dump(data, file)
		file.close()
	
	
	##################################################################
	
	def exportData(self, parent=None, source=None, target=None):
		
		if parent == None:
			if self.parent == None:
				parent = self
			else:
				parent = self.parent
		
		if source == None:
			if self.parent == None:
				source = self
			else:
				source = self.parent
		
		if target == None:
			if self.parent == None:
				target = self
			else:
				target = self.parent
		
		(date, localtime) = self.parseTimeStamp(time.time())
		
		default_filename = '%s %s.csv' % (date, \
		                      target.lineEditSessionProfile.text())
		
		default_filename = os.path.join(target.homepath, default_filename)
		
		output_file = QtGui.QFileDialog.getSaveFileName(parent=target, \
		                 caption="Export Session Data to File", \
		                 dir=default_filename, \
		                 filter="CSV File (*.csv);;Text File (*.txt)")
		
		try:
			output_file = output_file[0]
		except:
			output_file = ''
		
		if output_file == '':
			return
		
		if str(output_file).endswith('.csv'):
			
			outputData = self.exportDataToCSV(parent=parent, source=source, target=target)
		
		
		else:
			
			try:
				outputData = self.textEditDebugConsole.toPlainText()
			except:
				outputData = self.exportDataToCSV()
			
			
		file = open(str(output_file), 'w')
		file.write(outputData)
		file.close()
	
	
	##################################################################
	
	def exportDataToCSV(self, parent=None, source=None, target=None):
		
		if parent == None:
			if self.parent == None:
				parent = self
			else:
				parent = self.parent
		
		if source == None:
			if self.parent == None:
				source = self
			else:
				source = self.parent
		
		if target == None:
			if self.parent == None:
				target = self
			else:
				target = self.parent
		
		try:
			truncate_csv_timezone = target.configuration.EXPORT_CSV_TRUNCATE_TIMEZONE
		except:
			truncate_csv_timezone = False
		
		try:
			scrub_data = target.configuration.EXPORT_CSV_SCRUB_DATA
		except:
			scrub_data = False
		
		
		headers = 'Date,Time,Delta,Theta,Low Alpha,High Alpha,Low Beta,High Beta,Low Gamma,Mid Gamma,Attention,Meditation,Signal Level'
		
		customDataHeaders = []
		for header in parent.customDataHeaders:
			customDataHeaders.append(header)
		for plugin in parent.activePlugins:
			for header in plugin.customDataHeaders:
				customDataHeaders.append(header)
		
		for each in customDataHeaders:
			headers = headers + ',%s' % each
		
		headers = headers + '\n'
		
		csv = {}
		
		for packet in source.packets['signals']:
			
			if 'rawEeg' in packet.keys():
				continue
			
			if packet['timestamp'] not in csv.keys():
				
				#print packet
				timestamp = packet['timestamp']
				(date, localtime) = self.parseTimeStamp(timestamp, \
				                    truncate_time_zone=truncate_csv_timezone)
				
				csv[timestamp] = {}
				csv[timestamp]['Date'] = date
				csv[timestamp]['Time'] = localtime
				csv[timestamp]['Delta'] = ''
				csv[timestamp]['Theta'] = ''
				csv[timestamp]['Low Alpha'] = ''
				csv[timestamp]['High Alpha'] = ''
				csv[timestamp]['Low Beta'] = ''
				csv[timestamp]['High Beta'] = ''
				csv[timestamp]['Low Gamma'] = ''
				csv[timestamp]['Mid Gamma'] = ''
				csv[timestamp]['Attention'] = ''
				csv[timestamp]['Meditation'] = ''
				csv[timestamp]['Signal Level'] = ''
				
				for header in customDataHeaders:
					csv[timestamp][header] = ''
			
			
			if 'eSense' in packet.keys():
				if 'attention' in packet['eSense'].keys():
					csv[timestamp]['Attention'] = packet['eSense']['attention']
				if 'meditation' in packet['eSense'].keys():
					csv[timestamp]['Meditation'] = packet['eSense']['meditation']
			
			if 'eegPower' in packet.keys():
				if 'delta' in packet['eegPower'].keys():
					csv[timestamp]['Delta'] = packet['eegPower']['delta']
				if 'theta' in packet['eegPower'].keys():
					csv[timestamp]['Theta'] = packet['eegPower']['theta']
				if 'lowAlpha' in packet['eegPower'].keys():
					csv[timestamp]['Low Alpha'] = packet['eegPower']['lowAlpha']
				if 'highAlpha' in packet['eegPower'].keys():
					csv[timestamp]['High Alpha'] = packet['eegPower']['highAlpha']
				if 'lowBeta' in packet['eegPower'].keys():
					csv[timestamp]['Low Beta'] = packet['eegPower']['lowBeta']
				if 'highBeta' in packet['eegPower'].keys():
					csv[timestamp]['High Beta'] = packet['eegPower']['highBeta']
				if 'lowGamma' in packet['eegPower'].keys():
					csv[timestamp]['Low Gamma'] = packet['eegPower']['lowGamma']
				if 'highGamma' in packet['eegPower'].keys():
					csv[timestamp]['Mid Gamma'] = packet['eegPower']['highGamma']
			
			if 'poorSignalLevel' in packet.keys():
				csv[timestamp]['Signal Level'] = packet['poorSignalLevel']
			
			for header in customDataHeaders:
				if 'custom' in packet.keys() and \
				   header in packet['custom'].keys():
					csv[timestamp][header] = packet['custom'][header]
		
		
		if scrub_data:
			csv = self.scrubData(csv, truncate_csv_timezone)
		
		
		output = headers
		
		csv_keys = csv.keys()
		csv_keys.sort()
		
		for key in csv_keys:
			
			row = '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s' % \
			      (csv[key]['Date'], \
			       csv[key]['Time'], \
			       csv[key]['Delta'], \
			       csv[key]['Theta'], \
			       csv[key]['Low Alpha'], \
			       csv[key]['High Alpha'], \
			       csv[key]['Low Beta'], \
			       csv[key]['High Beta'], \
			       csv[key]['Low Gamma'], \
			       csv[key]['Mid Gamma'], \
			       csv[key]['Attention'], \
			       csv[key]['Meditation'], \
			       csv[key]['Signal Level'])
			
			for header in customDataHeaders:
				row = row + ',%s' % csv[key][header]
			
			row = row + '\n'
			
			output = output + row
		
		
		return(output)
	
	
	##################################################################
	
	def scrubData(self, csv, truncate_csv_timezone=False):
		
		# If there are missing packets, repeat a given packet once per missing
		# second until there is a gap between 1 and 2 seconds, in which case
		# produce a final duplicate packet at the mid-point between the packets

		if self.DEBUG:
			print "INFO: Scrubbing Data"
		
		last_time = None
		last_recorded_time = None
		
		output = {}
		
		csv_keys = csv.keys()
		csv_keys.sort()
		
		for key in csv_keys:
			
			timestamp = key

			if csv[key]['Attention'] == '':
				continue
			
			if last_time == None:
				# First entry in log
				last_time = timestamp
				last_recorded_time = timestamp
				output[key] = csv[key]
				continue
			
			else:
				
				#time_difference = timestamp - last_time
				time_difference = timestamp - last_recorded_time
				
				if (time_difference <= 1) and \
				   (time_difference >= PACKET_MINIMUM_TIME_DIFFERENCE_THRESHOLD):
					# Skip packets within the correct time threshold
					last_time = timestamp
					last_recorded_time = timestamp
					output[key] = csv[key]
					continue
				
				else:

					if self.DEBUG > 1:
						print "time_difference:",
						print time_difference
						print "timestamp:",
						print self.parseTimeStamp(timestamp)[-1].split(' ')[0]
						print "last_time:",
						print self.parseTimeStamp(last_time)[-1].split(' ')[0]
						print "last_recorded_time:",
						print self.parseTimeStamp(last_recorded_time)[-1].split(' ')[0]

					
					new_packet = csv[key].copy()
					
					if time_difference >= 2:
						
						##new_time = last_time + 1
						#new_time = last_recorded_time + 1

						count = int(time_difference)
						while count >= 1:
							new_packet = csv[key].copy()
							new_time = last_recorded_time + 1
							(date, formatted_new_time) = self.parseTimeStamp(new_time, \
							 truncate_time_zone=truncate_csv_timezone)
							new_packet['Time'] = formatted_new_time
							last_recorded_time = new_time
							last_time = timestamp
							output[new_time] = new_packet
							count = count - 1
						continue
						
					elif time_difference < PACKET_MINIMUM_TIME_DIFFERENCE_THRESHOLD:
						# Spread out "bunched up" packets
						#new_time = last_time + 1
						new_time = last_recorded_time + 1
					
					
					elif (time_difference < 2) and (time_difference > 1):
						
						#new_time = last_time + ((last_time - timestamp) / 2)
						#new_time = last_recorded_time + ((last_recorded_time - timestamp) / 2)
						#new_time = last_time + 1
						new_time = last_recorded_time + 1
					
					
					(date, formatted_new_time) = self.parseTimeStamp(new_time, \
					   truncate_time_zone=truncate_csv_timezone)
					
					new_packet['Time'] = formatted_new_time
					
					#last_time = new_time
					last_recorded_time = new_time
					last_time = timestamp
					output[new_time] = new_packet
					
					if self.DEBUG > 1:
						print "WARN: Scrubbing new packet:",
						print new_packet
						print
		
		
		return(output)
	
	
	##################################################################
	
	def resetData(self, source=None):
		
		if source == None:
			if self.parent == None:
				source = self
			else:
				source = self.parent
		
		#if target == None:
			#if self.parent == None:
				#target = self
			#else:
				#target = self.parent
		
		source.packets['rawEeg'] = []
		source.packets['signals'] = []
		
		source.thinkGearConnectServer.protocol.session_start_timestamp = \
			time.time()
		
		source.thinkGearConnectServer.protocol.packet_count = 0
		source.thinkGearConnectServer.protocol.bad_packets = 0
		
		self.updateProfileSessionStatus()
		
		try:
			source.textEditDebugConsole.setText("")
		except:
			pass
	
	
	#####################################################################
	
	def convert_seconds_to_datetime(self, duration):
		
		duration_hours = duration / (60 * 60)
		duration_minutes = (duration - (duration_hours * (60 * 60))) / 60
		duration_seconds = (duration - (duration_hours * (60 * 60)) - (duration_minutes * 60))
		
		duration_hours = '%i' % duration_hours
		if (len(duration_hours) == 1):
			duration_hours = "0%s" % duration_hours
		
		duration_minutes = '%i' % duration_minutes
		if (len(duration_minutes) == 1):
			duration_minutes = "0%s" % duration_minutes
		
		duration_seconds = '%i' % duration_seconds
		if (len(duration_seconds) == 1):
			duration_seconds = "0%s" % duration_seconds
		
		datetime = '%s:%s:%s' % (duration_hours, duration_minutes, duration_seconds)
		
		return(datetime)
	
	
	##################################################################
	
	def stop(self):
		
		if UPDATE_INTERFACE_VIA_TIMER:
			self.updateInterfaceTimer.stop()
		else:
			if self.thinkgearConnectClient != None:
				self.thinkgearConnectClient.exitThread()
		
		if self.thinkGearConnectServer != None:
			self.thinkGearConnectServer.exitThread()
	
	
	##################################################################
	
	def closeEvent(self, event):
		
		quit_message = "Are you sure you want to exit the program?"
		
		reply = QtGui.QMessageBox.question( \
		           self, \
		          'Message', \
		           quit_message, \
		           QtGui.QMessageBox.Yes, \
		           QtGui.QMessageBox.No)
		
		if reply == QtGui.QMessageBox.Yes:
			
			self.stop()
			
			event.accept()
		
		else:
			event.ignore()
