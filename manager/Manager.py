#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import errno

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
