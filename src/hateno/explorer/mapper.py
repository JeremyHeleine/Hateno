#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import itertools
import operator
import os
import re
import shutil

from ..folder import Folder
from ..maker import Maker
from ..simulation import Simulation
from ..utils import Events, string, jsonfiles

class Mapper():
	'''
	Use the Maker to generate simulations and associate them to numeric values.

	Parameters
	----------
	simulations_folder : Folder|str
		The simulations folder. Either a `Folder` instance or a path to a folder with a configuration file.

	config_name : str
		Name of the config to use with the Maker.

	generate_only : bool
		`True` to not add the simulations to the manager.
	'''

	def __init__(self, simulations_folder, config_name = None, *, generate_only = True):
		self._simulations_folder = simulations_folder if type(simulations_folder) is Folder else Folder(simulations_folder)
		self._config_name = config_name

		self._generate_only = generate_only
		self._maker_instance = None

		self._default_simulation = None
		self._tree = None
		self._output = None

		self._simulations_dir = None

		self._index_regex_compiled = None

		self.events = Events([
			'read-start', 'read-end',
			'map-start', 'map-end',
			'node-start', 'node-progress', 'node-end',
			'generate-start', 'generate-end',
			'evaluation-start', 'evaluation-end',
			'explorer-find-start', 'explorer-find-end',
			'explorer-searches-start', 'explorer-searches-end',
			'explorer-search-start', 'explorer-search-end',
			'explorer-search-iteration-start', 'explorer-search-iteration-end'
		])

	def __enter__(self):
		'''
		Context manager to call `close()` at the end.
		'''

		return self

	def __exit__(self, type, value, traceback):
		'''
		Ensure `close()` is called when exiting the context manager.
		'''

		self.close()

	@property
	def maker(self):
		'''
		Return the Maker instance.

		Returns
		-------
		maker : Maker
			Instance currently in used.
		'''

		if self._maker_instance is None:
			self._maker_instance = Maker(self._simulations_folder, self._config_name, override_options = {'generate_only': self._generate_only})

		return self._maker_instance

	def close(self):
		'''
		Properly exit the Maker instance.
		'''

		try:
			self._maker_instance.close()

		except AttributeError:
			pass

		else:
			self._maker_instance = None

	@property
	def tree(self):
		'''
		Get the current tree.

		Returns
		-------
		tree : dict
			The current tree to read.
		'''

		return self._tree

	@property
	def default_simulation(self):
		'''
		Get the current default simulation's settings.

		Returns
		-------
		default_simulation : dict
			The settings of the current default simulation.
		'''

		return self._default_simulation.raw_values_settings

	@property
	def output(self):
		'''
		Get the current output.

		Returns
		-------
		output : dict
			The output of the current tree.
		'''

		return self._output

	@property
	def tree_by_depths(self):
		'''
		Get the current tree, sorted by depths.

		Returns
		-------
		tree : dict
			The current tree to read.
		'''

		if self._tree is None:
			return None

		depth = 0
		tree = {depth: self._tree}

		current_depth = self._tree
		while 'foreach' in current_depth:
			depth += 1
			current_depth = current_depth['foreach']
			tree[depth] = current_depth

		return tree

	@property
	def _index_regex(self):
		'''
		Regex to detect an index in a test.

		Returns
		-------
		regex : re.Pattern
			The index regex.
		'''

		if self._index_regex_compiled is None:
			self._index_regex_compiled = re.compile(r'\[(-?[0-9]+)\]')

		return self._index_regex_compiled

	def _buildValues(self, vdesc):
		'''
		Build the list of values a node will use.
		For values description, we don't calculate the interpolated values now. The Simulation parser will, so we can use settings tags.

		Parameters
		----------
		vdesc : list|dict
			Explicit list, or description. A description is a dictionary with the following keys:
				* `from`: the first value(s),
				* `to`: the last value(s),
				* `n`: the number of values.

		Returns
		-------
		values : list
			The complete list of values for the node.
		'''

		if type(vdesc) is list:
			return [
				v if type(v) is list else [v]
				for v in vdesc
			]

		if type(vdesc['from']) is list:
			return [
				[
					f'(({a} + {k} * ({b} - ({a})) / {vdesc["n"] - 1}))'
					for a, b in zip(vdesc['from'], vdesc['to'])
				]
				for k in range(0, vdesc['n'])
			]

		return [
			[f'(({vdesc["from"]} + {k} * ({vdesc["to"]} - ({vdesc["from"]})) / {vdesc["n"] - 1}))']
			for k in range(0, vdesc['n'])
		]

	def _readTreeNode(self, node):
		'''
		Normalize the way a node is defined, i.e. always use `settings` with a list, and build the values.
		Detect the depth at which we will generate the simulations (the shallowest one before finding a stop).

		Parameters
		----------
		node : dict
			Description of the node.

		Returns
		-------
		normalized : dict
			The normalized node.
		'''

		settings = node.get('settings') or node.get('setting')
		if type(settings) is not list:
			settings = [settings]

		normalized = {
			'settings': [{'set': '', 'set_index': 0, 'name': '', **coords} for coords in settings],
			'values': self._buildValues(node['values'])
		}

		depth = len(self._nodes)
		self._nodes.append(normalized)

		self._simulations_settings.append(normalized['settings'])
		self._simulations_settings_values.append(normalized['values'])

		if 'foreach' in node:
			normalized['foreach'] = self._readTreeNode(node['foreach'])

		try:
			normalized['evaluation'] = node['evaluation']

		except KeyError:
			pass

		try:
			normalized['test'] = node['test']

		except KeyError:
			pass

		else:
			try:
				normalized['test'] = node['test_target']

			except KeyError:
				pass

			if isinstance(normalized['test'], (float, int)):
				normalized['test_target'] = normalized['test']
				normalized['test'] = f'([-2] - {normalized["test"]}) * ([-1] - {normalized["test"]}) <= 0'

			else:
				first_operator_match = re.search(r'([<>]=?|[!=]=|in)', normalized['test'].strip())

				if first_operator_match and first_operator_match.start() == 0:
					normalized['test'] = '[-1] ' + normalized['test']

			normalized['test_requested_indices'] = set(map(int, self._index_regex.findall(normalized['test'])))

		try:
			normalized['stop'] = node['stop']

		except KeyError:
			normalized['stop'] = False

		if normalized['stop']:
			self._generating_depth = max(self._generating_depth, depth + 1)

		return normalized

	def _readTree(self, tree):
		'''
		Define the default simulation and normalize the way the tree is defined.

		Parameters
		----------
		tree : dict
			Description of the tree to explore.
		'''

		self.events.trigger('read-start')

		self._default_simulation = Simulation(self._simulations_folder, {'settings': tree.get('default') or {}})
		self._simulations_settings = []
		self._simulations_settings_values = []
		self._generating_depth = 0
		self._nodes = []
		self._tree = self._readTreeNode(tree['tree'])

		self.events.trigger('read-end')

	def _generateSimulations(self, prev_values):
		'''
		Generate a set of simulations, corresponding to all children of a node.

		Parameters
		----------
		prev_values : tuple
			Indices of the values of the settings of the parent nodes.
		'''

		self.events.trigger('generate-start')

		if self._simulations_dir is None:
			self._simulations_dir = self._simulations_folder.tempdir()
			self._simulations = {}

		simulations_dir = os.path.join(self._simulations_dir, str(len(os.listdir(self._simulations_dir))))

		default_simulation = self._default_simulation.copy()
		for settings, values, k in zip(self._simulations_settings, self._simulations_settings_values, prev_values):
			for setting, value in zip(settings, values[k]):
				default_simulation.getSetting(setting).value = value

		simulations = []
		remaining_settings = self._simulations_settings[len(prev_values):]

		if remaining_settings:
			remaining_values = self._simulations_settings_values[len(prev_values):]
			remaining_values_indices = map(lambda l: range(len(l)), remaining_values)

			indices_coefs = tuple(itertools.accumulate([1] + list(reversed(list(map(lambda l: len(l), remaining_values[1:]))))))

			for values, K in zip(itertools.product(*remaining_values), itertools.product(*remaining_values_indices)):
				k = sum(map(operator.mul, indices_coefs, K))

				simulation = default_simulation.copy()
				simulation['folder'] = os.path.join(simulations_dir, str(k))

				for setting, value in zip(sum(remaining_settings, []), sum(values, [])):
					simulation.getSetting(setting).value = value

				simulations.append(simulation)
				self._simulations[prev_values + K] = simulation

		else:
			default_simulation['folder'] = os.path.join(simulations_dir, '0')
			simulations = [default_simulation]
			self._simulations[prev_values] = default_simulation

		self.maker.run(simulations)

		self.events.trigger('generate-end')

	def _deleteSimulations(self):
		'''
		Delete the simulations directory.
		'''

		if self._simulations_dir is not None:
			shutil.rmtree(self._simulations_dir)

			self._simulations_dir = None
			self._simulations = None

	def _evaluate(self, node, simulations):
		'''
		Evaluate the simulations of a node, and store the output.

		Parameters
		----------
		node : dict
			The current node.

		Simulations : list
			The list of simulations corresponding to the node.

		Returns
		-------
		evaluation : mixed
			Result of the evaluation, or `None` if there is no evaluation found in the node.
		'''

		if 'evaluation' not in node:
			return None

		self.events.trigger('evaluation-start')

		arg_to_pass = simulations if 'foreach' in node else simulations[0]
		evaluation = self._simulations_folder.evaluations.call(node['evaluation'], arg_to_pass)

		self.events.trigger('evaluation-end')

		return evaluation

	def _test(self, node, evaluations):
		'''
		Apply a test defined in a node.

		Parameters
		----------
		node : dict
			The current node.

		evaluations : list
			List of evaluations to consider.

		Returns
		-------
		result : mixed
			Result of the test (bool) or `None` if no test has been evaluated.
		'''

		if 'test' not in node:
			return None

		test = node['test']

		# Retrieve the requested indices and first see if the ones which should be different are really different
		# To do that, we "fix" negative indexes so they should be equal to their positive counterparts
		# If they are still negative, it seems that we don't have enough elements in the list: it will be detected in the next part
		# It is important to add the length of the list and to not use the modulo, to be sure we consider different elements

		unique_requested_indices = set(map(lambda k: k if k >= 0 else k + len(evaluations), node['test_requested_indices']))

		if len(unique_requested_indices) < len(node['test_requested_indices']):
			return None

		try:
			test = self._index_regex.sub(lambda m: str(evaluations[int(m.group(1))]), test)

		except IndexError:
			return None

		else:
			return string.safeEval(test)

	def _endNode(self, node, simulations, evaluations, output):
		'''
		Actions to execute at the end of the mapping of a node.
		First, evaluate the generated simulation(s).
		Then, apply the test.

		Parameters
		----------
		node : dict
			The mapped node.

		simulations : list
			The list of simulations to evaluate.

		evaluations : list
			The current list of evaluations for this node.

		output : dict
			Output of the node.

		Returns
		-------
		stop : bool
			`True` if the latest test is `True` and the node's `stop` is `True`.
		'''

		evaluation = self._evaluate(node, simulations)

		if evaluation is None:
			return False

		evaluations.append(evaluation)
		output['evaluation'] = evaluation

		test = self._test(node, evaluations)

		if test is None:
			return False

		output['test'] = test

		return node['stop'] and test

	def _mapNode(self, output, prev_values = ()):
		'''
		Map a node by associating evaluations to the right simulations.
		Generate the simulations if we are located at the right depth.

		Parameters
		----------
		output : dict
			Dictionary where to store the output of this node.

		prev_values : tuple
			Indices of the values for the parameters of the parent nodes.

		Returns
		-------
		simulations : list
			The list of simulations corresponding to this node.
		'''

		depth = len(prev_values)

		try:
			node = self._nodes[depth]

		except IndexError:
			node = None

		self.events.trigger('node-start', depth, node)

		if depth == self._generating_depth:
			self._generateSimulations(prev_values)

		if node is None:
			return [self._simulations[prev_values]]

		output['settings'] = node['settings']
		output['map'] = []

		simulations = []
		evaluations = []

		for k in range(len(node['values'])):
			sub_output = {'values': [], 'output': {}}

			sub_simulations = self._mapNode(sub_output['output'], prev_values + (k,))
			simulations += sub_simulations

			sub_output['values'] = [sub_simulations[0].getSetting(setting).value for setting in node['settings']]

			if not(sub_output['output']):
				del sub_output['output']

			stop = self._endNode(node, sub_simulations, evaluations, sub_output)
			output['map'].append(sub_output)

			self.events.trigger('node-progress', depth)

			if stop:
				break

		self.events.trigger('node-end', depth)

		return simulations

	def mapTree(self, tree):
		'''
		Map a tree.

		Parameters
		----------
		tree : dict
			Description of the tree to explore.

		Returns
		-------
		output : dict
			Output of the tree mapping.
		'''

		self._readTree(tree)

		self.events.trigger('map-start')

		self._output = {}
		self._mapNode(self._output)

		self._deleteSimulations()

		self.events.trigger('map-end')

		return self._output
