#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import errno
import inspect

import shutil
import tarfile

import re

from utils import jsonfiles, string
from manager.errors import *
import manager.checkers as checkers

class Manager():
	'''
	Manage a simulations folder: add, delete, extract or update simulations, based on their settings.

	Parameters
	----------
	folder : Folder
		The folder to manage.
	'''

	def __init__(self, folder):
		self._folder = folder

		self._simulations_list_file = os.path.join(self._folder.folder, '.simulations.list')
		self._simulations_list_dict = None

		self._checkers_regex_compiled = None
		self._settings_regex_compiled = None
		self._checkers_list = None

	@property
	def _simulations_list(self):
		'''
		Return the simulations list.

		Returns
		-------
		simulations_list : dict
			A name: settings dictionary.
		'''

		if self._simulations_list_dict is None:
			try:
				self._simulations_list_dict = jsonfiles.read(self._simulations_list_file)

			except FileNotFoundError:
				self._simulations_list_dict = {}

		return self._simulations_list_dict

	def saveSimulationsList(self):
		'''
		Save the list of simulations.
		'''

		jsonfiles.write(self._simulations_list, self._simulations_list_file)

	@property
	def _checkers_regex(self):
		'''
		Regex to determine whether a function's name corresponds to a checker.

		Returns
		-------
		regex : re.Pattern
			The checkers regex.
		'''

		if self._checkers_regex_compiled is None:
			self._checkers_regex_compiled = re.compile(r'^(file|folder|global)_([A-Za-z0-9_]+)$')

		return self._checkers_regex_compiled

	@property
	def _settings_regex(self):
		'''
		Regex to parse a string using some settings.

		Returns
		-------
		regex : re.Pattern
			The settings regex.
		'''

		if self._settings_regex_compiled is None:
			self._settings_regex_compiled = re.compile(r'\{setting:([^}]+)\}')

		return self._settings_regex_compiled

	@property
	def _checkers(self):
		'''
		Get the list of available checkers.

		Returns
		-------
		checkers : dict
			Checkers, sorted by category.
		'''

		if self._checkers_list is None:
			self._checkers_list = {cat: {} for cat in ['file', 'folder', 'global']}
			self.loadCheckersFromModule(checkers)

		return self._checkers_list

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

	def checkIntegrity(self, simulation):
		'''
		Check the integrity of a simulation.

		Parameters
		----------
		simulation : Simulation
			The simulation to check.

		Returns
		-------
		success : bool
			`True` if the integrity check is successful, `False` otherwise.
		'''

		# Parse a name (of file or folder), potentially with some settings values
		def parseName(name):
			for setting_match in self._settings_regex.finditer(name):
				try:
					name = name.replace(setting_match.group(0), str(simulation.reduced_settings[setting_match.group(1)]))

				except KeyError:
					pass

			return name

		tree = {}

		for output_entry in ['files', 'folders']:
			tree[output_entry] = []
			checkers_cat = output_entry[:-1]

			if output_entry in self._folder.settings['output']:
				for output in self._folder.settings['output'][output_entry]:
					parsed_name = parseName(output['name'])
					tree[output_entry].append(parsed_name)

					if 'checks' in output:
						for checker_name in output['checks']:
							if not(checker_name in self._checkers[checkers_cat]):
								raise CheckerNotFoundError(checker_name, checkers_cat)

							if not(self._checkers[checkers_cat][checker_name](simulation, parsed_name)):
								return False

		if 'checks' in self._folder.settings['output']:
			for checker_name in self._folder.settings['output']['checks']:
				if not(checker_name in self._checkers['global']):
					raise CheckerNotFoundError(checker_name, 'global')

				if not(self._checkers['global'][checker_name](simulation, tree)):
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

		with tarfile.open(os.path.join(self._folder.folder, f'{simulation_name}.tar.bz2'), 'w:bz2') as tar:
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

		with tarfile.open(os.path.join(self._folder.folder, f'{simulation_name}.tar.bz2'), 'r:bz2') as tar:
			tar.extractall(path = self._folder.folder)

		shutil.move(os.path.join(self._folder.folder, simulation_name), folder)

	def add(self, simulation, save_list = True):
		'''
		Add a simulation to the list.

		Parameters
		----------
		simulation : Simulation
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

		settings_str = string.fromObject(simulation.settings)
		simulation_name = string.hash(settings_str)

		if not(self.checkIntegrity(simulation)):
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
		simulation : Simulation
			The simulation to delete.

		save_list : boolean
			`True` to save the simulations list, `False` otherwise.

		Raises
		------
		SimulationNotFoundError
			The simulation does not exist in the list.
		'''

		simulation_name = string.hash(string.fromObject(simulation.settings))

		if not(simulation_name in self._simulations_list):
			raise SimulationNotFoundError(simulation_name)

		os.unlink(os.path.join(self._folder.folder, f'{simulation_name}.tar.bz2'))
		del self._simulations_list[simulation_name]

		if save_list:
			self.saveSimulationsList()

	def extract(self, simulation):
		'''
		Extract a simulation.

		Parameters
		----------
		simulation : Simulation
			The simulation to extract.

		Raises
		------
		SimulationNotFoundError
			The simulation does not exist in the list.

		SimulationFolderAlreadyExistError
			The destination of extraction already exists.
		'''

		simulation_name = string.hash(string.fromObject(simulation.settings))

		if not(simulation_name in self._simulations_list):
			raise SimulationNotFoundError(simulation_name)

		if os.path.exists(simulation['folder']):
			raise SimulationFolderAlreadyExistError(simulation['folder'])

		destination_path = os.path.dirname(os.path.normpath(simulation['folder']))
		if destination_path and not(os.path.isdir(destination_path)):
			os.makedirs(destination_path)

		self.uncompress(simulation_name, simulation['folder'])

	def batchAction(self, simulations, callback, args = {}, *, save_list = True, errors_store = (), errors_pass = (Error)):
		'''
		Apply a callback function to each simulation of a given list.

		Parameters
		----------
		simulations : list
			List of simulations.

		callback : function
			Function to call. The simulation will be passed as the first parameter.

		args : dict
			Additional named arguments to pass to the callback.

		save_list : boolean
			`True` to save the simulations list once the loop is over, `False` to not save it.

		errors_store : tuple
			List of exceptions that, when raised, lead to the storage of the involved simulation.

		errors_pass : tuple
			List of exceptions that, when raised, do nothing.

		Returns
		-------
		errors : list
			List of simulations which raised an error.
		'''

		errors = []

		for simulation in simulations:
			try:
				callback(simulation, **args)

			except errors_store:
				errors.append(simulation)

			except errors_pass:
				pass

		if save_list:
			self.saveSimulationsList()

		return errors

	def batchAdd(self, simulations):
		'''
		Add multiple simulations to the list.

		Parameters
		----------
		simulations : list
			List of simulations.

		Returns
		-------
		errors : list
			List of simulations that were not added because they raised an error.
		'''

		return self.batchAction(simulations, self.add, {'save_list': False}, save_list = True, errors_store = (SimulationFolderNotFoundError, SimulationIntegrityCheckFailedError))

	def batchDelete(self, simulations):
		'''
		Delete multiple simulations.

		Parameters
		----------
		simulations : list
			List of simulations.

		Returns
		-------
		errors : list
			List of simulations that were not deleted because they raised an error.
		'''

		return self.batchAction(simulations, self.delete, {'save_list': False}, save_list = True, errors_store = (SimulationNotFoundError))

	def batchExtract(self, simulations, *, ignore_existing = True):
		'''
		Extract multiple simulations.

		Parameters
		----------
		simulations : list
			List of simulations.

		ignore_existing : boolean
			Ignore simulations for which the destination folder already exists.

		Returns
		-------
		errors : list
			List of simulations that were not extracted because they raised an error.
		'''

		if ignore_existing:
			errors_store = (SimulationNotFoundError,)
			errors_pass = (SimulationFolderAlreadyExistError,)

		else:
			errors_store = (SimulationNotFoundError, SimulationFolderAlreadyExistError)
			errors_pass = ()

		return self.batchAction(simulations, self.extract, save_list = False, errors_store = errors_store, errors_pass = errors_pass)
