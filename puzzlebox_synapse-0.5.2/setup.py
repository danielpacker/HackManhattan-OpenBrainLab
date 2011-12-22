#!/usr/bin/env python
#
# Puzzlebox - ThinkGear Emulator - Py2Exe Distutils
#
# Copyright Puzzlebox Productions, LLC (2010-2011)
#
# This code is released under the GNU Pulic License (GPL) version 2
# For more information please refer to http://www.gnu.org/copyleft/gpl.html
#
# Last Update: 2011.12.07
#
#####################################################################

from distutils.core import setup
import os, sys
import glob

if (sys.platform == 'win32'):
	import py2exe
	import shutil
	import matplotlib

#####################################################################
# Main
#####################################################################

if __name__ != '__main__':
	
	sys.exit()


if (sys.platform == 'win32'):
	
	# Remove the build folder, a bit slower but ensures that build contains the latest
	shutil.rmtree("build", ignore_errors=True)
	
	options={"py2exe": { \
	            "includes": [ \
	               #"sip", #"PyQt4._qt", \
	               "PySide", \
	               "numpy", "pylab", \
	               "matplotlib", \
	               "matplotlib.backends", \
	               "matplotlib.backends.backend_qt4agg", \
	               "matplotlib.figure", \
	               "matplotlib.numerix.fft", \
	               "matplotlib.numerix.linear_algebra", \
	               "matplotlib.numerix.random_array", \
	               "matplotlib.backends.backend_tkagg"], \
	            "excludes": [ \
	               "bluetooth", "tcl", \
	               '_gtkagg', '_tkagg', '_agg2', \
	               '_cairo', '_cocoaagg', \
	               '_fltkagg', '_gtk', '_gtkcairo'], \
	            "dll_excludes": [ \
	               'tcl84.dll', 'tk84.dll' \
	               'libgdk-win32-2.0-0.dll',
	               'libgobject-2.0-0.dll', \
                       'MSVCP90.dll', \
                       ], \
	            #"packages": ["pytz"], \
	            "compressed": 2, \
	            "optimize": 2, \
	            "bundle_files": 2, \
	            "dist_dir": "dist", \
	            "xref": False, \
	            "skip_archive": False, \
	         }
	}
	
	data_files=[("", \
	               ["puzzlebox_synapse_configuration.ini"]),
	            ("images", \
	               ["images/puzzlebox.ico", \
	                "images/puzzlebox_logo.png"]),
	]
	
	# Add the mpl mpl-data folder and rc file
	data_files += matplotlib.get_py2exe_datafiles()
	
	matplotlib.use('Qt4Agg') # overrule configuration


else:
	options={}
	
	data_files=[("/etc/puzzlebox_synapse", \
	               ["puzzlebox_synapse_configuration.ini"]),
	            ("/usr/share/puzzlebox_synapse/images", \
	               ["images/puzzlebox.ico", \
	                "images/puzzlebox_logo.png"]),
	            ("/usr/share/applications", \
	               ["puzzlebox_synapse.desktop"]),
	           ]


setup(
	name='puzzlebox_synapse',
	version='0.5.2',
	description='Puzzlebox Synapse provides a GUI and socket-server interface to commercially available EEG headsets',
	author='Steve Castellotti',
	author_email='sc@puzzlebox.info',
	url='http://brainstorms.puzzlebox.info',
	py_modules=['Puzzlebox', \
	            'Puzzlebox.Synapse', \
	            'Puzzlebox.Synapse.Protocol', \
	            'Puzzlebox.Synapse.Server', \
	            'Puzzlebox.Synapse.Client', \
	            'Puzzlebox.Synapse.Interface', \
	            'Puzzlebox.Synapse.Interface_Design', \
	            'Puzzlebox.Synapse.Interface_Plot', \
	            'Puzzlebox.Synapse.Configuration', \
	            'synapse-protocol', \
	            'synapse-server', \
	            'synapse-client', \
	            'synapse-gui'], \
	console=["synapse-client.py", \
	         "synapse-server.py", \
	         "synapse-protocol.py"
	],
	options=options, \
	zipfile = r'lib\library.zip',
	data_files=data_files, \
	windows=[ \
		{
		 "script": "synapse-gui.py",
		 "icon_resources": [(1, \
		 os.path.join("images", "puzzlebox.ico"))]
		},
	],
	classifiers=[ \
		'Development Status :: 4 - Beta',
		'Intended Audience :: End Users/Desktop',
		'Programming Language :: Python',
		'Operating System :: OS Independent',
		'License :: OSI Approved :: GNU General Public License (GPL)',
		'Topic :: Scientific/Engineering :: Human Machine Interfaces',
	],
)
