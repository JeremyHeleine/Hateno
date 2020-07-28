#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import enum

from .errors import *

class JobsManager():
	'''
	Represent a list of jobs to watch the states of.
	'''

	def __init__(self):
		self._jobs = {}

	def add(self, name):
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

		if name in self._jobs:
			raise JobAlreadyExistingError(name)

		self._jobs[name] = Job()

	def delete(self, name):
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

		try:
			del self._jobs[name]

		except KeyError:
			raise JobNotFoundError(name)

	def clear(self):
		'''
		Clear the jobs list.
		'''

		self._jobs.clear()

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

class Job():
	'''
	Represent a job, i.e. a program executing one or more simulations.
	'''

	def __init__(self):
		self._state = JobState.WAITING

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

class JobState(enum.Enum):
	'''
	State of a job (waiting, running, ended, etc.).
	'''

	WAITING = enum.auto()
	RUNNING = enum.auto()
	SUCCEED = enum.auto()
	FAILED = enum.auto()
