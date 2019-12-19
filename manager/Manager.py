#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import errno

import shutil
import copy
import tarfile

from utils import jsonfiles, string

"""
Base class for exceptions occurring in the manager.
"""

class Error(Exception):
	pass

"""
Exception raised when we try to add a simulation to the manager, but the indicated folder does not exist.
"""

class SimulationFolderNotFoundError(Error):
	"""
	Store the folder's name.

	:param str folder:
		The folder which has not been found.
	"""

	def __init__(self, folder):
		self.folder = folder

"""
Exception raised when a folder fails to pass an integrity check.
"""

class SimulationIntegrityCheckFailedError(Error):
	"""
	Store the folder's name.

	:param str folder:
		The folder which has not been found.
	"""

	def __init__(self, folder):
		self.folder = folder

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

		self._settings = jsonfiles.read(self._settings_file)

		self._simulations_list_file = os.path.join(self._folder, '.simulations.list')
		self._simulations_list = {}

		if os.path.isfile(self._simulations_list_file):
			self._simulations_list = jsonfiles.read(self._simulations_list_file)

	"""
	Save the list of simulations.
	"""

	def saveSimulationsList(self):
		jsonfiles.write(self._simulations_list, self._simulations_list_file)

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

	"""
	Check the integrity of a simulation.

	:param str folder:
		Folder containing the simulation files.

	:return bool:
		`True` if the integrity check is successful, `False` otherwise.
	"""

	def checkIntegrity(self, folder):
		return True

	"""
	Create an archive to store a simulation.

	:param str folder:
		Folder to compress.

	:param str simulation_name:
		Name to use for the archive.
	"""

	def compress(self, folder, simulation_name):
		with tarfile.open(os.path.join(self._folder, f'{simulation_name}.tar.bz2'), 'w:bz2') as tar:
			tar.add(folder, arcname = simulation_name)

		shutil.rmtree(folder)

	"""
	Add a simulation to the list.

	:param dict simulation:
		The simulation to add.
	"""

	def add(self, simulation):
		if not(os.path.isdir(simulation['folder'])):
			raise SimulationFolderNotFoundError(simulation['folder'])

		if not(self.checkIntegrity(simulation['folder'])):
			raise SimulationIntegrityCheckFailedError(simulation['folder'])

		full_settings = self.generateSettings(simulation['settings'])
		settings_str = string.fromObject(full_settings)
		simulation_name = string.hash(settings_str)

		self.compress(simulation['folder'], simulation_name)

		self._simulations_list[simulation_name] = settings_str
		self.saveSimulationsList()
