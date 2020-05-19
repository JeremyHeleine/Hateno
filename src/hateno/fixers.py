#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
In this file, the default "values fixers" are defined.
A fixer always must admit at least one parameter: the value to fix. It must return the fixed value.
Additional parameters are allowed, set in the configurations file.

Convention: prefix the name of the function by `fixer_`.
'''

def fixer_intFloats(value):
	'''
	Converts floats like `2.0` into integers.
	'''

	if type(value) is float and int(value) == value:
		return int(value)

	return value

def fixer_round(value, n_digits):
	'''
	Round all float numbers.

	Parameters
	----------
	n_digits : int
		Number of digits to keep.
	'''

	if type(value) is float:
		return round(value, n_digits)

	return value

def fixer_sortlist(value):
	'''
	Sort a list.
	'''

	if type(value) is list:
		return sorted(value)

	return value

def fixer_list2str(value, separator = ', '):
	'''
	Convert a list into a string.

	Parameters
	----------
	separator : str
		String to place between each list item.
	'''

	if type(value) is list:
		return separator.join(map(str, value))

	return value
