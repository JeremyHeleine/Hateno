#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import stat
import time
import tempfile

from . import string

from .folder import Folder
from .simulation import Simulation
from .manager import Manager
from .generator import Generator
from .remote import RemoteFolder
from .watcher import Watcher
from .ui import UI
from .errors import *

class Maker():
	'''
	Assemble all components to extract simulations and automatically create them if they don't exist.

	Parameters
	----------
	simulations_folder : str
		The simulations folder. Must contain a settings file.

	remote_folder_conf : dict
		Configuration of the remote folder.

	mail_config : dict
		Configuration of the mailbox.

	mail_notifications_config : dict
		Mails notifications configuration.

	max_corrupted : int
		Maximum number of allowed corruptions. Corruptions counter is incremented each time at least one simulation is corrupted. If negative, there is no limit.

	max_failures : int
		Maximum number of allowed failures in the execution of a job. The counter is incremented each time at least one job fails. If negative, there is no limit.

	ui : bool
		`True` to show different informations in the UI, `False` to show nothing.
	'''

	def __init__(self, simulations_folder, remote_folder_conf, *, mail_config = None, mail_notifications_config = None, max_corrupted = -1, max_failures = 0, ui = False):
		self._simulations_folder = Folder(simulations_folder)
		self._remote_folder_conf = remote_folder_conf

		self._manager_instance = None
		self._generator_instance = None
		self._remote_folder_instance = None
		self._watcher_instance = None
		self._ui_instance = None
		self._ui_state_line = None

		self._mail_config = mail_config
		self._mail_notifications_config = mail_notifications_config

		self._max_corrupted = max_corrupted
		self._corruptions_counter = 0

		self._max_failures = max_failures
		self._failures_counter = 0

		self._show_ui = ui

	@property
	def _manager(self):
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
	def _generator(self):
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
			self.displayState('Connecting to the folder…')
			self._remote_folder_instance.open()
			self.displayState('Connection done.')

		return self._remote_folder_instance

	@property
	def _watcher(self):
		'''
		Returns the instance of Watcher used in the Maker.

		Returns
		-------
		watcher : Watcher
			Current instance, or a new one if `None`.
		'''

		if not(self._watcher_instance):
			if self._mail_config is None:
				self._watcher_instance = Watcher(remote_folder = self._remote_folder)

			else:
				self._watcher_instance = Watcher(mail_config = self._mail_config, mail_notifications_config = self._mail_notifications_config)

		return self._watcher_instance

	@property
	def _ui(self):
		'''
		Returns the instance of UI used in the Maker.

		Returns
		-------
		ui : UI
			Current instance, or a new one if `None`.
		'''

		if not(self._ui_instance) and self._show_ui:
			self._ui_instance = UI()

		return self._ui_instance

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

		try:
			self._watcher_instance.close()

		except AttributeError:
			pass

		self._watcher_instance = None

	def displayTextLine(self, text):
		'''
		Display a new text line.

		Parameters
		----------
		text : str
			Text to display.

		Returns
		-------
		text_line : str
			ID of the text line.
		'''

		if not(self._show_ui):
			return None

		return self._ui.addTextLine(text)

	def updateTextLine(self, text_line, new_text):
		'''
		Update a text line.

		Parameters
		----------
		text_line : str
			ID of the text line to update.

		new_text : str
			New text to display.
		'''

		if not(self._show_ui):
			return

		self._ui.replaceTextLine(text_line, new_text)

	def removeTextLine(self, text_line):
		'''
		Remove a text line.

		Parameters
		----------
		text_line : str
			ID of the text line to remove.
		'''

		if not(self._show_ui):
			return

		self._ui.removeTextLine(text_line)

	def displayState(self, state):
		'''
		Display a state message (creation of an instance, connection, …).

		Parameters
		----------
		state : str
			State to display.
		'''

		if not(self._show_ui):
			return

		if self._ui_state_line is None:
			self._ui_state_line = self.displayTextLine(state)

		else:
			self.updateTextLine(self._ui_state_line, state)

	def displayProgressBar(self, N):
		'''
		Add a new progress bar.

		Parameters
		----------
		N : int
			Final number to reach.

		Returns
		-------
		progress_bar : str
			ID of the progress bar.
		'''

		if not(self._show_ui):
			return None

		return self._ui.addProgressBar(N)

	def updateProgressBar(self, progress_bar, n = None):
		'''
		Update a progress bar.

		Parameters
		----------
		progress_bar : str
			ID of the progress bar to update.

		n : int
			New number to display (`None` to increment by one).
		'''

		if not(self._show_ui):
			return

		self._ui.updateProgressBar(progress_bar, n)

	def removeProgressBar(self, progress_bar):
		'''
		Remove a progress bar.

		Parameters
		----------
		progress_bar : str
			ID of the progress bar to remove.
		'''

		if not(self._show_ui):
			return

		self._ui.removeProgressBar(progress_bar)

	def parseScriptToLaunch(self, launch_option):
		'''
		Parse the `launch` option of a recipe to determine which skeleton/script must be called.

		Parameters
		----------
		launch_option : str
			Value of the `launch` option to parse.

		Returns
		-------
		script_to_launch : dict
			"Coordinates" of the script to launch.
		'''

		self.displayState('Parsing the launch option…')

		option_split = launch_option.rsplit(':', maxsplit = 2)
		option_split_num = [string.intOrNone(s) for s in option_split]

		cut = max([k for k, n in enumerate(option_split_num) if n is None]) + 1

		coords = option_split_num[cut:]
		coords += [-1] * (2 - len(coords))

		return {
			'name': ':'.join(option_split[:cut]),
			'skeleton': coords[0],
			'script': coords[1]
		}

	def run(self, simulations, generator_recipe):
		'''
		Main loop, run until all simulations are extracted or some jobs failed.

		Parameters
		----------
		simulations : list
			List of simulations to extract/generate.

		generator_recipe : dict
			Recipe to use in the generator to generate the scripts.

		Returns
		-------
		unknown_simulations : list
			List of simulations that failed to be generated.
		'''

		script_coords = self.parseScriptToLaunch(generator_recipe['launch'])

		self._corruptions_counter = 0
		self._failures_counter = 0

		while (self._max_corrupted < 0 or self._corruptions_counter <= self._max_corrupted) and (self._max_failures < 0 or self._failures_counter <= self._max_failures):
			unknown_simulations = self.extractSimulations(simulations)

			if not(unknown_simulations):
				break

			jobs_ids = self.generateSimulations(unknown_simulations, generator_recipe, script_coords)
			success = self.waitForJobs(jobs_ids, generator_recipe)

			if not(success):
				self._failures_counter += 1

			success = self.downloadSimulations(unknown_simulations)

			if not(success):
				self._corruptions_counter += 1

			self.displayState('Deleting the scripts folder…')
			self._remote_folder.deleteRemote([generator_recipe['basedir']])

		if unknown_simulations:
			self.displayState(string.plural(len(unknown_simulations), 'simulation still does not exist', 'simulations still do not exist'))

		else:
			self.displayState('All simulations have successfully been extracted')

		return unknown_simulations

	def extractSimulations(self, simulations):
		'''
		Extract a given set of simulations.

		Parameters
		----------
		simulations : list
			The list of simulations to extract.

		Returns
		-------
		unknown_simulations : list
			The list of simulations which do not exist (yet).
		'''

		self.displayState('Extracting the simulations…')
		progress_bar = self.displayProgressBar(len(simulations))

		unknown_simulations = self._manager.batchExtract(simulations, callback = lambda : self.updateProgressBar(progress_bar))

		self.removeProgressBar(progress_bar)

		return unknown_simulations

	def generateSimulations(self, simulations, recipe, script_coords):
		'''
		Generate the scripts to generate some unknown simulations, and run them.

		Parameters
		----------
		simulations : list
			List of simulations to create.

		recipe : dict
			Recipe to use in the generator.

		script_coords : dict
			'Coordinates' of the script to launch.

		Raises
		------
		ScriptNotFoundError
			The script to launch has not been found.

		Returns
		-------
		jobs_ids : list
			IDs of the jobs to wait.
		'''

		self.displayState('Generating the scripts…')

		scripts_dir = tempfile.mkdtemp(prefix = 'simulations-scripts_')
		recipe['basedir'] = self._remote_folder.sendDir(scripts_dir)

		self._generator.add(simulations)
		generated_scripts = self._generator.generate(scripts_dir, recipe, empty_dest = True)
		self._generator.clear()

		possible_skeletons_to_launch = [k for k, s in enumerate(recipe['subgroups_skeletons'] + recipe['wholegroup_skeletons']) if s == script_coords['name']]

		try:
			script_to_launch = generated_scripts[possible_skeletons_to_launch[script_coords['skeleton']]][script_coords['script']]

		except IndexError:
			raise ScriptNotFoundError(script_coords)

		script_mode = os.stat(script_to_launch['localpath']).st_mode
		if not(script_mode & stat.S_IXUSR & stat.S_IXGRP & stat.S_IXOTH):
			os.chmod(script_to_launch['localpath'], script_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

		self._remote_folder.sendDir(scripts_dir, delete = True, empty_dest = True)

		output = self._remote_folder.execute(script_to_launch['finalpath'])
		jobs_ids = list(map(lambda l: l.strip(), output.readlines()))

		return jobs_ids

	def waitForJobs(self, jobs_ids, recipe):
		'''
		Wait for a given list of jobs to finish.

		Parameters
		----------
		jobs_ids : list
			IDs of the jobs to wait.

		recipe : dict
			Generator recipe to use.

		Returns
		-------
		success : bool
			`True` is all jobs were finished normally, `False` if there was at least one failure.
		'''

		jobs_number = len(jobs_ids)
		jobs_numbers_by_state = {}

		self.displayState('Waiting for jobs to finish…')
		progress_bar = self.displayProgressBar(jobs_number)

		statuses = 'Current statuses: {waiting} waiting, {running} running, {succeed} succeed, {failed} failed'
		statuses_line = self.displayTextLine('')

		self._watcher.addJobsToWatch(jobs_ids)

		if self._mail_config is None:
			self._watcher.setJobsStatesPath(recipe['jobs_states_filename'])

		while True:
			self._watcher.updateJobsStates()
			jobs_numbers_by_state = self._watcher.getNumberOfJobsByStates(['waiting', 'running', 'succeed', 'failed'])
			finished = jobs_numbers_by_state['succeed'] + jobs_numbers_by_state['failed']

			self.updateProgressBar(progress_bar, finished)
			self.updateTextLine(statuses_line, statuses.format(**jobs_numbers_by_state))

			if finished == jobs_number:
				break

			time.sleep(0.5)

		self.removeProgressBar(progress_bar)
		self.removeTextLine(statuses_line)

		self._watcher.clearJobs()

		return jobs_numbers_by_state['failed'] == 0

	def downloadSimulations(self, simulations):
		'''
		Download the generated simulations and add them to the manager.

		Parameters
		----------
		simulations : list
			List of simulations to download.

		Returns
		-------
		success : bool
			`True` if all simulations has successfully been downloaded and added, `False` if there has been at least one issue.
		'''

		self.displayState('Downloading the simulations…')
		progress_bar = self.displayProgressBar(len(simulations))

		simulations_to_add = []

		for simulation in simulations:
			simulation = Simulation.ensureType(simulation, self._simulations_folder)

			tmpdir = tempfile.mkdtemp(prefix = 'simulation_')
			try:
				self._remote_folder.receiveDir(simulation['folder'], tmpdir, delete = True)

			except RemotePathNotFoundError:
				pass

			simulation['folder'] = tmpdir
			simulations_to_add.append(simulation)

			self.updateProgressBar(progress_bar)

		self.removeProgressBar(progress_bar)

		self.displayState('Adding the simulations to the manager…')
		progress_bar = self.displayProgressBar(len(simulations))

		failed_to_add = self._manager.batchAdd(simulations_to_add, callback = lambda : self.updateProgressBar(progress_bar))

		self.removeProgressBar(progress_bar)

		return not(bool(failed_to_add))
