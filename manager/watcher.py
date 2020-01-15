#!/usr/bin/env python3
# -*- coding: utf-8 -*-

class Watcher():
	'''
	Watch for events to detect the end of some simulations.

	Parameters
	----------
	remote_folder : RemoteFolder
		A RemoteFolder instance to use to search for notifications.

	states_path : str
		Path to the remote file containing the jobs states.
	'''

	def __init__(self, remote_folder, states_path):
		self._jobs_to_watch = set()
		self._jobs_states = {}

		self._remote_folder = remote_folder
		self._states_path = states_path

	def addJobsToWatch(self, jobs):
		'''
		Add some jobs to watch.

		Parameters
		----------
		jobs : list
			IDs of the jobs.
		'''

		self._jobs_to_watch |= set(jobs)

	def updateJobsStates(self):
		'''
		Remotely read the current states of the jobs.
		'''

		try:
			known_states = self._remote_folder.getFileContents(self._states_path)

		except FileNotFoundError:
			pass

		else:
			for job in self._jobs_to_watch & set(known_states.keys()):
				state = known_states[job]

				if state in ['waiting', 'began', 'succeed', 'failed']:
					self._jobs_states[job] = state

		self._jobs_states.update({job: 'waiting' for job in self._jobs_to_watch - set(self._jobs_states.keys())})
