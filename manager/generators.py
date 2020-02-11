#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
In this file, the default variables generators are defined.
A variable generator must admit two parameters and return the result corresponding to these two objects.
Behind the scenes, we use functools.reduce() to apply a generator to the list of objects.

Convention: prefix the name of the function by `generator_`.
'''

def generator_sum(a, b):
	'''
	Generate the sum of settings.
	'''

	return a + b
