#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import codecs
import base64
import hashlib
import json

"""
Represent an object as a base64 string.

:param dict|list obj:
	The object to represent.

:return str:
	The corresponding base64 string.
"""

def fromObject(obj):
	obj_str = json.dumps(obj, sort_keys = True)
	obj_str = base64.urlsafe_b64encode(obj_str.encode('utf-8')).decode('ascii')
	return obj_str

"""
Hash a string, mostly to serve as identifier.

:param str s:
	The string to hash.

:return str:
	The hash.
"""

def hash(s):
	h = hashlib.md5(s.encode('utf-8')).hexdigest()
	b = codecs.encode(codecs.decode(h.encode('utf-8'), 'hex'), 'base64').decode()

	return b[:-1].replace('+', '-').replace('/', '_')[:-2]
