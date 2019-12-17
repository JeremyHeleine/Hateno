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
