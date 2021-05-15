#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import selectors
import socket

from .message import Message
from ..utils.events import Events

class JobServer():
	'''
	Represent the server part of a job, which distributes the command lines over the clients.

	Parameters
	----------
	command_lines : list
		Command lines to execute.
	'''

	def __init__(self, command_lines):
		self._host = '127.0.0.1'
		self._port = 21621

		self._command_lines = command_lines
		self._current_command_line = -1

		self._clients = []

		self._log = []
		self.events = Events(['log'])

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
		Open the server by creating the selector and socket.
		'''

		self._selector = selectors.DefaultSelector()

		self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self._bindSocket()
		self._sock.listen()
		self._sock.setblocking(False)

		self._selector.register(self._sock, selectors.EVENT_READ, data = None)

	def _bindSocket(self):
		'''
		Bind the socket and change the port if necessary.
		'''

		try:
			self._sock.bind((self._host, self._port))

		except OSError:
			self._port += 1
			self._bindSocket()

	def close(self):
		'''
		Close the server.
		'''

		self._selector.close()

	@property
	def port(self):
		'''
		Get the port in use.

		Returns
		-------
		port : int
			The current port.
		'''

		return self._port

	@property
	def log(self):
		'''
		Get the log.

		Returns
		-------
		log : list
			The log, as a list of executed command lines.
		'''

		return self._log

	def _acceptConnection(self, sock):
		'''
		Accept the connection of a socket to the server.

		Parameters
		----------
		sock : socket.socket
			The socket to accept.
		'''

		conn, addr = sock.accept()
		conn.setblocking(False)

		message = Message(self._selector, conn)
		message.events.addListener('message-received', self._processRequest)

		self._clients.append(message)

		self._selector.register(conn, selectors.EVENT_READ, data = message)

	def _processRequest(self, message, req):
		'''
		Process a request sent by a client.

		Parameters
		----------
		message : Message
			Message instance of the client.

		req : dict
			The received request.
		'''

		if req['query'] == 'next':
			self._sendNextCommandLine(message)

		elif req['query'] == 'log':
			self._logCommandLine(req['content'])
			self._sendNextCommandLine(message)

	def _sendNextCommandLine(self, message):
		'''
		Send the next command line to execute.

		Parameters
		----------
		message : Message
			Message instance of the client.
		'''

		self._current_command_line += 1

		try:
			cmd = self._command_lines[self._current_command_line]

		except IndexError:
			cmd = None

		finally:
			message.setMessage({'command_line': cmd})

	def _logCommandLine(self, cmd):
		'''
		Log the result of a command line in the list.
		If there is a log file, update it.

		Parameters
		----------
		cmd : dict
			Result of the command line to log.
		'''

		self._log.append(cmd)
		self.events.trigger('log', self._log)

	def run(self):
		'''
		Run the event loop.
		'''

		while True:
			try:
				for key, mask in self._selector.select(timeout = None):
					if key.data is None:
						self._acceptConnection(key.fileobj)

					else:
						message = key.data
						try:
							message.processEvents(mask)

						except Exception:
							message.close()

				if self._allClosed():
					break

			except KeyboardInterrupt:
				break

	def _allClosed(self):
		'''
		Check whether all the clients closed their connections.

		Returns
		-------
		all_closed : bool
			`True` if all clients are closed, `False` if at least one client is still connected.
		'''

		if not(self._clients):
			return False

		closed_clients = [client for client in self._clients if client.closed]
		return self._clients == closed_clients
