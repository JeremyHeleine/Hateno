#!/usr/bin/env python3
# -*- coding: utf-8 -*-

class Error(Exception):
	'''
	Base class for exceptions occurring in the manager.
	'''

	pass

class SettingsSetNotFoundError(Error):
	'''
	Exception raised when a settings set has not been found.

	Parameters
	----------
	set_name : str
		Name of the set.
	'''

	def __init__(self, set_name):
		self.set_name = set_name

class SettingNotFoundError(Error):
	'''
	Exception raise when a setting has not been found in a given set.

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

class SimulationFolderNotFoundError(Error):
	'''
	Exception raised when we try to add a simulation to the manager, but the indicated folder does not exist.

	Parameters
	----------
	folder : str
		The folder which has not been found.
	'''

	def __init__(self, folder):
		self.folder = folder

class CheckersCategoryNotFoundError(Error):
	'''
	Exception raised when we try to access a checkers category which does not exist.

	Parameters
	----------
	category : str
		The category which has not been found.
	'''

	def __init__(self, category):
		self.category = category

class CheckerNotFoundError(Error):
	'''
	Exception raised when we try to access a checker which does not exist.

	Parameters
	----------
	category : str
		The checker's category.

	checker_name : str
		The name of the checker which has not been found.
	'''

	def __init__(self, category, checker_name):
		self.category = category
		self.checker_name = checker_name

class VariableGeneratorNotFoundError(Error):
	'''
	Exception raised when we try to access a variable generator which does not exist.

	Parameters
	----------
	generator_name : str
		Name of the generator which has not been found.
	'''

	def __init__(self, generator_name):
		self.generator_name = generator_name

class FixerNotFoundError(Error):
	'''
	Exception raised when we try to access a value fixer which does not exist.

	Parameters
	----------
	fixer_name : str
		Name of the fixer which has not been found.
	'''

	def __init__(self, fixer_name):
		self.fixer_name = fixer_name

class SimulationIntegrityCheckFailedError(Error):
	'''
	Exception raised when a folder fails to pass an integrity check.

	Parameters
	----------
	folder : str
		The folder which has not been found.
	'''

	def __init__(self, folder):
		self.folder = folder

class SimulationNotFoundError(Error):
	'''
	Exception raised when we look for a non existing simulation.

	Parameters
	----------
	simulation : str
		The name of the simulation which has not been found.
	'''

	def __init__(self, simulation):
		self.simulation = simulation

class SimulationFolderAlreadyExistError(Error):
	'''
	Exception raised when the folder of a simulation already exists.

	Parameters
	----------
	folder : str
		The name of the folder which should not exist.
	'''

	def __init__(self, folder):
		self.folder = folder

class EmptyListError(Error):
	'''
	Exception raised when a specific list is empty.
	'''

	pass

class DestinationFolderExistsError(Error):
	'''
	Exception raised when a destination folder already exists.
	'''

	pass

class ScriptNotFoundError(Error):
	'''
	Exception raised when a given script does not exist.

	Parameters
	----------
	script_coords : dict
		Coordinates of the script which has not been found.
	'''

	def __init__(self, script_coords):
		self.script_coords = script_coords

class RemotePathNotFoundError(Error):
	'''
	Exception raised when we try to access a remote path/directory which does not exist.

	Parameters
	----------
	remote_path : str
		The path.
	'''

	def __init__(self, remote_path):
		self.remote_path = remote_path

class UILineNotFoundError(Error):
	'''
	Exception raised when we try to access to a UI line which does not exist.

	Parameters
	----------
	id : str
		The ID of the unknown line.
	'''

	def __init__(self, id):
		self.id = id

class UIProgressBarNotFoundError(Error):
	'''
	Exception raised when we try to access to a UI progress bar which does not exist.

	Parameters
	----------
	id : str
		The ID of the unknown progress bar.
	'''

	def __init__(self, id):
		self.id = id

class UINonMovableLine(Error):
	'''
	Exception raised when we try to move a line which can't be moved.

	Parameters
	----------
	pos : int
		Position of the line.
	'''

	def __init__(self, pos):
		self.pos = pos

class WatcherNoConfigFoundError(Error):
	'''
	Exception raised when nothing is used to configure the watcher.
	'''

	pass

class WatcherTooManyConfigError(Error):
	'''
	Exception raised when there is more than one configuration for the watcher.
	'''

	pass

class WatcherNoRemoteFolderError(Error):
	'''
	Exception raised when we try to use the watcher's remote folder while there is no one set.
	'''

	pass

class WatcherNoStatesPathError(Error):
	'''
	Exception raised when we try to access the file containing the jobs states and there is no one set.
	'''

	pass

class WatcherNoMailConfigError(Error):
	'''
	Exception raised when we try to connect to the mailbox and no configuration file is given.
	'''

	pass

class WatcherNoMailNotificationsConfigError(Error):
	'''
	Exception raised when we try to access the mails notifications configuration without any configuration file provided.
	'''

	pass
