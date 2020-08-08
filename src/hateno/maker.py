#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import stat
import time
import tempfile

from . import string, jsonfiles

from .fcollection import FCollection
from .folder import Folder
from .simulation import Simulation
from .manager import Manager
from .generator import Generator
from .remote import RemoteFolder
from .jobs import JobsManager, JobState
from .errors import *
from .ui import UI

class Maker():
	'''
	Assemble all components to extract simulations and automatically create them if they don't exist.

	Parameters
	----------
	simulations_folder : str
		The simulations folder. Must contain a settings file.

	remote_folder_conf : dict
		Configuration of the remote folder.

	generator_recipe : dict
		Recipe to use to generate the simulations.

	settings_file : str
		Name of the settings file to create (for the extraction).

	max_corrupted : int
		Maximum number of allowed corruptions. Corruptions counter is incremented each time at least one simulation is corrupted. If negative, there is no limit.

	max_failures : int
		Maximum number of allowed failures in the execution of a job. The counter is incremented each time at least one job fails. If negative, there is no limit.
	'''

	def __init__(self, simulations_folder, remote_folder_conf, *, generator_recipe = None, settings_file = None, max_corrupted = -1, max_failures = 0):
		self._simulations_folder = Folder(simulations_folder)
		self._remote_folder_conf = remote_folder_conf

		self._manager_instance = None
		self._generator_instance = None
		self._remote_folder_instance = None
		self._jobs_manager = JobsManager()

		self._settings_file = settings_file
		self._script_coords = None
		self._generator_recipe = None
		self.generator_recipe = generator_recipe

		self._simulations_to_extract = []
		self._unknown_simulations = []
		self._jobs_ids = []

		self._max_corrupted = max_corrupted
		self._corruptions_counter = 0

		self._max_failures = max_failures
		self._failures_counter = 0

		self._paused = False
		self._state_attrs = ['simulations_to_extract', 'corruptions_counter', 'failures_counter', 'unknown_simulations', 'jobs_ids', 'generator_recipe']

		self._events_callbacks = FCollection(categories = ['close-start', 'close-end', 'remote-open-start', 'remote-open-end', 'delete-scripts', 'paused', 'resume', 'run-start', 'run-end', 'extract-start', 'extract-end', 'extract-progress', 'generate-start', 'generate-end', 'wait-start', 'wait-progress', 'wait-end', 'download-start', 'download-progress', 'download-end', 'addition-start', 'addition-progress', 'addition-end'])

	def __enter__(self):
		'''
		Context manager to call `close()` at the end.
		'''

		return self

	def __exit__(self, type, value, traceback):
		'''
		Ensure `close()` is called when exiting the context manager.
		'''

		self.close()

	@property
	def folder(self):
		'''
		Return the `Folder` instance.

		Returns
		-------
		folder : Folder
			The instance used by the maker.
		'''

		return self._simulations_folder

	@property
	def manager(self):
		'''
		Returns the instance of Manager used in the Maker.

		Returns
		-------
		manager : Manager
			Current instance, or a new one if `None`.
		'''

		if not(self._manager_instance):
			self._manager_instance = Manager(self._simulations_folder)

		return self._manager_instance

	@property
	def generator(self):
		'''
		Returns the instance of Generator used in the Maker.

		Returns
		-------
		generator : Generator
			Current instance, or a new one if `None`.
		'''

		if not(self._generator_instance):
			self._generator_instance = Generator(self._simulations_folder)

		return self._generator_instance

	@property
	def _remote_folder(self):
		'''
		Returns the instance of RemoteFolder used in the Maker.

		Returns
		-------
		remote_folder : RemoteFolder
			Current instance, or a new one if `None`.
		'''

		if not(self._remote_folder_instance):
			self._remote_folder_instance = RemoteFolder(self._remote_folder_conf)

			self._triggerEvent('remote-open-start')
			self._remote_folder_instance.open()
			self._triggerEvent('remote-open-end')

		return self._remote_folder_instance

	def close(self):
		'''
		Clear all instances of the modules.
		'''

		self._triggerEvent('close-start')

		self._generator_instance = None

		try:
			self._manager_instance.close()

		except AttributeError:
			pass

		try:
			self._remote_folder_instance.close()

		except AttributeError:
			pass

		self._remote_folder_instance = None

		self._triggerEvent('close-end')

	def addEventListener(self, event, f):
		'''
		Add a callback function to a given event.

		Parameters
		----------
		event : str
			Name of the event.

		f : function
			Function to attach.

		Raises
		------
		EventUnknownError
			The event does not exist.
		'''

		try:
			self._events_callbacks.set(f.__name__, f, category = event)

		except FCollectionCategoryNotFoundError:
			raise EventUnknownError(event)

	def _triggerEvent(self, event, *args):
		'''
		Call all functions attached to a given event.

		Parameters
		----------
		event : str
			Name of the event to trigger.

		args : mixed
			Arguments to pass to the callback functions.

		Raises
		------
		EventUnknownError
			The event does not exist.
		'''

		try:
			functions = self._events_callbacks.getAll(category = event)

		except FCollectionCategoryNotFoundError:
			raise EventUnknownError(event)

		else:
			for f in functions:
				f(*args)

	@property
	def paused(self):
		'''
		Getter for the paused state.

		Returns
		-------
		paused : bool
			`True` if the Maker has been paused, `False` otherwise.
		'''

		return self._paused

	def pause(self):
		'''
		Pause the Maker.

		Raises
		------
		MakerPausedError
			The Maker is already in paused state.
		'''

		if self._paused:
			raise MakerPausedError()

		self._paused = True
		self._triggerEvent('paused')

	def resume(self):
		'''
		Resume after a pause.

		Returns
		-------
		unknown_simulations : list
			List of simulations that failed to be generated. `None` if the Maker has been paused.

		Raises
		------
		MakerNotPausedError
			The Maker is not in paused state.
		'''

		if not(self._paused):
			raise MakerNotPausedError()

		self._paused = False
		self._triggerEvent('resume')
		return self.run(self._simulations_to_extract)

	def saveState(self, filename):
		'''
		Save the current state of the Maker when it is paused.

		Parameters
		----------
		filename : str
			Name of the file to use to write the state.

		Raises
		------
		MakerNotPausedError
			The Maker is not in paused state.
		'''

		if not(self._paused):
			raise MakerNotPausedError()

		state = {attr: getattr(self, f'_{attr}') for attr in self._state_attrs}

		jsonfiles.write(state, filename)

	def loadState(self, filename):
		'''
		Load a state.

		Parameters
		----------
		filename : str
			Name of the file to use to read the state.

		Raises
		------
		MakerNotPausedError
			The Maker is not in paused state.

		MakerStateWrongFormatError
			At least one key is missing in the stored state.
		'''

		if not(self._paused):
			raise MakerNotPausedError()

		state = jsonfiles.read(filename)

		try:
			for attr in self._state_attrs:
				setattr(self, f'_{attr}', state[attr])

		except KeyError:
			raise MakerStateWrongFormatError()

	@property
	def generator_recipe(self):
		'''
		Get the current generator recipe.

		Returns
		-------
		recipe : dict
			Current recipe.
		'''

		return self._generator_recipe

	@generator_recipe.setter
	def generator_recipe(self, recipe):
		'''
		Define the recipe to use to generate the simulations.

		Parameters
		----------
		recipe : dict
			The recipe to use.
		'''

		self._generator_recipe = recipe
		self._parseScriptToLaunch()

	def _parseScriptToLaunch(self):
		'''
		Parse the `launch` option of a recipe to determine which skeleton/script must be called.
		'''

		option_split = self.generator_recipe['launch'].rsplit(':', maxsplit = 2)
		option_split_num = [string.intOrNone(s) for s in option_split]

		cut = max([k for k, n in enumerate(option_split_num) if n is None]) + 1

		coords = option_split_num[cut:]
		coords += [-1] * (2 - len(coords))

		self._script_coords = {
			'name': ':'.join(option_split[:cut]),
			'skeleton': coords[0],
			'script': coords[1]
		}

	def run(self, simulations, *, corruptions_counter = 0, failures_counter = 0):
		'''
		Main loop, run until all simulations are extracted or some jobs failed.

		Parameters
		----------
		simulations : list
			List of simulations to extract/generate.

		corruptions_counter : int
			Initial value of the corruptions counter.

		failures_counter : int
		 	Initial value of the failures counter.

		Returns
		-------
		unknown_simulations : list
			List of simulations that failed to be generated. `None` if the Maker has been paused.
		'''

		self._triggerEvent('run-start')

		self._simulations_to_extract = simulations

		self._corruptions_counter = corruptions_counter
		self._failures_counter = failures_counter

		while self._runLoop():
			pass

		if self.paused:
			return None

		self._triggerEvent('run-end', self._unknown_simulations)

		return self._unknown_simulations

	def _runLoop(self):
		'''
		One loop of the `run()` method.

		Returns
		-------
		continue : bool
			`True` to continue the loop, `False` to break it.
		'''

		if not(self._jobs_ids):
			self.extractSimulations()

			if not(self._unknown_simulations):
				return False

			self.generateSimulations()

		try:
			if not(self.waitForJobs()):
				self._failures_counter += 1

		except KeyboardInterrupt:
			self.pause()
			return False

		if not(self.downloadSimulations()):
			self._corruptions_counter += 1

		self._triggerEvent('delete-scripts')
		self._remote_folder.deleteRemote([self._generator_recipe['basedir']])

		return (self._max_corrupted < 0 or self._corruptions_counter <= self._max_corrupted) and (self._max_failures < 0 or self._failures_counter <= self._max_failures)

	def extractSimulations(self):
		'''
		Try to extract the simulations.
		'''

		self._triggerEvent('extract-start', self._simulations_to_extract)

		self._unknown_simulations = self.manager.batchExtract(self._simulations_to_extract, settings_file = self._settings_file, callback = lambda : self._triggerEvent('extract-progress'))

		self._triggerEvent('extract-end')

	def generateSimulations(self):
		'''
		Generate the scripts to generate the unknown simulations, and run them.

		Raises
		------
		ScriptNotFoundError
			The script to launch has not been found.

		Returns
		-------
		jobs_ids : list
			IDs of the jobs to wait.
		'''

		self._triggerEvent('generate-start')

		scripts_dir = tempfile.mkdtemp(prefix = 'simulations-scripts_')
		self._generator_recipe['basedir'] = self._remote_folder.sendDir(scripts_dir)

		self.generator.add(self._unknown_simulations)
		generated_scripts = self.generator.generate(scripts_dir, self._generator_recipe, empty_dest = True)
		self.generator.clear()

		possible_skeletons_to_launch = [
			k
			for k, s in enumerate(self._generator_recipe['subgroups_skeletons'] + self._generator_recipe['wholegroup_skeletons'])
			if s == self._script_coords['name']
		]

		try:
			script_to_launch = generated_scripts[possible_skeletons_to_launch[self._script_coords['skeleton']]][self._script_coords['script']]

		except IndexError:
			raise ScriptNotFoundError(self._script_coords)

		script_mode = os.stat(script_to_launch['localpath']).st_mode
		if not(script_mode & stat.S_IXUSR & stat.S_IXGRP & stat.S_IXOTH):
			os.chmod(script_to_launch['localpath'], script_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

		self._remote_folder.sendDir(scripts_dir, delete = True, empty_dest = True)

		output = self._remote_folder.execute(script_to_launch['finalpath'])
		self._jobs_ids = list(map(lambda l: l.strip(), output.readlines()))

		self._triggerEvent('generate-end')

	def waitForJobs(self):
		'''
		Wait for the jobs to finish.

		Returns
		-------
		success : bool
			`True` is all jobs were finished normally, `False` if there was at least one failure.
		'''

		self._triggerEvent('wait-start', self._jobs_ids)

		jobs_by_state = {}
		previous_states = {}

		self._jobs_manager.add(*self._jobs_ids, ignore_existing = True)
		self._jobs_manager.linkToFile(self._generator_recipe['jobs_states_filename'], remote_folder = self._remote_folder)

		while True:
			self._jobs_manager.updateFromFile()
			jobs_by_state = {
				state: self._jobs_manager.getJobsWithStates([JobState[state.upper()]])
				for state in ['waiting', 'running', 'succeed', 'failed']
			}

			if jobs_by_state != previous_states:
				self._triggerEvent('wait-progress', jobs_by_state)

				if set(jobs_by_state['succeed'] + jobs_by_state['failed']) == set(self._jobs_ids):
					break

			previous_states = jobs_by_state
			time.sleep(0.5)

		self._jobs_manager.clear()
		self._jobs_ids = []

		self._remote_folder.deleteRemote([self._generator_recipe['jobs_states_filename']])

		self._triggerEvent('wait-end')

		return not(jobs_by_state['failed'])

	def downloadSimulations(self):
		'''
		Download the generated simulations and add them to the manager.

		Returns
		-------
		success : bool
			`True` if all simulations has successfully been downloaded and added, `False` if there has been at least one issue.
		'''

		self._triggerEvent('download-start', self._unknown_simulations)

		simulations_to_add = []

		for simulation in self._unknown_simulations:
			simulation = Simulation.ensureType(simulation, self._simulations_folder)

			tmpdir = tempfile.mkdtemp(prefix = 'simulation_')
			try:
				self._remote_folder.receiveDir(simulation['folder'], tmpdir, delete = True)

			except RemotePathNotFoundError:
				pass

			simulation['folder'] = tmpdir
			simulations_to_add.append(simulation)

			self._triggerEvent('download-progress')

		self._triggerEvent('download-end')

		self._triggerEvent('addition-start', simulations_to_add)

		failed_to_add = self.manager.batchAdd(simulations_to_add, callback = lambda : self._triggerEvent('addition-progress'))

		self._triggerEvent('addition-end')

		return not(bool(failed_to_add))

class MakerUI(UI):
	'''
	UI to show the different steps of the Maker.

	Parameters
	----------
	maker : Maker
		Instance of the Maker from which the event are triggered.
	'''

	def __init__(self, maker):
		super().__init__()

		self._maker = maker

		self._state_line = None
		self._main_progress_bar = None

		self._statuses = 'Current statuses: {waiting} waiting, {running} running, {succeed} succeed, {failed} failed'
		self._statuses_line = None

		self._maker.addEventListener('close-start', self._closeStart)
		self._maker.addEventListener('close-end', self._closeEnd)
		self._maker.addEventListener('remote-open-start', self._remoteOpenStart)
		self._maker.addEventListener('remote-open-end', self._remoteOpenEnd)
		self._maker.addEventListener('delete-scripts', self._deleteScripts)
		self._maker.addEventListener('paused', self._paused)
		self._maker.addEventListener('resume', self._resume)
		self._maker.addEventListener('run-start', self._runStart)
		self._maker.addEventListener('run-end', self._runEnd)
		self._maker.addEventListener('extract-start', self._extractStart)
		self._maker.addEventListener('extract-progress', self._extractProgress)
		self._maker.addEventListener('extract-end', self._extractEnd)
		self._maker.addEventListener('generate-start', self._generateStart)
		self._maker.addEventListener('generate-end', self._generateEnd)
		self._maker.addEventListener('wait-start', self._waitStart)
		self._maker.addEventListener('wait-progress', self._waitProgress)
		self._maker.addEventListener('wait-end', self._waitEnd)
		self._maker.addEventListener('download-start', self._downloadStart)
		self._maker.addEventListener('download-progress', self._downloadProgress)
		self._maker.addEventListener('download-end', self._downloadEnd)
		self._maker.addEventListener('addition-start', self._additionStart)
		self._maker.addEventListener('addition-progress', self._additionProgress)
		self._maker.addEventListener('addition-end', self._additionEnd)

	def _updateState(self, state):
		'''
		Text line to display the current state of the Maker.

		Parameters
		----------
		state : str
			State to display.
		'''

		if self._state_line is None:
			self._state_line = self.addTextLine(state)

		else:
			self._state_line.text = state

	def _closeStart(self):
		'''
		Maker starts closing.
		'''

		pass

	def _closeEnd(self):
		'''
		Maker is closed.
		'''

		pass

	def _remoteOpenStart(self):
		'''
		Connection to the RemoteFolder is started.
		'''

		self._updateState('Connection…')

	def _remoteOpenEnd(self):
		'''
		Connected to the RemoteFolder.
		'''

		self._updateState('Connected')

	def _deleteScripts(self):
		'''
		Deletion of the scripts.
		'''

		self._updateState('Deleting the scripts…')

	def _paused(self):
		'''
		The Maker has been paused.
		'''

		# Erase the "^C" due to the keyboard interruption
		print('\r  ', end = '\r')

		if not(self._main_progress_bar is None):
			self.removeItem(self._main_progress_bar)
			self._main_progress_bar = None

		if not(self._statuses_line is None):
			self.removeItem(self._statuses_line)
			self._statuses_line = None

		self._updateState('Paused')

	def _resume(self):
		'''
		Resume after a pause.
		'''

		pass

	def _runStart(self):
		'''
		The run loop just started.
		'''

		self._updateState('Running the Maker…')

	def _runEnd(self, unknown_simulations):
		'''
		The run loop has ended.

		Parameters
		----------
		unknown_simulations : list
			List of simulations that still do not exist.
		'''

		if unknown_simulations:
			self._updateState(string.plural(len(unknown_simulations), 'simulation still does not exist', 'simulations still do not exist'))

		else:
			self._updateState('All simulations have successfully been extracted')

	def _extractStart(self, simulations):
		'''
		Start the extraction of the simulations.

		Parameters
		----------
		simulations : list
			List of the simulations that will be extracted.
		'''

		self._updateState('Extracting the simulations…')
		self._main_progress_bar = self.addProgressBar(len(simulations))

	def _extractProgress(self):
		'''
		A simulation has just been extracted.
		'''

		self._main_progress_bar.counter += 1

	def _extractEnd(self):
		'''
		All simulations have been extracted.
		'''

		self.removeItem(self._main_progress_bar)
		self._main_progress_bar = None
		self._updateState('Simulations extracted')

	def _generateStart(self):
		'''
		Start the generation of the scripts.
		'''

		self._updateState('Generating the scripts…')

	def _generateEnd(self):
		'''
		Scripts are generated.
		'''

		self._updateState('Scripts generated')

	def _waitStart(self, jobs_ids):
		'''
		Start to wait for some jobs.

		Parameters
		----------
		jobs_ids : list
			IDs of the jobs to wait.
		'''

		self._updateState('Waiting for jobs to finish…')
		self._main_progress_bar = self.addProgressBar(len(jobs_ids))
		self._statuses_line = self.addTextLine(self._statuses.format(waiting = 0, running = 0, succeed = 0, failed = 0))

	def _waitProgress(self, jobs_by_state):
		'''
		The state of at least one job has changed.

		Parameters
		----------
		jobs_by_state : dict
			The jobs IDs, sorted by their state.
		'''

		self._statuses_line.text = self._statuses.format(**{state: len(jobs) for state, jobs in jobs_by_state.items()})
		self._main_progress_bar.counter = len(jobs_by_state['succeed'] + jobs_by_state['failed'])

	def _waitEnd(self):
		'''
		All jobs are finished.
		'''

		self.removeItem(self._statuses_line)
		self._statuses_line = None

		self.removeItem(self._main_progress_bar)
		self._main_progress_bar = None

		self._updateState('Jobs finished')

	def _downloadStart(self, simulations):
		'''
		Start to download the simulations.

		Parameters
		----------
		simulations : list
			Simulations that will be downloaded.
		'''

		self._updateState('Downloading the simulations…')
		self._main_progress_bar = self.addProgressBar(len(simulations))

	def _downloadProgress(self):
		'''
		A simulation has just been downloaded.
		'''

		self._main_progress_bar.counter += 1

	def _downloadEnd(self):
		'''
		All simulations have been downloaded.
		'''

		self.removeItem(self._main_progress_bar)
		self._main_progress_bar = None
		self._updateState('Simulations downloaded')

	def _additionStart(self, simulations):
		'''
		Start to add the simulations.

		Parameters
		----------
		simulations : list
			The simulations that will be added.
		'''

		self._updateState('Adding the simulations to the manager…')
		self._main_progress_bar = self.addProgressBar(len(simulations))

	def _additionProgress(self):
		'''
		A simulation has just been added.
		'''

		self._main_progress_bar.counter += 1

	def _additionEnd(self):
		'''
		All simulations have been added.
		'''

		self.removeItem(self._main_progress_bar)
		self._main_progress_bar = None
		self._updateState('Simulations added')
