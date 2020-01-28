#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import copy
import functools

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
