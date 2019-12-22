#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
In this file, the default checkers are defined.
A checker must belong into one of the following categories: file checkers, folder checkers, and global checkers.

--

A file checker can be applied to a file. It must have the following signature.
Convention: prefix the name of the function by `file_`.

:param dict simulation:
	The simulation which has been generated, as defined by the user.

:param list full_settings:
	The full list of settings for this simulation, with default values when needed.

:param str filename:
	The name of the file to check (path relative to the simulation's folder).

:return bool:
	`True` if the file successfully passed the test, `False` otherwise.

--

A folder checker can be applied to a folder. It must have the same signature as a file checker (the filename is replaced by the foldername).
Convention: prefix the name of the function by `folder_`.

--

A global checker can be applied to the whole simulation folder. It must have the same signature as a file/folder checker, except for the third argument, described below.
Convention: prefix the name of the function by `global_`.

:param dict tree:
	The list of files and folders names listed in the `output` in the configuration file.
"""

import os
import glob

"""
File checker.
Check if at least one file matching the pattern exists.
"""

def file_exists(simulation, settings, filename):
	matching_files = [entry for entry in glob.glob(os.path.join(simulation['folder'], filename)) if os.path.isfile(entry)]
	return len(matching_files) > 0

"""
File checker.
Check if all files matching the pattern are non empty.
"""

def file_notEmpty(simulation, settings, filename):
	nonempty_files = [entry for entry in glob.glob(os.path.join(simulation['folder'], filename)) if os.path.isfile(entry) and os.stat(entry).st_size != 0]
	return len(nonempty_files) > 0

"""
Folder check.
Check if at least one folder matching the pattern exists.
"""

def folder_exists(simulation, settings, foldername):
	matching_folders = [entry for entry in glob.glob(os.path.join(simulation['folder'], foldername)) if os.path.isdir(entry)]
	return len(matching_folders) > 0

"""
Folder check.
Check if the folder is not empty.
"""

def folder_notEmpty(simulation, settings, foldername):
	return len(os.listdir(os.path.join(simulation['folder'], foldername))) > 0

"""
Global check.
Check if no other file than the listed ones is present.
"""

def global_noMore(simulation, settings, tree):
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

	return set(folder_tree['folders']) == set(matching_tree['folders']) and set(folder_tree['files']) == set(matching_tree['files'])
