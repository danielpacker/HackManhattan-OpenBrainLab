# -*- coding: utf-8 -*-

# Copyright Puzzlebox Productions, LLC (2010-2011)
#
# This code is released under the GNU Pulic License (GPL) version 2
# For more information please refer to http://www.gnu.org/copyleft/gpl.html

# Old Class Name = puzzle_synapse_server_thinkgear

__changelog__ = """\
Last Update: 2011.12.06
"""

### IMPORTS ###

import os, sys, time
import signal
import math

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
		print "INFO: [Synapse:Server] Using PySide module"

if not configuration.ENABLE_PYSIDE:
	print "INFO: [Synapse:Server] Using PyQt4 module"
	from PyQt4 import QtCore, QtGui, QtNetwork


#try:
	#import PySide as PyQt4
	#from PySide import QtCore, QtGui, QtNetwork
#except:
	#print "Using PyQt4 module"
	#from PyQt4 import QtCore, QtGui, QtNetwork
#else:
	#print "Using PySide module"

##from PyQt4 import QtNetwork

#import Configuration as configuration
import Protocol as serial_interface

### GLOBALS ###

DEBUG = configuration.DEBUG

COMMUNICATION_MODE = 'Emit Signal'
#COMMUNICATION_MODE = 'Call Parent'

SERVER_INTERFACE = configuration.THINKGEAR_SERVER_INTERFACE
SERVER_PORT = configuration.THINKGEAR_SERVER_PORT
THINKGEAR_DEVICE_SERIAL_PORT = configuration.THINKGEAR_DEVICE_SERIAL_PORT
THINKGEAR_DEVICE_ID = configuration.THINKGEAR_DEVICE_ID

CLIENT_NO_REPLY_WAIT = configuration.CLIENT_NO_REPLY_WAIT * 1000

FLASH_POLICY_FILE_REQUEST = configuration.FLASH_POLICY_FILE_REQUEST
FLASH_SOCKET_POLICY_FILE = configuration.FLASH_SOCKET_POLICY_FILE

DELIMITER = configuration.THINKGEAR_DELIMITER

MESSAGE_FREQUENCY_TIMER = 1 * 1000 # 1 Hz (1000 ms)

ENABLE_SIMULATE_HEADSET_DATA = configuration.THINKGEAR_ENABLE_SIMULATE_HEADSET_DATA

BLINK_FREQUENCY_TIMER = configuration.THINKGEAR_BLINK_FREQUENCY_TIMER

DEFAULT_SAMPLE_WAVELENGTH = configuration.THINKGEAR_DEFAULT_SAMPLE_WAVELENGTH

THINKGEAR_EMULATION_MAX_ESENSE_VALUE = \
	configuration.THINKGEAR_EMULATION_MAX_ESENSE_VALUE
THINKGEAR_EMULATION_MAX_EEG_POWER_VALUE = \
	configuration.THINKGEAR_EMULATION_MAX_EEG_POWER_VALUE

THINKGEAR_ATTENTION_MULTIPLIER = configuration.THINKGEAR_ATTENTION_MULTIPLIER
THINKGEAR_MEDITATION_MULTIPLIER = configuration.THINKGEAR_MEDITATION_MULTIPLIER

THINKGEAR_EEG_POWER_MULTIPLIERS = configuration.THINKGEAR_EEG_POWER_MULTIPLIERS

DEFAULT_AUTHORIZATION_MESSAGE = \
	{"isAuthorized": True}
		# Tells the client whether the server has authorized
		# access to the user's headset data. The value is
		# either true or false.

DEFAULT_SIGNAL_LEVEL_MESSAGE = \
	{"poorSignalLevel": 0}
		# A quantifier of the quality of the brainwave signal.
		# This is an integer value that is generally in the
		# range of 0 to 200, with 0 indicating a
		# good signal and 200 indicating an off-head state.

DEFAULT_EEG_POWER_MESSAGE = \
	{"eegPower": { \
		'delta': 0, \
		'theta': 0, \
		'lowAlpha': 0, \
		'highAlpha': 0, \
		'lowBeta': 0, \
		'highBeta': 0, \
		'lowGamma': 0, \
		'highGamma': 0, \
		}, \
	} # A container for the EEG powers. These may
	  # be either integer or floating-point values.
	  # Maximum values are undocumented but assumed to be 65535

DEFAULT_ESENSE_MESSAGE = \
	{"eSense": { \
		'attention': 0, \
		'meditation': 0, \
		}, \
	} # A container for the eSense™ attributes.
	  # These are integer values between 0 and 100,
	  # where 0 is perceived as a lack of that attribute
	  # and 100 is an excess of that attribute.

DEFAULT_BLINK_MESSAGE = {"blinkStrength": 255}
	# The strength of a detected blink. This is
	# an integer in the range of 0-255.

DEFAULT_RAWEEG_MESSAGE = {"rawEeg": 255}
	# The raw data reading off the forehead sensor.
	# This may be either an integer or a floating-point value.

DEFAULT_PACKET = {}
DEFAULT_PACKET.update(DEFAULT_EEG_POWER_MESSAGE)
DEFAULT_PACKET.update(DEFAULT_SIGNAL_LEVEL_MESSAGE)
DEFAULT_PACKET.update(DEFAULT_ESENSE_MESSAGE)

DEFAULT_RESPONSE_MESSAGE = DEFAULT_SIGNAL_LEVEL_MESSAGE

### CLASS MODULE ###

class ThinkgearServer(QtCore.QThread):
	
	def __init__(self, log, \
		          server_interface=SERVER_INTERFACE, \
		          server_port=SERVER_PORT, \
		          device_address=THINKGEAR_DEVICE_SERIAL_PORT, \
		          device_id=THINKGEAR_DEVICE_ID, \
		          device_model=None, \
		          emulate_headset_data=ENABLE_SIMULATE_HEADSET_DATA, \
		          DEBUG=DEBUG, \
		          parent=None):
		
		QtCore.QThread.__init__(self,parent)
		
		self.log = log
		self.DEBUG = DEBUG
		self.parent = parent
		
		self.server_interface = server_interface
		self.server_port = server_port
		self.device_address = device_address
		self.device_id = device_id
		self.device_model = device_model
		self.emulate_headset_data = emulate_headset_data
		
		self.message_frequency_timer = MESSAGE_FREQUENCY_TIMER
		self.blink_frequency_timer = BLINK_FREQUENCY_TIMER
		
		self.connection_timestamp = time.time()
		self.blink_timestamp = time.time()
		
		self.connections = []
		self.packet_queue = []
		
		self.serial_device = None
		self.protocol = None
		
		self.connect(self, \
		             QtCore.SIGNAL("sendPacket()"), \
		             self.sendPacketQueue)
		
		self.configureEEG()
		
		self.configureNetwork()
		
		
		if (self.emulate_headset_data):
			self.emulationTimer = QtCore.QTimer()
			QtCore.QObject.connect(self.emulationTimer, \
				                    QtCore.SIGNAL("timeout()"), \
				                    self.emulationEvent)
			self.emulationTimer.start(MESSAGE_FREQUENCY_TIMER)
	
	
	##################################################################
	
	def configureEEG(self):
		
		if not self.emulate_headset_data:
			
			self.serial_device = \
				serial_interface.SerialDevice( \
					self.log, \
					device_address=self.device_address, \
					DEBUG=self.DEBUG, \
					parent=self)
			
			self.serial_device.start()
		
		else:
			self.serial_device = None
		
		
		self.protocol = \
			serial_interface.ProtocolHandler( \
				self.log, \
				self.serial_device, \
				device_id=self.device_id, \
				device_model=self.device_model, \
				DEBUG=self.DEBUG, \
				parent=self)
		
		self.protocol.start()
	
	
	##################################################################
	
	def emulationEvent(self):
		
		self.updateStatus()
		
		if COMMUNICATION_MODE == 'Emit Signal':
			self.emitSendPacketSignal()
		else:
			self.sendPacketQueue()
	
	
	##################################################################
	
	def configureNetwork(self):
	
		#self.blockSize = 0
		self.socket = QtNetwork.QTcpServer()
		self.socket.name = 'ThinkGear Server'
		
		if self.DEBUG:
			print "<---- [%s] Initializing server on %s:%i" % \
			   (self.socket.name, self.server_interface, self.server_port)
		
		
		if ((self.server_interface == '') or \
			 (self.server_interface == '*')):
			address=QtNetwork.QHostAddress.Any
		else:
			#address=self.server_interface
			address=QtNetwork.QHostAddress(self.server_interface)
		
		
		result = self.socket.listen(address, self.server_port)
		
		
		if not result:
			try:
				QtGui.QMessageBox.information( \
				self.parent, \
				self.socket.name, \
				"Unable to start the server on %s:%i" % \
				(self.server_interface, self.server_port))
			except:
				pass
			
			if self.DEBUG:
				print "ERROR [%s] Unable to start the server:" % self.socket.name,
				print self.socket.errorString()
			
			#self.parent.stopThinkGearConnectServer()
			#self.parent.pushButtonThinkGearConnect.nextCheckState()
			#self.parent.pushButtonThinkGearConnect.toggle()
			#self.parent.pushButtonThinkGearConnect.test.emit(QtCore.SIGNAL("clicked()"))
			
			self.socket.close()
			return
		
		
		self.socket.newConnection.connect(self.processConnection)
		#self.socket.error.connect(self.displayError)
	
	
	##################################################################
	
	def deleteDisconnected(self):
		
		connection_index = 0
		
		for connection in self.connections:
			
			try:
			
				if ((connection.state() != QtNetwork.QAbstractSocket.ConnectingState) and \
					(connection.state() != QtNetwork.QAbstractSocket.ConnectedState)):
					
					if self.DEBUG:
						print "- - [%s] Deleting disconnected socket" % self.socket.name
					
					connection.deleteLater()
					# Delete references to disconnected sockets
					del (self.connections[connection_index])
			
			except:
				# Delete references to sockets throwing exceptions
				del (self.connections[connection_index])
			
			connection_index += 1
	
	
	##################################################################
	
	def processConnection(self):
		
		clientConnection = self.socket.nextPendingConnection()
		clientConnection.disconnected.connect(self.deleteDisconnected)
		
		self.connections.append(clientConnection)
		
		self.clientConnection = clientConnection
		
		# the next connected client to enter the readyRead state
		# will be processed first
		clientConnection.readyRead.connect(self.processClientConnection)
	
	
	##################################################################
	
	def processClientConnection(self):
		
		clientConnection = self.clientConnection
		
		socket_buffer = clientConnection.readAll()
		
		for packet in socket_buffer.split(DELIMITER):
			
			data_to_process = None
			
			if packet != '':
				
				try:
					data_to_process = json.loads(packet.data())
				
				except Exception, e:
					
					# Special socket handling for Flash applications
					if (packet == FLASH_POLICY_FILE_REQUEST):
						
						if self.DEBUG:
							print "--> [%s] Flash policy file requested" % self.socket.name
						
						data_to_process = packet.data()
					
					
					else:
						
						if self.DEBUG:
							print "--> [ThinkGear Emulator] Partial data received (or error:",
							print e
							print ")."
							
							print "packet data:",
							print packet.data()
				
				
				else:
					
					if self.DEBUG:
						print "--> [%s] Received:" % self.socket.name,
						print data_to_process
				
				
				if (data_to_process != None):
					
					response = self.processData(data_to_process)
					
					if (response != None):
						
						self.sendResponse(clientConnection, response)
	
	
	##################################################################
	
	def sendResponse(self, connection, response, disconnect_after_sending=False):
		
		# Special socket handling for Flash applications
		if (response == FLASH_SOCKET_POLICY_FILE):
			data = response
		else:
			data = json.dumps(response)
			data = data + DELIMITER
		
		if connection.waitForConnected(CLIENT_NO_REPLY_WAIT):
			
			if self.DEBUG > 1:
				print "<-- [%s] Sending:" % self.socket.name,
				print data
			
			connection.write(data)
			connection.waitForBytesWritten(CLIENT_NO_REPLY_WAIT)
			
			if disconnect_after_sending:
				connection.disconnectFromHost()
	
	
	##################################################################
	
	def emitSendPacketSignal(self):
		
		self.emit(QtCore.SIGNAL("sendPacket()"))
	
	
	##################################################################
	
	def sendPacketQueue(self):
		
		#if self.DEBUG:
			#print "sendPacketQueue called"
		
		if self.connections != []:
			
			while (len(self.packet_queue) > 0):
				
				packet = self.packet_queue[0]
				del self.packet_queue[0]

				if packet.has_key("rawEeg"): return
				print packet
				
				for connection in self.connections:
					
					if connection.state() == QtNetwork.QAbstractSocket.ConnectedState:
						
						self.sendResponse(connection, packet)
		
		
		#if COMMUNICATION_MODE != 'Emit Signal' and (self.parent != None):
			#self.parent.processPacketThinkGear(self.protocol.data_packet)
	
	
	##################################################################
	
	def processData(self, data):
		
		response = None
		
		# Special socket handling for Flash applications
		if (data == FLASH_POLICY_FILE_REQUEST):
			
			response = FLASH_SOCKET_POLICY_FILE
			
			#self.packet_queue.insert(0, FLASH_SOCKET_POLICY_FILE)
		
		
		elif (type(data) == type({}) and \
		      data.has_key('appName') and \
		      data.has_key('appKey')):
			authorized = self.authorizeClient(data)
			
			response = {}
			response['isAuthorized'] = authorized
			
			#self.packet_queue.insert(0, response)
		
		
		return(response)
	
	
	##################################################################
	
	def validateChecksum(self, checksum):
		
		'''The key used by the client application to identify 
itself. This must be 40 hexadecimal characters, ideally generated
using an SHA-1 digest. The appKey is an identifier that is unique
to each application, rather than each instance of an application.
It is used by the server to bypass the authorization process if a
user had previously authorized the requesting client. To reduce
the chance of overlap with the appKey of other applications, 
the appKey should be generated using an SHA-1 digest.'''
		
		is_valid = True
		
		hexadecimal_characters = '0123456789abcdef'
		
		if len(checksum) != 40:
			is_valid = False
		else:
			for character in checksum:
				if character not in hexadecimal_characters:
					is_valid = False
		
		return(is_valid)
	
	
	##################################################################
	
	def authorizeClient(self, data):
	
		'''The client must initiate an authorization request
and the server must authorize the client before the
server will start transmitting any headset data.'''
		
		is_authorized = self.validateChecksum(data['appKey'])
		
		# A human-readable name identifying the client
		# application. This can be a maximum of 255 characters.
		
		if len(data['appName']) > 255:
			is_authorized = False
		
		
		return(is_authorized)
	
	
	##################################################################
	
	def calculateWavePoint(self, x, max_height=100, wave_length=10):
		
		# start at 0, increase to max value at half of one
		# wavelength, decrease to 0 by end of wavelength
		y = ( (max_height/2) * \
		      math.sin ((x-1) * ( math.pi / (wave_length / 2)))) + \
		      (max_height/2)
		
		# start at max value, decrease to 0 at half of one
		# wavelegnth, increase to max by end of wavelength
		#y = ( (max_height/2) * \
		      #math.cos (x * ( math.pi / (wave_length / 2)))) + \
		      #(max_height/2)
		
		
		return(y)
	
	
	##################################################################
	
	def simulateHeadsetData(self):
		
		response = DEFAULT_PACKET
		
		response['timestamp'] = time.time()
		
		time_value = self.connection_timestamp - time.time()
		
		for key in response.keys():
			
			if key == 'poorSignalLevel':
				pass
			
			elif key == 'eSense':
				plot = self.calculateWavePoint( \
					time_value, \
					max_height=100, \
					wave_length=DEFAULT_SAMPLE_WAVELENGTH)
				
				for each in response[key].keys():
					
					if ((each == 'attention') and \
						 (THINKGEAR_ATTENTION_MULTIPLIER != None)):
						value = plot * \
						   THINKGEAR_ATTENTION_MULTIPLIER
					
					elif ((each == 'meditation') and \
						   (THINKGEAR_MEDITATION_MULTIPLIER != None)):
						value = plot * \
						   THINKGEAR_MEDITATION_MULTIPLIER
					
					if value < 0:
						value = 0
					elif value > 100:
						value = 100
					
					response[key][each] = int(value)
			
			
			elif key == 'eegPower':
				plot = self.calculateWavePoint( \
					time_value, \
					max_height=65535, \
					wave_length=DEFAULT_SAMPLE_WAVELENGTH)
				
				for each in response[key].keys():
					if ((THINKGEAR_EEG_POWER_MULTIPLIERS != None) and \
						 (each in THINKGEAR_EEG_POWER_MULTIPLIERS.keys())):
						value = THINKGEAR_EEG_POWER_MULTIPLIERS[each] * plot
					else:
						value = plot
					response[key][each] = int(value)
		
		
		return(response)
	
	
	##################################################################
	
	def processPacketThinkGear(self, packet):
		
		if self.DEBUG > 2:
			print packet
		
		if (packet != {}):
			self.packet_queue.append(packet)
			
			if COMMUNICATION_MODE == 'Emit Signal':
				self.emitSendPacketSignal()
			
			else:
				self.sendPacketQueue()
				
				#if (self.parent != None):
					#self.parent.processPacketThinkGear(self.protocol.data_packet)
	
	
	##################################################################
	
	def updateStatus(self):
		
		# Craft a simulated data packet
		packet = self.simulateHeadsetData()
		
		self.packet_queue.append(packet)
		
		if (self.parent != None):
			self.parent.processPacketThinkGear(packet)
		
		# Include simulated blinks at desired frequency
		if ((self.blink_frequency_timer != None) and \
				(self.blink_frequency_timer > 0) and \
				(time.time() - self.blink_timestamp > \
				self.blink_frequency_timer)):
			
			self.blink_timestamp = time.time()
			
			packet = DEFAULT_BLINK_MESSAGE
			
			packet['timestamp'] = self.blink_timestamp
			
			self.packet_queue.append(packet)
	
	
	##################################################################
	
	def run(self):
		
		if self.DEBUG:
			print "<---- [%s] Main thread running" % self.socket.name
		
		self.exec_()
	
		
	##################################################################
	
	def exitThread(self, callThreadQuit=True):
		
		if (self.emulate_headset_data):
			try:
				self.emulationTimer.stop()
			except Exception, e:
				if self.DEBUG:
					print "ERROR: Exception when stopping emulation timer:",
					print e
		
		# Calling exitThread() on protocol first seems to occassionally 
		# create the following error:
		# RuntimeError: Internal C++ object (PySide.QtNetwork.QTcpSocket) already deleted.
		# Segmentation fault
		# ...when program is closed without pressing "Stop" button for EEG
		#if self.protocol != None:
			#self.protocol.exitThread()
		
		# Call disconnect block in protocol first due to above error
		self.protocol.disconnectHardware()
		
		if self.serial_device != None:
			self.serial_device.exitThread()
		
		if self.protocol != None:
			self.protocol.exitThread()
		
		self.socket.close()
		
		if callThreadQuit:
			QtCore.QThread.quit(self)
		
		if self.parent == None:
			sys.exit()
	
	
	##################################################################
	
	def resetDevice(self):
		
		if self.serial_device != None:
			self.serial_device.exitThread()
		
		if self.protocol != None:
			self.protocol.exitThread()
		
		self.configureEEG()

