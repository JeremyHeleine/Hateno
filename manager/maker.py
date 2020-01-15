#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from manager.manager import Manager
from manager.generator import Generator
from manager.remote import RemoteFolder

class Maker():
	'''
	Assemble all components to extract simulations and automatically create them if they don't exist.

	Parameters
	----------
	simulations_folder : str
		The simulations folder. Must contain a settings file.

	remote_folder_conf : str
		Path to the configuration file of the remote folder.
	'''

	def __init__(self, simulations_folder, remote_folder_conf):
		self._simulations_folder = simulations_folder
		self._remote_folder_conf = remote_folder_conf

		self._manager_instance = None
		self._generator_instance = None
		self._remote_folder_instance = None

	@property
	def _manager(self):
		'''
		Returns the instance of Manager used in the Maker.

		Returns
		-------
		manager : Manager
			Current instance, of a new one if `None`.
		'''

		if not(self._manager_instance):
			self._manager_instance = Manager(self._simulations_folder)

		return self._manager_instance

	@property
	def _generator(self):
		'''
		Returns the instance of Generator used in the Maker.

		Returns
		-------
		generator : Generator
			Current instance, of a new one if `None`.
		'''

		if not(self._generator_instance):
			self._generator_instance = Generator(self._simulations_folder)

		return self._generator_instance

	@property
	def _remote_folder(self):
		'''
		Returns the instance of Manager used in the Maker.

		Returns
		-------
		manager : Manager
			Current instance, of a new one if `None`.
		'''

		if not(self._remote_folder_instance):
			self._remote_folder_instance = RemoteFolder(self._remote_folder_conf)

		return self._remote_folder_instance

	def close(self):
		'''
		Clear all instances of the modules.
		'''

		self._manager_instance = None
		self._generator_instance = None

		try:
			self._remote_folder_instance.close()

		except AttributeError:
			pass

		self._remote_folder_instance = None

	def run(self, simulations):
		'''
		Main loop, run until all simulations are extracted or some jobs failed.

		Parameters
		----------
		simulations : list
			List of simulations to extract/generate.
		'''

		unknown_simulations = self._manager.batchExtract(simulations)
