#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
In this file, the default settings namers are defined.
A namer must admit the following signature.
Convention: prefix the name of the function by `namer_`.

Parameters
----------
setting : dict
	Representation of the setting.

Returns
-------
display_name : str
	The name to use when launching the simulation.
'''

def namer_appendLocalIndex(setting, separator = '-', only_if_multiple = False):
	'''
	Append the local index to the name.

	Parameters
	----------
	only_if_multiple : bool
		Append the index only if the setting is used more than once (locally).

	separator : str
		Separator between the name and the index.
	'''

	if only_if_multiple and setting['local_total'] <= 1:
		return setting['name']

	return setting['name'] + separator + str(setting['local_index'])

def namer_prependLocalIndex(setting, separator = '-', only_if_multiple = False):
	'''
	Prepend the local index to the name.

	Parameters
	----------
	only_if_multiple : bool
		Prepend the index only if the setting is used more than once (locally).

	separator : str
		Separator between the name and the index.
	'''

	if only_if_multiple and setting['local_total'] <= 1:
		return setting['name']

	return str(setting['local_index']) + separator + setting['name']

def namer_appendGlobalIndex(setting, separator = '-', only_if_multiple = False):
	'''
	Append the local index to the name.

	Parameters
	----------
	only_if_multiple : bool
		Append the index only if the setting is used more than once (globally).

	separator : str
		Separator between the name and the index.
	'''

	if only_if_multiple and setting['global_total'] <= 1:
		return setting['name']

	return setting['name'] + separator + str(setting['global_index'])

def namer_prependGlobalIndex(setting, separator = '-', only_if_multiple = False):
	'''
	Prepend the local index to the name.

	Parameters
	----------
	only_if_multiple : bool
		Prepend the index only if the setting is used more than once (globally).

	separator : str
		Separator between the name and the index.
	'''

	if only_if_multiple and setting['global_total'] <= 1:
		return setting['name']

	return str(setting['global_index']) + separator + setting['name']

def namer_suffix(setting, suffix = ''):
	'''
	Append a string to the name.

	Parameters
	----------
	suffix : str
		The string to append.
	'''

	return setting['name'] + suffix

def namer_prefix(setting, prefix = ''):
	'''
	Prepend a string to the name.

	Parameters
	----------
	prefix : str
		The string to prepend.
	'''

	return prefix + setting['name']
