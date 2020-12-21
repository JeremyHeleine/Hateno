#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import inspect

from .errors import *

class FCollection():
	'''
	Represent a collection of functions, with possible categories.

	Parameters
	----------
	categories : list
		Names of the categories to use.

	filter_regex : str
		Regex to use to filter the functions when we load them from a module.
	'''

	def __init__(self, *, categories = [], filter_regex = None):
		self._list = {}
		self._use_categories = bool(categories)

		if categories:
			self._list = {cat: {} for cat in categories}

		if filter_regex:
			self.setFilterRegex(filter_regex)

	def _getList(self, category = None):
		'''
		Get the right list to manage.

		Parameters
		----------
		category : str
			Name of the category, if any.

		Raises
		------
		FCollectionCategoryNotFoundError
			The category has not been found.

		Returns
		-------
		list_to_manage : dict
			The list to manage (either the whole list or a category's one).
		'''

		try:
			list_to_manage = self._list[category] if self._use_categories else self._list

		except KeyError:
			raise FCollectionCategoryNotFoundError(category)

		else:
			return list_to_manage

	def set(self, fname, f, *, category = None):
		'''
		Add a function to the collection, or replace an existing one.

		Parameters
		----------
		fname : str
			Name of the function.

		f : function
			Function to store.

		category : str
			Name of the category, if any.
		'''

		self._getList(category)[fname] = f

	def delete(self, fname, *, category = None):
		'''
		Delete a function.

		Parameters
		----------
		fname : str
			Name of the function to delete.

		category : str
			Name of the category, if any.

		Raises
		------
		FCollectionFunctionNotFoundError
			The function has not been found.
		'''

		list_to_manage = self._getList(category)

		try:
			del list_to_manage[fname]

		except KeyError:
			raise FCollectionFunctionNotFoundError(fname)

	def get(self, fname, *, category = None):
		'''
		Get a function.

		Parameters
		----------
		fname : str
			Name of the function to get.

		category : str
			Name of the category, if any.

		Raises
		------
		FCollectionFunctionNotFoundError
			The function has not been found.

		Returns
		-------
		f : function
			The wanted function.
		'''

		list_to_manage = self._getList(category)

		try:
			return list_to_manage[fname]

		except KeyError:
			raise FCollectionFunctionNotFoundError(fname)

	def getAll(self, *, category = None):
		'''
		Get all functions.

		Parameters
		----------
		category : str
			Name of the category, if any.

		Returns
		-------
		functions : list
			The list of stored functions.
		'''

		return list(self._getList(category).values())

	def call(self, fdesc, *args, category = None):
		'''
		Call a function.

		Parameters
		----------
		fdesc : str|list
			Name of the function to call, or list with name of the function as first item and then arguments to pass.

		args : mixed
			Args to pass to the function, before the description's ones.

		category : str
			Name of the category, if any.

		Returns
		-------
		output : mixed
			Output of the called function.
		'''

		list_to_manage = self._getList(category)

		if type(fdesc) is not list:
			fdesc = [fdesc]

		try:
			f = list_to_manage[fdesc[0]]

		except KeyError:
			raise FCollectionFunctionNotFoundError(fdesc[0])

		else:
			return f(*args, *fdesc[1:])

	def setFilterRegex(self, filter_regex):
		'''
		Define the filter regex.
		The regex must define a group named `name` which matches the function's name.
		If the collection is categorized, the regex must also define a group named `category`.

		Parameters
		----------
		filter_regex : str
			Filter regex to define.

		Raises
		------
		InvalidFilterRegexError
			The regex does not contain the required groups.
		'''

		regex = re.compile(filter_regex)

		if not('name' in regex.groupindex) or (self._use_categories and not('category' in regex.groupindex)):
			raise InvalidFilterRegexError(filter_regex)

		else:
			self._filter_regex = regex

	def loadFromModule(self, module):
		'''
		Load functions from a given module, according to the filter regex.

		Parameters
		----------
		module : Module
			Module (already loaded) where are defined the functions.
		'''

		for function in inspect.getmembers(module, inspect.isfunction):
			match = self._filter_regex.match(function[0])

			if match:
				category = match.group('category') if self._use_categories else None
				self.set(match.group('name'), function[1], category = category)
