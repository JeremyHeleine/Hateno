#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import copy
import functools
import re
import abc

from .errors import *
from . import string, jsonfiles

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

		self._indexed_settings = None

		self._setting_tag_regex_compiled = None
		self._eval_tag_regex_compiled = None
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

	def copy(self):
		'''
		Create a copy of the simulation.

		Returns
		-------
		simulation : Simulation
			The copy of the simulation.
		'''

		return Simulation(self._folder, {
			**self.globalsettings,
			'settings': {
				settings_set_name: [
					{s.name: s._value for s in settings_set}
					for settings_set in settings_sets
				]
				for settings_set_name, settings_sets in self._settings.items()
			}
		})

	@property
	def folder(self):
		'''
		Get the Folder instance used by the simulation.

		Returns
		-------
		folder : Folder
			The Folder instance.
		'''

		return self._folder

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
			return self.globalsettings[key]

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
			setting = [setting for setting in self._globalsettings if setting.name == key][0]

		except IndexError:
			raise KeyError('The key does not exist in the global settings')

		else:
			setting.value = value

	def writeSettingsFile(self, filename, *, folder = None):
		'''
		Write the settings into a file in the simulation's folder.

		Parameters
		----------
		filename : str
			Name of the file to write.

		folder : str
			Name of the folder in which the file should be saved. Default to the simulation's folder.
		'''

		jsonfiles.write(self.settings, os.path.join(folder or self['folder'], filename))

	@property
	def _globalsettings(self):
		'''
		Return (and generate if needed) the complete list of global settings.

		Returns
		-------
		raw_globalsettings : list
			The global settings.
		'''

		if self._raw_globalsettings is None:
			self.generateGlobalSettings()

		return self._raw_globalsettings

	@property
	def _settings(self):
		'''
		Return (and generate if needed) the complete list of settings as a dictionary.

		Returns
		-------
		raw_settings : dict
			The settings.
		'''

		if self._raw_settings is None:
			self.generateSettings()

		return self._raw_settings

	@property
	def raw_settings(self):
		'''
		Return a dictionary with the complete list of sets of settings.

		Returns
		-------
		settings : dict
			The list of settings.
		'''

		return {
			settings_set_name: [
				{s.name: s for s in settings_set}
				for settings_set in settings_sets
			]
			for settings_set_name, settings_sets in self._settings.items()
		}

	def getSetting(self, coords):
		'''
		Retrieve a setting from its set and name.

		Parameters
		----------
		coords : dict
			Describe the "coordinates" of the setting. Must contain the following keys:
				* `set`: the name of the set the setting belongs to,
				* `name`: the name of the setting.
			The following key is optional:
				* `set_index`: the index of the set. If not provided, default to 0.

		Returns
		-------
		setting : SimulationSetting
			The setting corresponding to the coordinates.
		'''

		coords = {
			'set_index': 0,
			**coords
		}

		return self.raw_settings[coords['set']][coords['set_index']][coords['name']]

	@property
	def settings(self):
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
				{s.name: s.value for s in settings_set if not(s.exclude)}
				for settings_set in settings_sets
			]
			for settings_set_name, settings_sets in self._settings.items()
		}

	@property
	def raw_values_settings(self):
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
				{s.name: s._value for s in settings_set}
				for settings_set in settings_sets
			]
			for settings_set_name, settings_sets in self._settings.items()
		}

	@property
	def settings_as_strings(self):
		'''
		Return the complete list of sets of settings to use, as strings.
		Take into account the `only_if` parameter.

		Returns
		-------
		settings : dict
			Settings, generated according to their pattern and organized by sets.
		'''

		return {
			set_name: [
				[str(s) for s in settings_set if s.shouldBeDisplayed()]
				for settings_set in settings_sets
			]
			for set_name, settings_sets in self._settings.items()
		}

	@property
	def globalsettings(self):
		'''
		Return the list of global settings, as a name: value dictionary.

		Returns
		-------
		settings : dict
			The global settings.
		'''

		return {setting.name: setting.value for setting in self._globalsettings}

	@property
	def command_line(self):
		'''
		Return the command line to use to generate this simulation.

		Returns
		-------
		command_line : str
			The command line to execute.
		'''

		return ' '.join([self._folder.settings['exec']] + sum(sum(self.settings_as_strings.values(), []), []))

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
			self._setting_tag_regex_compiled = re.compile(r'\{(?P<category>(?:global)?setting)(?:\[(?P<setname>.+?)\])?(?:\((?P<index>[0-9]+)\))?:(?P<name>.+?)\}')

		return self._setting_tag_regex_compiled

	@property
	def _eval_tag_regex(self):
		'''
		Regex to detect whether we need to evaluate a part of a string.

		Returns
		-------
		regex : re.Pattern
			The eval tag regex.
		'''

		# The `\)*` part is needed so we don't have troubles with functions calls right before the end of a string.
		# Without this, such calls (e.g. in "((sqrt(16)))") end the string prematurely.

		if self._eval_tag_regex_compiled is None:
			self._eval_tag_regex_compiled = re.compile(r'\(\((.*?\)*)\)\)')

		return self._eval_tag_regex_compiled

	def generateGlobalSettings(self):
		'''
		Generate the full list of global settings.
		'''

		self._raw_globalsettings = []

		for setting in self._folder.settings['globalsettings']:
			try:
				setting_value = self._user_settings[setting['name']]

			except KeyError:
				setting_value = setting['default']

			self._raw_globalsettings.append(SimulationGlobalSetting(self, setting['name'], setting_value))

	def getSettingCount(self, setting_name, set_name = None):
		'''
		Get the total number of uses of a given setting, globally or locally.

		Parameters
		----------
		setting_name : str
			Name of the setting to get the count of.

		set_name : str
			Name of the set for the local count.

		Raises
		------
		SettingsSetNotFoundError
			The provided set name does not exist.

		SettingNotFoundError
			The provided setting name does not exist.

		Returns
		-------
		count : int
			Local count if `set_name` is not `None`, global count otherwise.
		'''

		try:
			settings = self._indexed_settings['global'] if set_name is None else self._indexed_settings['local'][set_name]

		except KeyError:
			raise SettingsSetNotFoundError(set_name)

		else:
			try:
				return len(settings[setting_name])

			except KeyError:
				raise SettingNotFoundError(set_name, setting_name)

	def _indexSetting(self, setting, set_name):
		'''
		Add a setting to the index.

		Parameters
		----------
		setting : SimulationSetting
			The setting to index.

		set_name : str
			The name of the set the setting belongs to.
		'''

		if not(set_name in self._indexed_settings['local']):
			self._indexed_settings['local'][set_name] = {}

		indexes = []

		for indexes_dict in [self._indexed_settings['global'], self._indexed_settings['local'][set_name]]:
			try:
				indexes_dict[setting.name].append(setting)

			except KeyError:
				indexes_dict[setting.name] = [setting]

			indexes.append(len(indexes_dict[setting.name]) - 1)

		setting.setIndexes(*indexes)

	def _addRawSettingsSet(self, set_name, default_settings, values_set = {}):
		'''
		Add a raw settings set to the list.

		Parameters
		----------
		set_name : str
			Name of the set.

		default_settings : list
			List of the default settings of this set.

		values_set : dict
			Values to override the defaults.
		'''

		set_to_add = copy.deepcopy(default_settings)

		for setting in set_to_add:
			self._indexSetting(setting, set_name)

			try:
				setting.value = values_set[setting.name]

			except KeyError:
				pass

		try:
			self._raw_settings[set_name].append(set_to_add)

		except KeyError:
			self._raw_settings[set_name] = [set_to_add]

	def generateSettings(self):
		'''
		Generate the full list of settings, taking into account the user settings and the default values in the folder.
		The "raw settings" are generated.
		Each set of settings is a list of all settings in this set.
		'''

		if type(self._user_settings['settings']) is list:
			user_settings = {
				setting_set_name: [s['settings'] for s in self._user_settings['settings'] if s['set'] == setting_set_name]
				for setting_set_name in set([s['set'] for s in self._user_settings['settings']])
			}

		else:
			user_settings = self._user_settings['settings']

		default_pattern = self._folder.settings['setting_pattern']

		self._raw_settings = {}
		self._indexed_settings = {'global': {}, 'local': {}}

		for settings_set in self._folder.settings['settings']:
			default_settings = [
				SimulationSetting(self, settings_set['set'], s['name'])
				for s in settings_set['settings']
			]

			try:
				values_sets = user_settings[settings_set['set']]

			except KeyError:
				if settings_set['required']:
					self._addRawSettingsSet(settings_set['set'], default_settings)

			else:
				if not(type(values_sets) is list):
					values_sets = [values_sets]

				for values_set in values_sets:
					self._addRawSettingsSet(settings_set['set'], default_settings, values_set)

	def getSettingValueFromTag(self, match):
		'''
		Retrieve the value of a setting from a setting tag.

		Parameters
		----------
		match : re.Match
			Match object corresponding to a setting tag.

		Raises
		------
		SettingTagNotRecognizedError
			The setting tag has not been recognized/does not refer to an existing setting.

		Returns
		-------
		setting : mixed
			The value of the setting.
		'''

		try:
			if match.group('category') == 'globalsetting':
				return [
					setting.value
					for setting in self._globalsettings
					if setting.name == match.group('name')
				][0]

			set_dict = self._indexed_settings['global'] if match.group('setname') is None else self._indexed_settings['local'][match.group('setname')]
			set_list = set_dict[match.group('name')]

			k = 0 if match.group('index') is None else int(match.group('index'))

			return set_list[k].value

		except:
			raise SettingTagNotRecognizedError(match.group(0))

	def replaceSettingTag(self, match):
		'''
		Replace a setting tag (`{setting[set_name](k):setting_name}`) by the value of the right setting.
		To be called by `re.sub()`.

		Parameters
		----------
		match : re.Match
			Match object corresponding to a setting tag.

		Returns
		-------
		setting_value : str
			The value of the setting.
		'''

		try:
			return str(self.getSettingValueFromTag(match))

		except SettingTagNotRecognizedError:
			return match.group(0)

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

		# If the string is not a string, we don't have anything to do (seems reasonable!)
		# Then, we test if the string represents a number, so we can cast it

		if not(type(s) is str):
			return s

		try:
			return float(s)

		except ValueError:
			pass

		s = s.strip()

		# We search for settings tags in the string, and recursively replace them

		if self._raw_settings is None:
			self.generateSettings()

		fullmatch = self._setting_tag_regex.fullmatch(s)

		if fullmatch:
			try:
				return copy.deepcopy(self.getSettingValueFromTag(fullmatch))

			except KeyError:
				return s

		parsed = self._setting_tag_regex.sub(self.replaceSettingTag, s)

		self._parser_recursion_stack.append(s)

		if not(parsed in self._parser_recursion_stack):
			return self.parseString(parsed)

		self._parser_recursion_stack.clear()

		# Final step: we try to evaluate the needed parts of the string to apply allowed operations, if any.
		# ValueError is raised if the string contains any unallowed operation, like the use of exec() or other evil functions.

		try:
			fullmatch = self._eval_tag_regex.fullmatch(parsed)

			if fullmatch:
				parsed = string.safeEval(fullmatch.group(1))

			else:
				parsed = self._eval_tag_regex.sub(lambda m: str(string.safeEval(m.group(1))), parsed)

		except (SyntaxError, ValueError):
			pass

		return parsed

class SimulationBaseSetting(abc.ABC):
	'''
	Represent a setting, either global or normal (abstract class).

	Parameters
	----------
	simulation : Simulation
		The simulation using this setting.

	setting_name : str
		Name of the setting.

	setting_value : mixed
		Default value of the setting.
	'''

	def __init__(self, simulation, setting_name, setting_value):
		self._simulation = simulation

		self._name = setting_name
		self._value = setting_value

	def __deepcopy__(self, memo):
		'''
		Override the default behavior of `deepcopy()` to keep the references to the Simulation.
		'''

		cls = self.__class__
		result = cls.__new__(cls)
		memo[id(self)] = result

		for k, v in self.__dict__.items():
			if k == '_simulation':
				setattr(result, k, v)

			else:
				setattr(result, k, copy.deepcopy(v, memo))

		return result

	@property
	def name(self):
		'''
		Getter for the setting name.

		Returns
		-------
		name : str
			Name of the setting.
		'''

		return self._name

	@property
	def value(self):
		'''
		Getter for the setting value, with fixers applied.

		Returns
		-------
		value : mixed
			Value of the setting.
		'''

		try:
			fixers = self._fixers

		except AttributeError:
			fixers = {}

		return self._simulation.folder.applyFixers(self._simulation.parseString(self._value), **fixers)

	@value.setter
	def value(self, new_value):
		'''
		Setter for the setting value.

		Parameters
		----------
		new_value : mixed
			New value of the setting
		'''

		self._value = new_value

class SimulationGlobalSetting(SimulationBaseSetting):
	'''
	Represent a global setting.
	'''

	pass

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
