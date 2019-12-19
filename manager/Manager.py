#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import errno

import copy

from utils import json

"""
Manage a simulations folder: add, delete, extract or update simulations, based on their settings.
"""

class Manager():
	"""
	Initialize the manager with the folder to manage: load the settings and the current list of simulations.

	:param str folder:
		The folder to manage. Must contain a settings file.
	"""

	def __init__(self, folder):
		self._folder = folder
		self._settings_file = os.path.join(self._folder, '.simulations.conf')

		if not(os.path.isfile(self._settings_file)):
			raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), self._settings_file)

		self._settings = json.read(self._settings_file)

		self._simulations_list_file = os.path.join(self._folder, '.simulations.list')
		self._simulations_list = {}

		if os.path.isfile(self._simulations_list_file):
			self._simulations_list = json.read(self._simulations_list_file)

	"""
	Generate the full set of settings for a simulation.

	:param dict settings:
		Values of some settings for the simulation.

	:return dict:
		The full set of settings, with default values if needed.
	"""

	def generateSettings(self, settings):
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

			full_settings += sets_to_add

		return full_settings
