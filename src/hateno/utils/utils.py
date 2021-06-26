#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import importlib.util
import pathlib
import sys
import uuid

def findFolder():
	'''
	Find the Hateno-compatible folder we're currently in by testing the existence of the `.hateno` subfolder.
	First search in the current folder, then in the parent, and then the parent of the parent, etc.

	Returns
	-------
	folder : pathlib.Path
		Path to the folder, relatively to the current one. `None` if nothing has been found.
	'''

	folder = pathlib.Path('.').resolve()

	if (folder / '.hateno').is_dir():
		return folder

	for parent in folder.parents:
		if (parent / '.hateno').is_dir():
			return parent

	return None

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
