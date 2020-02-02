#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime

from manager.errors import *

def LOG(*args):
	with open('lines.txt', 'a') as f:
		f.write(' '.join(map(str, args)) + '\n')

class UI():
	'''
	Represent the user interface. Make easy the display of lines that can be updated, and the creation of progress bars.
	'''

	def __init__(self):
		self._text_lines = {}
		self._cursor_vertical_pos = 0

	@property
	def _last_line(self):
		'''
		Get the position of the last line.

		Returns
		-------
		pos : int
			The position of the last line.
		'''

		return len(self._text_lines)

	def moveCursorTo(self, pos):
		'''
		Move the cursor to a new vertical position.

		Parameters
		----------
		pos : int
			The position to go to.
		'''

		cursor_offset = pos - self._cursor_vertical_pos

		if cursor_offset != 0:
			cursor_direction = 'A' if cursor_offset < 0 else 'B'
			print(f'\u001b[{abs(cursor_offset)}{cursor_direction}', end = '\r')

			self._cursor_vertical_pos = pos

	def addTextLine(self, text):
		'''
		Add a new text line to display.

		Parameters
		----------
		text : str
			The text to display

		Returns
		-------
		id : str
			The ID to use to refer to this new line.
		'''

		self.moveCursorTo(self._last_line)
		print(text)

		line_id = hex(int(datetime.datetime.now().timestamp() * 1E6))[2:]
		self._text_lines[line_id] = {
			'position': self._cursor_vertical_pos,
			'text': text
		}

		self._cursor_vertical_pos += 1

		return line_id

	def replaceTextLine(self, id, new_text):
		'''
		Replace a text line.

		Parameters
		----------
		id : str
			The ID of the line to display.

		new_text : str
			The new text to display.

		Raises
		------
		UITextLineNotFoundError
			The ID does not refer to a known text line.
		'''

		try:
			text_line = self._text_lines[id]

		except KeyError:
			raise UITextLineNotFoundError(id)

		else:
			self.moveCursorTo(text_line['position'])

			print(' ' * len(text_line['text']), end = '\r')
			print(new_text, end = '\r')
			text_line['text'] = new_text

			self.moveCursorTo(self._last_line)

	def removeTextLine(self, line_id):
		'''
		Remove a text line and move all the lines below.

		Parameters
		----------
		line_id : str
			The ID of the line to remove.

		Raises
		------
		UITextLineNotFoundError
			The ID does not refer to a known text line.
		'''

		try:
			text_line = self._text_lines[line_id]

		except KeyError:
			raise UITextLineNotFoundError(line_id)

		else:
			self.moveCursorTo(text_line['position'])
			print(' ' * len(text_line['text']), end = '\r')

			for line in sorted(self._text_lines.values(), key = lambda line: line['position']):
				if line['position'] > text_line['position']:
					self.moveCursorTo(line['position'])
					print(' ' * len(line['text']), end = '\r')

					self.moveCursorTo(line['position'] - 1)
					print(line['text'], end = '\r')

					line['position'] -= 1

			del self._text_lines[line_id]
			self.moveCursorTo(self._last_line)
