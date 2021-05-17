#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

from .errors import *
from .basesetting import SimulationBaseSetting

class SimulationSetting(SimulationBaseSetting):
	'''
	Represent a simulation setting.

	Parameters
	----------
	simulation : Simulation
		Simulation that uses this setting.

	set_name : str
		Name of the set this setting is part of.

	setting_name : str
		Name of this setting.

	Raises
	------
	SettingsSetNotFoundError
		The settings set has not been found.

	SettingNotFoundError
		The setting has not been found in the set.
	'''

	def __init__(self, simulation, set_name, setting_name):
		try:
			self._settings_set_dict = [
				settings_set
				for settings_set in simulation.folder.settings['settings']
				if settings_set['set'] == set_name
			][0]

		except IndexError:
			raise SettingsSetNotFoundError(set_name)

		try:
			self._setting_dict = [
				setting
				for setting in self._settings_set_dict['settings']
				if setting['name'] == setting_name
			][0]

		except IndexError:
			raise SettingNotFoundError(set_name, setting_name)

		super().__init__(simulation, setting_name, self._setting_dict['default'])

		self._set_name = set_name
		self._exclude_for_db = 'exclude' in self._setting_dict and self._setting_dict['exclude']
		self._pattern = self._setting_dict['pattern'] if 'pattern' in self._setting_dict else self._simulation.folder.settings['setting_pattern']

		self._use_only_if = 'only_if' in self._setting_dict
		if self._use_only_if:
			self._only_if_value = self._setting_dict['only_if']

		self._fixers_dict = None
		self._namers_dict = None

	def __str__(self):
		'''
		Return a string representing the setting and its value, according to the pattern.

		Returns
		-------
		setting : str
			The representation of the setting.
		'''

		value = self.value

		if type(value) is str and (not(value) or re.search(r'\s', value) is not None):
			value = repr(value)

		elif type(value) is list:
			value = ' '.join(map(str, value))

		return self._pattern.format(name = self.display_name, value = value)

	def as_dict(self):
		'''
		Dictionary representation of the setting.

		Returns
		-------
		setting : dict
			A dictionary listing some properties of the setting.
		'''

		return {
			'name': self.name,
			'value': self.value,
			'local_index': self._local_index,
			'local_total': self._simulation.getSettingCount(self.name, self._set_name),
			'global_index': self._global_index,
			'global_total': self._simulation.getSettingCount(self.name)
		}

	def setIndexes(self, global_index, local_index):
		'''
		Define the global and local indexes of this setting.

		Parameters
		----------
		global_index : int
			Global index of this setting.

		local_index : int
			Local index of this setting.
		'''

		self._global_index = global_index
		self._local_index = local_index

	def _setModifier(self, modifier):
		'''
		Set a "modifier" property (fixers or namers).

		Parameters
		----------
		modifier : str
			Modifier to define.

		Returns
		-------
		modifier_functions : dict
			The functions to call, in the right order.
		'''

		modifier_functions = {'before': [], 'after': []}

		keys_to_search = {
			'before': [
				(self._setting_dict, ''),
				(self._settings_set_dict, ''),
				(self._setting_dict, '_before'),
				(self._settings_set_dict, '_before'),
				(self._setting_dict, '_between_before')
			],
			'after': [
				(self._setting_dict, '_between_after'),
				(self._settings_set_dict, '_after'),
				(self._setting_dict, '_after')
			]
		}

		for when, keys_path in keys_to_search.items():
			for dict_to_search, key_to_search in keys_path:
				try:
					modifier_functions[when] += dict_to_search[f'{modifier}{key_to_search}']

				except KeyError:
					pass

		return modifier_functions

	@property
	def _fixers(self):
		'''
		Get the fixers to apply to the value.

		Returns
		-------
		fixers : dict
			The list of fixers, in the right order.
		'''

		if self._fixers_dict is None:
			self._fixers_dict = self._setModifier('fixers')

		return self._fixers_dict

	@property
	def _namers(self):
		'''
		Get the namers to apply to the name.

		Returns
		-------
		namers : dict
			The list of namers, in the right order.
		'''

		if self._namers_dict is None:
			self._namers_dict = self._setModifier('namers')

		return self._namers_dict

	@property
	def display_name(self):
		'''
		Get the name of the setting to use inside the simulation.

		Returns
		-------
		name : str
			Name to use.
		'''

		return self._simulation.folder.applyNamers(self.as_dict(), **self._namers)

	@property
	def exclude(self):
		'''
		Return `True` if the setting should be excluded to define a simulation.

		Returns
		-------
		exclude : bool
			Exclusion parameter.
		'''

		return self._exclude_for_db

	def shouldBeDisplayed(self):
		'''
		Return `True` if the setting can be displayed/used for the execution.
		This check is based on the `only_if` parameter. There are several cases for the test string.

		1. It is a full test (e.g. `a < b`): we execute it as it is.
		2. It begins by a conditional operator (<, <=, >, >=, ==, !=, in): we test against the setting value.
		3. It does not contain any conditional operator: we test the equality against the setting value.

		Returns
		-------
		should_be_displayed : bool
			The result of the check.
		'''

		if not(self._use_only_if):
			return True

		if type(self._only_if_value) is str:
			first_operator_match = re.search(r'([<>]=?|[!=]=|in)', self._only_if_value.strip())

			if first_operator_match:
				if first_operator_match.start() > 0:
					return self._simulation.parseString(f'(({self._only_if_value}))')

				return self._simulation.parseString(f'(({repr(self.value)} {self._only_if_value}))')

			return self.value == self._simulation.parseString(self._only_if_value)

		return self.value == self._only_if_value
