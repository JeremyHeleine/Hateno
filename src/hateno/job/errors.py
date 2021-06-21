#!/usr/bin/env python3
# -*- coding: utf-8 -*-

class JobError(Exception):
	'''
	Base class for exceptions occurring in a job (server or client).
	'''

	pass

class JobDirAlreadyExistsError(JobError):
	'''
	Exception raised when we try to use a directory that already exists.

	Parameters
	----------
	job_dir : str
		The path to the directory.
	'''

	def __init__(self, job_dir):
		self.job_dir = job_dir
