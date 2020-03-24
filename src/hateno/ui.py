#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime

from .errors import *

class UI():
	'''
	Represent the user interface. Make easy the display of lines that can be updated, and the creation of progress bars.
	'''

	def __init__(self, *, progress_bars_length = 40, progress_bars_empty_char = '░', progress_bars_full_char = '█'):
		self._cursor_vertical_pos = 0

		self._text_lines = {}

		self._progress_bars = {}
		self._progress_bars_length = progress_bars_length
		self._progress_bars_empty_char = progress_bars_empty_char
		self._progress_bars_full_char = progress_bars_full_char

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
			'text': text,
			'length': len(text)
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

		pattern = f'{{n:>{len(str(N))}d}}/{{N:d}} {{bar:{self._progress_bars_empty_char}<{self._progress_bars_length}}} {{p:>6.1%}}'
		first_bar = pattern.format(n = 0, N = N, bar = '', p = 0)
		print(first_bar)

		bar_id = hex(int(datetime.datetime.now().timestamp() * 1E6))[2:]
		self._progress_bars[bar_id] = {
			'position': self._cursor_vertical_pos,
			'n': 0,
			'N': N,
			'pattern': pattern,
			'length': len(first_bar)
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

			print(' ' * text_line['length'], end = '\r')
			print(new_text, end = '\r')
			text_line['text'] = new_text
			text_line['length'] = len(new_text)

			self.moveCursorTo(self._last_line)

	def updateProgressBar(self, id, n = None):
		'''
		Update a progress bar.

		Parameters
		----------
		id : str
			The ID of the bar to update.

		n : int
			The new value of the counter. If `None`, increment the counter by one.

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

			if n is None:
				n = progress_bar['n'] + 1

			percentage = n / progress_bar['N']
			length_N = len(str(progress_bar['N']))

			print(f'{{n:>{length_N}d}}'.format(n = n), end = '\r')

			dx = length_N * 2 + 2
			self.moveCursorRight(dx)
			print(self._progress_bars_full_char * round(percentage * self._progress_bars_length), end = '\r')

			self.moveCursorRight(dx + self._progress_bars_length + 1)
			print('{p:>6.1%}'.format(p = percentage), end = '\r')

			progress_bar['n'] = n

			self.moveCursorTo(self._last_line)

	def moveUp(self, line):
		'''
		Move a line to the line above, assuming the above line is empty.

		Parameters
		----------
		line : dict
			Line to move.

		Raises
		------
		UINonMovableLine
			The line can't be moved.
		'''

		if line['position'] <= 0:
			raise UINonMovableLine(line['position'])

		self.moveCursorTo(line['position'])
		print(' ' * line['length'], end = '\r')

		text = ''
		try:
			text = line['text']

		except KeyError:
			percentage = line['n'] / line['N']
			text = line['pattern'].format(n = line['n'], N = line['N'], bar = self._progress_bars_full_char * round(percentage * self._progress_bars_length), p = percentage)

		finally:
			self.moveCursorTo(line['position'] - 1)
			print(text, end = '\r')
			line['position'] -= 1

	def moveUpFrom(self, pos):
		'''
		Move all lines starting at a given position.

		Parameters
		----------
		pos : int
			Position to start from.

		Raises
		------
		UINonMovableLine
			The line can't be moved.
		'''

		if pos <= 0:
			raise UINonMovableLine(pos)

		lines_to_move = [line for line in [*self._text_lines.values(), *self._progress_bars.values()] if line['position'] >= pos]
		lines_to_move.sort(key = lambda line: line['position'])

		for line in lines_to_move:
			self.moveUp(line)

	def _removeLine(self, lines, id):
		'''
		Remove a line and move up all the lines below.

		Parameters
		----------
		lines : dict
			Dict where the lines are stored.

		id : str
			ID of the line to remove.

		Raises
		------
		UILineNotFoundError
			The ID does not refer to a known text line.
		'''

		try:
			line = lines[id]

		except KeyError:
			raise UILineNotFoundError(id)

		else:
			self.moveCursorTo(line['position'])
			print(' ' * line['length'], end = '\r')

			self.moveUpFrom(line['position'] + 1)

			del lines[id]
			self.moveCursorTo(self._last_line)

	def removeTextLine(self, line_id):
		'''
		Remove a text line and move all the lines below.

		Parameters
		----------
		line_id : str
			The ID of the line to remove.
		'''

		self._removeLine(self._text_lines, line_id)

	def removeProgressBar(self, line_id):
		'''
		Remove a progress bar and move all the lines below.

		Parameters
		----------
		line_id : str
			The ID of the line to remove.
		'''

		self._removeLine(self._progress_bars, line_id)
