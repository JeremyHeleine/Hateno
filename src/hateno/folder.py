#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

from . import jsonfiles

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

		return self._settings
