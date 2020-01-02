#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import errno
import inspect

import shutil
import copy
import tarfile

import functools
import re

from utils import jsonfiles, string
from manager.errors import *
import manager.checkers as checkers

class Manager():
	'''
	Manage a simulations folder: add, delete, extract or update simulations, based on their settings.
	Initialize the manager with the folder to manage: load the settings and the current list of simulations.

	Parameters
	----------
	folder : str
		The folder to manage. Must contain a settings file.

	Raises
	------
	FileNotFoundError
		No `.simulations.conf` file found in folder.
	'''

	def __init__(self, folder):
		self._folder = folder
		self._settings_file = os.path.join(self._folder, '.simulations.conf')

		if not(os.path.isfile(self._settings_file)):
			raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), self._settings_file)

		self._settings = jsonfiles.read(self._settings_file)

		self._simulations_list_file = os.path.join(self._folder, '.simulations.list')
		self._simulations_list = {}

		if os.path.isfile(self._simulations_list_file):
			self._simulations_list = jsonfiles.read(self._simulations_list_file)

		self.generateRegexes()
		self.initCheckers()

	def saveSimulationsList(self):
		'''
		Save the list of simulations.
		'''

		jsonfiles.write(self._simulations_list, self._simulations_list_file)

	def generateRegexes(self):
		'''
		Compile in advance the regular expressions we use.
		'''

		# Used to parse a name of a file/folder with the value of a setting
		self._settings_regex = re.compile(r'\{setting:([^}]+)\}')

		# Used to determine if a function is a checker
		self._checkers_regex = re.compile(r'^(file|folder|global)_([A-Za-z0-9_]+)$')

	def initCheckers(self):
		'''
		Load the default checkers.
		'''

		self._checkers = {cat: {} for cat in ['file', 'folder', 'global']}
		self.loadCheckersFromModule(checkers)

	def loadCheckersFromModule(self, module):
		'''
		Load all checkers in a given module.

		Parameters
		----------
		module : Module
			Module (already loaded) where are defined the checkers.
		'''

		for function in inspect.getmembers(module, inspect.isfunction):
			checker_match = self._checkers_regex.match(function[0])

			if checker_match:
				self.setChecker(checker_match.group(1), checker_match.group(2), function[1])

	def setChecker(self, category, checker_name, checker):
		'''
		Set (add or replace) a checker.

		Parameters
		----------
		category : str
			Category of the checker (`file`, `folder` or `global`).

		checker_name : str
			Name of checker.

		checker : function
			Checker to register (callback function).
		'''

		if not(category in self._checkers):
			raise CheckersCategoryNotFoundError(category)

		self._checkers[category][checker_name] = checker

	def removeChecker(self, category, checker_name):
		'''
		Remove a checker.

		Parameters
		----------
		category : str
			Category of the checker (`file`, `folder` or `global`).

		checker_name : str
			Name of checker.
		'''

		if not(category in self._checkers):
			raise CheckersCategoryNotFoundError(category)

		if not(checker_name in self._checkers[category]):
			raise CheckerNotFoundError(checker_name, category)

		del self._checkers[category][checker_name]

	def generateSettings(self, settings):
		'''
		Generate the full set of settings for a simulation.

		Parameters
		----------
		settings : dict
			Values of some settings for the simulation.

		Returns
		-------
		full_settings : dict
			The full set of settings, with default values if needed.
		'''

		full_settings = []
		for settings_set in self._settings['settings']:
			settings_pairs = {s['name']: s['default'] for s in settings_set['settings']}
			values_sets = [s['settings'] for s in settings if s['set'] == settings_set['set']]

			sets_to_add = []
			for values_set in values_sets:
				pairs = copy.deepcopy(settings_pairs)
				pairs.update(values_set)
				sets_to_add.append(pairs)

			if not(sets_to_add) and settings_set['required']:
				sets_to_add.append(settings_pairs)

			full_settings += sets_to_add

		return full_settings

	def checkIntegrity(self, simulation, full_settings):
		'''
		Check the integrity of a simulation.

		Parameters
		----------
		simulation : dict
			The simulation to check.

		full_settings : list
			The full set of settings of this simulation.

		Returns
		-------
		success : bool
			`True` if the integrity check is successful, `False` otherwise.
		'''

		# Parse a name (of file or folder), potentially with some settings values
		# This function explicitely doesn't take into account multiple settings
		settings_values = functools.reduce(lambda a, b: {**a, **b}, full_settings)

		def parseName(name):
			for setting_match in self._settings_regex.finditer(name):
				try:
					name = name.replace(setting_match.group(0), str(settings_values[setting_match.group(1)]))
				except KeyError:
					pass

			return name

		tree = {}

		for output_entry in ['files', 'folders']:
			tree[output_entry] = []
			checkers_cat = output_entry[:-1]

			if output_entry in self._settings['output']:
				for output in self._settings['output'][output_entry]:
					parsed_name = parseName(output['name'])
					tree[output_entry].append(parsed_name)

					if 'checks' in output:
						for checker_name in output['checks']:
							if not(checker_name in self._checkers[checkers_cat]):
								raise CheckerNotFoundError(checker_name, checkers_cat)

							if not(self._checkers[checkers_cat][checker_name](simulation, full_settings, parsed_name)):
								return False

		if 'checks' in self._settings['output']:
			for checker_name in self._settings['output']['checks']:
				if not(checker_name in self._checkers['global']):
					raise CheckerNotFoundError(checker_name, 'global')

				if not(self._checkers['global'][checker_name](simulation, full_settings, tree)):
					return False

		return True

	def compress(self, folder, simulation_name):
		'''
		Create an archive to store a simulation.

		Parameters
		----------
		folder : str
			Folder to compress.

		simulation_name : str
			Name to use for the archive.
		'''

		with tarfile.open(os.path.join(self._folder, f'{simulation_name}.tar.bz2'), 'w:bz2') as tar:
			tar.add(folder, arcname = simulation_name)

		shutil.rmtree(folder)

	def uncompress(self, simulation_name, folder):
		'''
		Extract a simulation from an archive.

		Parameters
		----------
		simulation_name : str
			Name of the archive to extract.

		folder : str
			Folder into which the files must go.
		'''

		with tarfile.open(os.path.join(self._folder, f'{simulation_name}.tar.bz2'), 'r:bz2') as tar:
			tar.extractall(path = self._folder)

		shutil.move(os.path.join(self._folder, simulation_name), folder)

	def add(self, simulation, save_list = True):
		'''
		Add a simulation to the list.

		Parameters
		----------
		simulation : dict
			The simulation to add.

		save_list : boolean
			`True` to save the simulations list, `False` otherwise.

		Raises
		------
		SimulationFolderNotFoundError
			The folder indicated in the simulation does not exist.

		SimulationIntegrityCheckFailedError
			At least one integrity check failed.
		'''

		if not(os.path.isdir(simulation['folder'])):
			raise SimulationFolderNotFoundError(simulation['folder'])

		full_settings = self.generateSettings(simulation['settings'])
		settings_str = string.fromObject(full_settings)
		simulation_name = string.hash(settings_str)

		if not(self.checkIntegrity(simulation, full_settings)):
			raise SimulationIntegrityCheckFailedError(simulation['folder'])

		self.compress(simulation['folder'], simulation_name)

		self._simulations_list[simulation_name] = settings_str

		if save_list:
			self.saveSimulationsList()

	def delete(self, simulation, save_list = True):
		'''
		Delete a simulation.

		Parameters
		----------
		simulation : dict
			The simulation to delete.

		save_list : boolean
			`True` to save the simulations list, `False` otherwise.

		Raises
		------
		SimulationNotFoundError
			The simulation does not exist in the list.
		'''

		full_settings = self.generateSettings(simulation['settings'])
		simulation_name = string.hash(string.fromObject(full_settings))

		if not(simulation_name in self._simulations_list):
			raise SimulationNotFoundError(simulation_name)

		os.unlink(os.path.join(self._folder, f'{simulation_name}.tar.bz2'))
		del self._simulations_list[simulation_name]

		if save_list:
			self.saveSimulationsList()

	def extract(self, simulation):
		'''
		Extract a simulation.

		Parameters
		----------
		simulation : dict
			The simulation to extract.

		Raises
		------
		SimulationNotFoundError
			The simulation does not exist in the list.

		SimulationFolderAlreadyExistError
			The destination of extraction already exists.
		'''

		full_settings = self.generateSettings(simulation['settings'])
		simulation_name = string.hash(string.fromObject(full_settings))

		if not(simulation_name in self._simulations_list):
			raise SimulationNotFoundError(simulation_name)

		if os.path.exists(simulation['folder']):
			raise SimulationFolderAlreadyExistError(simulation['folder'])

		destination_path = os.path.dirname(os.path.normpath(simulation['folder']))
		if destination_path and not(os.path.isdir(destination_path)):
			os.makedirs(destination_path)

		self.uncompress(simulation_name, simulation['folder'])

	def batchAction(self, simulations, callback, args = {}, save_list = True):
		'''
		Apply a callback function to each simulation of a given list.

		Parameters
		----------
		simulations : list
			List of simulations, each being a dictionary.

		callback : function
			Function to call. The simulation will be passed as the first parameter.

		args : dict
			Additional named arguments to pass to the callback.

		save_list : boolean
			`True` to save the simulations list once the loop is over, `False` to not save it.

		Returns
		-------
		errors : list
			List of simulations which raised an error.
		'''

		errors = []

		for simulation in simulations:
			try:
				callback(simulation, **args)

			except Error:
				errors.append(simulation)

		if save_list:
			self.saveSimulationsList()

		return errors

	def batchAdd(self, simulations):
		'''
		Add multiple simulations to the list.

		Parameters
		----------
		simulations : list
			List of simulations, each being a dictionary.

		Returns
		-------
		errors : list
			List of simulations that were not added because they raised an error.
		'''

		return self.batchAction(simulations, self.add, {'save_list': False}, save_list = True)

	def batchDelete(self, simulations):
		'''
		Delete multiple simulations.

		Parameters
		----------
		simulations : list
			List of simulations, each being a dictionary.

		Returns
		-------
		errors : list
			List of simulations that were not deleted because they raised an error.
		'''

		return self.batchAction(simulations, self.delete, {'save_list': False}, save_list = True)

	def batchExtract(self, simulations):
		'''
		Extract multiple simulations.

		Parameters
		----------
		simulations : list
			List of simulations, each being a dictionary.
		'''

		return self.batchAction(simulations, self.extract, save_list = False)
