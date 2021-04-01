#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil
import re

from . import string, jsonfiles
from .folder import Folder
from .simulation import Simulation
from .maker import Maker, MakerUI
from .events import Events

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

		return self._default_simulation.settings

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
		self._tree = self._readTreeNode(tree['tree'])

		self.events.trigger('read-end')

	def _setSimulations(self, settings, simulations_values):
		'''
		Define the set of simulations to generate.

		Parameters
		----------
		settings : list
			The settings to alter.

		simulations_values : list
			The raw values of these settings.

		Returns
		-------
		simulations : list
			The newly defined simulations.
		'''

		if self._simulations_dir is None:
			self._simulations_dir = self._simulations_folder.tempdir()
			self._simulations = []

		simulations_dir = os.path.join(self._simulations_dir, str(len(os.listdir(self._simulations_dir))))

		simulations = []

		for k, values in enumerate(simulations_values):
			simulation = self._default_simulation.copy()
			simulation['folder'] = os.path.join(simulations_dir, str(k))

			for setting, value in zip(settings, values):
				simulation.getSetting(setting).value = value

			simulations.append(simulation)

		self._simulations += simulations

		return simulations

	def _generateSimulation(self, simulation):
		'''
		Generate a simulation.

		Parameters
		----------
		simulation : Simulation
			The simulation to generate.
		'''

		self.events.trigger('generate-start')

		self.maker.run([simulation])

		self.events.trigger('generate-end')

	def _deleteSimulations(self):
		'''
		Delete the simulations directory.
		'''

		if self._simulations_dir is not None:
			shutil.rmtree(self._simulations_dir)

			self._simulations_dir = None
			self._simulations = None

	def _evaluate(self, node, arg_to_pass):
		'''
		Evaluate the simulations of a node, and store the output.

		Parameters
		----------
		node : dict
			The current node.

		arg_to_pass : Simulation|list
			Either the simulation generated by the node, or the list of simulations.

		Returns
		-------
		evaluation : mixed
			Result of the evaluation, or `None` if there is no evaluation found in the node.
		'''

		if 'evaluation' not in node:
			return None

		self.events.trigger('evaluation-start')

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

	def _endNode(self, node, arg_to_evaluate, evaluations, output):
		'''
		Actions to execute at the end of the mapping of a node.
		First, evaluate the generated simulation(s).
		Then, apply the test.

		Parameters
		----------
		node : dict
			The mapped node.

		arg_to_evaluate : Simulation|list
			Either the simulation generated by the node, or the list of simulations.

		evaluations : list
			The current list of evaluations for this node.

		output : dict
			Output of the node.

		Returns
		-------
		stop : bool
			`True` if the latest test is `True` and the node's `stop` is `True`.
		'''

		evaluation = self._evaluate(node, arg_to_evaluate)

		if evaluation is None:
			return False

		evaluations.append(evaluation)
		output['evaluation'] = evaluation

		test = self._test(node, evaluations)

		if test is None:
			return False

		output['test'] = test

		return node['stop'] and test

	def _mapNode(self, node, depth = 0, prev_settings = [], prev_settings_values = [], parent_simulations = []):
		'''
		Prepare the values of the settings in a node, and then either map the children, or generate the simulations before evaluate.

		Parameters
		----------
		node : dict
			The node to map.

		depth : int
			Depth of the node.

		prev_settings : list
			The previous settings from the parent nodes.

		prev_settings_values : list
			The values of the previous settings.

		parent_simulations : list
			The set of simulations to fill for the parent node (will be evaluated).

		Returns
		-------
		output : dict
			Output of the node mapping.
		'''

		self.events.trigger('node-start', depth, node)

		map = []
		output = {'settings': node['settings'], 'map': map}

		evaluations = []

		if 'foreach' in node:
			for values in node['values']:
				simulations = []
				sub_output = self._mapNode(node['foreach'], depth+1, prev_settings + node['settings'], prev_settings_values + values, simulations)
				parent_simulations += simulations

				o = {
					'values': [simulations[0].getSetting(setting).value for setting in node['settings']],
					'output': sub_output
				}

				stop = self._endNode(node, simulations, evaluations, o)
				map.append(o)

				self.events.trigger('node-progress', depth)

				if stop:
					break

		else:
			simulations = self._setSimulations(prev_settings + node['settings'], [prev_settings_values + v for v in node['values']])
			generated_simulations = []

			for simulation in simulations:
				self._generateSimulation(simulation)
				generated_simulations.append(simulation)

				o = {
					'values': [simulation.getSetting(setting).value for setting in node['settings']]
				}

				stop = self._endNode(node, simulation, evaluations, o)
				map.append(o)

				self.events.trigger('node-progress', depth)

				if stop:
					break

			parent_simulations += generated_simulations

		self.events.trigger('node-end', depth)

		return output

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

		self._output = self._mapNode(self._tree)

		self._deleteSimulations()

		self.events.trigger('map-end')

		return self._output

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
