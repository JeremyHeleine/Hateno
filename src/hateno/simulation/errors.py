#!/usr/bin/env python3
# -*- coding: utf-8 -*-

class SimulationError(Exception):
	'''
	Base class for exceptions occurring in a Simulation.
	'''

	pass

class SettingNotFoundError(SimulationError):
	'''
	Exception raised when a setting has not been found in a given set.

	Parameters
	----------
	set_name : str
		Name of the set.

	setting_name : str
		Name of the setting
	'''

	def __init__(self, set_name, setting_name):
		self.set_name = set_name
		self.setting_name = setting_name


class SettingsSetNotFoundError(SimulationError):
	'''
	Exception raised when a settings set has not been found.

	Parameters
	----------
	set_name : str
		Name of the set.
	'''

	def __init__(self, set_name):
		self.set_name = set_name

class SettingTagNotRecognizedError(SimulationError):
	'''
	Exception raised when we try to analyse a setting tag but it fails.

	Parameters
	----------
	setting_tag : str
		The invalid tag.
	'''

	def __init__(self, setting_tag):
		self.setting_tag = setting_tag
