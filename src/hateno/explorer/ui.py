#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from ..maker import MakerUI
from ..utils import string

class MapperUI(MakerUI):
	'''
	UI to show the different steps of the Mapper.

	Parameters
	----------
	mapper : Mapper
		Instance of the Mapper from which the events are triggered.
	'''

	def __init__(self, mapper):
		super().__init__(mapper.maker)

		self._mapper = mapper

		self._mapper_state_line = None

		self._nodes_lines = {}
		self._nodes_bars = {}

		self._explorer_searches = None
		self._explorer_searches_n_tests = None
		self._explorer_search = None

		self._mapper.events.addListener('read-start', self._readStart)
		self._mapper.events.addListener('read-end', self._readEnd)
		self._mapper.events.addListener('map-start', self._mapStart)
		self._mapper.events.addListener('map-end', self._mapEnd)
		self._mapper.events.addListener('node-start', self._nodeStart)
		self._mapper.events.addListener('node-progress', self._nodeProgress)
		self._mapper.events.addListener('node-end', self._nodeEnd)
		self._mapper.events.addListener('generate-start', self._generateStart)
		self._mapper.events.addListener('generate-end', self._generateEnd)
		self._mapper.events.addListener('evaluation-start', self._evaluationStart)
		self._mapper.events.addListener('evaluation-end', self._evaluationEnd)
		self._mapper.events.addListener('explorer-find-end', self._explorerFindStart)
		self._mapper.events.addListener('explorer-find-end', self._explorerFindEnd)
		self._mapper.events.addListener('explorer-search-start', self._explorerSearchStart)
		self._mapper.events.addListener('explorer-search-end', self._explorerSearchEnd)
		self._mapper.events.addListener('explorer-searches-start', self._explorerSearchesStart)
		self._mapper.events.addListener('explorer-searches-end', self._explorerSearchesEnd)
		self._mapper.events.addListener('explorer-search-iteration-start', self._explorerSearchIterationStart)
		self._mapper.events.addListener('explorer-search-iteration-end', self._explorerSearchIterationEnd)

		self._mapper.maker.events.addListener('run-end', self._clearMakerState)

	def _updateMapperState(self, state):
		'''
		Text line to display the current state of the Mapper.

		Parameters
		----------
		state : str
			State to display.
		'''

		if self._mapper_state_line is None:
			self._mapper_state_line = self.addTextLine(state, position = 0)

		else:
			self._mapper_state_line.text = state

	def _clearMakerState(self, *args, **kwargs):
		'''
		We don't need the Maker state anymore: we erase it.
		'''

		self._clearState()

	def clearState(self):
		'''
		Clear the Mapper state.
		'''

		if self._mapper_state_line is not None:
			self.removeItem(self._mapper_state_line)
			self._mapper_state_line = None

	def _readStart(self):
		'''
		The interpretation of a tree has started.
		'''

		if self._explorer_searches is None:
			self._updateMapperState('Reading a tree…')

	def _readEnd(self):
		'''
		The tree is read.
		'''

		if self._explorer_searches is None:
			self._updateMapperState('Tree read')

	def _mapStart(self):
		'''
		The mapping of a tree has been started.
		'''

		if self._explorer_searches is None:
			self._updateMapperState('Mapping a tree…')

	def _mapEnd(self):
		'''
		The mapping of a tree has ended.
		'''

		if self._explorer_searches is None:
			self._updateMapperState('Tree mapped')

	def _nodeStart(self, depth, node):
		'''
		The mapping of a node has been started.

		Parameters
		----------
		depth : int
			Depth of the node.

		node : dict
			Description of the node.
		'''

		if node is not None:
			self._nodes_lines[depth] = self.addTextLine(f'Depth {depth}…', position = 2*depth + 1)
			self._nodes_bars[depth] = self.addProgressBar(len(node['values']), position = 2*depth + 2)

	def _nodeProgress(self, depth):
		'''
		The mapping of a node just progressed.

		Parameters
		----------
		depth : int
			Depth of the node.
		'''

		if depth in self._nodes_bars:
			self._nodes_bars[depth].counter += 1

	def _nodeEnd(self, depth):
		'''
		The mapping of a node has ended.

		Parameters
		----------
		depth : int
			Depth of the node.
		'''

		if depth in self._nodes_lines:
			self.removeItem(self._nodes_bars[depth])
			del self._nodes_bars[depth]

			self.removeItem(self._nodes_lines[depth])
			del self._nodes_lines[depth]

	def _generateStart(self):
		'''
		A set of simulations will be generated.
		'''

		pass

	def _generateEnd(self):
		'''
		A set of simulations has been generated.
		'''

		pass

	def _evaluationStart(self):
		'''
		The evaluation of a simulation has been started.
		'''

		pass

	def _evaluationEnd(self):
		'''
		The evaluation of a simulation has ended.
		'''

		pass

	def _explorerFindStart(self):
		'''
		An Explorer starts to find the tests evaluated to `True`.
		'''

		self._updateMapperState('Finding the true tests…')

	def _explorerFindEnd(self):
		'''
		The search for the tests has ended.
		'''

		self._updateMapperState('Exploration ended')

	def _explorerSearchesStart(self, searches, n_tests):
		'''
		An Explorer starts to search optimal settings.

		Parameters
		----------
		searches : dict
			Description of all the searches.

		n_tests : int
			Number of planned searches.
		'''

		self._explorer_searches = searches
		self._explorer_searches_n_tests = n_tests

		self._updateMapperState(f'Searching for {string.plural(n_tests, "value", "values")}…')

	def _explorerSearchesEnd(self):
		'''
		The search has ended.
		'''

		self._explorer_searches = None
		self._explorer_searches_n_tests = None

		self._updateMapperState('Searches ended')

	def _explorerSearchStart(self, search):
		'''
		An Explorer starts to search optimal settings for a particular test.

		Parameters
		----------
		search : dict
			Description of the starting search.
		'''

		self._explorer_search = search

		self._updateMapperState(f'Search {len(self._explorer_searches["searches"])+1}/{self._explorer_searches_n_tests}…')

	def _explorerSearchEnd(self):
		'''
		The search for one test has ended.
		'''

		self._explorer_search = None

		self._updateMapperState('Search ended')

	def _explorerSearchIterationStart(self):
		'''
		An iteration in a search has started.
		'''

		state = f'Search {len(self._explorer_searches["searches"])+1}/{self._explorer_searches_n_tests}'
		state += f', iteration {len(self._explorer_search["iterations"])+1}'

		if self._explorer_search['iterations']:
			state += f', current criterion: {self._explorer_search["iterations"][-1]["stopping_criterion"]}'

		self._updateMapperState(state)

	def _explorerSearchIterationEnd(self):
		'''
		An iteration in a search has ended.
		'''

		pass
