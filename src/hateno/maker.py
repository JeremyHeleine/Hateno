#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil
import stat
import time
import copy

from . import string, jsonfiles

from .events import Events
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
	simulations_folder : Folder|str
		The simulations folder. Must contain a settings file.

	config_name : str
		Name of the config to use. Indicate `None` to use the default configuration.

	override_options : dict
		Options to override.
	'''

	def __init__(self, simulations_folder, config_name = None, *, override_options = {}):
		self._simulations_folder = simulations_folder if type(simulations_folder) is Folder else Folder(simulations_folder)
		self._config_name = config_name

		self._manager_instance = None
		self._generator_instance = None
		self._remote_folder_instance = None
		self._jobs_manager = JobsManager()

		self._loadOptions(override_options)

		self._simulations_to_extract = []
		self._unknown_simulations = []
		self._jobs_ids = []

		self._remote_scripts_dir = None

		self._corruptions_counter = 0
		self._failures_counter = 0

		self._paused = False
		self._state_attrs = ['simulations_to_extract', 'corruptions_counter', 'failures_counter', 'unknown_simulations', 'jobs_ids', 'remote_scripts_dir']

		self.events = Events(['close-start', 'close-end', 'remote-open-start', 'remote-open-end', 'delete-scripts', 'paused', 'resume', 'run-start', 'run-end', 'extract-start', 'extract-end', 'extract-progress', 'generate-start', 'generate-end', 'wait-start', 'wait-progress', 'wait-end', 'download-start', 'download-progress', 'download-end', 'addition-start', 'addition-progress', 'addition-end'])

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
			self._manager_instance = Manager(self._simulations_folder, readonly = self._options['generate_only'])

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
			self._remote_folder_instance = RemoteFolder(self.folder.config('folder', self._config_name))

			self.events.trigger('remote-open-start')
			self._remote_folder_instance.open()
			self.events.trigger('remote-open-end')

		return self._remote_folder_instance

	def close(self):
		'''
		Clear all instances of the modules.
		'''

		self.events.trigger('close-start')

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

		self.events.trigger('close-end')

	def _loadOptions(self, override = {}):
		'''
		Load the options of the Maker, stored in the config folder.

		Parameters
		----------
		override : dict
			Options to impose the value of, despite the values in the config folder.
		'''

		self._options = {
			'settings_file': 'settings.json',
			'max_corrupted': -1,
			'max_failures': 0,
			'jobs_states_filename': 'jobs.txt',
			'jobs_output_filename': 'job.out',
			'generate_only': False
		}

		try:
			self._options.update(self.folder.config('maker', self._config_name))

		except TypeError:
			pass

		self._options.update(override)

	def _setSimulations(self, simulations):
		'''
		Set the list of simulations to extract.

		Parameters
		----------
		simulations : list
			The list of simulations to extract.
		'''

		self._simulations_to_extract = [
			Simulation.ensureType(simulation, self._simulations_folder).copy()
			for simulation in simulations
		]

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
		self.events.trigger('paused')

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
		self.events.trigger('resume')
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

		self.events.trigger('run-start')

		self._setSimulations(simulations)

		self._corruptions_counter = corruptions_counter
		self._failures_counter = failures_counter

		while self._runLoop():
			pass

		if self.paused:
			return None

		self.events.trigger('run-end', self._unknown_simulations)

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

			if (self._options['max_corrupted'] >= 0 and self._corruptions_counter > self._options['max_corrupted']) or (self._options['max_failures'] >= 0 and self._failures_counter > self._options['max_failures']):
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

		self.events.trigger('delete-scripts')
		self._remote_folder.deleteRemote([self._remote_scripts_dir])

		return True

	def extractSimulations(self):
		'''
		Try to extract the simulations.
		'''

		self.events.trigger('extract-start', self._simulations_to_extract)

		self._unknown_simulations = self.manager.batchExtract(self._simulations_to_extract, settings_file = self._options['settings_file'], callback = lambda : self.events.trigger('extract-progress'))

		if self._options['generate_only']:
			self._unknown_simulations = list(filter(lambda simulation: not(os.path.isdir(simulation['folder'])), self._unknown_simulations))

		self.events.trigger('extract-end')

	def generateSimulations(self):
		'''
		Generate the scripts to generate the unknown simulations, and run them.

		Returns
		-------
		jobs_ids : list
			IDs of the jobs to wait.
		'''

		self.events.trigger('generate-start')

		scripts_dir = self._simulations_folder.tempdir()
		self._remote_scripts_dir = self._remote_folder.send(scripts_dir)

		self._simulations_to_generate = [simulation.copy() for simulation in self._unknown_simulations]

		self._simulations_remote_basedir = f'simulations_{hex(int(time.time() * 1E7))[2:]}'
		for k, simulation in enumerate(self._simulations_to_generate):
			simulation['folder'] = os.path.join(self._simulations_remote_basedir, str(k))

		self.generator.add(self._simulations_to_generate)
		generated_scripts, script_to_launch = self.generator.generate(scripts_dir, self._config_name, empty_dest = True, basedir = self._remote_scripts_dir)
		self.generator.clear()

		self._remote_folder.send(scripts_dir, delete = True, replace = True)

		output = self._remote_folder.execute(script_to_launch)
		self._jobs_ids = list(map(lambda l: l.strip(), output.readlines()))

		self.events.trigger('generate-end')

	def waitForJobs(self):
		'''
		Wait for the jobs to finish.

		Returns
		-------
		success : bool
			`True` is all jobs were finished normally, `False` if there was at least one failure.
		'''

		self.events.trigger('wait-start', self._jobs_ids)

		jobs_by_state = {}
		previous_states = {}

		self._jobs_manager.add(*self._jobs_ids, ignore_existing = True)
		self._jobs_manager.linkToFile(self._options['jobs_states_filename'], remote_folder = self._remote_folder)

		while True:
			self._jobs_manager.updateFromFile()
			jobs_by_state = {
				state: self._jobs_manager.getJobsWithStates([JobState[state.upper()]])
				for state in ['waiting', 'running', 'succeed', 'failed']
			}

			if jobs_by_state != previous_states:
				self.events.trigger('wait-progress', jobs_by_state)

				if set([job['name'] for job in jobs_by_state['succeed'] + jobs_by_state['failed']]) == set(self._jobs_ids):
					break

			previous_states = jobs_by_state
			time.sleep(0.5)

		self._jobs_manager.clear()
		self._jobs_ids = []

		self._remote_folder.deleteRemote([self._options['jobs_states_filename']])

		self.events.trigger('wait-end')

		return not(jobs_by_state['failed'])

	def downloadSimulations(self):
		'''
		Download the generated simulations and add them to the manager.

		Returns
		-------
		success : bool
			`True` if all simulations has successfully been downloaded and added, `False` if there has been at least one issue.
		'''

		self.events.trigger('download-start', self._unknown_simulations)

		success = True

		for simulation, simulation_dest in zip(self._simulations_to_generate, self._unknown_simulations):
			tmpdir = self._simulations_folder.tempdir()
			try:
				self._remote_folder.receive(simulation['folder'], tmpdir, delete = True)

			except RemotePathNotFoundError:
				pass

			simulation['folder'] = tmpdir

			if self._options['generate_only']:
				if self._simulations_folder.checkIntegrity(simulation):
					destination_path = os.path.dirname(os.path.normpath(simulation_dest['folder']))
					if destination_path and not(os.path.isdir(destination_path)):
						os.makedirs(destination_path)

					os.rename(simulation['folder'], simulation_dest['folder'])

					if self._options['settings_file']:
						simulation_dest.writeSettingsFile(self._options['settings_file'])

				else:
					shutil.rmtree(simulation['folder'])
					success = False

			else:
				try:
					self.manager.add(simulation)

				except (SimulationFolderNotFoundError, SimulationIntegrityCheckFailedError):
					success = False

			self.events.trigger('download-progress')

		try:
			self._remote_folder.deleteRemote([self._simulations_remote_basedir])
		except FileNotFoundError:
			pass

		del self._simulations_remote_basedir
		del self._simulations_to_generate

		self.events.trigger('download-end')

		return success

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

		self._jobs_lines = {}
		self._jobs_bars = {}

		self._maker.events.addListener('close-start', self._closeStart)
		self._maker.events.addListener('close-end', self._closeEnd)
		self._maker.events.addListener('remote-open-start', self._remoteOpenStart)
		self._maker.events.addListener('remote-open-end', self._remoteOpenEnd)
		self._maker.events.addListener('delete-scripts', self._deleteScripts)
		self._maker.events.addListener('paused', self._paused)
		self._maker.events.addListener('resume', self._resume)
		self._maker.events.addListener('run-start', self._runStart)
		self._maker.events.addListener('run-end', self._runEnd)
		self._maker.events.addListener('extract-start', self._extractStart)
		self._maker.events.addListener('extract-progress', self._extractProgress)
		self._maker.events.addListener('extract-end', self._extractEnd)
		self._maker.events.addListener('generate-start', self._generateStart)
		self._maker.events.addListener('generate-end', self._generateEnd)
		self._maker.events.addListener('wait-start', self._waitStart)
		self._maker.events.addListener('wait-progress', self._waitProgress)
		self._maker.events.addListener('wait-end', self._waitEnd)
		self._maker.events.addListener('download-start', self._downloadStart)
		self._maker.events.addListener('download-progress', self._downloadProgress)
		self._maker.events.addListener('download-end', self._downloadEnd)

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

	def _clearState(self):
		'''
		Remove the state line.
		'''

		if not(self._state_line is None):
			self.removeItem(self._state_line)
			self._state_line = None

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

		if self._main_progress_bar is not None:
			self.removeItem(self._main_progress_bar)
			self._main_progress_bar = None

		if self._statuses_line is not None:
			self.removeItem(self._statuses_line)
			self._statuses_line = None

		for line, bar in zip(self._jobs_lines.values(), self._jobs_bars.values()):
			self.removeItem(line)
			self.removeItem(bar)

		self._jobs_lines.clear()
		self._jobs_bars.clear()

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
		Update the global statuses line and progress bar.
		Display a progress bar for each running job.

		Parameters
		----------
		jobs_by_state : dict
			The jobs IDs, sorted by their state.
		'''

		self._statuses_line.text = self._statuses.format(**{state: len(jobs) for state, jobs in jobs_by_state.items()})
		self._main_progress_bar.counter = len(jobs_by_state['succeed'] + jobs_by_state['failed'])

		for job in jobs_by_state['running']:
			if job['total_steps'] > 0:
				if not(job['name'] in self._jobs_lines):
					self._jobs_lines[job['name']] = self.addTextLine(f'Job {job["name"]} running…')
					self._jobs_bars[job['name']] = self.addProgressBar(job['total_steps'])

				self._jobs_bars[job['name']].counter = job['finished_steps']

		for job in jobs_by_state['succeed'] + jobs_by_state['failed']:
			if job['name'] in self._jobs_lines:
				self.removeItem(self._jobs_lines[job['name']])
				del self._jobs_lines[job['name']]

				self.removeItem(self._jobs_bars[job['name']])
				del self._jobs_bars[job['name']]

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
		Start to download and add the simulations.

		Parameters
		----------
		simulations : list
			Simulations that will be downloaded.
		'''

		self._updateState('Downloading the simulations…')
		self._main_progress_bar = self.addProgressBar(len(simulations))

	def _downloadProgress(self):
		'''
		A simulation has just been downloaded and added.
		'''

		self._main_progress_bar.counter += 1

	def _downloadEnd(self):
		'''
		All simulations have been downloaded and added.
		'''

		self.removeItem(self._main_progress_bar)
		self._main_progress_bar = None
		self._updateState('Simulations downloaded')
