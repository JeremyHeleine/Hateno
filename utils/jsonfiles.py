#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json

"""
Read a JSON file.

:param str filename:
	Path to the JSON file to read.

:return dict|list:
	The object described in the JSON file.
"""

def read(filename):
	with open(filename, 'r') as f:
		return json.loads(f.read())

"""
Save an object into a JSON file.

:param dict|list obj:
	Object to save.

:param str filename:
	Path to the JSON file.
"""

def write(obj, filename):
	with open(filename, 'w') as f:
		json.dump(obj, f, sort_keys = True, indent = 4, separators = (',', ': '))
