#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from .fcollection import FCollection
from .errors import *

class Events():
	'''
	Simple implementation of an events handling system.

	Parameters
	----------
	events_names : list
		Names of the events handled by this instance.
	'''

	def __init__(self, events_names):
		self._callbacks = FCollection(categories = events_names)

	def addListener(self, event, f):
		'''
		Add a callback function to a given event.

		Parameters
		----------
		event : str
			Name of the event.

		f : function
			Function to attach.

		Raises
		------
		EventUnknownError
			The event does not exist.
		'''

		try:
			self._callbacks.set(f.__name__, f, category = event)

		except FCollectionCategoryNotFoundError:
			raise EventUnknownError(event)

	def trigger(self, event, *args):
		'''
		Call all functions attached to a given event.

		Parameters
		----------
		event : str
			Name of the event to trigger.

		args : mixed
			Arguments to pass to the callback functions.

		Raises
		------
		EventUnknownError
			The event does not exist.
		'''

		try:
			functions = self._callbacks.getAll(category = event)

		except FCollectionCategoryNotFoundError:
			raise EventUnknownError(event)

		else:
			for f in functions:
				f(*args)
