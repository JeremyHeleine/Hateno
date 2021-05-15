#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from .item import UIDisplayedItem

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
