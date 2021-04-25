#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
import selectors
import struct
import io
import subprocess
import json

from . import jsonfiles
from .events import Events

class JobServer():
	'''
	Represent the server part of a job, which distributes the command lines over the clients.

	Parameters
	----------
	cmd_filename : str
		Path to the file where the command lines are stored.
	'''

	def __init__(self, cmd_filename):
		self._host = '127.0.0.1'
		self._port = 21621

		self._command_lines = jsonfiles.read(cmd_filename)
		self._current_command_line = -1

		self._clients = []

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
		'''

		return self._port

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
			message.setMessage({'command_line': self._next_command_line()})

	def _next_command_line(self):
		'''
		Get the next command line to execute.
		'''

		self._current_command_line += 1

		try:
			return self._command_lines[self._current_command_line]

		except IndexError:
			return None

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
			self.events.trigger('exec-start', response['command_line'])
			output = subprocess.check_output(response['command_line'], shell = True)
			self.events.trigger('exec-end', output.decode())

			message.setMessage({'query': 'next'})

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

class Message():
	'''
	Class to exchange messages between the server and a client.

	Parameters
	----------
	selector : selectors.DefaultSelector
		Selector used to manage the sockets events.

	sock : socket.socket
		The socket used to exchange the messages.
	'''

	def __init__(self, selector, sock):
		self._selector = selector
		self._sock = sock

		self._recv_buffer = b''
		self._send_buffer = b''

		self._received_msg_len = None
		self._received_msg = None

		self._msg_to_queue = None
		self._msg_queued = False
		self._msg_sent = False

		self._closed = False

		self.events = Events(['message-received', 'message-sent'])

	def close(self):
		'''
		Properly close and unregister the socket.
		'''

		try:
			self._selector.unregister(self._sock)

		except Exception:
			pass

		try:
			self._sock.close()

		except OSError:
			pass

		finally:
			self._sock = None
			self._closed = True

	@property
	def closed(self):
		'''
		Know when a connection has been closed.

		Returns
		-------
		closed : bool
			`True` if `close()` has been called, `False` otherwise.
		'''

		return self._closed

	def setMode(self, mode):
		'''
		Set the mask of the events to wait.

		Parameters
		----------
		mode : str
			Mode to set:
				* `r` for read,
				* `w` for write,
				* `rw` for read and write,
				* `idle` for none.

		Raises
		------
		ValueError
			The provided mode is unknown.
		'''

		if mode == 'r':
			mask = selectors.EVENT_READ

		elif mode == 'w':
			mask = selectors.EVENT_WRITE

		elif mode == 'rw':
			mask = selectors.EVENT_READ | selectors.EVENT_WRITE

		elif mode == 'idle':
			mask = 0

		else:
			raise ValueError('Invalid mode')

		self._selector.modify(self._sock, mask, data = self)

	def processEvents(self, mask):
		'''
		Either read or write a message, depending on the captured event.

		Parameters
		----------
		mask : int
			The captured event.
		'''

		if mask & selectors.EVENT_READ:
			self._read()

		if mask & selectors.EVENT_WRITE:
			self._write()

	def _read(self):
		'''
		Read a message.
		First read the length of the message, then read the full message.
		'''

		self._receive()

		if self._received_msg_len is None:
			self._readContentLength()

		if self._received_msg_len is not None and self._received_msg is None:
			self._readContent()

		if self._received_msg is not None:
			self.events.trigger('message-received', self, self._received_msg)
			self._received_msg = None
			self._received_msg_len = None

	def _receive(self):
		'''
		Concatenate the received bytes in the buffer.
		'''

		try:
			data = self._sock.recv(4096)

		except BlockingIOError:
			pass

		else:
			if data:
				self._recv_buffer += data

			else:
				raise RuntimeError('Peer closed.')

	def _readContentLength(self):
		'''
		Read the content length from the received bytes.
		'''

		header_len = 2

		if len(self._recv_buffer) >= header_len:
			self._received_msg_len = struct.unpack('>H', self._recv_buffer[:header_len])[0]
			self._recv_buffer = self._recv_buffer[header_len:]

	def _readContent(self):
		'''
		Read the content of the message from the received bytes.
		'''

		if len(self._recv_buffer) >= self._received_msg_len:
			content_bytes = self._recv_buffer[:self._received_msg_len]

			with io.TextIOWrapper(io.BytesIO(content_bytes), encoding = 'utf-8', newline = '') as text_io:
				self._received_msg = json.load(text_io)

			self._recv_buffer = self._recv_buffer[self._received_msg_len:]

	def _write(self):
		'''
		Write a message.
		'''

		if self._msg_to_queue is not None and not(self._msg_queued):
			self._queueMessage()

		self._send()

		if self._msg_sent:
			self.setMode('r')
			self.events.trigger('message-sent', self, self._msg_to_queue)

	def _queueMessage(self):
		'''
		Put the current message to send in the queue.
		'''

		content = json.dumps(self._msg_to_queue, ensure_ascii = False).encode('utf-8')
		message_header = struct.pack('>H', len(content))
		message = message_header + content

		self._send_buffer += message
		self._msg_queued = True

	def _send(self):
		'''
		Send the current buffer.
		'''

		if self._send_buffer:
			try:
				sent = self._sock.send(self._send_buffer)

			except BlockingIOError:
				pass

			else:
				self._send_buffer = self._send_buffer[sent:]

				if not(self._send_buffer):
					self._msg_sent = True

	def setMessage(self, msg):
		'''
		Set the message to queue.

		Parameters
		----------
		msg : dict
			Message to send.
		'''

		self._msg_to_queue = msg
		self._msg_queued = False
		self._msg_sent = False

		self.setMode('w')
