#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import shutil
import stat
from string import Template

from ..errors import *
from ..folder.folder import Folder
from ..simulation.simulation import Simulation
from ..utils import jsonfiles

class Generator():
	'''
	Generate the scripts to create some simulations.

	Parameters
	----------
	folder : Folder|str
		The folder to manage. Either a `Folder` instance or the path to the folder (used to create a `Folder` instance).
	'''

	def __init__(self, folder):
		self._folder = folder if type(folder) is Folder else Folder(folder)

		self._simulations_to_generate = []

		self._exec_regex_compiled = None

	@property
	def folder(self):
		'''
		Return the `Folder` instance.

		Returns
		-------
		folder : Folder
			The instance used by the generator.
		'''

		return self._folder

	@property
	def _exec_regex(self):
		'''
		Regex to position of exec commands.

		Returns
		-------
		regex : re.Pattern
			The exec regex.
		'''

		if self._exec_regex_compiled is None:
			self._exec_regex_compiled = re.compile('^[ \t]*#{3} BEGIN_EXEC #{3}$.+?^(?P<content>.+?)^[ \t]*#{3} END_EXEC #{3}$.+?^', flags = re.MULTILINE | re.DOTALL)

		return self._exec_regex_compiled

	def add(self, simulation):
		'''
		Add a simulation to generate.

		Parameters
		----------
		simulation : list|dict|Simulation
			The simulation(s) to add.
		'''

		if type(simulation) is list:
			for s in simulation:
				self.add(s)

		else:
			self._simulations_to_generate.append(Simulation.ensureType(simulation, self._folder))

	def clear(self):
		'''
		Clear the list of simulations to generate.
		'''

		self._simulations_to_generate.clear()

	@property
	def command_lines(self):
		'''
		Get the list of the command lines corresponding to the set of simulations.

		Returns
		-------
		command_lines : list
			The list of command lines.
		'''

		return [simulation.command_line for simulation in self._simulations_to_generate]

	def _createDestinationFolder(self, dest_folder, *, empty_dest = False):
		'''
		Create the folder where the scripts will be stored.

		Parameters
		----------
		dest_folder : str
			Destination folder where scripts should be stored.

		empty_dest : boolean
			If `True` and if the destination folder already exists, empty it before generating the scripts. If `False` the existence of the folder raises an error.

		Raises
		------
		DestinationFolderExistsError
			The destination folder already exists.
		'''

		if os.path.isdir(dest_folder):
			if empty_dest:
				for entry in [os.path.join(dest_folder, e) for e in os.listdir(dest_folder)]:
					(shutil.rmtree if os.path.isdir(entry) else os.unlink)(entry)

			else:
				raise DestinationFolderExistsError()

		else:
			os.makedirs(dest_folder)

	def _exportCommandLines(self, filename):
		'''
		Export the command lines to a JSON file.

		Parameters
		----------
		filename : str
			Name of the file to create.
		'''

		jsonfiles.write(self.command_lines, filename)

	def _replaceExecBlock(self, match):
		'''
		Replace the exec block of a skeleton with the exec commands.
		To be called by `re.sub()`.

		Parameters
		----------
		match : re.Match
			Match object from the exec regex.

		Returns
		-------
		exec_commands : str
			The exec commands.
		'''

		return ''.join([
			Template(match.group('content')).safe_substitute(LOG_FILENAME = self._config['log_filename'].replace('%k', str(k)))
			for k in range(0, min(self._config['n_exec'], len(self._simulations_to_generate)))
		])

	def generate(self, dest_folder, config_name = None, *, empty_dest = False, basedir = None):
		'''
		Generate the scripts to launch the simulations.

		Parameters
		----------
		dest_folder : str
			Destination folder where scripts should be stored.

		config_name : str
			Name of the config to use.

		empty_dest : boolean
			If `True` and if the destination folder already exists, empty it before generating the scripts. If `False` the existence of the folder raises an error.

		basedir : str
			Path to the "final" directory from which the scripts will be executed.

		Raises
		------
		EmptyListError
			The list of simulations to generate is empty.

		Returns
		-------
		script_path, log_path : tuple
			Remote paths of the generated script and the log file.
		'''

		if not(self._simulations_to_generate):
			raise EmptyListError()

		self._createDestinationFolder(dest_folder, empty_dest = empty_dest)

		self._exportCommandLines(os.path.join(dest_folder, 'command_lines.json'))

		self._config = self._folder.config('generator', config_name)
		skeleton_filename = self._folder.configFilepath(self._config['skeleton_filename'], config_name)

		with open(skeleton_filename, 'r') as f:
			skeleton = f.read()

		script_content = self._exec_regex.sub(self._replaceExecBlock, skeleton)

		variables = {
			key.upper(): value
			for key, value in self._config.items()
		}

		basedir = basedir or dest_folder
		variables['COMMAND_LINES_FILENAME'] = os.path.join(basedir, 'command_lines.json')
		variables['LOG_FILENAME'] = os.path.join(basedir, variables['LOG_FILENAME'])

		script_content = Template(script_content).safe_substitute(**variables)

		script_path = os.path.join(dest_folder, self._config['launch_filename'])
		with open(script_path, 'w') as f:
			f.write(script_content)

		os.chmod(script_path, os.stat(script_path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

		return (os.path.join(basedir, self._config['launch_filename']), variables['LOG_FILENAME'])
