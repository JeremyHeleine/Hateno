#!/usr/bin/env python3
# -*- coding: utf-8 -*-

class UIError(Exception):
	'''
	Base class for exceptions occurring in the UI.
	'''

	pass

class UINonMovableLine(UIError):
	'''
	Exception raised when we try to move a line which can't be moved.

	Parameters
	----------
	pos : int
		Position of the line.
	'''

	def __init__(self, pos):
		self.pos = pos
