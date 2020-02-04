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
		self._cursor_vertical_pos = 0

		self._text_lines = {}

		self._progress_bars = {}
		self._progress_bars_length = 40
		self._progress_bars_empty_char = '-'
		self._progress_bars_full_char = '#'

	@property
	def _last_line(self):
		'''
		Get the position of the last line.

		Returns
		-------
		pos : int
			The position of the last line.
		'''

		return len(self._text_lines) + len(self._progress_bars)

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

	def moveCursorRight(self, dx):
		'''
		Move the cursor to the right.

		Parameters
		----------
		dx : int
			The movement to execute.
		'''

		if dx > 0:
			print(f'\u001b[{dx}C', end = '')

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

	def addProgressBar(self, N):
		'''
		Add a new progress bar.

		Parameters
		----------
		N : int
			The final number to reach to display the famous 100%.

		Returns
		-------
		id : str
			The ID to use to refer to this progress bar.
		'''

		self.moveCursorTo(self._last_line)

		length_N = len(str(N))
		leading_spaces = ' ' * (length_N - 1)
		print(f'{leading_spaces}0/{N} ' + self._progress_bars_empty_char * self._progress_bars_length + '   0.0%')

		bar_id = hex(int(datetime.datetime.now().timestamp() * 1E6))[2:]
		self._progress_bars[bar_id] = {
			'position': self._cursor_vertical_pos,
			'n': 0,
			'N': N,
			'length_N': length_N
		}

		self._cursor_vertical_pos += 1

		return bar_id

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

	def updateProgressBar(self, id, n):
		'''
		Update a progress bar.

		Parameters
		----------
		id : str
			The ID of the bar to update.

		n : int
			The new value of the counter.

		Raises
		------
		UIProgressBarNotFoundError
			The ID does not refer to a known progress bar.
		'''

		try:
			progress_bar = self._progress_bars[id]

		except KeyError:
			raise UIProgressBarNotFoundError(id)

		else:
			self.moveCursorTo(progress_bar['position'])

			percentage = n / progress_bar['N']

			print(' ' * (progress_bar['length_N'] - len(str(n))) + str(n), end = '\r')

			dx = progress_bar['length_N'] * 2 + 2
			self.moveCursorRight(dx)
			print(self._progress_bars_full_char * round(percentage * self._progress_bars_length), end = '\r')

			self.moveCursorRight(dx + self._progress_bars_length + 1)
			print(round(percentage * 100, 1), end = '\r')

			progress_bar['n'] = n

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
