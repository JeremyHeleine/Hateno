#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import importlib.util
import json

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
		with open(filename, 'r') as f:
			return json.loads(f.read())

	except json.decoder.JSONDecodeError:
		if not(allow_generator):
			raise

		module_name = 'tmpobjectgenerator'
		spec = importlib.util.spec_from_file_location(module_name, filename)
		module = importlib.util.module_from_spec(spec)
		sys.modules[module_name] = module
		spec.loader.exec_module(module)

		return module.generate()

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
