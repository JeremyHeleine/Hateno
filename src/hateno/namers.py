#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
In this file, the default settings namers are defined.
A namer must admit the following signature.
Convention: prefix the name of the function by `namer_`.

Parameters
----------
name : str
	The name of the setting.

local_index : int
	The index of the setting, inside its set.

local_total : int
	The total number the setting has been used inside its set.

global_index : int
	The index of the setting, among all sets.

global_total : int
	The total number the setting has been used among all sets.

Returns
-------
display_name : str
	The name to use when launching the simulation.
'''

def namer_appendLocalIndex(name, local_index, local_total, global_index, global_total, separator = '-', only_if_multiple = False):
	'''
	Append the local index to the name.

	Parameters
	----------
	only_if_multiple : bool
		Append the index only if the setting is used more than once (locally).

	separator : str
		Separator between the name and the index.
	'''

	if only_if_multiple and local_total <= 1:
		return name

	return name + separator + str(local_index)

def namer_appendGlobalIndex(name, local_index, local_total, global_index, global_total, separator = '-', only_if_multiple = False):
	'''
	Append the local index to the name.

	Parameters
	----------
	only_if_multiple : bool
		Append the index only if the setting is used more than once (globally).

	separator : str
		Separator between the name and the index.
	'''

	if only_if_multiple and global_total <= 1:
		return name

	return name + separator + str(global_index)

def namer_suffix(name, local_index, local_total, global_index, global_total, suffix = ''):
	'''
	Append a string to the name.

	Parameters
	----------
	suffix : str
		The string to append.
	'''

	return name + suffix

def namer_prefix(name, local_index, local_total, global_index, global_total, prefix = ''):
	'''
	Prepend a string to the name.

	Parameters
	----------
	prefix : str
		The string to prepend.
	'''

	return prefix + name
