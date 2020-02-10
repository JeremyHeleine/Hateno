#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import imaplib

from manager.errors import *

class Watcher():
	'''
	Watch for events to detect the end of some simulations.

	Parameters
	----------
	remote_folder : RemoteFolder
		A RemoteFolder instance to use to search for notifications.

	mail_config : str
		Path to the configuration file of the mailbox.

	Raises
	------
	WatcherNoConfigFoundError
		Nothing used to configure the watcher.

	WatcherTooManyConfigError
		More than one configuration used.
	'''

	def __init__(self, *, remote_folder = None, states_path = '', mail_config = None):
		self._jobs_to_watch = set()
		self._jobs_states = {}

		self._remote_folder = remote_folder
		self._states_path = states_path

		self._mail_config = mail_config

		if self._remote_folder is None and self._mail_config is None:
			raise WatcherNoConfigFoundError()

		if not(self._remote_folder is None) and not(self._mail_config is None):
			raise WatcherTooManyConfigError()

	def addJobsToWatch(self, jobs):
		'''
		Add some jobs to watch.

		Parameters
		----------
		jobs : list
			IDs of the jobs.
		'''

		self._jobs_to_watch |= set(jobs)

	def clearJobs(self):
		'''
		Clear the list of jobs to watch.
		'''

		self._jobs_to_watch.clear()
		self._jobs_states.clear()

	def getJobsByStates(self, states):
		'''
		Get the list of jobs which are in a given state.

		Parameters
		----------
		states : list
			List of states to use to filter the jobs.

		Returns
		-------
		jobs : list
			The list of jobs in these states.
		'''

		return [job for job, state in self._jobs_states.items() if state in states]

	def getNumberOfJobsByState(self, state):
		'''
		Return the number of jobs in a given state.

		Parameters
		----------
		state : str
			The state to use to filter the jobs.

		Returns
		-------
		n_jobs : int
			The number of jobs in this state.
		'''

		return len(self.getJobsByStates([state]))

	def getNumberOfJobsByStates(self, states):
		'''
		Return the number of jobs in given states.

		Parameters
		----------
		states : list
			The states to use to filter the jobs.

		Returns
		-------
		n_jobs : dict
			A dictionary with keys equal to the wanted states and values the number of jobs in these states.
		'''

		return {state: self.getNumberOfJobsByState(state) for state in states}

	def setJobsStatesPath(self, states_path):
		'''
		Set the path to the remote file where we can find the jobs states.

		Parameters
		----------
		states_path : str
			Path to the remote file containing the jobs states.

		Raises
		------
		WatcherNoRemoteFolderError
			There is no RemoteFolder set.
		'''

		if self._remote_folder is None:
			raise WatcherNoRemoteFolderError()

		self._states_path = states_path

	def updateJobsStates(self):
		'''
		Remotely read the current states of the jobs.

		Raises
		------
		WatcherNoStatesPathError
			There is no path to look for the states.
		'''

		if not(self._states_path):
			raise WatcherNoStatesPathError()

		try:
			known_states = dict(self._remote_folder.getFileContents(self._states_path, callback = lambda l: tuple(map(lambda s: s.strip(), l.split(':')))))

		except FileNotFoundError:
			pass

		else:
			for job in self._jobs_to_watch & set(known_states.keys()):
				state = known_states[job]

				if state in ['waiting', 'running', 'succeed', 'failed']:
					self._jobs_states[job] = state

		self._jobs_states.update({job: 'waiting' for job in self._jobs_to_watch - set(self._jobs_states.keys())})
