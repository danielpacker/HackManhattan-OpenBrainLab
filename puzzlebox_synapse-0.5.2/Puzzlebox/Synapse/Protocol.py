# -*- coding: utf-8 -*-

# Copyright Puzzlebox Productions, LLC (2010-2011)
#
# This code is released under the GNU Pulic License (GPL) version 2
# For more information please refer to http://www.gnu.org/copyleft/gpl.html

# Old Classes:
#	puzzlebox_synapse_protocol_thinkgear = ProtocolHandler
#	puzzlebox_synapse_protocol_thinkgear_serial_device = SerialDevice

__changelog__ = """\
Last Update: 2011.12.04
"""

__doc__ = """\
Puzzlebox.Synapse.Protocol

usage:
  from Puzzlebox.Synapse import Protocol

Modules:
  Protocol.ProtocolHandler()
  Protocol.SerialDevice()

SPEC:

 CODE Definitions Table
 Single-Byte CODEs
 Extended             (Byte)
 Code Level   [CODE] [LENGTH] Data Value Meaning
 ----------   ------ -------- ------------------
           0    0x02        - POOR_SIGNAL Quality (0-255)
           0    0x04        - ATTENTION eSense (0 to 100)
           0    0x05        - MEDITATION eSense (0 to 100)
           0    0x16        - Blink Strength. (0-255) Sent only
                              when Blink event occurs.
 Multi-Byte CODEs
 Extended             (Byte)
 Code Level   [CODE] [LENGTH] Data Value Meaning
 ----------   ------ -------- ------------------
           0    0x80        2 RAW Wave Value: a single big-endian
                                16-bit two's-compliment signed value
                                (high-order byte followed by
                                low-order byte) (-32768 to 32767)
           0    0x83       24 ASIC_EEG_POWER: eight big-endian
                                3-byte unsigned integer values
                                representing delta, theta, low-alpha
                                high-alpha, low-beta, high-beta,
                                low-gamma, and mid-gamma EEG band
                                power values
         Any    0x55        - NEVER USED (reserved for [EXCODE])
         Any    0xAA        - NEVER USED (reserved for [SYNC])

MindWave Connection CODEs
[CODE] [DATA]    Data Value Meaning
------ --------- ------------
 0xC0  0xAB 0xCD Connect to headset with ID "ABCD"
 0xC1          - Disconnect
 0xC2          - Connect to first available headset

MindWave Response CODEs
Extended             (Byte)
Code Level   [CODE] [LENGTH] Data Value Meaning
----------   ------ -------- ------------------
         0    0xD0        3 Headset Connect Success
         0    0xD1        2 Headset Not Found
         0    0xD2        3 Headset Disconnected
         0    0xD3        0 Request Denied
         0    0xD4        1 Standby/Scan Mode

Linux Bluetooth serial protocol profile example:
    rfcomm connect rfcomm0 00:13:EF:00:1B:FE 3

TODO:
 - needs to handle:
   serial.serialutil.SerialException: 
   could not open port /dev/rfcomm0: 
   [Errno 16] Device or resource busy: '/dev/rfcomm0'

"""

### IMPORTS ###
import sys, time
import signal
import serial

if (sys.platform != 'win32'):
	import bluetooth


import Configuration as configuration

if configuration.ENABLE_PYSIDE:
	try:
		import PySide as PyQt4
		from PySide import QtCore
	except Exception, e:
		print "ERROR: Exception importing PySide:",
		print e
		configuration.ENABLE_PYSIDE = False
	else:
		print "INFO: [Synapse:Protocol] Using PySide module"

if not configuration.ENABLE_PYSIDE:
	print "INFO: [Synapse:Protocol] Using PyQt4 module"
	from PyQt4 import QtCore


#try:
	#import PySide as PyQt4
	#from PySide import QtCore
#except:
	#print "Using PyQt4 module"
	#from PyQt4 import QtCore
#else:
	#print "Using PySide module"

#import Configuration as configuration

### GLOBALS ###

DEBUG = configuration.DEBUG

THINKGEAR_DEVICE_SERIAL_PORT = configuration.THINKGEAR_DEVICE_SERIAL_PORT
#THINKGEAR_DEVICE_BLUETOOTH_ADDRESS = \
	#configuration.THINKGEAR_DEVICE_BLUETOOTH_ADDRESS

#DEFAULT_SERIAL_BAUDRATE = 57600
DEFAULT_SERIAL_BAUDRATE = 115200

#THINKGEAR_DEVICE_BLUETOOTH_ADDRESS = '00:13:EF:00:1B:FE'
THINKGEAR_DEVICE_BLUETOOTH_CHANNEL = 3

THINKGEAR_DEVICE_AUTOCONNECT_INTERVAL = 4 # seconds between attempting
                                          # to send auto-connect packets
THINKGEAR_DEVICE_ID = configuration.THINKGEAR_DEVICE_ID
#THINKGEAR_DEFAULT_DEVICE_ID = '\x7d\x68'
#THINKGEAR_DEFAULT_DEVICE_ID = '\xe4\x68'

PROTOCOL_SYNC = '\xAA'
PROTOCOL_EXCODE = '\x55'

EEG_POWER_BAND_ORDER = configuration.THINKGEAR_EEG_POWER_BAND_ORDER

DEVICE_BUFFER_CHECK_TIMER = 60 * 1000 # Check buffer size once every minute
DEVICE_READ_BUFFER_CHECK_TIMER = 10 * 1000 # Check buffer size once x seconds
DEVICE_BUFFER_MAX_SIZE = 180 # Reset buffer if it grow this large
                             # as this would indicate the processing
                             # algorithm is not keeping up with the device
                             # According to protocol specification,
                             # "...a complete, valid Packet is ... a maximum
                             # of 173 bytes long (possible if the Data Payload
                             # is the maximum 169 bytes long)."
                             # Therefore we reset if our buffer has grown longer
                             # than the maximum packet length as this means
                             # the processing algorthim is at least one full
                             # packet behind.

DEBUG_BYTE_COUNT = 819200
DEBUG_PACKET_COUNT = 1024

### CLASSES ###

class ProtocolHandler(QtCore.QThread):
	
	def __init__(self, log, \
			       serial_device, \
			       device_id=THINKGEAR_DEVICE_ID, \
			       device_model=None, \
			       DEBUG=DEBUG, \
			       parent=None):
		
		QtCore.QThread.__init__(self,parent)
		
		self.log = log
		self.DEBUG = DEBUG
		self.parent = parent
		
		self.device_id = device_id
		self.device_model = device_model
		
		self.device = None
		self.buffer = ''
		self.payload_timestamp = time.time()
		
		self.device = serial_device
		self.auto_connect_timestamp = time.time()
		
		self.data_packet = {}
		self.data_packet['eegPower'] = {}
		self.data_packet['eSense'] = {}
		
		self.packet_count = 0
		self.bad_packets = 0
		self.session_start_time = None
		
		self.keep_running = True
	
	
	##################################################################
	
	def communicateWithHandsfreeProfile(self):
		
		#"AT+CKPD=200" - Indicates a Bluetooth button press
		#"AT+VGM=" - Indicates a microphone volume change
		#"AT+VGS=" - Indicates a speakerphone volume change
		#"AT+BRSF=" - The Headset is asking what features are supported
		#"AT+CIND?" - The Headset is asking about the indicators that are signaled
		#"AT+CIND=?" - The Headset is asking about the test indicators
		#"AT+CMER=" - The Headset is asking which indicates are registered for updates
		#"ATA" - When an incoming call has been answered, usually a Bluetooth button press
		#"AT+CHUP" - When a call has been hung up, usually a Bluetooth button press
		#"ATD>" - The Headset is requesting the local device to perform a memory dial
		#"ATD" - The Headset is requesting to dial the number
		#"AT+BLDN" - The Headset is requesting to perform last number dialed
		#"AT+CCWA=" - The Headset has enabled call waiting
		#"AT+CLIP=" - The Headset has enabled CLI (Calling Line Identification)
		#"AT+VTS=" - The Headset is asking to send DTMF digits
		#"AT+CHLD=" - The Headset is asking to put the call on Hold
		#"AT+BVRA=" - The Headset is requesting voice recognition
		#"ATH" - Call hang-up
		
		#self.device.write('\x29')
		#self.device.write('AT+BRSF=24\r\n')
		
		buffer = ''
		
		while True:
			reply = self.device.read()
			
			if (len(reply) != 0):
				if DEBUG > 1:
					print reply
				buffer += reply
			
			if buffer == "AT+BRSF=24\r":
				print "--> Received:",
				print buffer
				response = '\r\nOK\r\n'
				print "<-- Sending:",
				print response.replace('\r\n', '')
				self.device.write(response)
				buffer = ''
			
			elif buffer == 'AT+CIND=?\r':
				print "--> Received:",
				print buffer
				# first field indicates that we have cellular service [0-1]
				# second field indicates that we're in a call (0 for false) [0-1]
				# third field indicates the current call setup (0 for idle) [0-3]
				response = '\r\n+CIND: 1,0,0\r\n'
				print "<-- Sending:",
				print response.replace('\r\n', '')
				self.device.write(response)
				response = '\r\nOK\r\n'
				print "<-- Sending:",
				print response.replace('\r\n', '')
				self.device.write(response)
				buffer = ''
			
			elif buffer == 'AT+CMER=3, 0, 0, 1\r':
				print "--> Received:",
				print buffer
				response = '\r\nOK\r\n'
				print "<-- Sending:",
				print response.replace('\r\n', '')
				self.device.write(response)
				response = '\r\n+CIEV:2,1\r\n'
				print "<-- Sending:",
				print response.replace('\r\n', '')
				self.device.write(response)
				response = '\r\n+CIEV:3,0\r\n'
				print "<-- Sending:",
				print response.replace('\r\n', '')
				self.device.write(response)
				buffer = ''
			
			elif buffer == 'AT+VGS=15\r':
				print "--> Received:",
				print buffer
				response = '\r\nOK\r\n'
				print "<-- Sending:",
				print response.replace('\r\n', '')
				self.device.write(response)
				buffer = ''
			
			elif buffer == 'AT+VGM=08\r':
				print "--> Received:",
				print buffer
				response = '\r\nOK\r\n'
				print "<-- Sending:",
				print response.replace('\r\n', '')
				self.device.write(response)
				buffer = ''
				
				
				self.exitThread()
				#self.keep_running = False
				#self.device.stop()
				#QtCore.QThread.quit(self)
				#sys.exit()
	
	
	##################################################################
	
	def hexStringEndianSwap(self, theString):
		"""Rearranges character-couples in a little endian hex string to
		convert it into a big endian hex string and vice-versa. i.e. 'A3F2'
		is converted to 'F2A3'
		
		@param theString: The string to swap character-couples in
		@return: A hex string with swapped character-couples. -1 on error.
		
		Taken from http://bytes.com/topic/python/answers/652429-convert-little-endian-hex-string-number#post2588668"""
		
		# We can't swap character couples in a string that has an odd number
		# of characters.
		if len(theString)%2 != 0:
			return -1
		
		# Swap the couples
		swapList = []
		for i in range(0, len(theString), 2):
			swapList.insert(0, theString[i:i+2])
		
		# Combine everything into one string. Don't use a delimeter.
		return ''.join(swapList)
	
	
	##################################################################
	
	def processRawEEGValue(self, data_values):
		
		'''SPEC: This Data Value consists of two bytes, and represents a 
		single raw wave sample. Its value is a signed 16-bit integer that 
		ranges from -32768 to 32767. The first byte of the Value represents 
		the high-order bits of the twos-compliment value, while the second 
		byte represents the low-order bits. To reconstruct the full raw 
		wave value, simply shift the rst byte left by 8 bits, and 
		bitwise-or with the second byte:
		
		short raw = (Value[0]<<8) | Value[1];
		
		where Value[0] is the high-order byte, and Value[1] is the 
		low-order byte. In systems or languages where bit operations are 
		inconvenient, the following arithmetic operations may be 
		substituted instead:
		
		raw = Value[0]*256 + Value[1];
		if( raw >= 32768 ) raw = raw - 65536;
		
		where raw is of any signed number type in the language that can 
		represent all the numbers from -32768 to 32767.
		
		Each ThinkGear model reports its raw wave information in only 
		certain areas of the full -32768 to 32767 range. For example, 
		MindSet reports raw waves that fall between approximately -2048 to 
		2047. By default, output of this Data Value is enabled, and is 
		outputed 512 times a second, or approximately once every 2ms.'''
		
		high_order = data_values[0:2]
		low_order = data_values[2:4]
		
		#high_order = high_order.encode("hex")
		high_order = int(high_order, 16)
		
		#low_order = low_order.encode("hex")
		low_order = int(low_order, 16)

		raw = high_order * 256 + low_order
		
		if (raw >= 32768):
			raw = raw - 65536
		
		
		return (raw)
	
	
	##################################################################
	
	def processAsicEegPower(self, data_values):
		
		'''SPEC: This Data Value represents the current magnitude of 8 
		commonly-recognized types of EEG (brain-waves). This Data Value 
		is output as a series of eight 3-byte unsigned integers in 
		little-endian format. 
		The eight EEG powers are output in the following order: 
		delta (0.5 - 2.75Hz), 
		theta (3.5 - 6.75Hz), 
		low-alpha (7.5 - 9.25Hz), 
		high-alpha (10 - 11.75Hz), 
		low-beta (13 - 16.75Hz), 
		high-beta (18 - 29.75Hz), 
		low-gamma (31 - 39.75Hz), and 
		mid-gamma (41 - 49.75Hz). 
		These values have no units and therefore are only meaningful compared 
		to each other and to themselves, to consider relative quantity and 
		temporal uctuations. By default, output of this Data Value is enabled, 
		and is typically output once a second.'''
		
		eegPower = {}
		
		eegPower['delta'] = data_values[0:6]
		eegPower['theta'] = data_values[6:12]
		eegPower['lowAlpha'] = data_values[12:18]
		eegPower['highAlpha'] = data_values[18:24]
		eegPower['lowBeta'] = data_values[24:30]
		eegPower['highBeta'] = data_values[30:36]
		eegPower['lowGamma'] = data_values[36:42]
		eegPower['highGamma'] = data_values[42:48]
		
		for key in eegPower.keys():
			eegPower[key] = self.hexStringEndianSwap(eegPower[key])
			#eegPower[key] = eegPower[key].encode("hex")
			eegPower[key] = int(eegPower[key], 16)
		
		
		return(eegPower)
	
	
	##################################################################
	
	def processDataRow(self, \
	                   extended_code_level, \
	                   code, \
	                   length, \
	                   data_values, \
	                   timestamp):
		
		'''CODE Definitions Table
		   Single-Byte CODEs
		   Extended             (Byte)
		   Code Level   [CODE] [LENGTH] Data Value Meaning
		   ----------   ------ -------- ------------------
		             0    0x02        - POOR_SIGNAL Quality (0-255)
		             0    0x04        - ATTENTION eSense (0 to 100)
		             0    0x05        - MEDITATION eSense (0 to 100)
		             0    0x16        - Blink Strength. (0-255) Sent only
		                                when Blink event occurs.
		   Multi-Byte CODEs
		   Extended             (Byte)
		   Code Level   [CODE] [LENGTH] Data Value Meaning
		   ----------   ------ -------- ------------------
		             0    0x80        2 RAW Wave Value: a single big-endian
		                                  16-bit two's-compliment signed value
		                                  (high-order byte followed by
		                                  low-order byte) (-32768 to 32767)
		             0    0x83       24 ASIC_EEG_POWER: eight big-endian
		                                  3-byte unsigned integer values
		                                  representing delta, theta, low-alpha
		                                  high-alpha, low-beta, high-beta,
		                                  low-gamma, and mid-gamma EEG band
		                                  power values
		           Any    0x55        - NEVER USED (reserved for [EXCODE])
		           Any    0xAA        - NEVER USED (reserved for [SYNC])
		
		   MindWave CODEs
		   Extended             (Byte)
		   Code Level   [CODE] [LENGTH] Data Value Meaning
		   ----------   ------ -------- ------------------
		             0    0xD0        3 Headset Connect Success
		             0    0xD1        2 Headset Not Found
		             0    0xD2        3 Headset Disconnected
		             0    0xD3        0 Request Denied
		             0    0xD4        1 Standby/Scan Mode'''
		
		packet_update = {}
		
		packet_update['timestamp'] = timestamp
		
		self.packet_count += 1
		
		if extended_code_level == 0:
			
			if code == '02':
				poor_signal_quality = int(data_values, 16)
				if self.DEBUG > 1:
					print # Empty line at the beginning of most packets
					print "poorSignalLevel:",
					print poor_signal_quality
				
				packet_update['poorSignalLevel'] = poor_signal_quality
			
			
			elif code == '04':
				attention = int(data_values, 16)
				if self.DEBUG > 1:
					print "attention:",
					print attention
				
				packet_update['eSense'] = {}
				packet_update['eSense']['attention'] = attention
			
			
			elif code == '05':
				meditation = int(data_values, 16)
				if self.DEBUG > 1:
					print "meditation:",
					print meditation
				
				packet_update['eSense'] = {}
				packet_update['eSense']['meditation'] = meditation
			
			
			elif code == '16':
				blink_strength = int(data_values, 16)
				if self.DEBUG > 1:
					print "blinkStrength:",
					print blink_strength
				
				packet_update['blinkStrength'] = blink_strength
			
			
			elif code == '80':
				#self.packet_count -= 1 # We don't count raw EEG packets for Interface
				raw_wave_value = data_values
				if self.DEBUG > 3:
					print "Raw EEG:",
					print raw_wave_value
				raw_eeg_value = self.processRawEEGValue(data_values)
				if self.DEBUG > 2:
					print "Raw EEG Value:",
					print raw_eeg_value
				
				packet_update['rawEeg'] = raw_eeg_value
			
			
			elif code == '83':
				asic_eeg_power = data_values
				if self.DEBUG > 2:
					print "ASIC_EEG_POWER:",
					print asic_eeg_power
				eegPower = self.processAsicEegPower(data_values)
				if self.DEBUG > 1:
					for key in EEG_POWER_BAND_ORDER:
						print "%s: %i" % (key, eegPower[key])
				
				packet_update['eegPower'] = {}
				for key in eegPower.keys():
					packet_update['eegPower'][key] = eegPower[key]
			
			
			elif code == 'd0':
				if self.DEBUG:
					print "INFO: ThinkGear Headset Connect Success"
				self.session_start_timestamp = time.time()
				self.packet_count = 0
				self.bad_packets = 0
			
			
			elif code == 'd1':
				current_time = time.time()
				if current_time - self.auto_connect_timestamp > \
					THINKGEAR_DEVICE_AUTOCONNECT_INTERVAL:
					if self.DEBUG:
						print "INFO: ThinkGear device not found. Writing auto-connect packet."
					self.auto_connect_timestamp = current_time
					self.device.device.write('\xc2')
					#self.device.device.write('\xc0\xe4\x68')
			
			
			elif code == 'd2':
				current_time = time.time()
				if current_time - self.auto_connect_timestamp > \
					THINKGEAR_DEVICE_AUTOCONNECT_INTERVAL:
					if self.DEBUG:
						print "INFO: ThinkGear device disconnected. Writing auto-connect packet."
					self.auto_connect_timestamp = current_time
					self.device.device.write('\xc2')
					#self.device.device.write('\xc0\xe4\x68')
			
			
			elif code == 'd3':
				current_time = time.time()
				if current_time - self.auto_connect_timestamp > \
					THINKGEAR_DEVICE_AUTOCONNECT_INTERVAL:
					if self.DEBUG:
						print "INFO: ThinkGear device request denied. Writing auto-connect packet."
					self.auto_connect_timestamp = current_time
					self.device.device.write('\xc2')
					#self.device.device.write('\xc0\xe4\x68')
			
			
			elif code == 'd4':
				current_time = time.time()
				if current_time - self.auto_connect_timestamp > \
					THINKGEAR_DEVICE_AUTOCONNECT_INTERVAL:
					if self.DEBUG:
						print "INFO: ThinkGear device in standby/scan mode. Writing auto-connect packet."
					self.auto_connect_timestamp = current_time
					self.device.device.write('\xc2')
					#self.device.device.write('\xc0\xe4\x68')
			
			
			else:
				self.bad_packets += 1
				if self.DEBUG:
					print "ERROR: data payload row code not matched:",
					print code
		
		
		return(packet_update)
	
	
	##################################################################
	
	def processDataPayload(self, data_payload, timestamp):
		
		'''A DataRow consists of bytes in the following format:
		([EXCODE]...) [CODE] ([VLENGTH])   [VALUE...]
		____________________ ____________ ___________
		^^^^(Value Type)^^^^ ^^(length)^^ ^^(value)^^'''
		
		
		if self.DEBUG > 3:
			print "data payload:",
			for byte in data_payload:
				print byte.encode("hex"),
			print
		
		byte_index = 0
		
		# Parse the extended_code_level, code, and length
		while (byte_index < len(data_payload)):
			extended_code_level = 0
			
			# 1. Parse and count the number of [EXCODE] (0x55)
			#    bytes that may be at the beginning of the
			#    current DataRow.
			while (data_payload[byte_index] == PROTOCOL_EXCODE):
				extended_code_level += 1
				byte_index += 1
			
			# 2. Parse the [CODE] byte for the current DataRow.
			code = data_payload[byte_index]
			byte_index += 1
			code = code.encode("hex")
			
			# 3. If [CODE] >= 0x80, parse the next byte as the 
			#    [VLENGTH] byte for the current DataRow.
			if (code > '\x7f'.encode("hex")):
				length = data_payload[byte_index]
				byte_index += 1
				length = length.encode("hex")
				length = int(length, 16)
			else:
				length = 1
			
			
			if self.DEBUG > 3:
				print "EXCODE level:",
				print extended_code_level,
				print " CODE:",
				print code,
				print " length:",
				print length
				#print type(code)
			
			data_values = ''
			value_index = 0
			
			# 4. Parse and handle the [VALUE...] byte(s) of the current 
			#    DataRow, based on the DataRow's [EXCODE] level, [CODE], 
			#    and [VLENGTH] (refer to the Code De nitions Table).
			while value_index < length:
				# Uh-oh more C mojo
				try:
					value = data_payload[(byte_index + value_index)] # & 0xFF
				except:
					if self.DEBUG:
						print "ERROR: failed to parse and handle the [VALUE...] bytes of the current DataRow"
					break
				data_values += value.encode("hex")
				value_index += 1
			
			if self.DEBUG > 3:
				print "Data Values:",
				print data_values
				print
			
			packet_update = self.processDataRow(extended_code_level, \
			                                    code, \
			                                    length, \
			                                    data_values, \
			                                    timestamp)
			
			self.updateDataPacket(packet_update)
			
			
			byte_index += length
			
			# 5. If not all bytes have been parsed from the payload[] array,
			# return to step 1. to continue parsing the next DataRow.
	
	
	##################################################################
	
	def parseStream(self):
		
		'''Each Packet begins with its Header, followed by its Data Payload, 
		and ends with the Payload's Check-sum Byte, as follows:
		[SYNC] [SYNC] [PLENGTH]      [PAYLOAD...]         [CHKSUM]
		_______________________      _____________     ____________
		^^^^^^^^(Header)^^^^^^^      ^^(Payload)^^     ^(Checksum)^'''
		
		# Loop forever, parsing one Packet per loop...
		packet_count = 0
		
		while self.keep_running:
			
			# Synchronize on [SYNC] bytes
			# Read from stream until two consecutive [SYNC] bytes are found
			byte = self.device.read()
			if (byte != PROTOCOL_SYNC):
				continue
			
			byte = self.device.read()
			if (byte != PROTOCOL_SYNC):
				continue
			
			self.payload_timestamp = time.time()
			
			# Parse [PLENGTH] byte
			
			# SPEC: [PLENGTH] byte indicates the length, in bytes, of the 
			# Packet's Data Payload [PAYLOAD...] section, and may be any value 
			# from 0 up to 169. Any higher value indicates an error 
			# (PLENGTH TOO LARGE). Be sure to note that [PLENGTH] is the length 
			# of the Packet's Data Payload, NOT of the entire Packet. 
			# The Packet's complete length will always be [PLENGTH] + 4.
			
			byte = self.device.read()
			packet_length = byte.encode("hex")
			packet_length = int(packet_length, 16)
			
			if (packet_length > 170):
				self.bad_packets += 1
				if self.DEBUG:
					print "ERROR: packet length bad"
					continue
			
			
			# Collect [PAYLOAD...] bytes
			data_payload = self.device.read(packet_length)
			
			
			# Calculate [PAYLOAD...] checksum
			
			# SPEC: The [CHKSUM] Byte must be used to verify the integrity of the
			# Packet's Data Payload. The Payload's Checksum is defined as:
			#  1. summing all the bytes of the Packet's Data Payload
			#  2. taking the lowest 8 bits of the sum
			#  3. performing the bit inverse (one's compliment inverse)
			#     on those lowest 8 bits
			
			payload_checksum = 0
			for byte in data_payload:
				value = byte.encode("hex")
				value = int(value, 16)
				payload_checksum += value
			
			
			# Take the lowest 8 bits of the calculated payload_checksum
			# and invert them. Serious C code mojo follows.
			payload_checksum &= 0xff
			payload_checksum = ~payload_checksum & 0xff
			
			
			# Parse [CKSUM] byte
			packet_checksum = self.device.read()
			packet_checksum = packet_checksum.encode("hex")
			packet_checksum = int(packet_checksum, 16)
			
			
			# Verify [CKSUM] byte against calculated [PAYLOAD...] checksum
			if packet_checksum != payload_checksum:
				self.bad_packets += 1
				if self.DEBUG > 1:
					print "ERROR: packet checksum does not match"
					print "       packet_checksum:",
					print packet_checksum
					print "       payload_checksum:",
					print payload_checksum
					
					#self.device.checkBuffer()
				
				continue
			
			
			else:
				# Since [CKSUM] is OK, parse the Data Payload
				if self.DEBUG > 3:
					print "packet checksum correct"
				
				
				self.processDataPayload(data_payload, self.payload_timestamp)
				
				
				#if self.DEBUG > 1:
					#packet_count += 1
					#if packet_count >= DEBUG_PACKET_COUNT:
						#print "max debugging count reached, disconnecting"
						#self.keep_running = False
						#self.device.stop()
						#QtCore.QThread.quit(self)
						##sys.exit()
	
	
	##################################################################
	
	def updateDataPacket(self, packet_update):
		
		if 'eSense' in packet_update.keys():
			process_packet = {'eSense': {}}
			for key in packet_update['eSense'].keys():
				self.data_packet['eSense'][key] = packet_update['eSense'][key]
				process_packet['eSense'][key] = packet_update['eSense'][key]
		
		else:
			self.data_packet.update(packet_update)
			process_packet = packet_update
		
		
		process_packet['timestamp'] = packet_update['timestamp']
		
		
		if self.DEBUG > 3:
			print self.data_packet
		
		
		if (self.parent != None):
			
			# NOTE: is it possible this call is blocking the Protocol
			#       thread from continuing to parse data?
			
			self.parent.processPacketThinkGear(process_packet)
	
	
	##################################################################
	
	def disconnectHardware(self):
		
		if self.device != None and self.device.device != None:
			if self.device_model == 'NeuroSky MindWave':
				if self.DEBUG:
					print "INFO: ThinkGear device model MindWave selected. Writing disconnect packet."
				try:
					self.device.device.write('\xc1')
				except Exception, e:
					if self.DEBUG:
						print "ERROR: failed to write disconnect packet: ",
						print e
	
	
	##################################################################
	
	def run(self):
		
		self.packet_count = 0
		self.bad_packets = 0
		self.session_start_timestamp = time.time()
		
		if self.device != None and self.device.device != None:
			if self.device_model == 'NeuroSky MindWave':
				if self.DEBUG:
					print "INFO: ThinkGear device model MindWave selected. Writing disconnect packet."
				self.device.device.write('\xc1')
				if self.DEBUG:
					print "INFO: ThinkGear device model MindWave selected. Writing auto-connect packet."
				self.device.device.write('\xc2')
			else:
				if self.device_model != None and self.DEBUG:
					print "INFO: %s device model selected" % self.device_model
			self.parseStream()
	
	
	##################################################################
	
	def exitThread(self, callThreadQuit=True):
		
		#if self.device != None and self.device.device != None:
			#if self.device_model == 'NeuroSky MindWave':
				#if self.DEBUG:
					#print "INFO: ThinkGear device model MindWave selected. Writing disconnect packet."
				#try:
					#self.device.device.write('\xc1')
				#except Exception, e:
					#if self.DEBUG:
						#print "ERROR: failed to write disconnect packet: ",
						#print e
		
		self.disconnectHardware()
		
		try:
			self.device.stop()
		except:
			pass
		
		
		if callThreadQuit:
			QtCore.QThread.quit(self)


#####################################################################
#####################################################################

class SerialDevice(QtCore.QThread):
	
	def __init__(self, log, \
			       device_address=THINKGEAR_DEVICE_SERIAL_PORT, \
			       DEBUG=DEBUG, \
			       parent=None):
		
		QtCore.QThread.__init__(self, parent)
		
		self.log = log
		self.DEBUG = DEBUG
		self.parent = parent
		
		self.device_address = device_address
		self.device = None
		self.buffer = ''
		
		if (self.device_address.count(':') == 5):
			# Device address is a Bluetooth MAC address
			if self.DEBUG:
				print "Initializing Bluetooth Device",
				print self.device_address
			self.device = self.initializeBluetoothDevice()
		else:
			# Device address is a serial port address
			if self.DEBUG:
				print "Initializing Serial Device",
				print self.device_address
			self.device = self.initializeSerialDevice()
		
		self.buffer_check_timer = QtCore.QTimer()
		QtCore.QObject.connect(self.buffer_check_timer, \
		                       QtCore.SIGNAL("timeout()"), \
		                       self.checkBuffer)
		self.buffer_check_timer.start(DEVICE_BUFFER_CHECK_TIMER)
		
		self.read_buffer_check_timer = QtCore.QTimer()
		QtCore.QObject.connect(self.read_buffer_check_timer, \
		                       QtCore.SIGNAL("timeout()"), \
		                       self.checkReadBuffer)
#		self.read_buffer_check_timer.start(DEVICE_READ_BUFFER_CHECK_TIMER)
		
		self.keep_running = True
	
	
	##################################################################
	
	def initializeBluetoothDevice(self):
		
		socket = bluetooth.BluetoothSocket( bluetooth.RFCOMM )
		
		try:
			socket.connect((self.device_address, THINKGEAR_DEVICE_BLUETOOTH_CHANNEL))
		
		except Exception, e:
			if self.DEBUG:
				print "ERROR:",
				print e
				sys.exit()
		
		
		return socket
	
	
	##################################################################
	
	def initializeSerialDevice(self):
		
		baudrate = DEFAULT_SERIAL_BAUDRATE
		bytesize = 8
		parity = 'NONE'
		stopbits = 1
		software_flow_control = 'f'
		rts_cts_flow_control = 'f'
		#timeout = 15
		timeout = 5
		
		# convert bytesize
		if (bytesize == 5):
			init_byte_size = serial.FIVEBITS
		elif (bytesize == 6):
			init_byte_size = serial.SIXBITS
		elif (bytesize == 7):
			init_byte_size = serial.SEVENBITS
		elif (bytesize == 8):
			init_byte_size = serial.EIGHTBITS
		else:
			#self.log.perror("Invalid value for %s modem byte size! Using default (8)" % modem_type)
			init_byte_size = serial.EIGHTBITS
		
		# convert parity
		if (parity == 'NONE'):
			init_parity = serial.PARITY_NONE
		elif (parity == 'EVEN'):
			init_parity = serial.PARITY_EVEN
		elif (parity == 'ODD'):
			init_parity = serial.PARITY_ODD
		else:
			#self.log.perror("Invalid value for %s modem parity! Using default (NONE)" % modem_type)
			init_parity = serial.PARITY_NONE
		
		# convert stopbits
		if (stopbits == 1):
			init_stopbits = serial.STOPBITS_ONE
		elif (stopbits == 2):
			init_stopbits = serial.STOPBITS_TWO
		else:
			#self.log.perror("Invalid value for %s modem stopbits! Using default (8)" % modem_type)
			init_byte_size = serial.STOPBITS_ONE
		
		# convert software flow control
		if (software_flow_control == 't'):
			init_software_flow_control = 1
		else:
			init_software_flow_control = 0
		
		# convert rts cts flow control
		if (rts_cts_flow_control == 't'):
			init_rts_cts_flow_control = 1
		else:
			init_rts_cts_flow_control = 0
		
		
		try:
##			device = serial.Serial(port = self.device_address, \
##				                    baudrate = baudrate, \
##				                    bytesize = init_byte_size, \
##				                    parity = init_parity, \
##				                    stopbits = init_stopbits, \
##				                    xonxoff = init_software_flow_control, \
##				                    rtscts = init_rts_cts_flow_control, \
##				                    timeout = timeout)
			
			device = serialWrapper(port = self.device_address, \
				                    baudrate = baudrate, \
				                    bytesize = init_byte_size, \
				                    parity = init_parity, \
				                    stopbits = init_stopbits, \
				                    xonxoff = init_software_flow_control, \
				                    rtscts = init_rts_cts_flow_control, \
				                    timeout = timeout)
		
		except Exception, e:
			if self.DEBUG:
				print "ERROR:",
				print e,
				print self.device_address
				#sys.exit()
				return(None)
		
		
		device.flushInput()
		#device.flushOutput()
		
		
		#if self.DEBUG:
			#print "Writing device connect packet"
		#device.write('\xc2')
		
		
		return(device)
	
	
	##################################################################
	
	def checkBuffer(self):
		
		if self.DEBUG > 1:
			print "INFO: Buffer size check:",
			print len(self.buffer),
			print "(maximum before reset is %i)" % DEVICE_BUFFER_MAX_SIZE
		
		if (DEVICE_BUFFER_MAX_SIZE <= len(self.buffer)):
			
			if self.DEBUG:
				print "ERROR: Buffer size has grown too large, resetting"
			
			self.reset()
	
	
	##################################################################
	
	def checkReadBuffer(self):
		
		if self.DEBUG > 1:
			print "INFO: Read buffer timer check"
		
		current_time = time.time()
		
		if ((self.parent != None) and \
		    (self.parent.protocol != None)):
			
			if (current_time - self.parent.protocol.payload_timestamp > \
				 DEVICE_BUFFER_CHECK_TIMER):
				
				if self.DEBUG:
					print "ERROR: Read buffer timer has expired, resetting connection"
				
			self.parent.resetDevice()
	
	
	##################################################################
	
	def reset(self):
		
		self.buffer = ''
	
	
	##################################################################
	
	def read(self, length=1):
		
		# Sleep for 2 ms if buffer is empty
		# Based on 512 Hz refresh rate of NeuroSky MindSet device
		# (1/512) * 1000 = 1.9531250
		while len(self.buffer) < length:
			try:
				QtCore.QThread.msleep(2)
			except Exception, e:
				#if self.DEBUG:
					#print "ERROR: Protocol failed to call QtCore.QThread.msleep(2) in read():",
					#print e
				pass
			
		bytes = self.buffer[:length]
		
		self.buffer = self.buffer[length:]
		
		return(bytes)
	
	
	##################################################################
	
	def stop(self):
		
		self.keep_running = False
		self.buffer_check_timer.stop()
		self.read_buffer_check_timer.stop()
		self.buffer = ''
	
	
	##################################################################
	
	def exitThread(self, callThreadQuit=True):
		
		self.stop()
		self.close()
		
		if callThreadQuit:
			QtCore.QThread.quit(self)
	
	
	##################################################################
	
	def close(self):
		
		if self.device != None:
			
			try:
				self.device.close()
			except Exception, e:
				#if self.DEBUG:
					#print "ERROR: Protocol failed to close device in close():",
					#print e
				pass
	
	
	##################################################################
	
	def run(self):
		
		if self.device == None:
			self.keep_running = False
		
		self.buffer = ''
		
		while self.keep_running:
			
			try:
				#byte = self.device.read()
				byte = self.device.recv(1)
				
				if (len(byte) != 0):
					if self.DEBUG > 2:
						print "Device read:",
						print byte
						
					self.buffer += byte
			
			except:
				if self.DEBUG:
					print "ERROR: failed to read from serial device"
				break
		
		
		self.exitThread()


#####################################################################
#####################################################################

class serialWrapper(serial.Serial):
	
	#__init__(port=None, baudrate=9600, bytesize=EIGHTBITS, parity=PARITY_NONE, stopbits=STOPBITS_ONE, timeout=None, xonxoff=False, rtscts=False, writeTimeout=None, dsrdtr=False, interCharTimeout=None)
	
	def recv(self, size=1):
		
		return(self.read(size))

