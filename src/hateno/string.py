#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import codecs
import base64
import hashlib
import uuid
import json
import ast

from math import sqrt, cos, sin

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

def toObject(s):
	'''
	Convert a base64 string into the object it represents.

	Parameters
	----------
	s : str
		The string to convert.

	Returns
	-------
	obj : dict|list
		The represented object.
	'''

	obj_str = base64.urlsafe_b64decode(s).decode('utf-8')
	return json.loads(obj_str)

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

def uniqueID():
	'''
	Generate a unique ID.

	Returns
	-------
	id : str
		The generated ID, as a 32-character hexadecimal string.
	'''

	return uuid.uuid4().hex

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

def safeEval(expr):
	'''
	Safely evaluate an expression by allowing only certain tokens. The following is allowed.
	* Numbers (of any kind: 1, 2.3, 5e-4, etc.)
	* Normal strings
	* Lists
	* Booleans
	* Arithmetic operators:
		+, -, *, /, //, %, **
	* Conditional operators:
		==, !=, <, <=, >, >=, and, or, not(), in
	* Mathematical functions:
		abs, sqrt, cos, sin, tan

	Parameters
	----------
	expr : str
		Expression to evaluate.

	Returns
	-------
	res : mixed
		The result of the expression.

	Raises
	------
	ValueError
		The expression contains an unallowed token.
	'''

	whitelist_sample = 'False - True <= -1**2 < 1 + f(1) > 1.5 * 2 >= 2 / 2 and 1 // 2 == 0 or not(1 % 2 != 0) or "a" in ["a", "b"]'
	nodes_whitelist = set([x.__class__.__name__ for x in ast.walk(ast.parse(whitelist_sample))])
	names_whitelist = set(['abs', 'sqrt', 'cos', 'sin', 'tan'])

	nodes = set([x.__class__.__name__ for x in ast.walk(ast.parse(expr))])
	names = set([x.id for x in ast.walk(ast.parse(expr)) if x.__class__.__name__ == 'Name'])

	if (nodes - nodes_whitelist) | (names - names_whitelist):
		raise ValueError(f'Unallowed expression `{expr}`')

	return eval(expr)
