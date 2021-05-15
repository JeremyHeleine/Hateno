#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import selectors
import socket
import subprocess

from .message import Message
from ..utils.events import Events

class JobClient():
	'''
	Represent a client part of the job, which executes the command lines.

	Parameters
	----------
	host : str
		Host of the server.

	port : int
		Port of the server.
	'''

	def __init__(self, host, port):
		self._host = host
		self._port = port

		self.events = Events(['exec-start', 'exec-end'])

		self._open()

	def __enter__(self):
		'''
		Context manager to call `close()` at the end.
		'''

		return self

	def __exit__(self, type, value, traceback):
		'''
		Ensure `close()` is called when exiting the context manager.
		'''

		self.close()

	def _open(self):
		'''
		Open the connection with the server.
		'''

		self._selector = selectors.DefaultSelector()

		self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self._sock.setblocking(False)
		self._sock.connect_ex((self._host, self._port))

		message = Message(self._selector, self._sock)
		message.events.addListener('message-received', self._processResponse)

		self._selector.register(self._sock, selectors.EVENT_WRITE, data = message)

		message.setMessage({'query': 'next'})

	def close(self):
		'''
		Close the connection.
		'''

		self._selector.close()

	def _processResponse(self, message, response):
		'''
		Process the response of a request to the server.

		Parameters
		----------
		message : Message
			Message instance of the connection.

		response : dict
			Response of the server.
		'''

		message.setMode('idle')

		if response['command_line'] is not None:
			cmd = {
				'exec': response['command_line']
			}

			self.events.trigger('exec-start', cmd)

			p = subprocess.run(response['command_line'], shell = True, capture_output = True, encoding = 'utf-8')
			cmd['stdout'] = p.stdout
			cmd['stderr'] = p.stderr
			cmd['success'] = p.returncode == 0

			self.events.trigger('exec-end', cmd)

			message.setMessage({'query': 'log', 'content': cmd})

		else:
			message.close()

	def run(self):
		'''
		Run the event loop.
		'''

		while True:
			try:
				for key, mask in self._selector.select(timeout = 1):
					message = key.data

					try:
						message.processEvents(mask)

					except Exception:
						message.close()

				if not(self._selector.get_map()):
					break

			except KeyboardInterrupt:
				break
