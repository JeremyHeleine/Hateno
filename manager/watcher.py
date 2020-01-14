#!/usr/bin/env python3
# -*- coding: utf-8 -*-

class Watcher():
	'''
	Watch for events to detect the end of some simulations.
	'''

	def __init__(self):
		self._jobs_to_watch = set()
		self._began_jobs = set()
		self._succeed_jobs = set()
		self._failed_jobs = set()

	def addJobsToWatch(self, jobs):
		'''
		Add some jobs to watch.

		Parameters
		----------
		jobs : list
			IDs of the jobs.
		'''

		self._jobs_to_watch |= set(jobs)
