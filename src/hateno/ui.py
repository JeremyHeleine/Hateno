#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import abc
import functools

from math import floor, log10

from .errors import *

class UI():
	'''
	Represent the user interface. Make easy the display of lines that can be updated, and the creation of progress bars.

	Parameters
	----------
	progress_bars_length : int
		Length of the progress bars, in characters.

	progress_bars_empty_char : str
		Character to use for the "empty" part of the progress bars.

	progress_bars_full_char : str
		Character to use to fill a progress bar.

	progress_bars_percentage_precision : int
		Precision to use for the display of the percentage in the progress bars.
	'''

	def __init__(self, *, progress_bars_length = 40, progress_bars_empty_char = '░', progress_bars_full_char = '█', progress_bars_percentage_precision = 'auto'):
		self._cursor_vertical_pos = 0
		self._max_line = 0

		self._items = []

		self._progress_bars_length = progress_bars_length
		self._progress_bars_empty_char = progress_bars_empty_char
		self._progress_bars_full_char = progress_bars_full_char
		self._progress_bars_percentage_precision = progress_bars_percentage_precision

	@property
	def _last_line(self):
		'''
		Get the position of the last line.

		Returns
		-------
		pos : int
			The position of the last line.
		'''

		items = sorted(self._items, key = lambda item: item.position)
		if items:
			return items[-1].position + items[-1].height

		return 0

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

	def moveToLastLine(self):
		'''
		Move the cursor to the last line.
		Before, check if the last line already exists.
		'''

		last_line = self._last_line

		if last_line > self._max_line:
			self.moveCursorTo(last_line - 1)
			print('')
			self._cursor_vertical_pos += 1
			self._max_line = last_line

		self.moveCursorTo(last_line)

	def _addItem(self, item_type, args, *, position = -1):
		'''
		Add an item to display.

		Parameters
		----------
		item_type : type
			Type of the item to add (child of UIDisplayedItem).

		args : dict
			Args to pass to the constructor of the item to add.

		position : int
			Position of the item. Default to `-1`: the item is added at the end.

		Returns
		-------
		item : UIDisplayedItem
			The newly added item.
		'''

		if position >= 0:
			self.moveDownFrom(position)
			self.moveCursorTo(position)

		else:
			self.moveToLastLine()

		item = item_type(self, **args)
		self._items.append(item)
		item.render()

		return item

	def addTextLine(self, text, *, position = -1):
		'''
		Add a new text line to display.

		Parameters
		----------
		text : str
			The text to display

		position : int
			Position of the text line. Default to `-1`: the text line is added at the end.

		Returns
		-------
		text_line : UITextLine
			Object representing the added text line.
		'''

		return self._addItem(UITextLine, {
			'text': text
		}, position = position)

	def addProgressBar(self, total, *, bar_length = None, empty_char = None, full_char = None, percentage_precision = None, position = -1):
		'''
		Add a new progress bar.

		Parameters
		----------
		total : int
			The final number to reach to display the famous 100%.

		bar_length : int
			Length of the progress bar.

		empty_char : str
			Character to use for the empty part of the bar.

		full_char : str
			Character to use to fill the bar.

		percentage_precision : int
			Precision to use for the display of the percentage.

		position : int
			Position of the progress bar. Default to `-1`: the progress bar is added at the end.

		Returns
		-------
		progress_bar : UIProgressBar
			Object representing the added progress bar.
		'''

		return self._addItem(UIProgressBar, {
			'total': total,
			'bar_length': bar_length or self._progress_bars_length,
			'empty_char': empty_char or self._progress_bars_empty_char,
			'full_char': full_char or self._progress_bars_full_char,
			'percentage_precision': percentage_precision or self._progress_bars_percentage_precision
		}, position = position)

	def moveUp(self, item):
		'''
		Move an item to the line above, assuming the above line is empty.

		Parameters
		----------
		item : UIDisplayedItem
			Item to move.

		Raises
		------
		UINonMovableLine
			The line can't be moved.
		'''

		if item.position <= 0:
			raise UINonMovableLine(item.position)

		item.clear()
		self.moveCursorTo(item.position - 1)
		item.position -= 1
		item.render()

	def moveUpFrom(self, pos):
		'''
		Move up all lines starting at a given position.

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

		items_to_move = [item for item in self._items if item.position >= pos]
		items_to_move.sort(key = lambda item: item.position)

		for item in items_to_move:
			self.moveUp(item)

	def moveDown(self, item):
		'''
		Move an item to the line below, assuming it is empty.

		Parameters
		----------
		item : UIDisplayedItem
			Item to move.

		Raises
		------
		UINonMovableLine
			The line can't be moved.
		'''

		item.clear()
		self.moveCursorTo(item.position + 1)
		item.position += 1
		item.render()

	def moveDownFrom(self, pos):
		'''
		Move down all lines starting at a given position.

		Parameters
		----------
		pos : int
			Position to start from.

		Raises
		------
		UINonMovableLine
			The line can't be moved.
		'''

		items_to_move = [item for item in self._items if item.position >= pos]
		items_to_move.sort(key = lambda item: item.position, reverse = True)

		for item in items_to_move:
			self.moveDown(item)

	def removeItem(self, item):
		'''
		Remove a displayed item, and then move up all the lines below.

		Parameters
		----------
		item : UIDisplayedItem
			The item to remove.
		'''

		item.clear()
		self.moveUpFrom(item.position + 1)
		self._items.remove(item)
		self.moveToLastLine()

class UIDisplayedItem(abc.ABC):
	'''
	Represent an item displayed in the UI (abstract class).

	Parameters
	----------
	ui : UI
		The UI object this item belongs to.
	'''

	def __init__(self, ui):
		self.ui = ui
		self.position = self.ui._cursor_vertical_pos

	@abc.abstractproperty
	def height(self):
		'''
		The number of lines used by the item.

		Returns
		-------
		height : int
			The number of lines.
		'''

		pass

	@abc.abstractproperty
	def width(self):
		'''
		The width, in characters, of the item.

		Returns
		-------
		width : int
			The width of the item.
		'''

		pass

	@classmethod
	def renderer(cls, func):
		'''
		Decorator for children's render() method.
		'''

		@functools.wraps(func)
		def wrapper(self, *args, **kwargs):
			self.ui.moveCursorTo(self.position)

			func(self, *args, **kwargs)

			self.ui.moveToLastLine()

		return wrapper

	@abc.abstractmethod
	def render(self):
		'''
		Render the item.
		'''

		pass

	def clear(self):
		'''
		Display enough spaces to clear the object.
		'''

		self.ui.moveCursorTo(self.position)
		print(' ' * self.width, end = '\r')
		self.ui.moveToLastLine()

class UITextLine(UIDisplayedItem):
	'''
	Represent a text line displayed in the UI.

	Parameters
	----------
	ui : UI
		The UI object this text line belongs to.

	text : str
		The text to display.
	'''

	def __init__(self, ui, text):
		super().__init__(ui)

		self._text = text

	@property
	def height(self):
		'''
		The number of lines used by the text line.
		Currently, always one. Multilines are not supported yet.

		Returns
		-------
		height : int
			The number of lines used by the text.
		'''

		return 1

	@property
	def width(self):
		'''
		The width of the text line, i.e. the length of the text.

		Returns
		-------
		width : int
			The length of the text.
		'''

		return len(self.text)

	@property
	def text(self):
		'''
		Getter for the displayed text.

		Returns
		-------
		text : str
			Displayed text.
		'''

		return self._text

	@UIDisplayedItem.renderer
	def render(self):
		'''
		Print the text.
		'''

		print(self._text, end = '\r')

	@text.setter
	def text(self, new_text):
		'''
		Change the displayed text.

		Parameters
		----------
		new_text : str
			New text to display.
		'''

		self.clear()
		self._text = new_text
		self.render()

class UIProgressBar(UIDisplayedItem):
	'''
	Represent a progress bar displayed in the UI.

	Parameters
	----------
	ui : UI
		The UI object this text line belongs to.

	total : int
		The final number to reach.

	bar_length : int
		Length of the progress bar.

	empty_char : str
		Character to use for the empty part of the bar.

	full_char : str
		Character to use to fill the bar.

	percentage_precision : int|str
		Precision to use for the display of the percentage.
		Special value `'auto'` to guess the needed precision from the total.
	'''

	def __init__(self, ui, total, *, bar_length = 40, empty_char = '░', full_char = '█', percentage_precision = 'auto'):
		super().__init__(ui)

		self._total = total
		self._counter = 0

		self._bar_length = bar_length
		self._empty_char = empty_char
		self._full_char = full_char

		if percentage_precision == 'auto':
			self._percentage_precision = abs(floor(log10(100 / self._total))) if self._total > 100 else 0

		else:
			self._percentage_precision = percentage_precision

		self._pattern = ' '.join([
			f'{{counter:>{len(str(self._total))}d}}/{self._total}',
			f'{{bar:{self._empty_char}<{self._bar_length}}}',
			f'{{percentage:>{5 + self._percentage_precision}.{self._percentage_precision}%}}'
		])

	@property
	def height(self):
		'''
		The number of lines used by the progress bar.

		Returns
		-------
		height : int
			The number of lines used by the progress bar.
		'''

		return 1

	@property
	def width(self):
		'''
		The width of the progress bar.

		Returns
		-------
		width : int
			The complete width (counter + bar + percentage lengths).
		'''

		return len(self._pattern.format(counter = 0, bar = '', percentage = 0))

	@property
	def counter(self):
		'''
		The current value of the counter.

		Returns
		-------
		counter : int
			Counter value.
		'''

		return self._counter

	@UIDisplayedItem.renderer
	def render(self):
		'''
		Print the progress bar.
		'''

		percentage = self._counter / self._total
		n_full_chars = round(percentage * self._bar_length)

		print(self._pattern.format(counter = self._counter, bar = self._full_char * n_full_chars, percentage = percentage), end = '\r')

	@counter.setter
	def counter(self, n):
		'''
		Set the value of the counter.
		'''

		self.clear()
		self._counter = n
		self.render()

	def update(self, delta = 1):
		'''
		Set the value of the counter by adding an increment.

		Parameters
		----------
		delta : int
			Increment to add.
		'''

		self.counter += delta
