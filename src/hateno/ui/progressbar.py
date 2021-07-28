#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from math import floor, log10

from .item import UIDisplayedItem

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
