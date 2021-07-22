#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import time

import watchdog.events

from .filewatcher import FileWatcher
from ..utils import Events, jsonfiles, string

class JobClient():
	'''
	Client part of a job, executing the command lines sent by the server.

	Parameters
	----------
	job_dir : str
		Path to the job directory where the messaging files are stored.
	'''

	def __init__(self, job_dir):
		self._job_dir = job_dir

		self.events = Events([
			'received', 'sent'
		])

	def __enter__(self):
		'''
		Context manager to automatically call `stop()`.
		'''

		self.start()
		return self

	def __exit__(self, *args, **kwargs):
		'''
		Call `stop()` when exiting a context manager.
		'''

		self.stop()

	def start(self):
		'''
		Create the messaging file for this client.
		'''

		self._waitForServerReady()

		self._client_id = string.uniqueID()
		self._client_filename = os.path.join(self._job_dir, f'{self._client_id}.json')

		self._event_handler = FileEventHandler(self._processResponse)

		with open(self._client_filename, 'w') as f:
			f.write('')

	def stop(self):
		'''
		Delete the messaging file of the client.
		'''

		try:
			os.unlink(self._client_filename)

		except FileNotFoundError:
			pass

	def _waitForServerReady(self):
		'''
		Wait until the server is ready (i.e. the job directory has been created).
		'''

		while True:
			try:
				os.stat(self._job_dir)

			except FileNotFoundError:
				time.sleep(0.1)

			else:
				break

	def _processResponse(self, response):
		'''
		Handle the response from the server.
		If the server sent a command line, execute it and send the log.
		If the "command line" is `None`, stop everything.

		Parameters
		----------
		response : dict
			Message sent by the server.
		'''

		self._wait = False

		self.events.trigger('received', response['command_line'])

		if response['command_line'] is not None:
			p = subprocess.run(response['command_line'], shell = True, capture_output = True, encoding = 'utf-8')

			log = {
				'log': {
					'exec': response['command_line'],
					'stdout': p.stdout,
					'stderr': p.stderr,
					'success': p.returncode == 0
				},
				'state': 'ready'
			}

			self._sendAndWait(log)

	def _sendAndWait(self, req):
		'''
		Send a message to the server and wait for the response.

		Parameters
		----------
		req : dict
			Request to send.
		'''

		try:
			with FileWatcher(self._event_handler, self._client_filename):
				jsonfiles.write(req, self._client_filename)
				self.events.trigger('sent', req)

				self._wait = True
				while self._wait:
					time.sleep(0.1)

		except FileNotFoundError:
			pass

	def run(self):
		'''
		Run "loop". Tell the server the client is ready and wait for the first command line.
		'''

		self._sendAndWait({'state': 'ready'})

class FileEventHandler(watchdog.events.FileSystemEventHandler):
	'''
	Handle the events from the files modifications.

	Parameters
	----------
	response : function
		Function to call to handle a response from the server.
	'''

	def __init__(self, response):
		self._response = response

		self._prev_message = None

	def on_modified(self, evt):
		'''
		The client file has been modified.
		Read the content of the file and test whether it is a message from the server.

		Parameters
		----------
		evt : watchdog.events.FileModifiedEvent
			Object given by Watchdog containing infos about the modified file.
		'''

		try:
			content = jsonfiles.read(evt.src_path)

		except:
			pass

		else:
			if content == self._prev_message:
				return

			self._prev_message = content

			if 'command_line' in content:
				self._response(content)
