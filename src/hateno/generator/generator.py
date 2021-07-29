#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import shutil
import stat
from string import Template

from .errors import *
from ..folder import Folder
from ..simulation import Simulation
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

		self._forloop_regex_compiled = None

		self._variables = None

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
	def _forloop_regex(self):
		'''
		Regex for detecting a `for` loop.

		Returns
		-------
		regex : re.Pattern
			The `for` loop regex.
		'''

		if self._forloop_regex_compiled is None:
			self._forloop_regex_compiled = re.compile('^[ \t]*#{3} FOR (?P<varname>[A-Z0-9_]+) FROM (?P<from>\$?[A-Z0-9_]+) TO (?P<to>\$?[A-Z0-9_]+)$.+?^(?P<content>.+?)^[ \t]*#{3}$.+?^', flags = re.MULTILINE | re.DOTALL)

		return self._forloop_regex_compiled

	@property
	def variables(self):
		'''
		Get the latest generated variables.

		Returns
		-------
		variables : dict
			The variables generated for the latest script.
		'''

		return self._variables

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
		self._variables = None

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

		with open(filename, 'w') as f:
			f.write('\n'.join(self.command_lines) + '\n')

	def _loadConfig(self, config_name, basedir):
		'''
		Load the config and set the variables.

		Parameters
		----------
		config_name : str
			Name of the config to load.

		basedir : str
			Base directory to use in the paths.
		'''

		self._config = self._folder.config('generator', config_name)

		self._variables = {
			key.upper(): value
			for key, value in self._config.items()
		}

		self._variables['N_JOB'] = min(self._variables['N_JOB'], len(self._simulations_to_generate))

		self._variables['HATENO'] = self._folder.config('folder', config_name)['hateno']

		self._variables['BASEDIR'] = basedir

		self._variables['COMMAND_LINES_FILENAME'] = os.path.join(basedir, 'command_lines.txt')
		self._variables['JOB_DIRECTORY'] = os.path.join(basedir, self._variables['JOB_DIRECTORY'])
		self._variables['LOG_FILENAME'] = os.path.join(basedir, self._variables['LOG_FILENAME'])

		for skeleton_filename in self._folder.skeletons(self._config['skeletons']):
			skeleton = os.path.basename(skeleton_filename)
			varname = skeleton.upper().replace('.', '_')
			self._variables[f'FILE_{varname}'] = os.path.join(basedir, skeleton)

	def _replaceVariables(self, s):
		'''
		Parse a string to replace the possible variables.

		Parameters
		----------
		s : str
			The string to parse.

		Returns
		-------
		parsed : str
			The parsed string.
		'''

		return Template(s).safe_substitute(**self._variables)

	def _replaceForLoop(self, match):
		'''
		Replace the a `for` loop of a skeleton.
		To be called by `re.sub()`.

		Parameters
		----------
		match : re.Match
			Match object from the `for` loop regex.

		Returns
		-------
		loop_content : str
			The loop replaced.
		'''

		loop_from = int(self._replaceVariables(match.group('from')))
		loop_to = int(self._replaceVariables(match.group('to')))

		return ''.join([
			self._replaceVariables(match.group('content'))
			for k in range(loop_from, loop_to + 1)
		])

	def _generateScript(self, skeleton_filename, script_filename):
		'''
		Generate a script from a skeleton.

		Parameters
		----------
		skeleton_filename : str
			Path to the skeleton.

		script_filename : str
			Path to the script to write.
		'''

		with open(skeleton_filename, 'r') as f:
			skeleton = f.read()

		script_content = self._forloop_regex.sub(self._replaceForLoop, skeleton)
		script_content = self._replaceVariables(script_content)

		with open(script_filename, 'w') as f:
			f.write(script_content)

		os.chmod(script_filename, os.stat(script_filename).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

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
		GeneratorEmptyListError
			The list of simulations to generate is empty.
		'''

		if not(self._simulations_to_generate):
			raise GeneratorEmptyListError()

		self._createDestinationFolder(dest_folder, empty_dest = empty_dest)
		self._loadConfig(config_name, basedir or dest_folder)

		self._exportCommandLines(os.path.join(dest_folder, 'command_lines.txt'))

		for skeleton_filename in self._folder.skeletons(self._config['skeletons']):
			self._generateScript(skeleton_filename, os.path.join(dest_folder, os.path.basename(skeleton_filename)))
