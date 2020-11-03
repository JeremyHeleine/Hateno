#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import importlib.util
import uuid

def loadModuleFromFile(filename):
	'''
	Load a source file to use as a module.

	Parameters
	----------
	filename : str
		Path to the file to load.

	Returns
	-------
	module : module
		Loaded module.
	'''

	module_name = uuid.uuid4().hex
	spec = importlib.util.spec_from_file_location(module_name, filename)
	module = importlib.util.module_from_spec(spec)
	sys.modules[module_name] = module
	spec.loader.exec_module(module)

	return module
