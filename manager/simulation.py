#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import copy
import functools
import re

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

		self._raw_settings = None

		self._setting_tag_regex_compiled = None

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
		Access to a user setting.

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
			return self._user_settings[key]

		except KeyError:
			raise KeyError('The key does not exist in the user settings')

	def __setitem__(self, key, value):
		'''
		Change a user setting.

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
			self._user_settings[key] = value

		except KeyError:
			raise KeyError('The key does not exist in the user settings')

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
	def settings_as_strings(self):
		'''
		Return the complete list of sets of settings to use, as strings.

		Returns
		-------
		settings : list
			Settings, generated according to their pattern.
		'''

		return [
			[s['pattern'].format(name = s['name'], value = s['value']) for s in settings_set]
			for settings_set in self._settings
		]

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

		self._raw_settings = []
		default_pattern = self._folder.settings['setting_pattern']

		for settings_set in self._folder.settings['settings']:
			default_settings = [
				{
					'name': s['name'],
					'value': s['default'],
					'exclude': 'exclude' in s and s['exclude'],
					'pattern': s['pattern'] if 'pattern' in s else default_pattern
				}
				for s in settings_set['settings']
			]

			values_sets = [s['settings'] for s in self._user_settings['settings'] if s['set'] == settings_set['set']]

			if values_sets:
				for values_set in values_sets:
					set_to_add = copy.deepcopy(default_settings)

					for setting in set_to_add:
						try:
							setting['value'] = values_set[setting['name']]

						except KeyError:
							pass

					self._raw_settings.append(set_to_add)

			elif settings_set['required']:
				self._raw_settings.append(default_settings)

	def parseString(self, s):
		'''
		Parse a string to take into account possible settings.
		The tag `{setting:name}` is replaced by the value of the simulation's setting named `name`.
		The tag `{globalsetting:name}` is replaced by the value of the global setting named `name`.

		Parameters
		----------
		s : str
			The string to parse.

		Returns
		-------
		parsed : str
			The parsed string.
		'''

		settings = {
			'setting': self.reduced_settings,
			'globalsetting': self._user_settings
		}

		parsed = ''
		k0 = 0

		for match in self._setting_tag_regex.finditer(s):
			parsed += s[k0:match.start()]

			try:
				parsed += settings[match.group('category')][match.group('name')]

			except KeyError:
				parsed += match.group(0)

			k0 = match.end()

		parsed += s[k0:]

		return parsed
