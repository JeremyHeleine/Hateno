#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import abc
import copy

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
