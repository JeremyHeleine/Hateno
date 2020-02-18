#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import codecs
import base64
import hashlib
import json

def intOrNone(s):
	'''
	Convert a string into either an integer or a `None`.

	Parameters
	----------
	s : str
		The string to convert.

	Returns
	-------
	converted : int|None
		The wanted integer if `s` represents one, `None` otherwise.
	'''

	if re.match(r'^-?[0-9]+$', s):
		return int(s)

	return None

def fromObject(obj):
	'''
	Represent an object as a base64 string.

	Parameters
	----------
	obj : dict|list
		The object to represent.

	Returns
	-------
	obj_str : str
		The corresponding base64 string.
	'''

	obj_str = json.dumps(obj, sort_keys = True)
	obj_str = base64.urlsafe_b64encode(obj_str.encode('utf-8')).decode('ascii')
	return obj_str

def hash(s):
	'''
	Hash a string, mostly to serve as identifier.

	Parameters
	----------
	s : str
		The string to hash.

	Returns
	-------
	hash : str
		The hash.
	'''

	h = hashlib.md5(s.encode('utf-8')).hexdigest()
	b = codecs.encode(codecs.decode(h.encode('utf-8'), 'hex'), 'base64').decode()

	return b[:-1].replace('+', '-').replace('/', '_')[:-2]

def plural(n, if_single, if_plural, *, add_n = True):
	'''
	Return a string or another, depending on a number.

	Parameters
	----------
	n : int
		The number to test.

	if_single : str
		The string to return if `n` is lower or equal than 1.

	if_plural : str
		The string to return if `n` is greater than 1.

	add_n : bool
		`True` to prepend the string by the number, `False` to only get the string.

	Returns
	-------
	s : str
		The single or plural string, depending on the test.
	'''

	s = if_plural if n > 1 else if_single

	if add_n:
		s = f'{n} {s}'

	return s
