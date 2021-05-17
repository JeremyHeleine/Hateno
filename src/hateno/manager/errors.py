#!/usr/bin/env python3
# -*- coding: utf-8 -*-

class ManagerError(Exception):
	'''
	Base class for exceptions occurring in the Manager.
	'''

	pass

class ManagerAlreadyRunningError(ManagerError):
	'''
	Exception raised when a instance of the Manager is created while another is still running.
	'''

	pass

class ManagerOperationNotAllowed(ManagerError):
	'''
	Exception raised when we try to perform an operation that is not allowed (e.g. write something in read only mode).
	'''

	pass

class SimulationFolderAlreadyExistError(ManagerError):
	'''
	Exception raised when the folder of a simulation already exists.

	Parameters
	----------
	folder : str
		The name of the folder which should not exist.
	'''

	def __init__(self, folder):
		self.folder = folder

class SimulationFolderNotFoundError(ManagerError):
	'''
	Exception raised when we try to add a simulation to the manager, but the indicated folder does not exist.

	Parameters
	----------
	folder : str
		The folder which has not been found.
	'''

	def __init__(self, folder):
		self.folder = folder

class SimulationIntegrityCheckFailedError(ManagerError):
	'''
	Exception raised when a folder fails to pass an integrity check.

	Parameters
	----------
	folder : str
		The folder which has not been found.
	'''

	def __init__(self, folder):
		self.folder = folder

class SimulationNotFoundError(ManagerError):
	'''
	Exception raised when we look for a non existing simulation.

	Parameters
	----------
	simulation : str
		The name of the simulation which has not been found.
	'''

	def __init__(self, simulation):
		self.simulation = simulation
