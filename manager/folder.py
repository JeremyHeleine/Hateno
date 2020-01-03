#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import copy

from utils import jsonfiles

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

		self._settings = jsonfiles.read(self._settings_file)

	def generateSettings(self, settings, as_strings = False):
		'''
		Generate the full set of settings for a simulation.

		Parameters
		----------
		settings : dict
			Values of some settings for the simulation.

		as_strings : boolean
			`True` to get a string representation of the settings, `False` to get them as a dictionary.

		Returns
		-------
		full_settings : dict
			The full set of settings, with default values if needed.
		'''

		full_settings = []
		for settings_set in self._settings['settings']:
			settings_pairs = {s['name']: s['default'] for s in settings_set['settings']}
			values_sets = [s['settings'] for s in settings if s['set'] == settings_set['set']]

			sets_to_add = []
			for values_set in values_sets:
				pairs = copy.deepcopy(settings_pairs)
				pairs.update(values_set)
				sets_to_add.append(pairs)

			if not(sets_to_add) and settings_set['required']:
				sets_to_add.append(settings_pairs)

			if as_strings:
				patterns = {
					s['name']: s['pattern'] if 'pattern' in s else self._settings['setting_pattern']
					for s in settings_set['settings']
				}

				full_settings += [
					[
						patterns[setting_name].format(name = setting_name, value = setting_value)
						for setting_name, setting_value in set_to_add.items()
					]
					for set_to_add in sets_to_add
				]

			else:
				full_settings += sets_to_add

		return full_settings
