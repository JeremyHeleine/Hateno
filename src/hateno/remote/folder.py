#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import io
import os
import paramiko
import shutil
import subprocess
import time

from .localsftp import LocalSFTP
from .sftp import SFTP
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

	def callHateno(self, script, args):
		'''
		Call Hateno on the remote.

		Parameters
		----------
		script : str
		 	The Hateno script to call.

		args : list
			Args to pass to the call.
		'''

		cmd = f'{self._configuration["hateno"]} {script} '
		cmd += ' '.join(args)

		if 'pre_hateno' in self._configuration:
			cmd = f'{self._configuration["pre_hateno"]}; {cmd}'

		self.execute(cmd)

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
