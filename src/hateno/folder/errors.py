#!/usr/bin/env python3
# -*- coding: utf-8 -*-

class FolderError(Exception):
	'''
	Base class for exceptions occurring in the Folder.
	'''

	pass

class ConfigNotFoundError(FolderError):
	'''
	Exception raised when we try to access a non-existing configuration folder.

	Parameters
	----------
	foldername : str
		Name of the folder.
	'''

	def __init__(self, foldername):
		self.foldername = foldername

class NoConfigError(FolderError):
	'''
	Exception raised when we try to access a configuration but no foldername is given.
	'''

	pass

class SkeletonsNotFoundError(FolderError):
	'''
	Exception raised when we try to access a non-existing skeletons folder.

	Parameters
	----------
	skeletons_name : str
		Name of the folder.
	'''

	def __init__(self, skeletons_name):
		self.skeletons_name = skeletons_name
