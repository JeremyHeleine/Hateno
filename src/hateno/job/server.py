#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import shutil
import time

import watchdog.events

from .errors import *
from .filewatcher import FileWatcher
from ..utils import jsonfiles

class JobServer():
	'''
	'''

	def __init__(self, command_lines_filename, job_dir):
		self._command_lines_filename = command_lines_filename
		self._job_dir = job_dir

		self._event_handler = FileEventHandler(self._job_dir, self._newClient, self._clientGone, self._processRequest)
		self._watcher = FileWatcher(self._event_handler, self._job_dir)

		self._clients = []

		self._log = []

	def __enter__(self):
		'''
		'''

		self.start()
		return self

	def __exit__(self, *args, **kwargs):
		'''
		'''

		self.stop()

	def start(self):
		'''
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
		'''

		self._watcher.stop()
		self._command_lines_file.close()
		shutil.rmtree(self._job_dir)

	@property
	def log(self):
		'''
		'''

		return self._log

	def _newClient(self, id):
		'''
		'''

		self._clients.append(id)

	def _sendNextCommandLine(self, client_id):
		'''
		'''

		try:
			cmd = next(self._command_lines)

		except StopIteration:
			cmd = None

		finally:
			jsonfiles.write({
				'command_line': cmd
			}, os.path.join(self._job_dir, f'{client_id}.json'))

	def _clientGone(self, id):
		'''
		'''

		self._clients.remove(id)

	def _processRequest(self, client_id, req):
		'''
		'''

		if 'log' in req:
			self._log.append(req['log'])

		if req['state'] == 'ready':
			self._sendNextCommandLine(client_id)

	def run(self):
		'''
		'''

		while not(self._log) or self._clients:
			try:
				time.sleep(0.1)

			except KeyboardInterrupt:
				break

class FileEventHandler(watchdog.events.RegexMatchingEventHandler):
	'''
	'''

	def __init__(self, job_dir, new_client, client_gone, request):
		super().__init__(regexes = [os.path.join(job_dir, r'[0-9a-f]+\.json')])

		self._new_client = new_client
		self._client_gone = client_gone
		self._request = request

		self._prev_message = {}

	def on_created(self, evt):
		'''
		'''

		client_id = self._filename2id(evt.src_path)
		self._prev_message[client_id] = None

		self._new_client(client_id)

	def on_deleted(self, evt):
		'''
		'''

		client_id = self._filename2id(evt.src_path)
		del self._prev_message[client_id]

		self._client_gone(client_id)

	def on_modified(self, evt):
		'''
		'''

		try:
			content = jsonfiles.read(evt.src_path)

		except json.decoder.JSONDecodeError:
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
		'''

		return os.path.splitext(os.path.basename(filename))[0]
