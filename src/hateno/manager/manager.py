#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime
import errno
import os
import shutil
import tarfile

from .errors import *
from ..folder import Folder
from ..simulation import Simulation
from ..utils import jsonfiles, string

class Manager():
	'''
	Manage a simulations folder: add, delete, extract or update simulations, based on their settings.

	Parameters
	----------
	folder : Folder|string
		The folder to manage. Either a `Folder` instance or the path to the folder (used to create a `Folder` instance).

	readonly : bool
		If `True`, open an instance in "read only" mode. Running indicator file is ignored, but only extraction is allowed.

	Raises
	------
	ManagerAlreadyRunningError
		A Manager instance is already running.
	'''

	def __init__(self, folder, *, readonly = False):
		self._folder = folder if type(folder) is Folder else Folder(folder)

		self._simulations_list_dict = None

		self._readonly = readonly

		self._delete_running_indicator = False

		if not(self._readonly):
			if os.path.isfile(self._folder.running_manager_indicator_filename):
				self._delete_running_indicator = False
				raise ManagerAlreadyRunningError()

			# Add a file into the configuration folder to indicate a Manager instance is currently running
			with open(self._folder.running_manager_indicator_filename, 'w') as f:
				f.write(str(datetime.datetime.now()))

			self._delete_running_indicator = True

	def __enter__(self):
		'''
		Context manager so we can use `with` instead of manually calling `close()`.
		'''

		return self

	def __exit__(self, type, value, traceback):
		'''
		Ensure `close()` is called when exiting the context manager.
		'''

		self.close()

	def close(self):
		'''
		Delete the "running indicator".
		Should always be called before destroying the instance to ensure the indicator is deleted.
		'''

		if self._delete_running_indicator:
			os.unlink(self._folder.running_manager_indicator_filename)

	@property
	def folder(self):
		'''
		Return the `Folder` instance.

		Returns
		-------
		folder : Folder
			The instance used by the manager.
		'''

		return self._folder

	@property
	def _simulations_list(self):
		'''
		Return the simulations list.

		Returns
		-------
		simulations_list : dict
			A name: settings dictionary.
		'''

		if self._simulations_list_dict is None:
			try:
				self._simulations_list_dict = jsonfiles.read(self._folder.simulations_list_filename)

			except FileNotFoundError:
				self._simulations_list_dict = {}

		return self._simulations_list_dict

	def saveSimulationsList(self):
		'''
		Save the list of simulations.

		Raises
		------
		ManagerOperationNotAllowed
			The list cannot be written in read only mode.
		'''

		if self._readonly:
			raise ManagerOperationNotAllowed()

		jsonfiles.write(self._simulations_list, self._folder.simulations_list_filename)

	def compress(self, folder, simulation_name):
		'''
		Create an archive to store a simulation.

		Parameters
		----------
		folder : str
			Folder to compress.

		simulation_name : str
			Name to use for the archive.
		'''

		with tarfile.open(os.path.join(self._folder.simulations_folder, f'{simulation_name}.tar.bz2'), 'w:bz2') as tar:
			tar.add(folder, arcname = simulation_name)

		shutil.rmtree(folder)

	def uncompress(self, simulation_name, folder):
		'''
		Extract a simulation from an archive.

		Parameters
		----------
		simulation_name : str
			Name of the archive to extract.

		folder : str
			Folder into which the files must go.
		'''

		with tarfile.open(os.path.join(self._folder.simulations_folder, f'{simulation_name}.tar.bz2'), 'r:bz2') as tar:
			tar.extractall(path = self._folder.tmp_folder)

		if os.path.isdir(folder):
			os.rmdir(folder)

		shutil.move(os.path.join(self._folder.tmp_folder, simulation_name), folder)

	def getSimulationsNumber(self):
		'''
		Returns the total number of simulations stored in the folder.

		Returns
		-------
		n : int
			The number of simulations.
		'''

		return len(self._simulations_list)

	def settingsOf(self, simulation_id):
		'''
		Return the whole settings set of a simulation.

		Parameters
		----------
		simulation_id : str
			Identifier of the simulation, either its name or its hashed settings.

		Raises
		------
		SimulationNotFoundError
			The simulation does not exist in the list.

		Returns
		-------
		settings : dict
			Settings of the simulation.
		'''

		try:
			if len(simulation_id) == 32:
				settings_str = [infos['settings'] for infos in self._simulations_list.values() if infos['name'] == simulation_id][0]

			else:
				settings_str = self._simulations_list[simulation_id]['settings']

		except (IndexError, KeyError):
			raise SimulationNotFoundError(simulation_id)

		else:
			return string.toObject(settings_str)

	def exists(self, simulation):
		'''
		Check whether a simulation does exist in the folder.

		Parameters
		----------
		simulation : Simulation|dict
			The simulation to check the existence of.

		Returns
		-------
		exists : bool
			`True` if the simulation exists, `False` otherwise.
		'''

		simulation = Simulation.ensureType(simulation, self._folder)
		settings_hashed = string.hash(string.fromObject(simulation.settings))

		return (settings_hashed in self._simulations_list)

	def add(self, simulation, *, save_list = True):
		'''
		Add a simulation to the list.

		Parameters
		----------
		simulation : Simulation|dict
			The simulation to add.

		save_list : boolean
			`True` to save the simulations list, `False` otherwise.

		Raises
		------
		ManagerOperationNotAllowed
			Addition is not allowed in read only mode.

		SimulationFolderNotFoundError
			The folder indicated in the simulation does not exist.

		SimulationIntegrityCheckFailedError
			At least one integrity check failed.
		'''

		if self._readonly:
			raise ManagerOperationNotAllowed()

		simulation = Simulation.ensureType(simulation, self._folder)

		if not(os.path.isdir(simulation['folder'])):
			raise SimulationFolderNotFoundError(simulation['folder'])

		settings_str = string.fromObject(simulation.settings)
		settings_hashed = string.hash(settings_str)
		simulation_name = string.uniqueID()

		if not(self._folder.checkIntegrity(simulation)):
			raise SimulationIntegrityCheckFailedError(simulation['folder'])

		self.compress(simulation['folder'], simulation_name)

		self._simulations_list[settings_hashed] = {
			'name': simulation_name,
			'added': datetime.datetime.now().isoformat(sep = ' ', timespec = 'seconds'),
			'settings': settings_str
		}

		if save_list:
			self.saveSimulationsList()

	def addFromFolder(self, folder, *, save_list = True, settings_file = 'settings.json'):
		'''
		Add a simulation from its folder.

		Parameters
		----------
		folder : str
			Path to the folder to add.

		save_list : boolean
			`True` to save the simulations list, `False` otherwise.

		settings_file : str
			Name of the file containing the settings.

		Raises
		------
		ManagerOperationNotAllowed
			Addition is not allowed in read only mode.

		SimulationFolderNotFoundError
			The indicated folder does not exist.

		SimulationIntegrityCheckFailedError
			At least one integrity check failed.
		'''

		if self._readonly:
			raise ManagerOperationNotAllowed()

		if not(os.path.isdir(folder)):
			raise SimulationFolderNotFoundError(folder)

		settings_filepath = os.path.join(folder, settings_file)
		settings = jsonfiles.read(settings_filepath)

		os.unlink(settings_filepath)

		try:
			self.add({
				'folder': folder,
				'settings': settings
			}, save_list = save_list)

		except SimulationIntegrityCheckFailedError:
			jsonfiles.write(settings, settings_filepath)
			raise

	def delete(self, simulation, *, save_list = True):
		'''
		Delete a simulation.

		Parameters
		----------
		simulation : Simulation|dict
			The simulation to delete.

		save_list : boolean
			`True` to save the simulations list, `False` otherwise.

		Raises
		------
		ManagerOperationNotAllowed
			Deletion is not allowed in read only mode.

		SimulationNotFoundError
			The simulation does not exist in the list.
		'''

		if self._readonly:
			raise ManagerOperationNotAllowed()

		simulation = Simulation.ensureType(simulation, self._folder)
		settings_hashed = string.hash(string.fromObject(simulation.settings))

		if not(settings_hashed in self._simulations_list):
			raise SimulationNotFoundError(settings_hashed)

		simulation_name = self._simulations_list[settings_hashed]['name']

		os.unlink(os.path.join(self._folder.simulations_folder, f'{simulation_name}.tar.bz2'))
		del self._simulations_list[settings_hashed]

		if save_list:
			self.saveSimulationsList()

	def deleteFromFolder(self, folder, *, save_list = True, settings_file = 'settings.json'):
		'''
		Delete a simulation from its folder.

		Parameters
		----------
		folder : str
			Path to the folder to delete.

		save_list : boolean
			`True` to save the simulations list, `False` otherwise.

		settings_file : str
			Name of the file containing the settings.

		Raises
		------
		ManagerOperationNotAllowed
			Deletion is not allowed in read only mode.

		SimulationFolderNotFoundError
			The indicated folder does not exist.
		'''

		if self._readonly:
			raise ManagerOperationNotAllowed()

		if not(os.path.isdir(folder)):
			raise SimulationFolderNotFoundError(folder)

		settings = jsonfiles.read(os.path.join(folder, settings_file))

		self.delete({
			'folder': folder,
			'settings': settings
		}, save_list = save_list)

	def extract(self, simulation, *, settings_file = None):
		'''
		Extract a simulation.

		Parameters
		----------
		simulation : Simulation|dict
			The simulation to extract.

		settings_file : str
			Name of the file to create to store the simulation's settings.

		Raises
		------
		SimulationNotFoundError
			The simulation does not exist in the list.

		SimulationFolderAlreadyExistError
			The destination of extraction already exists.
		'''

		simulation = Simulation.ensureType(simulation, self._folder)
		settings_hashed = string.hash(string.fromObject(simulation.settings))

		if not(settings_hashed in self._simulations_list):
			raise SimulationNotFoundError(settings_hashed)

		if os.path.exists(simulation['folder']):
			raise SimulationFolderAlreadyExistError(simulation['folder'])

		simulation_name = self._simulations_list[settings_hashed]['name']

		destination_path = os.path.dirname(os.path.normpath(simulation['folder']))
		if destination_path and not(os.path.isdir(destination_path)):
			os.makedirs(destination_path)

		self.uncompress(simulation_name, simulation['folder'])

		if settings_file:
			simulation.writeSettingsFile(settings_file)

	def batchAction(self, simulations, action, args = {}, *, save_list = True, errors_store = (), errors_pass = (Exception), callback = None):
		'''
		Apply a callback function to each simulation of a given list.

		Parameters
		----------
		simulations : list
			List of simulations.

		action : function
			Function to call. The simulation will be passed as the first parameter.

		args : dict
			Additional named arguments to pass to the callback.

		save_list : boolean
			`True` to save the simulations list once the loop is over, `False` to not save it.

		errors_store : tuple
			List of exceptions that, when raised, lead to the storage of the involved simulation.

		errors_pass : tuple
			List of exceptions that, when raised, do nothing.

		callback : function
			Function to call at the end of each action.

		Returns
		-------
		errors : list
			List of simulations which raised an error.
		'''

		errors = []

		for simulation in simulations:
			try:
				action(simulation, **args)

			except errors_store:
				errors.append(simulation)

			except errors_pass:
				pass

			if not(callback is None):
				callback()

		if save_list:
			self.saveSimulationsList()

		return errors

	def batchAdd(self, simulations, *, callback = None):
		'''
		Add multiple simulations to the list.

		Parameters
		----------
		simulations : list
			List of simulations.

		callback : function
			Function to call at the end of each addition.

		Returns
		-------
		errors : list
			List of simulations that were not added because they raised an error.
		'''

		return self.batchAction(simulations, self.add, {'save_list': False}, save_list = True, errors_store = (SimulationFolderNotFoundError, SimulationIntegrityCheckFailedError), callback = callback)

	def batchAddFromFolder(self, folders, *, settings_file = 'settings.json', callback = None):
		'''
		Add multiple simulations from their folders.

		Parameters
		----------
		folders : list
			List of folders.

		callback : function
			Function to call at the end of each addition.

		Returns
		-------
		errors : list
			List of simulations that were not added because they raised an error.
		'''

		return self.batchAction(folders, self.addFromFolder, {'settings_file': settings_file, 'save_list': False}, save_list = True, errors_store = (SimulationFolderNotFoundError, SimulationIntegrityCheckFailedError), callback = callback)

	def batchDelete(self, simulations, *, callback = None):
		'''
		Delete multiple simulations.

		Parameters
		----------
		simulations : list
			List of simulations.

		callback : function
			Function to call at the end of each deletion.

		Returns
		-------
		errors : list
			List of simulations that were not deleted because they raised an error.
		'''

		return self.batchAction(simulations, self.delete, {'save_list': False}, save_list = True, errors_store = (SimulationNotFoundError), callback = callback)

	def batchDeleteFromFolder(self, folders, *, settings_file = 'settings.json', callback = None):
		'''
		Delete multiple simulations from their folders.

		Parameters
		----------
		folders : list
			List of folders.

		callback : function
			Function to call at the end of each deletion.

		Returns
		-------
		errors : list
			List of simulations that were not deleted because they raised an error.
		'''

		return self.batchAction(folders, self.deleteFromFolder, {'settings_file': settings_file, 'save_list': False}, save_list = True, errors_store = (SimulationNotFoundError), callback = callback)

	def batchExtract(self, simulations, *, settings_file = None, ignore_existing = True, callback = None):
		'''
		Extract multiple simulations.

		Parameters
		----------
		simulations : list
			List of simulations.

		ignore_existing : boolean
			Ignore simulations for which the destination folder already exists.

		callback : function
			Function to call at the end of each extraction.

		Returns
		-------
		errors : list
			List of simulations that were not extracted because they raised an error.
		'''

		if ignore_existing:
			errors_store = (SimulationNotFoundError,)
			errors_pass = (SimulationFolderAlreadyExistError,)

		else:
			errors_store = (SimulationNotFoundError, SimulationFolderAlreadyExistError)
			errors_pass = ()

		return self.batchAction(simulations, self.extract, {'settings_file': settings_file}, save_list = False, errors_store = errors_store, errors_pass = errors_pass, callback = callback)

	def update(self, callback = None):
		'''
		Update the simulations list to take into account new settings.
		If the archive no longer exists, remove it from the simulations list.

		Parameters
		----------
		callback : function
			Function to call at each treated simulation.

		Raises
		------
		ManagerOperationNotAllowed
			Updating is not allowed in read only mode.
		'''

		if self._readonly:
			raise ManagerOperationNotAllowed()

		new_simulations_list = {}

		for settings_hashed, infos in self._simulations_list.items():
			if os.path.isfile(os.path.join(self._folder.simulations_folder, f'{infos["name"]}.tar.bz2')):
				simulation = Simulation.ensureType({
					'folder': '',
					'settings': string.toObject(infos['settings'])
				}, self._folder)

				settings_str = string.fromObject(simulation.settings)
				settings_hashed = string.hash(settings_str)

				new_simulations_list[settings_hashed] = {
					**infos,
					**{'settings': settings_str}
				}

			if not(callback is None):
				callback()

		self._simulations_list_dict = new_simulations_list
		self.saveSimulationsList()

	def transform(self, transformation, simulations_settings = None, callback = None):
		'''
		Apply a transformation operation to a given list of simulations, e.g. to store new informations.

		Parameters
		----------
		transformation : function
			Transformation to apply. This function must accept the following parameters.

				simulation : Simulation
					A Simulation object representing the settings of the current simulation.

			The function returns the new settings of the simulation.
			If `None`, the settings are not changed.

		simulations_settings : list
			List of simulations to transform (only their settings). If `None`, will transform all the stored simulations.

		callback : function
			Function to call once a simulation has been transformed.

		Raises
		------
		ManagerOperationNotAllowed
			Transformation is not allowed in read only mode.
		'''

		if self._readonly:
			raise ManagerOperationNotAllowed()

		if not(simulations_settings):
			simulations_settings = [string.toObject(infos['settings']) for infos in self._simulations_list.values()]

		for settings in simulations_settings:
			simulation_dir = self._folder.tempdir()

			simulation = Simulation.ensureType({
				'folder': simulation_dir,
				'settings': settings
			}, self._folder)

			settings_hashed = string.hash(string.fromObject(simulation.settings))
			simulation_infos = self._simulations_list[settings_hashed]

			self.uncompress(simulation_infos['name'], simulation_dir)
			new_settings = transformation(simulation)
			os.unlink(os.path.join(self._folder.simulations_folder, f'{simulation_infos["name"]}.tar.bz2'))
			self.compress(simulation_dir, simulation_infos['name'])

			if not(new_settings is None):
				new_simulation = Simulation.ensureType({
					'folder': simulation_dir,
					'settings': new_settings
				}, self._folder)

				new_settings_str = string.fromObject(new_simulation.settings)
				new_settings_hashed = string.hash(new_settings_str)

				del self._simulations_list[settings_hashed]

				self._simulations_list[new_settings_hashed] = {
					**simulation_infos,
					**{'settings': new_settings_str}
				}

				self.saveSimulationsList()

			if not(callback is None):
				callback()

	def clear(self, callback = None):
		'''
		Delete all simulations in the folder.

		Parameters
		----------
		callback : function
			Function to call at each deleted simulation.

		Raises
		------
		ManagerOperationNotAllowed
			Clearing is not allowed in read only mode.
		'''

		if self._readonly:
			raise ManagerOperationNotAllowed()

		for infos in self._simulations_list.values():
			os.unlink(os.path.join(self._folder.simulations_folder, f'{infos["name"]}.tar.bz2'))

			if not(callback is None):
				callback()

		self._simulations_list_dict = {}
		self.saveSimulationsList()
