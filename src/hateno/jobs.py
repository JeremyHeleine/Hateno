#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import enum
import json

from .errors import *

class JobsManager():
	'''
	Represent a list of jobs to watch the states of.
	'''

	def __init__(self):
		self._jobs = {}

		self._remote_folder = None
		self._linked_file = None

	def linkToFile(self, filename, *, remote_folder = None):
		'''
		Link the manager to a file, to read and write the jobs states.

		Parameters
		----------
		filename : str
			Name of the file to link.

		remote_folder : RemoteFolder
			Remote folder to use, where the file is located.
			Optional, if not provided, local file is assumed.
		'''

		self._remote_folder = remote_folder
		self._linked_file = filename

	def add(self, *names):
		'''
		Add a job to manage.

		Parameters
		----------
		name : str
			Name of the job.

		Raises
		------
		JobAlreadyExistingError
			The job already exists in the list.
		'''

		for name in names:
			if name in self._jobs:
				raise JobAlreadyExistingError(name)

			self._jobs[name] = Job()

	def delete(self, *names):
		'''
		Remove a job from the list.

		Parameters
		----------
		name : str
			Name of the job.

		Raises
		------
		JobNotFoundError
			The job does not exist.
		'''

		for name in names:
			try:
				del self._jobs[name]

			except KeyError:
				raise JobNotFoundError(name)

	def clear(self):
		'''
		Clear the jobs list.
		'''

		keys_to_remove = list(self._jobs.keys())
		self._jobs.clear()

		if not(self._linked_file is None):
			jobs = self._getFileContent()
			for key in keys_to_remove:
				del jobs[key]

			self._writeToFile(jobs)

	def getJob(self, name):
		'''
		Get a job from its name.

		Parameters
		----------
		name : str
			Name of the job.

		Returns
		-------
		job : Job
			The job named `name`.

		Raises
		------
		JobNotFoundError
			The job does not exist.
		'''

		try:
			return self._jobs[name]

		except KeyError:
			raise JobNotFoundError(name)

	def getJobsWithStates(self, states):
		'''
		Get the list of jobs in given states.

		Parameters
		----------
		states : list
			List of `JobState`s to use to filter the jobs.

		Returns
		-------
		jobs : list
			The list of the names of the jobs in these states.
		'''

		return [name for name, job in self._jobs.items() if job.state in states]

	def setJobState(self, name, state):
		'''
		Set the state of a job.

		Parameters
		----------
		name : str
			Name of the job to update.

		state : JobState
			New state of the job.

		Raises
		------
		JobNotFoundError
			The job does not exist.
		'''

		try:
			self._jobs[name].state = state

		except KeyError:
			raise JobNotFoundError(name)

	def _getFileContent(self):
		'''
		Get the content of the linked file.

		Returns
		-------
		states : dict
			States stored in the file.
		'''

		try:
			if self._remote_folder is None:
				with open(self._linked_file, 'r') as f:
					file = f.read()

			else:
				file = self._remote_folder.getFileContents(self._linked_file)

		except FileNotFoundError:
			return {}

		else:
			return json.loads(file)

	def _writeToFile(self, jobs):
		'''
		Write a dict to the linked file.

		Parameters
		----------
		jobs : dict
			Jobs and their states to write in the file, as a dictionary.
		'''

		jobs_txt = json.dumps(jobs)

		if self._remote_folder is None:
			with open(self._linked_file, 'w') as f:
				f.write(jobs_txt)

		else:
			self._remote_folder.putFileContents(self._linked_file, jobs_txt)

	def updateFromFile(self):
		'''
		Read the states of the registered jobs from the linked file.
		'''

		states = self._getFileContent()

		for job_name, job in self._jobs.items():
			try:
				job.updateFromDict(states[job_name])

			except KeyError:
				pass

	def saveToFile(self):
		'''
		Write the current states to the linked file.
		'''

		jobs = self._getFileContent()

		jobs.update({
			job_name: job.__dict__
			for job_name, job in self._jobs.items()
		})

		self._writeToFile(jobs)

class Job():
	'''
	Represent a job, i.e. a program executing one or more simulations.
	'''

	def __init__(self):
		self._state = JobState.WAITING

	@property
	def __dict__(self):
		'''
		Rewrite the default dict representation, for easier serialization.

		Returns
		-------
		job_dict : dict
			Representation of the job.
		'''

		return {'state': self._state.name}

	@property
	def state(self):
		'''
		Get the current state of the job.

		Returns
		-------
		state : JobState
			State of the job.
		'''

		return self._state

	@state.setter
	def state(self, new_state):
		'''
		Update the state of the job.

		Parameters
		----------
		new_state : JobState
			The new state to store.
		'''

		self._state = new_state

	def updateFromDict(self, job_dict):
		'''
		Update the state of the job from a dictionary.

		Parameters
		----------
		job_dict : dict
			Dictionary representing the job.

		Raises
		------
		JobStateNotFoundError
			The description of the state has not been found in the dictionary.

		UnknownJobStateError
			The given job state is unknown.
		'''

		try:
			state = job_dict['state']

		except KeyError:
			raise JobStateNotFoundError()

		else:
			try:
				self.state = JobState[state.upper()]

			except KeyError:
				raise UnknownJobStateError(state)

class JobState(enum.Enum):
	'''
	State of a job (waiting, running, ended, etc.).
	'''

	WAITING = enum.auto()
	RUNNING = enum.auto()
	SUCCEED = enum.auto()
	FAILED = enum.auto()
