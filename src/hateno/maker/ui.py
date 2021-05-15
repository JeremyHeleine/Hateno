#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from ..ui.ui import UI
from ..utils import string

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

	def _waitStart(self, n_simulations):
		'''
		Start to wait for a job.

		Parameters
		----------
		n_simulations : int
			Number of simulations in the job.
		'''

		simulations = string.plural(n_simulations, 'simulation', 'simulations')
		self._updateState(f'Waiting for {simulations} to execute…')
		self._main_progress_bar = self.addProgressBar(n_simulations)

	def _waitProgress(self, n_executed):
		'''
		Update the number of executed simulations.

		Parameters
		----------
		n_executed : int
			Number of executed simulations.
		'''

		self._main_progress_bar.counter = n_executed

	def _waitEnd(self):
		'''
		The job has finished.
		'''

		self.removeItem(self._main_progress_bar)
		self._main_progress_bar = None

		self._updateState('Simulations executed')

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
