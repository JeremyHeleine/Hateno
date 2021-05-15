#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
In this file, the default checkers are defined.
A checker must belong into one of the following categories: file checkers, folder checkers, and global checkers.

--

A file checker can be applied to a file. It must have the following signature.
Convention: prefix the name of the function by `file_`.

Parameters
----------
simulation : Simulation
	The simulation which has been generated, as defined by the user.

filename : str
	The name of the file to check (path relative to the simulation's folder).

Returns
-------
success : bool
	`True` if the file successfully passed the test, `False` otherwise.

--

A folder checker can be applied to a folder. It must have the same signature as a file checker (the filename is replaced by the foldername).
Convention: prefix the name of the function by `folder_`.

--

A global checker can be applied to the whole simulation folder. It must have the same signature as a file/folder checker, except for the third argument, described below.
Convention: prefix the name of the function by `global_`.

Parameters
----------
tree : dict
	The list of files and folders names listed in the `output` in the configuration file.
'''

import glob
import os

def file_exists(simulation, filename, check_if = None):
	'''
	File checker.
	Check if at least one file matching the pattern exists.

	Parameters
	----------
	check_if : str
		If provided, do the check only if this condition is true.
	'''

	if check_if is not None and not(simulation.parseString(f'(({check_if}))')):
		return True

	matching_files = [entry for entry in glob.glob(os.path.join(simulation['folder'], filename)) if os.path.isfile(entry)]
	return len(matching_files) > 0

def file_notEmpty(simulation, filename, check_if = None):
	'''
	File checker.
	Check if all files matching the pattern are non empty.

	Parameters
	----------
	check_if : str
		If provided, do the check only if this condition is true.
	'''

	if check_if is not None and not(simulation.parseString(f'(({check_if}))')):
		return True

	nonempty_files = [entry for entry in glob.glob(os.path.join(simulation['folder'], filename)) if os.path.isfile(entry) and os.stat(entry).st_size != 0]
	return len(nonempty_files) > 0

def folder_exists(simulation, foldername, check_if = None):
	'''
	Folder check.
	Check if at least one folder matching the pattern exists.

	Parameters
	----------
	check_if : str
		If provided, do the check only if this condition is true.
	'''

	if check_if is not None and not(simulation.parseString(f'(({check_if}))')):
		return True

	matching_folders = [entry for entry in glob.glob(os.path.join(simulation['folder'], foldername)) if os.path.isdir(entry)]
	return len(matching_folders) > 0

def folder_notEmpty(simulation, foldername, check_if = None):
	'''
	Folder check.
	Check if the folder is not empty.

	Parameters
	----------
	check_if : str
		If provided, do the check only if this condition is true.
	'''

	if check_if is not None and not(simulation.parseString(f'(({check_if}))')):
		return True

	return len(os.listdir(os.path.join(simulation['folder'], foldername))) > 0

def global_noMore(simulation, tree):
	'''
	Global check.
	Check if no other file than the listed ones is present.
	'''

	folder_paths = [(
		list(map(lambda n: os.path.relpath(os.path.join(dirpath, n), simulation['folder']), dirnames)),
		list(map(lambda n: os.path.relpath(os.path.join(dirpath, n), simulation['folder']), filenames))
	) for dirpath, dirnames, filenames in os.walk(simulation['folder'])]

	dirnames, filenames = zip(*folder_paths)
	folder_tree = {
		'folders': sum(dirnames, []),
		'files': sum(filenames, [])
	}

	matching_tree = {
		output_entry: [os.path.relpath(entry, simulation['folder']) for entry in sum([glob.glob(os.path.join(simulation['folder'], pattern)) for pattern in patterns], [])]
		for output_entry, patterns in tree.items()
	}

	return set(folder_tree['folders']) <= set(matching_tree['folders']) and set(folder_tree['files']) <= set(matching_tree['files'])
