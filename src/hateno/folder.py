#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import errno
import copy

from . import string, jsonfiles
from .errors import *
from .fcollection import FCollection
from . import namers as default_namers
from . import fixers as default_fixers

MAIN_FOLDER = '.hateno'
CONFIG_FOLDER = 'config'
SKELETONS_FOLDER = 'skeletons'
SIMULATIONS_FOLDER = 'simulations'

CONF_FILENAME = 'hateno.conf'
SIMULATIONS_LIST_FILENAME = 'simulations.list'
RUNNING_MANAGER_INDICATOR_FILENAME = 'manager.running'

class Folder():
	'''
	Base class for each system needing access to the configuration files of a simulations folder.
	Initialize with the simulations folder and load the settings.

	Parameters
	----------
	folder : str
		The simulations folder. Must contain a settings file.

	Raises
	------
	FileNotFoundError
		No configuration file found in the configuration folder.
	'''

	def __init__(self, folder):
		self._folder = folder
		self._conf_folder_path = os.path.join(self._folder, MAIN_FOLDER)
		self._settings_file = os.path.join(self._conf_folder_path, CONF_FILENAME)

		if not(os.path.isfile(self._settings_file)):
			raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), self._settings_file)

		self._settings = None

		self._configs = {}
		self._skeletons = {}

		self._namers = None
		self._fixers = None

	@property
	def folder(self):
		'''
		Return the folder's path.

		Returns
		-------
		path : str
			The path.
		'''

		return self._folder

	def config(self, configname, foldername = None):
		'''
		Get a configuration object.

		Parameters
		----------
		configname : str
			Name of the wanted configuration.

		foldername : str
			Name of the configuration folder. If `None`, use the default config indicated in the configuration file.

		Raises
		------
		NoConfigError
			No configuration folder name given.

		Returns
		-------
		config : dict
			Dictionary stored in the right configuration file.
		'''

		foldername = foldername or self.settings.get('default_config')

		if foldername is None:
			raise NoConfigError()

		if foldername not in self._configs:
			self._configs[foldername] = {}

		if configname not in self._configs[foldername]:
			try:
				self._configs[foldername][configname] = jsonfiles.read(os.path.join(self._conf_folder_path, CONFIG_FOLDER, foldername, f'{configname}.json'))

			except FileNotFoundError:
				self._configs[foldername][configname] = None

		return self._configs[foldername][configname]

	def skeletons(self, foldername):
		'''
		Get the paths to the skeletons files in a given folder.

		Parameters
		----------
		foldername : str
			Name of the skeletons folder.

		Returns
		-------
		paths : dict
			The lists of paths: subgroups skeletons, wholegroup skeletons and script to launch "coordinates".
		'''

		if foldername not in self._skeletons:
			folder = os.path.join(self._conf_folder_path, SKELETONS_FOLDER, foldername)
			recipe = jsonfiles.read(os.path.join(folder, 'recipe.json'))

			self._skeletons[foldername] = {
				category: [
					os.path.join(folder, skeleton)
					for skeleton in recipe[category]
				]
				for category in ['subgroups', 'wholegroup']
			}

			option_split = os.path.join(folder, recipe['launch']).rsplit(':', maxsplit = 2)
			option_split_num = [string.intOrNone(s) for s in option_split]

			cut = max([k for k, n in enumerate(option_split_num) if n is None]) + 1

			script_name = ':'.join(option_split[:cut])
			coords = option_split_num[cut:]
			coords += [-1] * (2 - len(coords))

			self._skeletons[foldername]['script_to_launch'] = {
				'name': script_name,
				'coords': coords
			}

		return self._skeletons[foldername]

	@property
	def simulations_list_filename(self):
		'''
		Return the path to the file where the list of simulations is stored.

		Returns
		-------
		path : str
			Path to the simulations list file.
		'''

		return os.path.join(self._conf_folder_path, SIMULATIONS_LIST_FILENAME)

	@property
	def simulations_folder(self):
		'''
		Return the path to the folder where the simulations are stored.
		Create the folder if it does not exist.

		Returns
		-------
		path : str
			Path to the simulations folder.
		'''

		path = os.path.join(self._conf_folder_path, SIMULATIONS_FOLDER)
		if not(os.path.isdir(path)):
			os.makedirs(path)

		return path

	@property
	def running_manager_indicator_filename(self):
		'''
		Return the path to the file indicating the Manager is currently running.

		Returns
		-------
		path : str
			Path to the indicator file.
		'''

		return os.path.join(self._conf_folder_path, RUNNING_MANAGER_INDICATOR_FILENAME)

	@property
	def settings(self):
		'''
		Return the content of the settings file as a dictionary.

		Returns
		-------
		settings : dict
			The folder's settings.
		'''

		if self._settings is None:
			self._settings = jsonfiles.read(self._settings_file)

			if 'namers' not in self._settings:
				self._settings['namers'] = []

			if 'fixers' not in self._settings:
				self._settings['fixers'] = []

		return self._settings

	@property
	def fixers(self):
		'''
		Get the list of available values fixers.

		Returns
		-------
		fixers : FCollection
			The collection of values fixers.
		'''

		if self._fixers is None:
			self._fixers = FCollection(filter_regex = r'^fixer_(?P<name>[A-Za-z0-9_]+)$')
			self._fixers.loadFromModule(default_fixers)

		return self._fixers

	@property
	def namers(self):
		'''
		Get the list of available namers.

		Returns
		-------
		namers : FCollection
			The collection of namers.
		'''

		if self._namers is None:
			self._namers = FCollection(filter_regex = r'^namer_(?P<name>[A-Za-z0-9_]+)$')
			self._namers.loadFromModule(default_namers)

		return self._namers

	def applyFixers(self, value, *, before = [], after = []):
		'''
		Fix a value to prevent false duplicates (e.g. this prevents to consider `0.0` and `0` as different values).
		Each item of a list of fixers is either a fixer's name or a list beginning with the fixer's name and followed by the arguments to pass to the fixer.

		Parameters
		----------
		value : mixed
			The value to fix.

		before : list
			List of fixers to apply before the global ones.

		after : list
			List of fixers to apply after the global ones.

		Returns
		-------
		fixed : mixed
			The same value, fixed.

		Raises
		------
		FixerNotFoundError
			The fixer's name has not been found.
		'''

		value = copy.deepcopy(value)

		for fixer in before + self.settings['fixers'] + after:
			if type(fixer) is not list:
				fixer = [fixer]

			try:
				fixer_func = self.fixers.get(fixer[0])

			except FCollectionFunctionNotFoundError:
				raise FixerNotFoundError(fixer[0])

			else:
				value = fixer_func(value, *fixer[1:])

		return value

	def applyNamers(self, name, local_index, local_total, global_index, global_total, *, before = [], after = []):
		'''
		Transform the name of a setting before being used in a simulation.

		Parameters
		----------
		name : str
			The name of the setting to alter.

		local_index : int
			The index of the setting, inside its set.

		local_total : int
			The total number the setting has been used inside its set.

		global_index : int
			The index of the setting, among all sets.

		global_total : int
			The total number the setting has been used among all sets.

		before : list
			List of namers to apply before the global ones.

		after : list
			List of namers to apply after the global ones.

		Returns
		-------
		name : str
			The name to use.

		Raises
		------
		NamerNotFoundError
			The namer's name has not been found.
		'''

		for namer in before + self.settings['namers'] + after:
			if type(namer) is not list:
				namer = [namer]

			try:
				namer_func = self.namers.get(namer[0])

			except FCollectionFunctionNotFoundError:
				raise NamerNotFoundError(namer[0])

			else:
				name = namer_func(name, local_index, local_total, global_index, global_total, *namer[1:])

		return name
