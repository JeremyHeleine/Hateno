#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
In this file, the default checkers are defined.
A checker must belong into one of the following categories: file checkers, folder checkers, and global checkers.

--

A file checker can be applied to a file. It must accept have the following signature.
Convention: prefix the name of the function by `file_`.

:param dict simulation:
	The simulation which has been generated, as defined by the user.

:param list full_settings:
	The full list of settings for this simulation, with default values when needed.

:param str filename:
	The name of the file to check (path relative to the simulation's folder).

:return bool:
	`True` if the file successfully passed the test, `False` otherwise.
"""

import os

"""
File checker.
Check if the file exists.
"""

def file_exists(simulation, settings, filename):
	return os.path.isfile(os.path.join(simulation['folder'], filename))

"""
File checker.
Check if a file contains is not empty.
"""

def file_notEmpty(simulation, settings, filename):
	return os.stat(os.path.join(simulation['folder'], filename)).st_size != 0
