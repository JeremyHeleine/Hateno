#!/usr/bin/env python3
# -*- coding: utf-8 -*-

class Error(Exception):
	'''
	Base class for exceptions occurring in the manager.
	'''

	pass

class OperationNotAllowed(Error):
	'''
	Exception raised when we try to perform an operation that is not allowed (e.g. write something in read only mode).
	'''

	pass

class NoConfigError(Error):
	'''
	Exception raised when we try to access a configuration but no foldername is given.
	'''

	pass

class ConfigNotFoundError(Error):
	'''
	Exception raised when we try to access a non-existing configuration folder.

	Parameters
	----------
	foldername : str
		Name of the folder.
	'''

	def __init__(self, foldername):
		self.foldername = foldername

class FCollectionCategoryNotFoundError(Error):
	'''
	Exception raised when we try to access a non-existing category of an FCollection.

	Parameters
	----------
	category : str
		Name of the category.
	'''

	def __init__(self, category):
		self.category = category

class FCollectionFunctionNotFoundError(Error):
	'''
	Exception raised when we try to access a non-existing function of an FCollection.

	Parameters
	----------
	fname : str
		Name of the function.
	'''

	def __init__(self, fname):
		self.fname = fname

class InvalidFilterRegexError(Error):
	'''
	Exception raised when we define the filter regex of an FCollection without the required groups.

	Parameters
	----------
	regex : str
		The invalid regex.
	'''

	def __init__(self, regex):
		self.regex = regex

class SettingTagNotRecognizedError(Error):
	'''
	Exception raised when we try to analyse a setting tag but it fails.

	Parameters
	----------
	setting_tag : str
		The invalid tag.
	'''

	def __init__(self, setting_tag):
		self.setting_tag = setting_tag

class JobAlreadyExistingError(Error):
	'''
	Exception raised when we try to add a job to manage that already exists.

	Parameters
	----------
	job_name : str
		Name of the job.
	'''

	def __init__(self, job_name):
		self.job_name = job_name

class JobNotFoundError(Error):
	'''
	Exception raised when we try to access a non existing job.

	Parameters
	----------
	job_name : str
		Name of the job.
	'''

	def __init__(self, job_name):
		self.job_name = job_name

class JobStateNotFoundError(Error):
	'''
	Exception raised when we try to read the state of a job from a dict, without the right key.
	'''

	pass

class UnknownJobStateError(Error):
	'''
	Exception raised when we try to use an unknown job state.

	Parameters
	----------
	state : str
		Name of the unknown state.
	'''

	def __init__(self, state):
		self.state = state

class ManagerAlreadyRunningError(Error):
	'''
	Exception raised when a instance of the Manager is created while another is still running.
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

class NamerNotFoundError(Error):
	'''
	Exception raised when we try to access a namer which does not exist.

	Parameters
	----------
	namer_name : str
		Name of the namer which has not been found.
	'''

	def __init__(self, namer_name):
		self.namer_name = namer_name

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

class EventUnknownError(Error):
	'''
	Exception raised when we try to use an unkown event.

	Parameters
	----------
	event : str
		Name of the event.
	'''

	def __init__(self, event):
		self.event = event

class MakerPausedError(Error):
	'''
	Exception raised when the Maker is paused while it should not be.
	'''

	pass

class MakerNotPausedError(Error):
	'''
	Exception raised when the Maker is not paused while it should be.
	'''

	pass

class MakerStateWrongFormatError(Error):
	'''
	Exception raised when we try to read a Maker state that is in the wrong format.
	'''

	pass

class ExplorerDepthNotFoundError(Error):
	'''
	Exception raised when we try to access a non existing depth in a map.

	Parameters
	----------
	depth : int
		The non existing depth.
	'''

	def __init__(self, depth):
		self.depth = depth

class ExplorerStopNotFoundError(Error):
	'''
	Exception raised when we try to access a stop that is not defined.

	Parameters
	----------
	depth : int
		The depth at which the stop was requested.
	'''

	def __init__(self, depth):
		self.depth = depth

class ExplorerSearchNoSolutionError(Error):
	'''
	Exception raised when we search in the wrong interval.
	'''

	pass
