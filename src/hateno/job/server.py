#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil
import time

import watchdog.events

from .errors import *
from .filewatcher import FileWatcher
from ..utils import Events, jsonfiles

class JobServer():
	'''
	Server part of a job, distributing the command lines over the clients.

	Parameters
	----------
	command_lines_filename : str
		Path to the file listing the command lines to execute (one command line per line).

	job_dir : str
		Path to the job directory to create to store the messaging files.
	'''

	def __init__(self, command_lines_filename, job_dir):
		self._command_lines_filename = command_lines_filename
		self._job_dir = job_dir

		self._event_handler = FileEventHandler(self._job_dir, self._newClient, self._clientGone, self._processRequest)
		self._watcher = FileWatcher(self._event_handler, self._job_dir)

		self._clients = []

		self._log = []

		self.events = Events([
			'client-new', 'client-gone',
			'sent', 'log'
		])

	def __enter__(self):
		'''
		Context manager to automatically call `stop()`.
		'''

		self.start()
		return self

	def __exit__(self, *args, **kwargs):
		'''
		Call `stop()` after exiting a context manager.
		'''

		self.stop()

	def start(self):
		'''
		Start the server.
		Create the job directory.
		Create the generator providing the command lines.

		Raises
		------
		JobDirAlreadyExistsError
			The folder indicated as job directory already exists.
		'''

		try:
			os.makedirs(self._job_dir)

		except FileExistsError:
			raise JobDirAlreadyExistsError(self._job_dir)

		self._command_lines_file = open(self._command_lines_filename, 'r')
		self._command_lines = (row.strip() for row in self._command_lines_file)

		self._watcher.start()

	def stop(self):
		'''
		Stop the server: close the command lines file and remove the job directory.
		'''

		self._watcher.stop()
		self._command_lines_file.close()
		shutil.rmtree(self._job_dir)

	@property
	def log(self):
		'''
		Get the current log.

		Returns
		-------
		log : list
			List of the logs sent by the clients.
		'''

		return self._log

	def _newClient(self, id):
		'''
		A new client has been created: add it to the clients list.

		Parameters
		----------
		id : str
			ID of the client.
		'''

		self._clients.append(id)
		self.events.trigger('client-new', id)

	def _clientGone(self, id):
		'''
		A client has been deleted: remote it from the clients list.

		Parameters
		----------
		id : str
			ID of the client.
		'''

		self._clients.remove(id)
		self.events.trigger('client-gone', id)

	def _processRequest(self, client_id, req):
		'''
		Process the request from a client.

		Parameters
		----------
		client_id : str
			ID of the client.

		req : dict
			Request sent by the client.
		'''

		if 'log' in req:
			self._logCmd(req['log'])

		if req['state'] == 'ready':
			self._sendNextCommandLine(client_id)

	def _sendNextCommandLine(self, client_id):
		'''
		Send the next command line to a client.
		If there is no command line anymore, send `None`.

		Parameters
		----------
		client_id : str
			ID of the client to send to command line to.
		'''

		try:
			cmd = next(self._command_lines)

		except StopIteration:
			cmd = None

		finally:
			jsonfiles.write({
				'command_line': cmd
			}, os.path.join(self._job_dir, f'{client_id}.json'))

			self.events.trigger('sent', cmd, client_id)

	def _logCmd(self, res):
		'''
		Log the result of a command line.

		Parameters
		----------
		res : dict
			Result to log.
		'''

		self._log.append(res)
		self.events.trigger('log', res)

	def run(self):
		'''
		Run loop, stopped when there is no client anymore.
		'''

		while not(self._log) or self._clients:
			try:
				time.sleep(0.1)

			except KeyboardInterrupt:
				break

class FileEventHandler(watchdog.events.RegexMatchingEventHandler):
	'''
	Handle the events from the files.

	Parameters
	----------
	job_dir : str
		Path to the job directory.

	new_client : function
		Function to call when a new client is created.

	client_gone : function
		Function to call when a client is deleted.

	request : function
		Function to call to handle the request from a client.
	'''

	def __init__(self, job_dir, new_client, client_gone, request):
		super().__init__(regexes = [os.path.join(job_dir, r'[0-9a-f]+\.json')])

		self._new_client = new_client
		self._client_gone = client_gone
		self._request = request

		self._prev_message = {}

	def on_created(self, evt):
		'''
		A file has been created in the job directory: a new client is here.
		Call the right callback. We then call `on_modified()` to be sure the first content of the file is processed.

		Parameters
		----------
		evt : watchdog.events.FileCreatedEvent
			Event object from Watchdog containing infos about the client file.
		'''

		client_id = self._filename2id(evt.src_path)
		self._prev_message[client_id] = None

		self._new_client(client_id)

		self.on_modified(evt)

	def on_deleted(self, evt):
		'''
		A file has been deleted: say goodbye to a client.

		Parameters
		----------
		evt : watchdog.events.FileDeletedEvent
			Event object from Watchdog containing infos about the client file.
		'''

		client_id = self._filename2id(evt.src_path)
		del self._prev_message[client_id]

		self._client_gone(client_id)

	def on_modified(self, evt):
		'''
		A file has been modified: maybe a message from a client.
		If it is the case, call the right callback.

		Parameters
		----------
		evt : watchdog.events.FileModifiedEvent
			Event object from Watchdog containing infos about the client file.
		'''

		try:
			content = jsonfiles.read(evt.src_path)

		except:
			pass

		else:
			client_id = self._filename2id(evt.src_path)

			if content == self._prev_message[client_id]:
				return

			self._prev_message[client_id] = content

			if 'state' in content:
				self._request(client_id, content)

	def _filename2id(self, filename):
		'''
		Convert a client filename into an ID.
		It is simply the base name of the file, without extension.

		Parameters
		----------
		filename : str
			Path to the client file.
		'''

		return os.path.splitext(os.path.basename(filename))[0]
