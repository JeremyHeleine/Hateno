#!/usr/bin/env python3
# -*- coding: utf-8 -*-

class MakerError(Exception):
	'''
	Base class for exceptions occurring in the Maker.
	'''

	pass

class MakerPausedError(MakerError):
	'''
	Exception raised when the Maker is paused while it should not be.
	'''

	pass

class MakerNotPausedError(MakerError):
	'''
	Exception raised when the Maker is not paused while it should be.
	'''

	pass

class MakerStateWrongFormatError(MakerError):
	'''
	Exception raised when we try to read a Maker state that is in the wrong format.
	'''

	pass
