#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
In this file, the default "values fixers" are defined.

Convention: prefix the name of the function by `fixer_`.
'''

def fixer_intFloats(value):
	'''
	Converts floats like `2.0` into integers.
	'''

	if type(value) is float and int(value) == value:
		return int(value)

	return value
