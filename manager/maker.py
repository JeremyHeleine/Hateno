#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import stat
import time
import tempfile
import copy

from utils import string

from manager.folder import Folder
from manager.manager import Manager
from manager.generator import Generator
from manager.remote import RemoteFolder
from manager.watcher import Watcher
from manager.ui import UI
from manager.errors import *

class Maker():
	'''
	Assemble all components to extract simulations and automatically create them if they don't exist.

	Parameters
	----------
	simulations_folder : str
		The simulations folder. Must contain a settings file.

	remote_folder_conf : str
		Path to the configuration file of the remote folder.
	'''

	def __init__(self, simulations_folder, remote_folder_conf):
		self._simulations_folder = Folder(simulations_folder)
		self._remote_folder_conf = remote_folder_conf

		self._manager_instance = None
		self._generator_instance = None
		self._remote_folder_instance = None
		self._watcher_instance = None
		self._ui_instance = None
		self._ui_state_line = None

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
			self.displayState('Creating the Manager…')
			self._manager_instance = Manager(self._simulations_folder)
			self.displayState('Manager created.')

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
			self.displayState('Creating the Generator…')
			self._generator_instance = Generator(self._simulations_folder)
			self.displayState('Generator created.')

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
			self.displayState('Creating the RemoteFolder…')
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
			self.displayState('Creating the Watcher…')
			self._watcher_instance = Watcher(self._remote_folder)
			self.displayState('Watcher created.')

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

		if not(self._ui_instance):
			self._ui_instance = UI()

		return self._ui_instance

	def close(self):
		'''
		Clear all instances of the modules.
		'''

		self.displayState('Closing all instances…')

		self._manager_instance = None
		self._generator_instance = None

		try:
			self._remote_folder_instance.close()

		except AttributeError:
			pass

		self._remote_folder_instance = None

	def displayState(self, state):
		'''
		Display a state message (creation of an instance, connection, …).

		Parameters
		----------
		state : str
			State to display.
		'''

		if self._ui_state_line is None:
			self._ui_state_line = self._ui.addTextLine(state)

		else:
			self._ui.replaceTextLine(self._ui_state_line, state)

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
		'''

		script_coords = self.parseScriptToLaunch(generator_recipe['launch'])

		while True:
			self.displayState('Extracting the simulations…')
			unknown_simulations = self._manager.batchExtract(simulations)

			if not(unknown_simulations):
				break

			jobs_ids = self.generateSimulations(unknown_simulations, generator_recipe, script_coords)
			self.waitForJobs(jobs_ids, generator_recipe)
			self.downloadSimulations(unknown_simulations)
			self.displayState('Deleting the scripts folder…')
			self._remote_folder.deleteRemote([generator_recipe['basedir']])

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
		'''

		self._watcher.addJobsToWatch(jobs_ids)

		self.displayState('Waiting for jobs to finish…')

		while True:
			self._watcher.updateJobsStates(recipe['jobs_states_filename'])

			if self._watcher.areJobsFinished():
				break

			time.sleep(10)

		self._watcher.clearJobs()

	def downloadSimulations(self, simulations):
		'''
		Download the generated simulations and add them to the manager.

		Parameters
		----------
		simulations : list
			List of simulations to download.
		'''

		self.displayState('Downloading the simulations…')

		simulations_to_add = []

		for simulation in simulations:
			tmpdir = tempfile.mkdtemp(prefix = 'simulation_')
			self._remote_folder.receiveDir(simulation['folder'], tmpdir, delete = True)

			simulation_to_add = copy.deepcopy(simulation)
			simulation_to_add['folder'] = tmpdir
			simulations_to_add.append(simulation_to_add)

		self._manager.batchAdd(simulations_to_add)
