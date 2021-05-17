#!/usr/bin/env python3
# -*- coding: utf-8 -*-

class RemoteFolderError(Exception):
	'''
	Base class for exceptions occurring in a RemoteFolder.
	'''

	pass

class RemotePathNotFoundError(RemoteFolderError):
	'''
	Exception raised when we try to access a remote path/directory which does not exist.

	Parameters
	----------
	remote_path : str
		The path.
	'''

	def __init__(self, remote_path):
		self.remote_path = remote_path
