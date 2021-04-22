#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import selectors
import struct
import io
import json

from .events import Events

class Message():
	'''
	Base class to exchange messages between the server and a client.

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
			self.events.trigger('message-received', self._received_msg)
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
			self.events.trigger('message-sent', self._msg_to_queue)

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
