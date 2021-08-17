#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import time

from . import utils

def read(filename, *, allow_generator = False):
	'''
	Read a JSON file.

	Parameters
	----------
	filename : str
		Path to the JSON file to read.

	allow_generator : bool
		`True` to allow the use of a Python script as a generator of the object, `False` to allow JSON only.

	Returns
	-------
	obj : dict|list
		The object described in the JSON file.
	'''

	try:
		file_parts = os.path.splitext(filename)
		ext_parts = file_parts[1].split(':', maxsplit = 1)

		args = []
		if len(ext_parts) == 2:
			args = ext_parts[1].split(',')
			filename = ''.join([file_parts[0], ext_parts[0]])

		with open(filename, 'r') as f:
			return json.loads(f.read())

	except json.decoder.JSONDecodeError:
		if not(allow_generator):
			raise

		module = utils.loadModuleFromFile(filename)
		return module.generate(*args)

def readRetry(filename, *, max_failures = 10, delay = 0.1):
	'''
	Read a JSON file and retry if there is an error.

	Parameters
	----------
	filename : str
		Path to the JSON file to read.

	Returns
	-------
	obj : dict|list
		The object described in the JSON file.
	'''

	failures = 0

	while True:
		try:
			return read(filename)

		except json.decoder.JSONDecodeError:
			failures += 1

			if failures > max_failures:
				raise

			time.sleep(delay)

def write(obj, filename, *, sort_keys = False):
	'''
	Save an object into a JSON file.

	Parameters
	----------
	obj : dict|list
		Object to save.

	filename : str
		Path to the JSON file.

	sort_keys : bool
		`True` to sort the keys before writing the file.
	'''

	dirname = os.path.dirname(filename)
	if dirname and not(os.path.isdir(dirname)):
		os.makedirs(dirname)

	with open(filename, 'w') as f:
		json.dump(obj, f, sort_keys = sort_keys, indent = '\t', separators = (',', ': '))
