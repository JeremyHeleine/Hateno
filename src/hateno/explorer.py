#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from .folder import Folder
from .mapper import Mapper
from .errors import *

class Explorer():
	'''
	Use the Mapper to search for particular settings values.

	Parameters
	----------
	mapper : Mapper
		Instance of the Mapper to use.
	'''

	def __init__(self, mapper):
		self._mapper = mapper
		self._found = None

	def _findInNode(self, node, depth = 0, prev_settings = [], prev_values = []):
		'''
		Find true tests in a node.

		Parameters
		----------
		node : dict
			Current node.

		depth : int
			Depth of the node.

		prev_settings : list
			Settings of the parent nodes.

		prev_values : list
			Values of the parent nodes' settings for this node.
		'''

		if depth not in self._found and 'test' in self._tree[depth]:
			self._found[depth] = {
				'settings': prev_settings + node['settings'],
				'test': self._tree[depth]['test'],
				'true_tests': [],
				'evaluations': [],
				'values': []
			}

		for k, m in enumerate(node['map']):
			if m.get('test'):
				self._found[depth]['values'].append(prev_values + m['values'])
				self._found[depth]['evaluations'].append(m['evaluation'])

				sub_map = node['map'][:k+1]
				self._found[depth]['true_tests'].append({
					f'[{j}]': {
						'values': prev_values + sub_map[j]['values'],
						'evaluation': sub_map[j]['evaluation']
					}
					for j in self._tree[depth]['test_requested_indices']
				})

			if 'output' in m:
				self._findInNode(m['output'], depth + 1, prev_settings + node['settings'], prev_values + m['values'])

	def find(self, tree = None):
		'''
		Find the settings leading to `True` tests.

		Parameters
		----------
		tree : dict
			Description of the tree to explore. If `None`, use the latest Mapper output.
		'''

		if tree is not None:
			self._mapper.mapTree(tree)

		self._tree = self._mapper.tree_by_depths

		self._mapper.events.trigger('explorer-find-start')

		self._found = {}
		self._findInNode(self._mapper.output)

		self._mapper.events.trigger('explorer-find-end')

		return self._found

	def _searchInterval(self):
		'''
		Determine the new search interval.
		For the first iteration, use the whole interval.
		For the others, see where the solution should be located.
		'''

		try:
			latest = self._current_search['iterations'][-1]

		except IndexError:
			self._current_search_iteration['interval'] = self._current_search['interval']

		else:
			if self._mapper._test(self._search_tree['tree'], [latest['interval']['evaluations'][0], latest['evaluation']]):
				self._current_search_iteration['interval'] = {
					'bounds': (latest['interval']['bounds'][0], latest['iterate']),
					'evaluations': (latest['interval']['evaluations'][0], latest['evaluation'])
				}

			else:
				self._current_search_iteration['interval'] = {
					'bounds': (latest['iterate'], latest['interval']['bounds'][1]),
					'evaluations': (latest['evaluation'], latest['interval']['evaluations'][1])
				}

	def _dichotomy(self):
		'''
		Calculate the new iterate of a search by using a dichotomy method.
		'''

		self._current_search_iteration['iterate'] = 0.5 * sum(self._current_search_iteration['interval']['bounds'])

	def _secant(self):
		'''
		Calculate the new iterate of a search by using a secant method.
		'''

		x0, x1 = self._current_search_iteration['interval']['bounds']
		y0, y1 = self._current_search_iteration['interval']['evaluations']

		target = self._tree[self._search['depth']]['test_target']

		self._current_search_iteration['iterate'] = x0 + (target - y0) * (x1 - x0) / (y1 - y0)

	def _searchStopCriterion(self):
		'''
		Calculate the stop criterion of the current iteration.
		'''

		if 'test_target' in self._tree[self._search['depth']]:
			self._current_search_iteration['stopping_criterion'] = abs(self._tree[self._search['depth']]['test_target'] - self._current_search_iteration['evaluation'])

		else:
			a, b = self._current_search_iteration['interval']['bounds']
			self._current_search_iteration['stopping_criterion'] = abs(b - a)

	def _buildSearchTree(self):
		'''
		Build the tree to map the new iterate.
		'''

		default_simulation = self._mapper.default_simulation

		for setting, value in zip(self._search['previous_settings'], self._current_search['previous_values']):
			default_simulation[setting['set']][setting['set_index']][setting['name']] = value

		new_tree = self._tree[self._search['depth']]
		new_tree['values'] = [self._current_search_iteration['iterate']]

		self._search_tree = {
			'default': default_simulation,
			'tree': new_tree
		}

	def _searchIteration(self):
		'''
		Iteration of a search.
		'''

		self._mapper.events.trigger('explorer-search-iteration-start')

		self._current_search_iteration = {}
		self._searchInterval()

		if 'test_target' in self._tree[self._search['depth']]:
			self._secant()
		else:
			self._dichotomy()

		self._buildSearchTree()
		self._mapper.mapTree(self._search_tree)

		self._current_search_iteration['evaluation'] = self._mapper.output['map'][0]['evaluation']
		self._searchStopCriterion()

		self._current_search['iterations'].append(self._current_search_iteration)

		self._mapper.events.trigger('explorer-search-iteration-end')

		if self._current_search_iteration['stopping_criterion'] >= self._search_tolerance and len(self._current_search['iterations']) < self._search_itermax:
			self._searchIteration()

	def search(self, tree = None, depth = None, *, tolerance = 1E-5, itermax = 20):
		'''
		Search for the best values to verify a test.
		There must be only one setting at the searched depth.
		The test must involve the last two evaluations.
		The initial values indicated in the map are used to define the search interval: the solution is assumed to be inside it.

		Parameters
		----------
		tree : dict
			Description of the tree to explore. If `None`, use the latest Mapper output.

		depth : int
			Depth to optimize. If `None`, use the first depth defining a test.

		tolerance : float
			Search tolerance.

		itermax : int
			Maximum number of iterations allowed.
		'''

		if self._found is None:
			self.find(tree)

		self._search_tolerance = tolerance
		self._search_itermax = itermax

		if depth is None:
			depth = list(self._found.keys())[0]

		found = self._found[depth]

		self._search = {
			'depth': depth,
			'previous_settings': found['settings'][:-1],
			'setting': found['settings'][-1],
			'searches': []
		}

		self._mapper.events.trigger('explorer-searches-start', self._search, len(found['true_tests']))

		for test in found['true_tests']:
			self._current_search = {
				'previous_values': test['[-1]']['values'][:-1],
				'interval': {
					'bounds': (test['[-2]']['values'][-1], test['[-1]']['values'][-1]),
					'evaluations': (test['[-2]']['evaluation'], test['[-1]']['evaluation'])
				},
				'iterations': []
			}

			self._mapper.events.trigger('explorer-search-start', self._current_search)

			self._searchIteration()

			self._mapper.events.trigger('explorer-search-end')
			self._search['searches'].append(self._current_search)

		self._mapper.events.trigger('explorer-searches-end')

		return self._search
