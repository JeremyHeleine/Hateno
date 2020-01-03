#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from manager.folder import Folder

class Generator(Folder):
	'''
	Generate some scripts to create a set of simulations.
	Initialize the list of simulations to generate.

	Parameters
	----------
	folder : str
		The folder to manage. Must contain a settings file.
	'''

	def __init__(self, folder):
		super().__init__(folder)

		self._simulations_to_generate = []

	def add(self, simulations):
		'''
		Add simulations to generate.

		Parameters
		----------
		simulations : list|dict
			List of simulations to add.
		'''

		if type(simulations) is dict:
			self._simulations_to_generate.append(simulations)

		else:
			self._simulations_to_generate += simulations

	def clear(self):
		'''
		Clear the list of simulations to generate.
		'''

		self._simulations_to_generate.clear()

	def parse(self):
		'''
		Parse the current list of simulations to generate the corresponding command lines.

		Returns
		-------
		command_lines : list
			List of command lines, one per simulation to generate
		'''

		return [
			' '.join([self._settings['exec']] + sum(self.generateSettings(simulation['settings'], as_strings = True), []))
			for simulation in self._simulations_to_generate
		]
