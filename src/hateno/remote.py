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

	def __enter__(self):
		'''
		Context manager to call `open()` and `close()` automatically.
		'''

		self.open()
		return self

	def __exit__(self, type, value, traceback):
		'''
		Ensure `close()` is called when exiting the context manager.
		'''

		self.close()

	def _connectSSH(self, config):
		'''
		Open an SSH connection.

		Parameters
		----------
		config : dict
			Parameters of the connection to open.
		'''

		ssh = paramiko.SSHClient()
		ssh.load_system_host_keys()
		ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

		connect_params = {'username': config['user']}

		try:
			connect_params['port'] = config['port']

		except KeyError:
			pass

		try:
			gate = self._connectSSH(config['gate'])

		except KeyError:
			pass

		else:
			connect_params['sock'] = gate.get_transport().open_channel('direct-tcpip', (config['host'], 22), ('', 0))

		ssh.connect(config['host'], **connect_params)

		return ssh

	def open(self):
		'''
		Open the connection.
		'''

		if self._local:
			self._sftp = LocalSFTP()

		else:
			self._ssh = self._connectSSH(self._configuration)
			self._sftp = SFTP.from_transport(self._ssh.get_transport())

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

	def getFileContents(self, remote_path):
		'''
		Retrieve the content of a remote file.

		Parameters
		----------
		remote_path : str
			Path of the remote file to read.

		Returns
		-------
		content : str
			Content of the file, as a string.
		'''

		with self._sftp.open(remote_path, 'r') as f:
			return f.read()

	def putFileContents(self, remote_path, content):
		'''
		Write the content of a remote file.

		Parameters
		----------
		remote_path : str
			Path of the remote file to write.

		content : str
			Content to write.
		'''

		with self._sftp.open(remote_path, 'w') as f:
			f.write(content)

	def appendToFile(self, remote_path, content):
		'''
		Append a string to a remote file.

		Parameters
		----------
		remote_path : str
			Path of the remote file to write into.

		content : str
			Content to append.
		'''

		with self._sftp.open(remote_path, 'a') as f:
			f.write(content)

	def send(self, local_path, remote_path = None, *, delete = False, replace = False):
		'''
		Send a file or a folder.

		Parameters
		----------
		local_path : str
			Path of the file/folder to send.

		remote_path : str
			Path of the remote file/folder to create.

		delete : boolean
			`True` to delete the local file/folder, once sent.

		replace : bool
			If `False`, send a file only if the source is more recent. Otherwise always send it.

		Raises
		------
		FileNotFoundError
			The local file/folder does not exist.

		Returns
		-------
		remote_path : str
			Remote path of the sent file/directory.
		'''

		stats = os.stat(local_path)

		if not(remote_path):
			remote_path = os.path.basename(os.path.normpath(local_path))

		self._sftp.put(local_path, remote_path, replace, delete)

		return remote_path

	def receive(self, remote_path, local_path = None, *, delete = False):
		'''
		Receive (download) a file or a folder.

		Parameters
		----------
		remote_path : str
			Path of the remote file/folder to receive.

		local_path : str
			Name of the file/folder to create.

		delete : boolean
			`True` to delete the remote file/folder.

		Raises
		------
		RemotePathNotFoundError
			The remote file/folder does not exist.

		Returns
		-------
		local_path : str
			Local path of the received file/folder.
		'''

		try:
			stats = self._sftp.stat(remote_path)

		except FileNotFoundError:
			raise RemotePathNotFoundError(remote_path)

		if not(local_path):
			local_path = os.path.basename(os.path.normpath(remote_path))

		self._sftp.get(remote_path, local_path, delete)

		return local_path

	def deleteRemote(self, entries):
		'''
		Recursively delete some remote entries.

		Parameters
		----------
		entries : str|list
			Single path, or list of paths to delete.
		'''

		if type(entries) is not list:
			entries = [entries]

		for entry in entries:
			self._sftp.remove(entry)

	def deleteLocal(self, entries):
		'''
		Recursively delete some local entries.

		Parameters
		----------
		entries : str|list
			Single path, or list of paths to delete.
		'''

		if type(entries) is not list:
			entries = [entries]

		for entry in entries:
			(shutil.rmtree if os.path.isdir(entry) else os.unlink)(entry)

class SFTP(paramiko.SFTPClient):
	'''
	Overwrite some methods to add some options.
	'''

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

	def remove(self, path):
		'''
		Remove a file or a folder.

		Parameters
		----------
		path : str
			Path of the file/folder to remove.
		'''

		if stat.S_ISDIR(self.stat(path).st_mode):
			for entry in self.listdir(path):
				self.remove(os.path.join(path, entry))

			self.rmdir(path)

		else:
			super().remove(path)

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
