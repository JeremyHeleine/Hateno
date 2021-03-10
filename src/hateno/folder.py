#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import errno
import copy
import tempfile
import glob

from . import utils, string, jsonfiles
from .errors import *
from .fcollection import FCollection
from . import namers as default_namers
from . import fixers as default_fixers
from . import checkers as default_checkers

MAIN_FOLDER = '.hateno'
CONFIG_FOLDER = 'config'
SKELETONS_FOLDER = 'skeletons'
SIMULATIONS_FOLDER = 'simulations'
TMP_FOLDER = 'tmp'

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
		self._tmp_dir = os.path.join(self._conf_folder_path, TMP_FOLDER)

		if not(os.path.isfile(self._settings_file)):
			raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), self._settings_file)

		if not(os.path.isdir(self._tmp_dir)):
			os.makedirs(self._tmp_dir)

		self._settings = None

		self._config_folders_dict = None
		self._configs = {}
		self._skeletons_folders_dict = None
		self._skeletons = {}

		self._program_files = None

		self._namers = None
		self._fixers = None
		self._checkers = None
		self._evaluations = None

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

	@property
	def tmp_folder(self):
		'''
		Return the temporary folder's path.

		Returns
		-------
		path : str
			The path.
		'''

		return self._tmp_dir

	def tempdir(self):
		'''
		Create a temporary directory.

		Returns
		-------
		path : str
			The path to the created folder.
		'''

		return tempfile.mkdtemp(dir = self._tmp_dir)

	@property
	def _config_folders(self):
		'''
		The list of the available configuration folders.

		Returns
		-------
		folders : dict
			A dictionary associating the folders' names to their paths.
		'''

		if self._config_folders_dict is None:
			self._config_folders_dict = {}

			# First, the imported folders, then the local one.
			# In this way, the local configs will always overwrite the imported ones.

			if 'import_config' in self.settings:
				if type(self.settings['import_config']) is not list:
					self.settings['import_config'] = [self.settings['import_config']]

				for import_desc in self.settings['import_config']:
					foldername = import_desc.get('name') or import_desc['config']
					self._config_folders_dict[foldername] = os.path.normpath(os.path.join(self._folder, import_desc['folder'], MAIN_FOLDER, CONFIG_FOLDER, foldername))

			base_folder = os.path.join(self._conf_folder_path, CONFIG_FOLDER)

			if os.path.isdir(base_folder):
				for foldername in os.listdir(base_folder):
					path = os.path.join(base_folder, foldername)

					if os.path.isdir(path):
						self._config_folders_dict[foldername] = path

		return self._config_folders_dict

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
			if len(self._config_folders) != 1:
				raise NoConfigError()

			else:
				foldername = list(self._config_folders.keys())[0]

		if foldername not in self._config_folders:
			raise ConfigNotFoundError(foldername)

		if foldername not in self._configs:
			self._configs[foldername] = {}

		if configname not in self._configs[foldername]:
			try:
				self._configs[foldername][configname] = jsonfiles.read(os.path.join(self._config_folders[foldername], f'{configname}.json'))

			except FileNotFoundError:
				self._configs[foldername][configname] = None

		return self._configs[foldername][configname]

	@property
	def _skeletons_folders(self):
		'''
		The list of the available skeletons folders.

		Returns
		-------
		folders : dict
			A dictionary associating the folders' names to their paths.
		'''

		if self._skeletons_folders_dict is None:
			self._skeletons_folders_dict = {}

			if 'import_skeleton' in self.settings:
				if type(self.settings['import_skeleton']) is not list:
					self.settings['import_skeleton'] = [self.settings['import_skeleton']]

				for import_desc in self.settings['import_skeleton']:
					foldername = import_desc.get('name') or import_desc['skeleton']
					self._skeletons_folders_dict[foldername] = os.path.normpath(os.path.join(self._folder, import_desc['folder'], MAIN_FOLDER, SKELETONS_FOLDER, foldername))

			base_folder = os.path.join(self._conf_folder_path, SKELETONS_FOLDER)

			if os.path.isdir(base_folder):
				for foldername in os.listdir(base_folder):
					path = os.path.join(base_folder, foldername)

					if os.path.isdir(path):
						self._skeletons_folders_dict[foldername] = path

		return self._skeletons_folders_dict

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
			folder = self._skeletons_folders[foldername]
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
	def program_files(self):
		'''
		Get the list of the files defined in the configuration file.

		Returns
		-------
		files : list
			A list of files. Each item is a tuple. First item is the local path, second item is the remote one.
		'''

		if self._program_files is None:
			self._program_files = []

			try:
				for path_item in self.settings['files']:
					given_path, dest = path_item if type(path_item) is list else (path_item, '')

					for path in glob.glob(os.path.normpath(os.path.join(self._conf_folder_path, given_path))):
						if os.path.isfile(path):
							self._program_files.append((path, os.path.join(dest, os.path.basename(path))))

						else:
							self._program_files += [(os.path.join(root, file), os.path.join(dest, root, file)) for root, folders, files in os.walk(path) for file in files]

			except KeyError:
				pass

		return self._program_files

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

			custom_fixers_file = os.path.join(self._conf_folder_path, 'fixers.py')
			if os.path.isfile(custom_fixers_file):
				self._fixers.loadFromModule(utils.loadModuleFromFile(custom_fixers_file))

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

			custom_namers_file = os.path.join(self._conf_folder_path, 'namers.py')
			if os.path.isfile(custom_namers_file):
				self._namers.loadFromModule(utils.loadModuleFromFile(custom_namers_file))

		return self._namers

	@property
	def checkers(self):
		'''
		Get the list of available checkers.

		Returns
		-------
		checkers : FCollection
			The collection of checkers.
		'''

		if self._checkers is None:
			self._checkers = FCollection(
				categories = ['file', 'folder', 'global'],
				filter_regex = r'^(?P<category>file|folder|global)_(?P<name>[A-Za-z0-9_]+)$'
			)

			self._checkers.loadFromModule(default_checkers)

			custom_checkers_file = os.path.join(self._conf_folder_path, 'checkers.py')
			if os.path.isfile(custom_checkers_file):
				self._checkers.loadFromModule(utils.loadModuleFromFile(custom_checkers_file))

		return self._checkers

	@property
	def evaluations(self):
		'''
		Get the list of available evaluation functions.

		Returns
		-------
		evaluations : FCollection
			The collection of evaluation functions.
		'''

		if self._evaluations is None:
			self._evaluations = FCollection(filter_regex = r'^eval_(?P<name>[A-Za-z0-9_]+)$')

			evaluations_file = os.path.join(self._conf_folder_path, 'evaluations.py')
			if os.path.isfile(evaluations_file):
				self._evaluations.loadFromModule(utils.loadModuleFromFile(evaluations_file))

		return self._evaluations

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
			value = self.fixers.call(fixer, value)

		return value

	def applyNamers(self, setting, *, before = [], after = []):
		'''
		Transform the name of a setting before being used in a simulation.

		Parameters
		----------
		setting : dict
			Representation of the setting.

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
			setting['name'] = self.namers.call(namer, setting)

		return setting['name']

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

			if output_entry in self.settings['output']:
				for output in self.settings['output'][output_entry]:
					parsed_name = str(simulation.parseString(output['name']))
					tree[output_entry].append(parsed_name)

					if 'checks' in output:
						for checker in output['checks']:
							if not(self.checkers.call(checker, simulation, parsed_name, category = checkers_cat)):
								return False

		if 'checks' in self.settings['output']:
			for checker in self.settings['output']['checks']:
				if not(self.checkers.call(checker, simulation, tree, category = 'global')):
					return False

		return True
