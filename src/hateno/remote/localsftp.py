#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil

class LocalSFTP():
	'''
	Implement some actions on local files, with the same methods names than paramiko.SFTP.

	Parameters
	----------
	wd : str
		Working directory (base directory to use for the files).
	'''

	def __init__(self, wd = '.'):
		self.chdir(wd)

	def chdir(self, wd):
		'''
		Change the working directory.
		If the new working directory does not exist, create it.

		Parameters
		----------
		wd : str
			Working directory to use.
		'''

		if not(os.path.isdir(wd)):
			os.makedirs(wd)

		self._wd = wd

	def path(self, path):
		'''
		Prepend a path with the working directory.

		Parameters
		----------
		path : str
			Path to prepend.

		Returns
		-------
		complete_path : str
			The complete path, prepended.
		'''

		return os.path.join(self._wd, path)

	def put(self, local_path, remote_path, replace = False, delete = False):
		'''
		Copy or move a file or folder into the working directory.

		Parameters
		----------
		local_path : str
			Path to the file/folder to copy.

		remote_path : str
			Path of the copied file/folder.

		replace : bool
			If `False`, send a file only if the source is more recent. Otherwise always send it.

		delete : bool
			If `True`, move the local file/folder, if `False`, copy it.
		'''

		send = shutil.move

		if os.path.isfile(local_path):
			if not(replace):
				try:
					if os.stat(local_path).st_mtime <= os.stat(self.path(remote_path)).st_mtime:
						return None

				except FileNotFoundError:
					pass

			if not(delete):
				send = shutil.copy

		else:
			if not(delete):
				send = shutil.copytree

			if replace and os.path.isdir(self.path(remote_path)):
				shutil.rmtree(self.path(remote_path))

		try:
			send(local_path, self.path(remote_path))

		except FileNotFoundError:
			os.makedirs(os.path.dirname(self.path(remote_path)))
			send(local_path, self.path(remote_path))

	def get(self, remote_path, local_path, delete = False):
		'''
		Copy or move a file or folder from the working directory.

		Parameters
		----------
		remote_path : str
			Path to the file/folder to copy.

		local_path : str
			Path of the copied file/folder.

		delete : bool
			If `True`, move the remote file/folder, if `False`, copy it.
		'''

		if os.path.isdir(local_path):
			shutil.rmtree(local_path)

		receive = shutil.move

		if not(delete):
			receive = shutil.copy if os.path.isfile(self.path(remote_path)) else shutil.copytree

		try:
			receive(self.path(remote_path), local_path)

		except FileNotFoundError:
			os.makedirs(os.path.dirname(local_path))
			receive(self.path(remote_path), local_path)

	def remove(self, path):
		'''
		Remove a file or a folder.

		Parameters
		----------
		path : str
			Path to the file/folder to remove.
		'''

		path = self.path(path)

		if os.path.isfile(path):
			os.unlink(path)

		else:
			shutil.rmtree(path)

	def stat(self, path):
		'''
		Get some numbers about a file.

		Parameters
		----------
		path : str
			Path of the file.

		Returns
		-------
		res : os.stat_result
			Result of the stat function.
		'''

		return os.stat(self.path(path))

	def open(self, path, mode):
		'''
		Open a file.

		Parameters
		----------
		path : str
			Path to the file to open.

		mode : str
			Opening mode.

		Returns
		-------
		fid : TextIOWrapper
			Opened file.
		'''

		return open(self.path(path), mode)
