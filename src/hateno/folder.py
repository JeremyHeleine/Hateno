#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import inspect

from . import jsonfiles
from .errors import *
from . import fixers

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
		No `.simulations.conf` file found in folder.
	'''

	def __init__(self, folder):
		self._folder = folder
		self._settings_file = os.path.join(self._folder, '.simulations.conf')

		if not(os.path.isfile(self._settings_file)):
			raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), self._settings_file)

		self._settings = None

		self._fixers_regex_compiled = None
		self._fixers_list = None

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

			if not('fixes' in self._settings):
				self._settings['fixes'] = []

		return self._settings

	@property
	def _fixers_regex(self):
		'''
		Regex to detect whether a function's name corresponds to a value fixer.

		Returns
		-------
		regex : re.Pattern
			The fixers regex.
		'''

		if self._fixers_regex_compiled is None:
			self._fixers_regex_compiled = re.compile(r'^fixer_([A-Za-z0-9_]+)$')

		return self._fixers_regex_compiled

	@property
	def _fixers(self):
		'''
		Get the list of available values fixers.

		Returns
		-------
		fixers : dict
			The values fixers.
		'''

		if self._fixers_list is None:
			self._fixers_list = {}
			self.loadFixersFromModule(fixers)

		return self._fixers_list

	def loadFixersFromModule(self, module):
		'''
		Load all values fixers in a given module.

		Parameters
		----------
		module : Module
			Module (already loaded) where are defined the fixers.
		'''

		for function in inspect.getmembers(module, inspect.isfunction):
			fixer_match = self._fixers_regex.match(function[0])

			if fixer_match:
				self.setFixer(fixer_match.group(1), function[1])

	def setFixer(self, fixer_name, fixer):
		'''
		Set (add or replace) a value fixer.

		Parameters
		----------
		fixer_name : str
			Name of the fixer.

		fixer : function
			Fixer to register.
		'''

		self._fixers[fixer_name] = fixer

	def removeFixer(self, fixer_name):
		'''
		Remove a value fixer.

		Parameters
		----------
		fixer_name : str
			Name of the fixer to remove.
		'''

		if not(fixer_name in self._fixers):
			raise FixerNotFoundError(fixer_name)

		del self._fixers[fixer_name]

	def applyFixers(self, value, before = [], after = []):
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

		for fixer in before + self.settings['fixes'] + after:
			if not(type(fixer) is list):
				fixer = [fixer]

			if not(fixer[0] in self._fixers):
				raise FixerNotFoundError(fixer[0])

			value = self._fixers[fixer[0]](value, *fixer[1:])

		return value
