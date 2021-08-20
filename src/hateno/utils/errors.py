#!/usr/bin/env python3
# -*- coding: utf-8 -*-

class EventsError(Exception):
	'''
	Base class for exceptions occurring with the Events class.
	'''

	pass

class EventUnknownError(EventsError):
	'''
	Exception raised when we try to use an unkown event.

	Parameters
	----------
	event : str
		Name of the event.
	'''

	def __init__(self, event):
		self.event = event

class FCollectionError(Exception):
	'''
	Base class for exceptions occurring in an FCollection.
	'''

	pass

class FCollectionCategoryNotFoundError(FCollectionError):
	'''
	Exception raised when we try to access a non-existing category of an FCollection.

	Parameters
	----------
	category : str
		Name of the category.
	'''

	def __init__(self, category):
		self.category = category

class FCollectionFunctionNotFoundError(FCollectionError):
	'''
	Exception raised when we try to access a non-existing function of an FCollection.

	Parameters
	----------
	fname : str
		Name of the function.
	'''

	def __init__(self, fname):
		self.fname = fname

class FCollectionInvalidFilterRegexError(FCollectionError):
	'''
	Exception raised when we define the filter regex of an FCollection without the required groups.

	Parameters
	----------
	regex : str
		The invalid regex.
	'''

	def __init__(self, regex):
		self.regex = regex

class FileNotLockableError(Exception):
	'''
	Exception raised when we try to lock a file that cannot be locked.
	'''

	pass
