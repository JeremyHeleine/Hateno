#!/usr/bin/env python3
# -*- coding: utf-8 -*-

class GeneratorError(Exception):
	'''
	Base class for exceptions occurring in the Generator.
	'''

	pass

class DestinationFolderExistsError(GeneratorError):
	'''
	Exception raised when a destination folder already exists.
	'''

	pass

class GeneratorEmptyListError(GeneratorError):
	'''
	Exception raised when a specific list is empty.
	'''

	pass
