#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import stat
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

	def copyChmodToRemote(self, filename, remote_path):
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

	def copyChmodToLocal(self, remote_path, filename):
		'''
		Change the chmod of a local file to reflect a remote one.

		Parameters
		----------
		remote_path : str
			Name of the file to use to copy the chmod.

		filename : str
			Local path to alter.
		'''

		os.chmod(filename, self._sftp.lstat(remote_path).st_mode & 0o777)

	def sendFile(self, filename, remote_path = None, *, copy_permissions = True, delete = False):
		'''
		Send a file.

		Parameters
		----------
		filename : str
			Name of the file to send.

		remote_path : str
			Path of the remote file to write.

		copy_permissions : boolean
			`True` to copy the chmod from the local file.

		delete : boolean
			`True` to delete the local file, once sent.
		'''

		if not(remote_path):
			remote_path = os.path.basename(filename)

		self._sftp.put(filename, remote_path)

		if copy_permissions:
			self.copyChmodToRemote(filename, remote_path)

		if delete:
			os.unlink(filename)

	def receiveFile(self, remote_path, filename = None, *, copy_permissions = True, delete = False):
		'''
		Receive (download) a file.

		Parameters
		----------
		remote_path : str
			Path of the remote file to receive.

		filename : str
			Name of the file to create.

		copy_permissions : boolean
			`True` to copy the chmod from the remote file.

		delete : boolean
			`True` to delete the remote file.
		'''

		if not(filename):
			filename = os.path.basename(remote_path)

		self._sftp.get(remote_path, filename)

		if copy_permissions:
			self.copyChmodToLocal(remote_path, filename)

		if delete:
			self._sftp.remove(remote_path)

	def sendDir(self, directory, remote_path = None, *, copy_permissions = True, delete = False, empty_dest = False):
		'''
		Send a directory.

		Parameters
		----------
		directory : str
			Name of the directory to send.

		remote_path : str
			Path of the remote directory to create.

		copy_permissions : boolean
			`True` to copy the chmod from the local directory.

		delete : boolean
			`True` to delete the local directory, once sent.

		empty_dest : boolean
			`True` to ensure the destination folder is empty.
		'''

		if not(remote_path):
			remote_path = os.path.basename(os.path.normpath(directory))

		try:
			entries = self._sftp.listdir(remote_path)

			if empty_dest and entries:
				self.deleteRemote([os.path.join(remote_path, e) for e in entries])

		except FileNotFoundError:
			self._sftp.mkdir(remote_path)

		if copy_permissions:
			self.copyChmodToRemote(directory, remote_path)

		for entry in [(entry, os.path.join(directory, entry)) for entry in os.listdir(directory)]:
			(self.sendDir if os.path.isdir(entry[1]) else self.sendFile)(entry[1], os.path.join(remote_path, entry[0]), copy_permissions = copy_permissions, delete = delete)

		if delete:
			os.rmdir(directory)

	def receiveDir(self, remote_path, directory = None, *, copy_permissions = True, delete = False, empty_dest = False):
		'''
		Receive (download) a directory.

		Parameters
		----------
		remote_path : str
			Path of the remote directory to receive.

		directory : str
			Name of the directory to create.

		copy_permissions : boolean
			`True` to copy the chmod from the remote directory.

		delete : boolean
			`True` to delete the remote directory.

		empty_dest : boolean
			`True` to ensure the destination folder is empty.
		'''

		if not(directory):
			directory = os.path.basename(os.path.normpath(remote_path))

		try:
			entries = os.listdir(directory)

			if empty_dest and entries:
				self.deleteLocal([os.path.join(directory, e) for e in entries])

		except FileNotFoundError:
			os.makedirs(directory)

		if copy_permissions:
			self.copyChmodToLocal(remote_path, directory)

		for entry in [(entry, os.path.join(remote_path, entry)) for entry in self._sftp.listdir(directory)]:
			(self.receiveDir if self._sftp.lstat(entry[1]).st_mode & stat.S_IFDIR else self.receiveFile)(entry[1], os.path.join(directory, entry[0]), copy_permissions = copy_permissions, delete = delete)

		if delete:
			self._sftp.rmdir(remote_path)

	def deleteRemote(self, entries):
		'''
		Recursively delete some remote entries.

		Parameters
		----------
		entries : list
			List of paths to delete.
		'''

		for entry in entries:
			if self._sftp.lstat(entry).st_mode & stat.S_IFDIR:
				self.deleteRemote([os.path.join(entry, e) for e in self._sftp.listdir(entry)])
				self._sftp.rmdir(entry)

			else:
				self._sftp.remove(entry)

	def deleteLocal(self, entries):
		'''
		Recursively delete some local entries.

		Parameters
		----------
		entries : list
			List of paths to delete.
		'''

		for entry in entries:
			(shutil.rmtree if os.path.isdir(entry) else os.unlink)(entry)
