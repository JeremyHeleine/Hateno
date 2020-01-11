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

	'''
	Open the connection.
	'''

	def open(self):
		self._ssh = paramiko.SSHClient()
		self._ssh.load_system_host_keys()
		self._ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
		self._ssh.connect(self._configuration['host'], username = self._configuration['user'])

		self._sftp = self._ssh.open_sftp()

		if 'working_directory' in self._configuration:
			self._sftp.chdir(self._configuration['working_directory'])

	'''
	Close the connection.
	'''

	def close(self):
		try:
			self._ssh.close()

		except AttributeError:
			pass
