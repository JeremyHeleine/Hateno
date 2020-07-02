#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import errno

from . import jsonfiles
from .errors import *
from .fcollection import FCollection
from . import namers as default_namers
from . import fixers as default_fixers

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
		No `simulations.conf` file found in the configuration folder.
	'''

	def __init__(self, folder):
		self._folder = folder
		self._conf_folder_path = os.path.join(self._folder, '.hateno')
		self._settings_file = self.confFilePath('simulations.conf')

		if not(os.path.isfile(self._settings_file)):
			raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), self._settings_file)

		self._settings = None

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

	@property
	def conf_folder(self):
		'''
		Return the configuration folder path.

		Returns
		-------
		path : str
			The path.
		'''

		return self._conf_folder_path

	def confFilePath(self, filename):
		'''
		Return the path to a configuration file, with a given filename.

		Parameters
		----------
		filename : str
			Name of the file.

		Returns
		-------
		path : str
			Path to the file.
		'''

		return os.path.join(self._conf_folder_path, filename)

	@property
	def settings(self):
		'''
		Return the content of the settings file as a dictionary.

		Returns
		-------
		settings : dict
			The folder's settings.
		'''

		if not(self._settings):
			self._settings = jsonfiles.read(self._settings_file)

			if not('namers' in self._settings):
				self._settings['namers'] = []

			if not('fixers' in self._settings):
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

		for fixer in before + self.settings['fixers'] + after:
			if not(type(fixer) is list):
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
			if not(type(namer) is list):
				namer = [namer]

			try:
				namer_func = self.namers.get(namer[0])

			except FCollectionFunctionNotFoundError:
				raise NamerNotFoundError(namer[0])

			else:
				name = namer_func(name, local_index, local_total, global_index, global_total, *namer[1:])

		return name
