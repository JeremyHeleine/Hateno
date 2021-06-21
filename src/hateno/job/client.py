#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import subprocess
import time

import watchdog.events

from .filewatcher import FileWatcher
from ..utils import jsonfiles, string

class JobClient():
	'''
	'''

	def __init__(self, job_dir):
		self._job_dir = job_dir

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

		self._client_id = string.uniqueID()
		self._client_filename = os.path.join(self._job_dir, f'{self._client_id}.json')

		self._event_handler = FileEventHandler(self._processResponse)

		with open(self._client_filename, 'w') as f:
			f.write('')

	def stop(self):
		'''
		'''

		try:
			os.unlink(self._client_filename)

		except FileNotFoundError:
			pass

	def _processResponse(self, response):
		'''
		'''

		self._wait = False

		if response['command_line'] is not None:
			p = subprocess.run(response['command_line'], shell = True, capture_output = True, encoding = 'utf-8')

			self._sendAndWait({
				'log': {
					'exec': response['command_line'],
					'stdout': p.stdout,
					'stderr': p.stderr,
					'success': p.returncode == 0
				},
				'state': 'ready'
			})

	def _sendAndWait(self, req):
		'''
		'''

		try:
			with FileWatcher(self._event_handler, self._client_filename):
				jsonfiles.write(req, self._client_filename)

				self._wait = True
				while self._wait:
					time.sleep(0.1)

		except FileNotFoundError:
			pass

	def run(self):
		'''
		'''

		self._sendAndWait({'state': 'ready'})

class FileEventHandler(watchdog.events.FileSystemEventHandler):
	'''
	'''

	def __init__(self, response):
		self._response = response

		self._prev_message = None

	def on_modified(self, evt):
		'''
		'''

		try:
			content = jsonfiles.read(evt.src_path)

		except json.decoder.JSONDecodeError:
			pass

		else:
			if content == self._prev_message:
				return

			self._prev_message = content

			if 'command_line' in content:
				self._response(content)
