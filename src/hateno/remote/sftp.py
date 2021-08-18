#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import paramiko
import stat
import time

class SFTP(paramiko.SFTPClient):
	'''
	Overwrite some methods to add some options.
	'''

	def chdir(self, wd):
		'''
		Change the current working directory.
		If it does not exist yet, create it.

		Parameters
		----------
		wd : str
			Working directory to use.
		'''

		try:
			s = self.stat(wd)

		except FileNotFoundError:
			self._makedirs(wd)

		finally:
			super().chdir(wd)

	def _copyLocalChmod(self, local_path, remote_path):
		'''
		Change the chmod of a remote file/folder to reflect a local one.

		Parameters
		----------
		local_path : str
			Name of the file/folder to use to copy the chmod.

		remote_path : str
			Remote path to alter.
		'''

		self.chmod(remote_path, os.stat(local_path).st_mode & 0o777)

	def _copyRemoteChmod(self, remote_path, local_path):
		'''
		Change the chmod of a local file/folder to reflect a remote one.

		Parameters
		----------
		remote_path : str
			Name of the file/folder to use to copy the chmod.

		local_path : str
			Local path to alter.
		'''

		os.chmod(local_path, self.stat(remote_path).st_mode & 0o777)

	def _makedirs(self, directory):
		'''
		Recursively create a directory.

		Parameters
		----------
		directory : str
			Path to create.
		'''

		try:
			self.mkdir(directory)

		except FileNotFoundError:
			self._makedirs(os.path.dirname(os.path.normpath(directory)))
			self.mkdir(directory)

	def put(self, local_path, remote_path, replace = False, delete = False):
		'''
		Send a file or a folder.

		Parameters
		----------
		local_path : str
			Path to the file/folder to send.

		remote_path : str
			Path of the remote file/folder to create.

		replace : bool
			If `False`, send a file only if the source is more recent. Otherwise always send it.

		delete : bool
			If `True`, delete the local file/folder once sent.
		'''

		if os.path.isfile(local_path):
			if not(replace):
				try:
					if os.stat(local_path).st_mtime <= self.stat(remote_path).st_mtime:
						return None

				except FileNotFoundError:
					pass

			try:
				super().put(local_path, remote_path)

			except FileNotFoundError:
				self._makedirs(os.path.dirname(remote_path))
				super().put(local_path, remote_path)

			self._copyLocalChmod(local_path, remote_path)

			if delete:
				os.unlink(local_path)

		else:
			for entry in os.listdir(local_path):
				self.put(os.path.join(local_path, entry), os.path.join(remote_path, entry), replace, delete)

			if delete:
				os.rmdir(local_path)

	def get(self, remote_path, local_path, delete = False):
		'''
		Download a file or a folder.

		Parameters
		----------
		remote_path : str
			Path to the file/folder to download.

		local_path : str
			Path of file/folder to create.

		delete : bool
			If `True`, delete the remote file/folder once downloaded.
		'''

		if stat.S_ISDIR(self.stat(remote_path).st_mode):
			for entry in self.listdir(remote_path):
				self.get(os.path.join(remote_path, entry), os.path.join(local_path, entry), delete)

			if delete:
				self.rmdir(remote_path)

		else:
			try:
				super().get(remote_path, local_path)

			except FileNotFoundError:
				os.makedirs(os.path.dirname(local_path))
				super().get(remote_path, local_path)

			self._copyRemoteChmod(remote_path, local_path)

			if delete:
				self.remove(remote_path)

	def remove(self, path, *, retry_rmdir = 3):
		'''
		Remove a file or a folder.

		Parameters
		----------
		path : str
			Path of the file/folder to remove.

		retry_rmdir : int
			Number of times we should retry to remove a directory.
		'''

		if stat.S_ISDIR(self.stat(path).st_mode):
			# We recursively empty the folder
			# After that, we should be able to call `rmdir()`
			# If not, that means a file has been added to the folder while we was emptying it

			for entry in self.listdir(path):
				self.remove(os.path.join(path, entry))

			try:
				self.rmdir(path)

			except OSError:
				if retry_rmdir > 0:
					self.remove(path, retry_rmdir = retry_rmdir - 1)

				else:
					raise

		else:
			super().remove(path)
