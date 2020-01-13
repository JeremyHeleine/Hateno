#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import paramiko

from utils import jsonfiles

class RemoteFolder():
	'''
	Send files to and receive from a remote folder.

	Parameters
	----------
	folder_conf : str
		Path to the configuration file of the remote folder.

	Raises
	------
	FileNotFoundError
		The configuration file does not exist.
	'''

	def __init__(self, folder_conf):
		self._configuration_file = folder_conf

		if not(os.path.isfile(self._configuration_file)):
			raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), self._configuration_file)

		self._configuration = jsonfiles.read(self._configuration_file)

	def open(self):
		'''
		Open the connection.
		'''

		self._ssh = paramiko.SSHClient()
		self._ssh.load_system_host_keys()
		self._ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
		self._ssh.connect(self._configuration['host'], username = self._configuration['user'])

		self._sftp = self._ssh.open_sftp()

		if 'working_directory' in self._configuration:
			self._sftp.chdir(self._configuration['working_directory'])

	def close(self):
		'''
		Close the connection.
		'''

		try:
			self._ssh.close()

		except AttributeError:
			pass

	def copyChmod(self, filename, remote_path):
		'''
		Change the chmod of a remote file to reflect a local one.

		Parameters
		----------
		filename : str
			Name of the file to use to copy the chmod.

		remote_path : str
			Remote path to alter.
		'''

		self._sftp.chmod(remote_path, os.stat(filename).st_mode & 0o777)

	def sendFile(self, filename, remote_path = None, *, copy_permissions = True, delete = False):
		'''
		Send a file.

		Parameters
		----------
		filename : str
			Name of the file to send.

		remote_path : str
			Path of the remote file to write.

		permissions : int
			Permissions of the remote file.

		delete : boolean
			`True` to delete the local file, once sent.
		'''

		if not(remote_path):
			remote_path = os.path.basename(filename)

		self._sftp.put(filename, remote_path)

		if copy_permissions:
			self.copyChmod(filename, remote_path)

		if delete:
			os.unlink(filename)

	def sendDir(self, directory, remote_path = None, *, copy_permissions = True, delete = False):
		'''
		Send a directory.

		Parameters
		----------
		directory : str
			Name of the directory to send.

		remote_path : str
			Path of the remote directory to create.
		'''

		if not(remote_path):
			remote_path = os.path.basename(os.path.normpath(directory))

		try:
			entries = self._sftp.listdir(remote_path)

		except FileNotFoundError:
			self._sftp.mkdir(remote_path)

		if copy_permissions:
			self.copyChmod(directory, remote_path)

		for entry in [(entry, os.path.join(directory, entry)) for entry in os.listdir(directory)]:
			(self.sendDir if os.path.isdir(entry[1]) else self.sendFile)(entry[1], os.path.join(remote_path, entry[0]), copy_permissions = copy_permissions, delete = delete)

		if delete:
			os.rmdir(directory)
