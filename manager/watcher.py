#!/usr/bin/env python3
# -*- coding: utf-8 -*-

class Watcher():
	'''
	Watch for events to detect the end of some simulations.

	Parameters
	----------
	remote_folder : RemoteFolder
		A RemoteFolder instance to use to search for notifications.
	'''

	def __init__(self, remote_folder):
		self._jobs_to_watch = set()
		self._jobs_states = {}

		self._remote_folder = remote_folder

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

	def areJobsFinished(self):
		'''
		Determine whether all jobs are finished or not.

		Returns
		-------
		jobs_finished : boolean
			`True` if all jobs are finished, `False` if there is still at least one running.
		'''

		return self._jobs_to_watch == set([job for job, state in self._jobs_states.items() if state in ['succeed', 'failed']])

	def getNumberOfFinishedJobs(self):
		'''
		Return the number of finished (either succeed or failed) jobs.

		Returns
		-------
		finished : int
			The number of finished jobs.
		'''

		return len(set([job for job, state in self._jobs_states.items() if state in ['succeed', 'failed']]))

	def updateJobsStates(self, states_path):
		'''
		Remotely read the current states of the jobs.

		states_path : str
			Path to the remote file containing the jobs states.
		'''

		try:
			known_states = dict(self._remote_folder.getFileContents(states_path, callback = lambda l: tuple(map(lambda s: s.strip(), l.split(':')))))

		except FileNotFoundError:
			pass

		else:
			for job in self._jobs_to_watch & set(known_states.keys()):
				state = known_states[job]

				if state in ['waiting', 'began', 'succeed', 'failed']:
					self._jobs_states[job] = state

		self._jobs_states.update({job: 'waiting' for job in self._jobs_to_watch - set(self._jobs_states.keys())})
