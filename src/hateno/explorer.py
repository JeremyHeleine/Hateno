#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from .folder import Folder
from .mapper import Mapper

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

		self._found = {}
		self._findInNode(self._mapper.output)

		return self._found
