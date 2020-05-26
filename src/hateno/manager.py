#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import errno
import inspect

import shutil
import tarfile
import tempfile

import re

from . import jsonfiles, string
from .errors import *
from .simulation import Simulation
from . import checkers

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

		tree = {}

		for output_entry in ['files', 'folders']:
			tree[output_entry] = []
			checkers_cat = output_entry[:-1]

			if output_entry in self._folder.settings['output']:
				for output in self._folder.settings['output'][output_entry]:
					parsed_name = str(simulation.parseString(output['name']))
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

		if os.path.isdir(folder):
			os.rmdir(folder)

		shutil.move(os.path.join(self._folder.folder, simulation_name), folder)

	def getSimulationsNumber(self):
		'''
		Returns the total number of simulations stored in the folder.

		Returns
		-------
		n : int
			The number of simulations.
		'''

		return len(self._simulations_list)

	def settingsOf(self, simulation_name):
		'''
		Return the whole settings set of a simulation.

		Parameters
		----------
		simulation_name : str
			Name of the simulation.

		Raises
		------
		SimulationNotFoundError
			The simulation does not exist in the list.

		Returns
		-------
		settings : dict
			Settings of the simulation.
		'''

		try:
			return string.toObject(self._simulations_list[simulation_name]['settings'])

		except KeyError:
			raise SimulationNotFoundError(simulation_name)

	def add(self, simulation, save_list = True):
		'''
		Add a simulation to the list.

		Parameters
		----------
		simulation : Simulation|dict
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

		simulation = Simulation.ensureType(simulation, self._folder)

		if not(os.path.isdir(simulation['folder'])):
			raise SimulationFolderNotFoundError(simulation['folder'])

		settings_str = string.fromObject(simulation.settings_dict)
		settings_hashed = string.hash(settings_str)
		simulation_name = string.uniqueID()

		if not(self.checkIntegrity(simulation)):
			raise SimulationIntegrityCheckFailedError(simulation['folder'])

		self.compress(simulation['folder'], simulation_name)

		self._simulations_list[settings_hashed] = {
			'name': simulation_name,
			'settings': settings_str
		}

		if save_list:
			self.saveSimulationsList()

	def delete(self, simulation, save_list = True):
		'''
		Delete a simulation.

		Parameters
		----------
		simulation : Simulation|dict
			The simulation to delete.

		save_list : boolean
			`True` to save the simulations list, `False` otherwise.

		Raises
		------
		SimulationNotFoundError
			The simulation does not exist in the list.
		'''

		simulation = Simulation.ensureType(simulation, self._folder)
		settings_hashed = string.hash(string.fromObject(simulation.settings_dict))

		if not(settings_hashed in self._simulations_list):
			raise SimulationNotFoundError(settings_hashed)

		simulation_name = self._simulations_list[settings_hashed]['name']

		os.unlink(os.path.join(self._folder.folder, f'{simulation_name}.tar.bz2'))
		del self._simulations_list[settings_hashed]

		if save_list:
			self.saveSimulationsList()

	def extract(self, simulation, settings_file = None):
		'''
		Extract a simulation.

		Parameters
		----------
		simulation : Simulation|dict
			The simulation to extract.

		settings_file : str
			Name of the file to create to store the simulation's settings.

		Raises
		------
		SimulationNotFoundError
			The simulation does not exist in the list.

		SimulationFolderAlreadyExistError
			The destination of extraction already exists.
		'''

		simulation = Simulation.ensureType(simulation, self._folder)
		settings_hashed = string.hash(string.fromObject(simulation.settings_dict))

		if not(settings_hashed in self._simulations_list):
			raise SimulationNotFoundError(settings_hashed)

		if os.path.exists(simulation['folder']):
			raise SimulationFolderAlreadyExistError(simulation['folder'])

		simulation_name = self._simulations_list[settings_hashed]['name']

		destination_path = os.path.dirname(os.path.normpath(simulation['folder']))
		if destination_path and not(os.path.isdir(destination_path)):
			os.makedirs(destination_path)

		self.uncompress(simulation_name, simulation['folder'])

		if settings_file:
			jsonfiles.write(simulation.settings_dict, os.path.join(simulation['folder'], settings_file))

	def batchAction(self, simulations, action, args = {}, *, save_list = True, errors_store = (), errors_pass = (Error), callback = None):
		'''
		Apply a callback function to each simulation of a given list.

		Parameters
		----------
		simulations : list
			List of simulations.

		action : function
			Function to call. The simulation will be passed as the first parameter.

		args : dict
			Additional named arguments to pass to the callback.

		save_list : boolean
			`True` to save the simulations list once the loop is over, `False` to not save it.

		errors_store : tuple
			List of exceptions that, when raised, lead to the storage of the involved simulation.

		errors_pass : tuple
			List of exceptions that, when raised, do nothing.

		callback : function
			Function to call at the end of each action.

		Returns
		-------
		errors : list
			List of simulations which raised an error.
		'''

		errors = []

		for simulation in simulations:
			try:
				action(simulation, **args)

			except errors_store:
				errors.append(simulation)

			except errors_pass:
				pass

			if not(callback is None):
				callback()

		if save_list:
			self.saveSimulationsList()

		return errors

	def batchAdd(self, simulations, *, callback = None):
		'''
		Add multiple simulations to the list.

		Parameters
		----------
		simulations : list
			List of simulations.

		callback : function
			Function to call at the end of each addition.

		Returns
		-------
		errors : list
			List of simulations that were not added because they raised an error.
		'''

		return self.batchAction(simulations, self.add, {'save_list': False}, save_list = True, errors_store = (SimulationFolderNotFoundError, SimulationIntegrityCheckFailedError), callback = callback)

	def batchDelete(self, simulations, *, callback = None):
		'''
		Delete multiple simulations.

		Parameters
		----------
		simulations : list
			List of simulations.

		callback : function
			Function to call at the end of each deletion.

		Returns
		-------
		errors : list
			List of simulations that were not deleted because they raised an error.
		'''

		return self.batchAction(simulations, self.delete, {'save_list': False}, save_list = True, errors_store = (SimulationNotFoundError), callback = callback)

	def batchExtract(self, simulations, *, settings_file = None, ignore_existing = True, callback = None):
		'''
		Extract multiple simulations.

		Parameters
		----------
		simulations : list
			List of simulations.

		ignore_existing : boolean
			Ignore simulations for which the destination folder already exists.

		callback : function
			Function to call at the end of each extraction.

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

		return self.batchAction(simulations, self.extract, {'settings_file': settings_file}, save_list = False, errors_store = errors_store, errors_pass = errors_pass, callback = callback)

	def checkSimulationsList(self, callback = None):
		'''
		Check whether the simulations list has the right format.
		If it has the old one, update all the necessary files.

		Parameters
		----------
		callback : function
			Function to call at each treated simulation.
		'''

		test_infos = self._simulations_list[list(self._simulations_list.keys())[0]]

		if not(type(test_infos) is dict) or not('name' in test_infos and 'settings' in test_infos):
			new_simulations_list = {}

			for settings_hashed, settings_str in self._simulations_list.items():
				simulation_name = string.uniqueID()
				tmp_path = os.path.join(self._folder.folder, simulation_name)

				self.uncompress(settings_hashed, tmp_path)
				os.unlink(os.path.join(self._folder.folder, f'{settings_hashed}.tar.bz2'))
				self.compress(tmp_path, simulation_name)

				new_simulations_list[settings_hashed] = {
					'name': simulation_name,
					'settings': settings_str
				}

				if not(callback is None):
					callback()

			self._simulations_list_dict = new_simulations_list
			self.saveSimulationsList()

	def update(self, callback = None):
		'''
		Update the simulations list to take into account new settings.

		Parameters
		----------
		callback : function
			Function to call at each treated simulation.
		'''

		new_simulations_list = {}

		for settings_hashed, infos in self._simulations_list.items():
			simulation = Simulation.ensureType({
				'folder': '',
				'settings': string.toObject(infos['settings'])
			}, self._folder)

			settings_str = string.fromObject(simulation.settings_dict)
			settings_hashed = string.hash(settings_str)

			new_simulations_list[settings_hashed] = {
				'name': infos['name'],
				'settings': settings_str
			}

			if not(callback is None):
				callback()

		self._simulations_list_dict = new_simulations_list
		self.saveSimulationsList()

	def transform(self, transformation, simulations_settings = None, callback = None):
		'''
		Apply a transformation operation to a given list of simulations, e.g. to store new informations.

		Parameters
		----------
		transformation : function
			Transformation to apply. This function must accept the following parameters.

				simulation : Simulation
					A Simulation object representing the settings of the current simulation.

			Returned value is ignored.

		simulations_settings : list
			List of simulations to transform (only their settings). If `None`, will transform all the stored simulations.

		callback : function
			Function to call once a simulation has been transformed.
		'''

		if not(simulations_settings):
			simulations_settings = [string.toObject(infos['settings']) for infos in self._simulations_list.values()]

		for settings in simulations_settings:
			simulation_dir = tempfile.mkdtemp(prefix = 'simulation_')

			simulation = Simulation.ensureType({
				'folder': simulation_dir,
				'settings': settings
			}, self._folder)

			settings_hashed = string.hash(string.fromObject(simulation.settings_dict))
			simulation_name = self._simulations_list[settings_hashed]['name']

			self.uncompress(simulation_name, simulation_dir)
			transformation(simulation)
			os.unlink(os.path.join(self._folder.folder, f'{simulation_name}.tar.bz2'))
			self.compress(simulation_dir, simulation_name)

			if not(callback is None):
				callback()
