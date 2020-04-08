#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import io
import os
import stat
import shutil
import subprocess
import paramiko

from . import jsonfiles
from .errors import *

class RemoteFolder():
	'''
	Send files to and receive from a remote folder.

	Parameters
	----------
	folder_conf : dict
		Configuration of the remote folder.

	Raises
	------
	FileNotFoundError
		The configuration file does not exist.
	'''

	def __init__(self, folder_conf):
		self._configuration = folder_conf
		self._local = (self._configuration['host'] == 'local')

	def open(self):
		'''
		Open the connection.
		'''

		if self._local:
			self._sftp = LocalSFTP()

		else:
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

	def execute(self, cmd):
		'''
		Remotely execute a command from the working directory.

		Parameters
		----------
		cmd : str
			Command to execute.

		Returns
		-------
		output : paramiko.ChannelFile
			Output of the command (file-like object).
		'''

		if 'working_directory' in self._configuration:
			cmd = f'cd {self._configuration["working_directory"]}; {cmd}'

		if self._local:
			p = subprocess.run(cmd, shell = True, stdout = subprocess.PIPE)

			stdout = io.StringIO(p.stdout.decode())
			return stdout

		else:
			stdin, stdout, stderr = self._ssh.exec_command(cmd)
			return stdout

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

		os.chmod(filename, self._sftp.stat(remote_path).st_mode & 0o777)

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

		Returns
		-------
		remote_path : str
			Remote path of the sent file.
		'''

		if not(remote_path):
			remote_path = os.path.basename(filename)

		self._sftp.put(filename, remote_path)

		if copy_permissions:
			self.copyChmodToRemote(filename, remote_path)

		if delete:
			os.unlink(filename)

		return remote_path

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

		Raises
		------
		RemotePathNotFoundError
			The remote file does not exist.

		Returns
		-------
		filename : str
			Path of the received file.
		'''

		if not(filename):
			filename = os.path.basename(remote_path)

		try:
			self._sftp.get(remote_path, filename)

		except FileNotFoundError:
			raise RemotePathNotFoundError(remote_path)

		if copy_permissions:
			self.copyChmodToLocal(remote_path, filename)

		if delete:
			self._sftp.remove(remote_path)

		return filename

	def getFileContents(self, remote_path, *, callback = None):
		'''
		Retrieve the content of a remote file.

		Parameters
		----------
		remote_path : str
			Path of the remote file to read.

		callback : function
			Function to transform each line.

		Returns
		-------
		content : list
			Content of the file, as a list of lines.
		'''

		content = []

		with self._sftp.open(remote_path, 'r') as f:
			if callback is None:
				content = f.readlines()

			else:
				for line in f:
					content.append(callback(line))

		return content

	def makedirs(self, directory):
		'''
		Recursively create a directory.

		Parameters
		----------
		directory : str
			Path to create.
		'''

		try:
			self._sftp.mkdir(directory)

		except FileNotFoundError:
			self.makedirs(os.path.split(os.path.normpath(directory))[0])
			self._sftp.mkdir(directory)

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

		Returns
		-------
		remote_path : str
			Remote path of the sent directory.
		'''

		if not(remote_path):
			remote_path = os.path.basename(os.path.normpath(directory))

		try:
			entries = self._sftp.listdir(remote_path)

			if empty_dest and entries:
				self.deleteRemote([os.path.join(remote_path, e) for e in entries])

		except FileNotFoundError:
			self.makedirs(remote_path)

		if copy_permissions:
			self.copyChmodToRemote(directory, remote_path)

		for entry in [(entry, os.path.join(directory, entry)) for entry in os.listdir(directory)]:
			(self.sendDir if os.path.isdir(entry[1]) else self.sendFile)(entry[1], os.path.join(remote_path, entry[0]), copy_permissions = copy_permissions, delete = delete)

		if delete:
			os.rmdir(directory)

		return remote_path

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

		Raises
		------
		RemotePathNotFoundError
			The remote directory does not exist.

		Returns
		-------
		directory : str
			Local path of the received directory.
		'''

		try:
			stats = self._sftp.stat(remote_path)

		except FileNotFoundError:
			raise RemotePathNotFoundError(remote_path)

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

		for entry in [(entry, os.path.join(remote_path, entry)) for entry in self._sftp.listdir(remote_path)]:
			(self.receiveDir if stat.S_ISDIR(self._sftp.stat(entry[1]).st_mode) else self.receiveFile)(entry[1], os.path.join(directory, entry[0]), copy_permissions = copy_permissions, delete = delete)

		if delete:
			self._sftp.rmdir(remote_path)

		return directory

	def send(self, local_path, remote_path = None, *, copy_permissions = True, delete = False, empty_dest = False):
		'''
		Send a file or a directory.

		Parameters
		----------
		local_path : str
			Path of the file/directory to send.

		remote_path : str
			Path of the remote file/directory to create.

		copy_permissions : boolean
			`True` to copy the chmod from the local file/directory.

		delete : boolean
			`True` to delete the local file/directory, once sent.

		empty_dest : boolean
			`True` to ensure the destination folder is empty in the case of a directory.

		Returns
		-------
		remote_path : str
			Remote path of the sent file/directory.
		'''

		kwargs = {
			'copy_permissions': copy_permissions,
			'delete': delete
		}

		send = self.sendFile

		if os.path.isdir(local_path):
			send = self.sendDir
			kwargs['empty_dest'] = empty_dest

		return send(local_path, remote_path, **kwargs)

	def receive(self, remote_path, local_path = None, *, copy_permissions = True, delete = False, empty_dest = False):
		'''
		Receive (download) a file/directory.

		Parameters
		----------
		remote_path : str
			Path of the remote file/directory to receive.

		local_path : str
			Name of the file/directory to create.

		copy_permissions : boolean
			`True` to copy the chmod from the remote file/directory.

		delete : boolean
			`True` to delete the remote file/directory.

		empty_dest : boolean
			`True` to ensure the destination folder is empty in the case of a directory.

		Returns
		-------
		local_path : str
			Local path of the received file/directory.
		'''

		kwargs = {
			'copy_permissions': copy_permissions,
			'delete': delete
		}

		receive = self.receiveFile

		if stat.S_ISDIR(self._sftp.stat(remote_path).st_mode):
			receive = self.receiveDir
			kwargs['empty_dest'] = empty_dest

		return receive(remote_path, local_path, **kwargs)

	def deleteRemote(self, entries):
		'''
		Recursively delete some remote entries.

		Parameters
		----------
		entries : list
			List of paths to delete.
		'''

		for entry in entries:
			if stat.S_ISDIR(self._sftp.stat(entry).st_mode):
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

class LocalSFTP():
	'''
	Implement some actions on local files, with the same methods names than paramiko.SFTP.

	Parameters
	----------
	wd : str
		Working directory (base directory to use for the files).
	'''

	def __init__(self, wd = '.'):
		self._wd = wd

	def chdir(self, wd):
		'''
		Change the working directory.

		Parameters
		----------
		wd : str
			Working directory to use.
		'''

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

	def put(self, local_path, remote_path):
		'''
		Copy a file into the working directory.

		Parameters
		----------
		local_path : str
			Path to the file to copy.

		remote_path : str
			Path of the copied file.
		'''

		shutil.copy(local_path, self.path(remote_path))

	def get(self, remote_path, local_path):
		'''
		Copy a file from the working directory.

		Parameters
		----------
		remote_path : str
			Path to the file to copy.

		local_path : str
			Path of the copied file.
		'''

		shutil.copy(self.path(remote_path), local_path)

	def remove(self, path):
		'''
		Remove a file.

		Parameters
		----------
		path : str
			Path to the file to remove.
		'''

		os.unlink(self.path(path))

	def mkdir(self, dir):
		'''
		Create a directory.

		Parameters
		----------
		dir : str
			Path to the directory to create.
		'''

		os.mkdir(self.path(dir))

	def rmdir(self, dir):
		'''
		Remove a directory.

		Parameters
		----------
		dir : str
			Path to the directory to remove.
		'''

		os.rmdir(self.path(dir))

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

	def chmod(self, path, mode):
		'''
		Change the mode of a file.

		Parameters
		----------
		path : str
			Path to the file to alter.

		mode : int
			New mode to apply.
		'''

		os.chmod(self.path(path), mode)

	def listdir(self, dir):
		'''
		List a directory.

		Parameters
		----------
		dir : str
			Path of the directory to list.

		Returns
		-------
		content : list
			Entries contained in the directory.
		'''

		return os.listdir(self.path(dir))

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
