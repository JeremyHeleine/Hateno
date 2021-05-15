#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import abc
import functools

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
