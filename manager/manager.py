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
import manager.checkers as checkers

"""
Base class for exceptions occurring in the manager.
"""

class Error(Exception):
	pass

"""
Exception raised when we try to add a simulation to the manager, but the indicated folder does not exist.
"""

class SimulationFolderNotFoundError(Error):
	"""
	Store the folder's name.

	:param str folder:
		The folder which has not been found.
	"""

	def __init__(self, folder):
		self.folder = folder

"""
Exception raised when we try to access a checkers category which does not exist.
"""

class CheckersCategoryNotFoundError(Error):
	"""
	Store the category's name.

	:param str category:
		The category which has not been found.
	"""

	def __init__(self, category):
		self.category = category

"""
Exception raised when we try to access a checker which does not exist.
"""

class CheckerNotFoundError(Error):
	"""
	Store the category and checker names.

	:param str category:
		The checker's category.

	:param str checker_name:
		The name of the checker which has not been found.
	"""

	def __init__(self, category, checker_name):
		self.category = category
		self.checker_name = checker_name

"""
Exception raised when a folder fails to pass an integrity check.
"""

class SimulationIntegrityCheckFailedError(Error):
	"""
	Store the folder's name.

	:param str folder:
		The folder which has not been found.
	"""

	def __init__(self, folder):
		self.folder = folder

"""
Exception raised when we look for a non existing simulation.
"""

class SimulationNotFoundError(Error):
	"""
	Store the simulation's name.

	:param str simulation:
		The name of the simulation which has not been found.
	"""

	def __init__(self, simulation):
		self.simulation = simulation

"""
Exception raised when the folder of a simulation already exists.
"""

class SimulationFolderAlreadyExistError(Error):
	"""
	Store the folder's name.

	:param str folder:
		The name of the folder which should not exist.
	"""

	def __init__(self, folder):
		self.folder = folder

"""
Manage a simulations folder: add, delete, extract or update simulations, based on their settings.
"""

class Manager():
	"""
	Initialize the manager with the folder to manage: load the settings and the current list of simulations.

	:param str folder:
		The folder to manage. Must contain a settings file.
	"""

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

	"""
	Save the list of simulations.
	"""

	def saveSimulationsList(self):
		jsonfiles.write(self._simulations_list, self._simulations_list_file)

	"""
	Compile in advance the regular expressions we use.
	"""

	def generateRegexes(self):
		# Used to parse a name of a file/folder with the value of a setting
		self._settings_regex = re.compile(r'\{setting:([^}]+)\}')

		# Used to determine if a function is a checker
		self._checkers_regex = re.compile(r'^(file|folder|global)_([A-Za-z0-9_]+)$')

	"""
	Load the default checkers.
	"""

	def initCheckers(self):
		self._checkers = {cat: {} for cat in ['file', 'folder', 'global']}
		self.loadCheckersFromModule(checkers)

	"""
	Load all checkers in a given module.

	:param Module module:
		Module (already loaded) where are defined the checkers.
	"""

	def loadCheckersFromModule(self, module):
		for function in inspect.getmembers(module, inspect.isfunction):
			checker_match = self._checkers_regex.match(function[0])

			if checker_match:
				self.setChecker(checker_match.group(1), checker_match.group(2), function[1])

	"""
	Set (add or replace) a checker.

	:param str category:
		Category of the checker (`file`, `folder` or `global`).

	:param str checker_name:
		Name of checker.

	:param function checker:
		Checker to register (callback function).
	"""

	def setChecker(self, category, checker_name, checker):
		if not(category in self._checkers):
			raise CheckersCategoryNotFoundError(category)

		self._checkers[category][checker_name] = checker

	"""
	Remove a checker.

	:param str category:
		Category of the checker (`file`, `folder` or `global`).

	:param str checker_name:
		Name of checker.
	"""

	def removeChecker(self, category, checker_name):
		if not(category in self._checkers):
			raise CheckersCategoryNotFoundError(category)

		if not(checker_name in self._checkers[category]):
			raise CheckerNotFoundError(checker_name, category)

		del self._checkers[category][checker_name]

	"""
	Generate the full set of settings for a simulation.

	:param dict settings:
		Values of some settings for the simulation.

	:return dict:
		The full set of settings, with default values if needed.
	"""

	def generateSettings(self, settings):
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

	"""
	Check the integrity of a simulation.

	:param dict simulation:
		The simulation to check.

	:param list full_settings:
		The full set of settings of this simulation.

	:return bool:
		`True` if the integrity check is successful, `False` otherwise.
	"""

	def checkIntegrity(self, simulation, full_settings):
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

		try:
			for output_entry in ['files', 'folders']:
				checkers_cat = output_entry[:-1]

				for output in self._settings['output'][output_entry]:
					for checker_name in output['checks']:
						if not(checker_name in self._checkers[checkers_cat]):
							raise CheckerNotFoundError(checker_name, checkers_cat)

						if not(self._checkers[checkers_cat][checker_name](simulation, full_settings, parseName(output['name']))):
							return False

		except KeyError:
			pass

		if 'checks' in self._settings['output']:
			pass

		return True

	"""
	Create an archive to store a simulation.

	:param str folder:
		Folder to compress.

	:param str simulation_name:
		Name to use for the archive.
	"""

	def compress(self, folder, simulation_name):
		with tarfile.open(os.path.join(self._folder, f'{simulation_name}.tar.bz2'), 'w:bz2') as tar:
			tar.add(folder, arcname = simulation_name)

		shutil.rmtree(folder)

	"""
	Extract a simulation from an archive.

	:param str simulation_name:
		Name of the archive to extract.

	:param str folder:
		Folder into which the files must go.
	"""

	def uncompress(self, simulation_name, folder):
		with tarfile.open(os.path.join(self._folder, f'{simulation_name}.tar.bz2'), 'r:bz2') as tar:
			tar.extractall(path = self._folder)

		shutil.move(os.path.join(self._folder, simulation_name), folder)

	"""
	Add a simulation to the list.

	:param dict simulation:
		The simulation to add.
	"""

	def add(self, simulation):
		if not(os.path.isdir(simulation['folder'])):
			raise SimulationFolderNotFoundError(simulation['folder'])

		full_settings = self.generateSettings(simulation['settings'])
		settings_str = string.fromObject(full_settings)
		simulation_name = string.hash(settings_str)

		if not(self.checkIntegrity(simulation, full_settings)):
			raise SimulationIntegrityCheckFailedError(simulation['folder'])

		self.compress(simulation['folder'], simulation_name)

		self._simulations_list[simulation_name] = settings_str
		self.saveSimulationsList()

	"""
	Delete a simulation.

	:param dict simulation:
		The simulation to delete.
	"""

	def delete(self, simulation):
		full_settings = self.generateSettings(simulation['settings'])
		simulation_name = string.hash(string.fromObject(full_settings))

		if not(simulation_name in self._simulations_list):
			raise SimulationNotFoundError(simulation_name)

		os.unlink(os.path.join(self._folder, f'{simulation_name}.tar.bz2'))
		del self._simulations_list[simulation_name]
		self.saveSimulationsList()

	"""
	Extract a simulation.

	:param dict simulation:
		The simulation to extract.
	"""

	def extract(self, simulation):
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
