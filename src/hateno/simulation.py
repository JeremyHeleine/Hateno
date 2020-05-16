#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import copy
import functools
import re
import inspect

from .errors import *
from . import fixers

class Simulation():
	'''
	Represent a simulation, itself identified by its settings.

	Parameters
	----------
	folder : Folder
		Instance of `Folder` for the current simulation's folder.

	settings : dict
		Dictionary listing the user settings.
	'''

	def __init__(self, folder, settings):
		self._folder = folder
		self._user_settings = settings

		self._raw_globalsettings = None
		self._raw_settings = None
		self._raw_settings_dict = None

		self._fixers_regex_compiled = None
		self._fixers_list = None

		self._setting_tag_regex_compiled = None
		self._parser_recursion_stack = []

	@classmethod
	def ensureType(cls, simulation, folder):
		'''
		Ensure a variable is a Simulation object.

		Parameters
		----------
		simulation : dict|Simulation
			The variable to check.

		folder : Folder
			The `Folder` instance to use in case we need to create a new object.

		Returns
		-------
		simulation : Simulation
			The simulation as a Simulation instance.
		'''

		if type(simulation) is cls:
			return simulation

		return cls(folder, simulation)

	def __getitem__(self, key):
		'''
		Access to a global setting.

		Parameters
		----------
		key : str
			The key of the setting to get.

		Raises
		------
		KeyError
			The key does not exist.

		Returns
		-------
		value : mixed
			The corresponding value.
		'''

		try:
			return self.reduced_globalsettings[key]

		except KeyError:
			raise KeyError('The key does not exist in the global settings')

	def __setitem__(self, key, value):
		'''
		Change a global setting.

		Parameters
		----------
		key : str
			The key of the setting to change.

		value : mixed
			The new value of the setting.

		Raises
		------
		KeyError
			The key does not exist.
		'''

		try:
			setting = [setting for setting in self._globalsettings if setting['name'] == key][0]

		except IndexError:
			raise KeyError('The key does not exist in the global settings')

		else:
			setting['value'] = value

	@property
	def _globalsettings(self):
		'''
		Return (and generate if needed) the complete list of global settings.

		Returns
		-------
		raw_globalsettings : list
			The global settings.
		'''

		if not(self._raw_globalsettings):
			self.generateGlobalSettings()

		return self._raw_globalsettings

	@property
	def _settings(self):
		'''
		Return (and generate if needed) the complete list of settings.

		Returns
		-------
		raw_settings : list
			The settings.
		'''

		if not(self._raw_settings):
			self.generateSettings()

		return self._raw_settings

	@property
	def _settings_dict(self):
		'''
		Return (and generate if needed) the complete list of settings as a dictionary.

		Returns
		-------
		raw_settings : dict
			The settings.
		'''

		if not(self._raw_settings_dict):
			self.generateSettings()

		return self._raw_settings_dict

	@property
	def settings(self):
		'''
		Return the complete list of sets of settings to use, as dictionaries.
		The settings with `exclude` to `True` are ignored.

		Returns
		-------
		settings : list
			List of sets of settings.
		'''

		return [
			{s['name']: s['value'] for s in settings_set if not(s['exclude'])}
			for settings_set in self._settings
		]

	@property
	def settings_dict(self):
		'''
		Return a dictionary with the complete list of sets of settings to use, as dictionaries.
		The settings with `exclude` to `True` are ignored.

		Returns
		-------
		settings : dict
			List of sets of settings.
		'''

		return {
			settings_set_name: [
				{s['name']: s['value'] for s in settings_set if not(s['exclude'])}
				for settings_set in settings_sets
			]
			for settings_set_name, settings_sets in self._settings_dict.items()
		}

	@property
	def settings_as_strings(self):
		'''
		Return the complete list of sets of settings to use, as strings.
		Take into account the `only_if` parameter.

		Returns
		-------
		settings : list
			Settings, generated according to their pattern.
		'''

		return [
			[
				s['pattern'].format(name = s['name'], value = s['value'])
				for s in settings_set
				if not('only_if' in s) or s['value'] == s['only_if']
			]
			for settings_set in self._settings
		]

	@property
	def reduced_globalsettings(self):
		'''
		Return the list of global settings, as a name: value dictionary.

		Returns
		-------
		settings : dict
			The global settings.
		'''

		return {setting['name']: setting['value'] for setting in self._globalsettings}

	@property
	def reduced_settings(self):
		'''
		Return the list of settings, as a name: value dictionary.
		Ignore multiple occurrences of the same setting.

		Returns
		-------
		settings : dict
			The settings.
		'''

		return functools.reduce(lambda a, b: {**a, **b}, self.settings)

	@property
	def command_line(self):
		'''
		Return the command line to use to generate this simulation.

		Returns
		-------
		command_line : str
			The command line to execute.
		'''

		return ' '.join([self._folder.settings['exec']] + sum(self.settings_as_strings, []))

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
	def _setting_tag_regex(self):
		'''
		Regex to detect whether there is a setting or global setting tag in a string.

		Returns
		-------
		regex : re.Pattern
			The setting tag regex.
		'''

		if self._setting_tag_regex_compiled is None:
			self._setting_tag_regex_compiled = re.compile(r'\{(?P<category>(?:global)?setting):(?P<name>[^}]+)\}')

		return self._setting_tag_regex_compiled

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

	def generateGlobalSettings(self):
		'''
		Generate the full list of global settings.
		'''

		self._raw_globalsettings = []

		for setting in self._folder.settings['globalsettings']:
			self._raw_globalsettings.append({
				'name': setting['name'],
				'value': self.fixValue(self._user_settings[setting['name']]) if setting['name'] in self._user_settings else setting['default']
			})

		self.parseGlobalSettings()

	def generateSettings(self):
		'''
		Generate the full list of settings, taking into account the user settings and the default values in the folder.
		The "raw settings" are generated. Each setting is a dictionary:
		```
		{
			'name': 'name of the setting',
			'value': 'value of the setting (initialized with the default one)',
			'exclude': 'boolean to determine if we should exclude this setting for the comparison things',
			'pattern': 'the pattern to use when we generate the corresponding string'
		}
		```
		Each set of settings is a list of all settings in this set.
		'''

		if type(self._user_settings['settings']) is list:
			user_settings = {
				setting_set_name: [s['settings'] for s in self._user_settings['settings'] if s['set'] == setting_set_name]
				for setting_set_name in set([s['set'] for s in self._user_settings['settings']])
			}

		else:
			user_settings = self._user_settings['settings']

		self._raw_settings_dict = {}
		default_pattern = self._folder.settings['setting_pattern']

		for settings_set in self._folder.settings['settings']:
			default_settings = [
				{
					'name': s['name'],
					'value': s['default'],
					'exclude': 'exclude' in s and s['exclude'],
					'pattern': s['pattern'] if 'pattern' in s else default_pattern,
					**({'only_if': s['only_if']} if 'only_if' in s else {})
				}
				for s in settings_set['settings']
			]

			try:
				values_sets = user_settings[settings_set['set']]

			except KeyError:
				if settings_set['required']:
					self._raw_settings_dict[settings_set['set']] = [default_settings]

			else:
				if not(type(values_sets) is list):
					values_sets = [values_sets]

				self._raw_settings_dict[settings_set['set']] = []

				for values_set in values_sets:
					set_to_add = copy.deepcopy(default_settings)

					for setting in set_to_add:
						try:
							setting['value'] = self.fixValue(values_set[setting['name']])

						except KeyError:
							pass

					self._raw_settings_dict[settings_set['set']].append(set_to_add)

		self._raw_settings = sum(self._raw_settings_dict.values(), [])
		self.parseSettings()

	def fixValue(self, value):
		'''
		Fix a value to prevent false duplicates (e.g. this prevent to consider `0.0` and `0` as different values).

		Parameters
		----------
		value : mixed
			The value to fix.

		Returns
		-------
		fixed : mixed
			The same value, fixed.
		'''

		if 'fixes' in self._folder.settings:
			for fixer in self._folder.settings['fixes']:
				if not(type(fixer) is list):
					fixer = [fixer]

				if not(fixer[0] in self._fixers):
					raise FixerNotFoundError(fixer[0])

				value = self._fixers[fixer[0]](value, *fixer[1:])

		return value

	def parseString(self, s):
		'''
		Parse a string to take into account possible settings.
		The tag `{setting:name}` is replaced by the value of the simulation's setting named `name`.
		The tag `{globalsetting:name}` is replaced by the value of the global setting named `name`.

		Tags are replaced recursively.

		Parameters
		----------
		s : str
			The string to parse.

		Returns
		-------
		parsed : mixed
			The parsed string, or a copy of the setting if the whole string is just one tag.
		'''

		if not(type(s) is str):
			return s

		settings = {
			'setting': self.reduced_settings,
			'globalsetting': self.reduced_globalsettings
		}

		fullmatch = self._setting_tag_regex.fullmatch(s)

		if fullmatch:
			try:
				return copy.deepcopy(settings[fullmatch.group('category')][fullmatch.group('name')])

			except KeyError:
				return s

		parsed = ''
		k0 = 0

		for match in self._setting_tag_regex.finditer(s):
			parsed += s[k0:match.start()]

			try:
				parsed += str(settings[match.group('category')][match.group('name')])

			except KeyError:
				parsed += match.group(0)

			k0 = match.end()

		parsed += s[k0:]

		self._parser_recursion_stack.append(s)

		if not(parsed in self._parser_recursion_stack):
			return self.parseString(parsed)

		self._parser_recursion_stack.clear()

		return parsed

	def parseGlobalSettings(self):
		'''
		Parse the global settings to take into account possible other settings' values.
		'''

		for setting in self._globalsettings:
			setting['value'] = self.parseString(setting['value'])

	def parseSettings(self):
		'''
		Parse the settings to take into account possible other settings' values.
		'''

		for settings_set in self._settings:
			for setting in settings_set:
				setting['value'] = self.parseString(setting['value'])
