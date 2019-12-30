#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json

def read(filename):
	'''
	Read a JSON file.

	Parameters
	----------
	filename : str
		Path to the JSON file to read.

	Returns
	-------
	obj : dict|list
		The object described in the JSON file.
	'''

	with open(filename, 'r') as f:
		return json.loads(f.read())

def write(obj, filename):
	'''
	Save an object into a JSON file.

	Parameters
	----------
	obj : dict|list
		Object to save.

	filename : str
		Path to the JSON file.
	'''

	with open(filename, 'w') as f:
		json.dump(obj, f, sort_keys = True, indent = 4, separators = (',', ': '))
