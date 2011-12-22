# -*- coding: utf-8 -*-

# Copyright Puzzlebox Productions, LLC (2010-2011)
#
# This code is released under the GNU Pulic License (GPL) version 2
# For more information please refer to http://www.gnu.org/copyleft/gpl.html

__changelog__ = """\
Last Update: 2011.12.05
"""

import os

#import Puzzlebox.Synapse.Configuration as configuration
import Configuration as configuration

if configuration.ENABLE_PYSIDE:
	try:
		import PySide as PyQt4
		from PySide import QtCore, QtGui
	except:
		print "ERROR: Exception importing PySide:",
		print e
		configuration.ENABLE_PYSIDE = False
	else:
		print "INFO: [Synapse:Interface_Plot] Using PySide module"
		os.environ["QT_API"] = "pyside"
		import matplotlib
		matplotlib.use("Qt4Agg")

if not configuration.ENABLE_PYSIDE:
	print "INFO: [Synapse:Interface_Plot] Using PyQt4 module"
	from PyQt4 import QtCore, QtGui


### IMPORTS ###
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from numpy import arange, sin, pi


### GLOBALS ###

DEBUG = configuration.DEBUG
INTERFACE_RAW_EEG_UPDATE_FREQUENCY = 512


#####################################################################

class matplotlibCanvas(FigureCanvas):
	
	"""Ultimately, this is a QWidget (as well as a FigureCanvasAgg, etc.)."""
	
	def __init__(self, parent=None, width=8, height=4, dpi=100, title=None):
		
		fig = Figure(figsize=(width, height), dpi=dpi)
		self.axes_top = fig.add_subplot(211)
		self.axes_bottom = fig.add_subplot(212)
		# We want the axes cleared every time plot() is called
		self.axes_top.hold(False)
		self.axes_bottom.hold(False)
		
		if title != None:
			fig.suptitle(title, fontsize=12)
		
		FigureCanvas.__init__(self, fig)
		self.setParent(parent)
		
		FigureCanvas.setSizePolicy(self,
											QtGui.QSizePolicy.Expanding,
											QtGui.QSizePolicy.Expanding)
		FigureCanvas.updateGeometry(self)


#####################################################################
#####################################################################

class rawEEGMatplotlibCanvas(matplotlibCanvas):
	
	def __init__(self,  *args, **kwargs):
		
		matplotlibCanvas.__init__(self, *args, **kwargs)
		
		self.DEBUG=DEBUG
		
		#timer = QtCore.QTimer(self)
		#QtCore.QObject.connect(timer, QtCore.SIGNAL("timeout()"), self.update_figure)
		#timer.start(256)
		
		self.update_top_frequency = \
		   INTERFACE_RAW_EEG_UPDATE_FREQUENCY
		self.update_bottom_frequency = \
		   INTERFACE_RAW_EEG_UPDATE_FREQUENCY / 2
		
		self.values_top = []
		self.values_bottom = []
		
		self.axes_top.set_xbound(0, self.update_top_frequency)
		self.axes_top.set_ybound(-2048, 2047)
		
		self.axes_bottom.set_xbound(0, self.update_bottom_frequency)
		self.axes_bottom.set_ybound(-512, 512)
		
		self.axes_top.grid(True)
		self.axes_bottom.grid(True)
		
		self.axes_top.text(self.update_top_frequency + 24, \
		                   0, \
		                   '1.0 seconds', \
		                   rotation='vertical', \
		                   verticalalignment='center')
		
		self.axes_bottom.text(self.update_bottom_frequency + 12, \
		                   0, \
		                   '0.5 seconds', \
		                   rotation='vertical', \
		                   verticalalignment='center')
		
		self.axes_top.set_autoscale_on(False)
		self.axes_bottom.set_autoscale_on(False)
	
	
	##################################################################
	
	def update_figure(self, value):
		
		self.values_top.append(value)
		self.values_bottom.append(value)
		
		if len(self.values_top) == self.update_top_frequency:
			
			self.axes_top.plot(range(self.update_top_frequency), \
			               self.values_top, \
			               'b-', \
			               scalex=False, \
			               scaley=False)
			
			#self.axes_top.set_ylabel('%i Hz' % self.update_top_frequency)
			self.axes_top.grid(True)
			
			self.axes_top.text(self.update_top_frequency + 24, \
			                   0, \
			                   '1.0 seconds', \
			                   rotation='vertical', \
			                   verticalalignment='center')
			
			self.draw()
			
			self.values_top = []
		
		
		if len(self.values_bottom) == self.update_bottom_frequency:
			
			self.axes_bottom.plot(range(self.update_bottom_frequency), \
			               self.values_bottom, \
			               'r-', \
			               scalex=False, \
			               scaley=False)
			
			#self.axes_bottom.set_ylabel('%i Hz' % self.update_bottom_frequency)
			self.axes_bottom.grid(True)
			
			self.axes_bottom.text(self.update_bottom_frequency + 12, \
			                   0, \
			                   '0.5 seconds', \
			                   rotation='vertical', \
			                   verticalalignment='center')
			
			self.draw()
			
			self.values_bottom = []


#####################################################################
#####################################################################

class chartEEGMatplotlibCanvas(matplotlibCanvas):
	
	def __init__(self,  *args, **kwargs):
		
		matplotlibCanvas.__init__(self, *args, **kwargs)
		
		self.DEBUG=DEBUG
		
		self.graph_length = 30
		
		self.values_eeg_bands = {}
		
		for key in configuration.THINKGEAR_EEG_POWER_BAND_ORDER:
			self.values_eeg_bands[key] = []
			for x in range(self.graph_length):
				self.values_eeg_bands[key].append(0)
		
		
		self.values_esense = {'attention': [], \
		                      'meditation': []}
		
		for key in self.values_esense.keys():
			for x in range(self.graph_length):
				self.values_esense[key].append(0)
		
		
		self.axes_top.set_xbound(self.graph_length, 0)
		self.axes_top.set_ybound(0, 100)
		
		self.axes_bottom.set_xbound(self.graph_length, 0)
		self.axes_bottom.set_ybound(0, 100)
		
		self.axes_top.grid(True)
		self.axes_bottom.grid(True)
		
		self.axes_top.text(self.graph_length + 1, \
		                   50, \
		                   'Frequency Bands', \
		                   rotation='vertical', \
		                   verticalalignment='center')
		
		self.axes_bottom.text(self.graph_length + 1, \
		                   50, \
		                   'eSense Values', \
		                   rotation='vertical', \
		                   verticalalignment='center')
		
		self.axes_top.set_autoscale_on(False)
		self.axes_bottom.set_autoscale_on(False)
	
	
	##################################################################
	
	def update_values(self, index, values):
		
		if (index == 'eegPower'):
			
			for key in values.keys():
				self.values_eeg_bands[key].append(values[key])
				self.values_eeg_bands[key] = \
					self.values_eeg_bands[key][1:]		
		
		
		elif (index == 'eSense'):
			
			for key in values.keys():
				
				self.values_esense[key].append(values[key])
				self.values_esense[key] = \
					self.values_esense[key][1:]
	
	
	##################################################################
	
	def update_figure(self, index, values):
		
		if (index == 'eegPower'):
			
			label_values = self.axes_top.plot(range(self.graph_length), \
			                   #self.values_eeg_bands['delta'], \
			                   #configuration.INTERFACE_CHART_STYLES['delta'], \
			                   #self.values_eeg_bands['theta'], \
			                   #configuration.INTERFACE_CHART_STYLES['theta'], \
			                   self.values_eeg_bands['lowAlpha'], \
			                   configuration.INTERFACE_CHART_STYLES['lowAlpha'], \
			                   self.values_eeg_bands['highAlpha'], \
			                   configuration.INTERFACE_CHART_STYLES['highAlpha'], \
			                   self.values_eeg_bands['lowBeta'], \
			                   configuration.INTERFACE_CHART_STYLES['lowBeta'], \
			                   self.values_eeg_bands['highBeta'], \
			                   configuration.INTERFACE_CHART_STYLES['highBeta'], \
			                   #self.values_eeg_bands['lowGamma'], \
			                   #configuration.INTERFACE_CHART_STYLES['lowGamma'], \
			                   #self.values_eeg_bands['highGamma'], \
			                   #configuration.INTERFACE_CHART_STYLES['highGamma'], \
			                   scalex=False, \
			                   scaley=True)
			
			self.axes_top.grid(True)
			
			self.axes_top.text(self.graph_length + 1, \
			                   50, \
			                   '                            Frequency Bands', \
			                   rotation='vertical', \
			                   verticalalignment='center')
			
			self.axes_top.legend( \
			   (label_values[0], label_values[1], label_values[2], label_values[3]), \
			   ('LowAlpha', 'HighAlpha', 'LowBeta', 'HighBeta'), \
			   loc='center left')
			
			self.draw()
		
		
		elif (index == 'eSense'):
			
			label_values = self.axes_bottom.plot(range(self.graph_length), \
			                      self.values_esense['attention'], \
			                      configuration.INTERFACE_CHART_STYLES['attention'], \
			                      self.values_esense['meditation'], \
			                      configuration.INTERFACE_CHART_STYLES['meditation'], \
			                      scalex=False, \
			                      scaley=False)
			
			
			self.axes_bottom.grid(True)
			
			self.axes_bottom.text(self.graph_length + 1, \
			                      50, \
			                      'eSense Values', \
			                      rotation='vertical', \
			                      verticalalignment='center')
			
			self.axes_bottom.legend( \
			   (label_values[0], label_values[1]), \
			   ('Attention', 'Meditation'), \
			   loc='lower left')
			
			self.draw()

