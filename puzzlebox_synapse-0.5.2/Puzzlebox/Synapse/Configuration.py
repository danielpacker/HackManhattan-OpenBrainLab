#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Puzzlebox Productions, LLC (2010-2011)
#
# This code is released under the GNU Pulic License (GPL) version 2
# For more information please refer to http://www.gnu.org/copyleft/gpl.html

__changelog__ = """\
Last Update: 2011.12.04
"""

import os, sys

#####################################################################
# General configuration
#####################################################################

DEBUG = 1

CONFIGURATION_FILE_PATH = 'puzzlebox_synapse_configuration.ini'

if (sys.platform != 'win32'):
	if not os.path.exists(CONFIGURATION_FILE_PATH):
		CONFIGURATION_FILE_PATH = \
			os.path.join('/etc/puzzlebox_synapse', CONFIGURATION_FILE_PATH)

ENABLE_PYSIDE = True
ENABLE_HCITOOL = False

INTERFACE_CHART_STYLES = { \
	'attention': 'r-', \
	'meditation': 'b-', \
	'delta': 'g-', \
	'theta': 'y-', \
	'lowAlpha': 'c-', \
	'highAlpha': 'b-', \
	'lowBeta': 'r-', \
	'highBeta': 'm-', \
	'lowGamma': 'k-', \
	'highGamma': 'k-', \
}

INTERFACE_TAB_POSITION = 'North'

#The following color abbreviations are supported:
#character 	color
#‘b’ 	blue
#‘g’ 	green
#‘r’ 	red
#‘c’ 	cyan
#‘m’ 	magenta
#‘y’ 	yellow
#‘k’ 	black
#‘w’ 	white

#The following format string characters are accepted to control the line style or marker:
#character 	description
#'-' 	solid line style
#'--' 	dashed line style
#'-.' 	dash-dot line style
#':' 	dotted line style
#'.' 	point marker
#',' 	pixel marker
#'o' 	circle marker
#'v' 	triangle_down marker
#'^' 	triangle_up marker
#'<' 	triangle_left marker
#'>' 	triangle_right marker
#'1' 	tri_down marker
#'2' 	tri_up marker
#'3' 	tri_left marker
#'4' 	tri_right marker
#'s' 	square marker
#'p' 	pentagon marker
#'*' 	star marker
#'h' 	hexagon1 marker
#'H' 	hexagon2 marker
#'+' 	plus marker
#'x' 	x marker
#'D' 	diamond marker
#'d' 	thin_diamond marker
#'|' 	vline marker
#'_' 	hline marker


#####################################################################
# Network addresses
#####################################################################

THINKGEAR_SERVER_INTERFACE = '' # listen on all of server's network interfaces
#THINKGEAR_SERVER_HOST = '127.0.0.1'
THINKGEAR_SERVER_HOST = '*'
THINKGEAR_SERVER_PORT = 13854


#####################################################################
# ThinkGear Device configuration
#####################################################################

DEFAULT_THINKGEAR_DEVICE_SERIAL_PORT_WINDOWS = 'COM2'
DEFAULT_THINKGEAR_DEVICE_SERIAL_PORT_LINUX = '/dev/rfcomm0'

if (sys.platform == 'win32'):
	THINKGEAR_DEVICE_SERIAL_PORT = DEFAULT_THINKGEAR_DEVICE_SERIAL_PORT_WINDOWS
else:
	THINKGEAR_DEVICE_SERIAL_PORT = DEFAULT_THINKGEAR_DEVICE_SERIAL_PORT_LINUX

# Use Bluetooth MAC address for Linux
THINKGEAR_DEVICE_BLUETOOTH_ADDRESS = ''
# THINKGEAR_DEVICE_BLUETOOTH_ADDRESS = '00:13:EF:xx:xx:xx' # Linux example

THINKGEAR_DEVICE_ID = None

#####################################################################
# Server configuration
#####################################################################

CLIENT_NO_REPLY_WAIT = 5 # how many seconds before considering a component dead


#####################################################################
# ThinkGear Connect configuration
#####################################################################

THINKGEAR_DELIMITER = '\r'

THINKGEAR_CONFIGURATION_PARAMETERS = {"enableRawOutput": False, "format": "Json"}

ENABLE_THINKGEAR_AUTHORIZATION = False

THINKGEAR_AUTHORIZATION_REQUEST = { \
        "appName": "Puzzlebox Brainstorms", \
        "appKey": "2e285d7bd5565c0ea73e7e265c73f0691d932408"
        }

THINKGEAR_EEG_POWER_BAND_ORDER = ['delta', \
                                  'theta', \
                                  'lowAlpha', \
                                  'highAlpha', \
                                  'lowBeta', \
                                  'highBeta', \
                                  'lowGamma', \
                                  'highGamma']

THINKGEAR_EMULATION_MAX_ESENSE_VALUE = 100
THINKGEAR_EMULATION_MAX_EEG_POWER_VALUE = 16384

THINKGEAR_ATTENTION_MULTIPLIER = 1.0
THINKGEAR_MEDITATION_MULTIPLIER = 1.0

THINKGEAR_EEG_POWER_MULTIPLIERS = { \
	'delta': 1.0, \
	'theta': 1.0, \
	'lowAlpha': 1.0, \
	'highAlpha': 1.0, \
	'lowBeta': 1.0, \
	'highBeta': 1.0, \
	'lowGamma': 1.0, \
	'highGamma': 1.0, \
}


#####################################################################
# ThinkGear Connect Server Emulator configuration
#####################################################################

THINKGEAR_ENABLE_SIMULATE_HEADSET_DATA = True

THINKGEAR_BLINK_FREQUENCY_TIMER = 6 # blink every 6 seconds
                                    # (6 seconds is listed by Wikipedia
                                    # as being the average number of times
                                    # an adult blinks in a laboratory setting)

THINKGEAR_DEFAULT_SAMPLE_WAVELENGTH = 30 # number of seconds from 0 to max
                                         # and back to 0 for any given
                                         # detection value below


#####################################################################
# Flash socket policy handling
#####################################################################

FLASH_POLICY_FILE_REQUEST = \
        '<policy-file-request/>%c' % 0 # NULL byte termination
FLASH_SOCKET_POLICY_FILE = '''<?xml version="1.0"?>
<!DOCTYPE cross-domain-policy SYSTEM "http://www.macromedia.com/xml/dtds/cross-domain-policy.dtd">
<cross-domain-policy>
   <site-control permitted-cross-domain-policies="all" />
   <allow-access-from domain="*" to-ports="%i" />
</cross-domain-policy>%c''' % (THINKGEAR_SERVER_PORT, 0)


#####################################################################
# Configuration File Parser
#####################################################################

if os.path.exists(CONFIGURATION_FILE_PATH):
	
	file = open(CONFIGURATION_FILE_PATH, 'r')
	
	for line in file.readlines():
		line = line.strip()
		if len(line) == 0:
			continue
		if line[0] == '#':
			continue
		if line.find('=') == -1:
			continue
		if (line == "THINKGEAR_DEVICE_SERIAL_PORT = ''"):
			# use operating system default if device not set manually
			continue
		try:
			exec line
		except:
			if DEBUG:
				print "Error recognizing configuration option:",
				print line

