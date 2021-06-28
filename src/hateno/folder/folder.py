#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import copy
import errno
import glob
import os
import tempfile

from . import checkers as default_checkers
from . import fixers as default_fixers
from . import namers as default_namers
from .errors import *
from ..utils import FCollection, utils, string, jsonfiles

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

	def _relpath(self, path):
		'''
		Transform a path relative to the configuration folder.

		Parameters
		----------
		path : str
			Path (relative to the configuration folder) to transform.

		Returns
		-------
		relative_path : str
			The path.
		'''

		return os.path.normpath(os.path.join(self._conf_folder_path, path))

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

			for import_desc in self.settings['import']:
				try:
					to_import = import_desc['config']

				except KeyError:
					pass

				else:
					self._config_folders_dict.update({
						foldername: self._relpath(os.path.join(import_desc['from'], MAIN_FOLDER, CONFIG_FOLDER, foldername))
						for foldername in to_import
					})

			base_folder = os.path.join(self._conf_folder_path, CONFIG_FOLDER)

			if os.path.isdir(base_folder):
				for foldername in os.listdir(base_folder):
					path = os.path.join(base_folder, foldername)

					if os.path.isdir(path):
						self._config_folders_dict[foldername] = path

		return self._config_folders_dict

	def configname(self, foldername = None):
		'''
		Get the name of a configuration.

		Parameters
		----------
		foldername : str
			Name of the configuration folder. If `None`, use the default config indicated in the configuration file.

		Raises
		------
		NoConfigError
			No configuration folder name given.

		ConfigNotFoundError
			The asked config name is not defined.

		Returns
		-------
		foldername : str
			Name of the configuration folder.
		'''

		foldername = foldername or self.settings.get('default_config')

		if foldername is None:
			if len(self._config_folders) != 1:
				raise NoConfigError()

			else:
				foldername = list(self._config_folders.keys())[0]

		if foldername not in self._config_folders:
			raise ConfigNotFoundError(foldername)

		return foldername

	def configFilepath(self, filename, foldername = None):
		'''
		Get the path to a file in a config folder.

		Parameters
		----------
		filename : str
			Name of the file.

		foldername : str
			Name of the configuration folder. If `None`, use the default config indicated in the configuration file.

		Raises
		------
		NoConfigError
			No configuration folder name given.

		Returns
		-------
		path : str
			Path to the file.
		'''

		foldername = self.configname(foldername)
		return os.path.join(self._config_folders[foldername], filename)

	def config(self, configname, foldername = None):
		'''
		Get a configuration object.

		Parameters
		----------
		configname : str
			Name of the wanted configuration.

		foldername : str
			Name of the configuration folder. If `None`, use the default config indicated in the configuration file.

		Returns
		-------
		config : dict
			Dictionary stored in the right configuration file.
		'''

		foldername = self.configname(foldername)

		if foldername not in self._configs:
			self._configs[foldername] = {}

		if configname not in self._configs[foldername]:
			try:
				self._configs[foldername][configname] = jsonfiles.read(self.configFilepath(f'{configname}.json', foldername))

			except FileNotFoundError:
				self._configs[foldername][configname] = None

		return self._configs[foldername][configname]

	@property
	def _skeletons_folders(self):
		'''
		The list of the available skeletons.

		Returns
		-------
		folders : dict
			A dictionary associating the folders' names to their paths.
		'''

		if self._skeletons_folders_dict is None:
			self._skeletons_folders_dict = {}

			for import_desc in self.settings['import']:
				try:
					to_import = import_desc['skeletons']

				except KeyError:
					pass

				else:
					self._skeletons_folders_dict.update({
						foldername: self._relpath(os.path.join(import_desc['from'], MAIN_FOLDER, SKELETONS_FOLDER, foldername))
						for foldername in to_import
					})

			base_folder = os.path.join(self._conf_folder_path, SKELETONS_FOLDER)

			if os.path.isdir(base_folder):
				for foldername in os.listdir(base_folder):
					path = os.path.join(base_folder, foldername)

					if os.path.isdir(path):
						self._skeletons_folders_dict[foldername] = path

		return self._skeletons_folders_dict

	def skeletons(self, skeletons_name):
		'''
		Get the skeletons filepaths.

		Parameters
		----------
		skeletons_name : str
			Name of the skeletons folder.

		Raises
		------
		SkeletonsNotFoundError
			The skeletons folder does not exist.

		Returns
		-------
		filepaths : list
			The paths of the skeletons.
		'''

		if skeletons_name not in self._skeletons_folders:
			raise SkeletonsNotFoundError(skeletons_name)

		if skeletons_name not in self._skeletons:
			path = self._skeletons_folders[skeletons_name]
			self._skeletons[skeletons_name] = [os.path.join(path, filename) for filename in os.listdir(path)]

		return self._skeletons[skeletons_name]

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

			if 'import' not in self._settings:
				self._settings['import'] = []

			elif type(self._settings['import']) is not list:
				self._settings['import'] = [self._settings['import']]

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
							self._program_files += [
								(
									os.path.join(root, file),
									os.path.join(dest, os.path.relpath(os.path.join(root, file), os.path.join(path, '..')))
								)
								for root, folders, files in os.walk(path)
								for file in files
							]

			except KeyError:
				pass

		return self._program_files

	def _loadFCollection(self, filter_regex, default_module, custom_filename, categories = []):
		'''
		Load a collection of functions used in the folder (fixers, namers, etc.).
		First load the default functions, then the imported ones, and finally the custom ones.
		In that way, the custom functions, defined in the current folder, will always overwrite the default and imported ones.

		Parameters
		----------
		filter_regex : str
			Regex to use to filter the functions in a module.

		default_module : module
			Module where the default functions are defined.

		custom_filename : str
			Name of the file (without extension) where the custom functions should be defined.

		categories : list
			List of categories to use in the FCollection.

		Returns
		-------
		collection : FCollection
			The loaded collection.
		'''

		collection = FCollection(categories = categories, filter_regex = filter_regex)

		if default_module is not None:
			collection.loadFromModule(default_module)

		for import_desc in self.settings['import']:
			try:
				to_import = import_desc['functions']

			except KeyError:
				pass

			else:
				if custom_filename in to_import:
					import_file = self._relpath(os.path.join(import_desc['from'], MAIN_FOLDER, f'{custom_filename}.py'))

					if os.path.isfile(import_file):
						collection.loadFromModule(utils.loadModuleFromFile(import_file))

		custom_file = os.path.join(self._conf_folder_path, f'{custom_filename}.py')
		if os.path.isfile(custom_file):
			collection.loadFromModule(utils.loadModuleFromFile(custom_file))

		return collection

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
			self._fixers = self._loadFCollection(r'^fixer_(?P<name>[A-Za-z0-9_]+)$', default_fixers, 'fixers')

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
			self._namers = self._loadFCollection(r'^namer_(?P<name>[A-Za-z0-9_]+)$', default_namers, 'namers')

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
			self._checkers = self._loadFCollection(r'^(?P<category>file|folder|global)_(?P<name>[A-Za-z0-9_]+)$', default_checkers, 'checkers', ['file', 'folder', 'global'])

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
			self._evaluations = self._loadFCollection(r'^eval_(?P<name>[A-Za-z0-9_]+)$', None, 'evaluations')

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
