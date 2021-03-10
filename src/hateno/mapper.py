#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil
import re

from . import string, jsonfiles
from .folder import Folder
from .simulation import Simulation
from .maker import Maker
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

		self._simulations_dir = None

		self._index_regex_compiled = None

		self.events = Events(['read-start', 'read-end', 'map-start', 'map-end', 'generate-start', 'generate-end', 'evaluation-start', 'evaluation-end'])

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
			if isinstance(normalized['test'], (float, int)):
				normalized['test'] = f'([-2] - {normalized["test"]}) * ([-1] - {normalized["test"]}) <= 0'

			else:
				first_operator_match = re.search(r'([<>]=?|[!=]=|in)', normalized['test'].strip())

				if first_operator_match and first_operator_match.start() == 0:
					normalized['test'] = '[-1] ' + normalized['test']

			normalized['test_requested_indices'] = set(map(int, self._index_regex.findall(normalized['test'])))

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
		'''

		if self._simulations_dir is None:
			self._simulations_dir = self._simulations_folder.tempdir()

		simulations_dir = os.path.join(self._simulations_dir, str(len(os.listdir(self._simulations_dir))))

		self._simulations = []

		for k, values in enumerate(simulations_values):
			simulation = self._default_simulation.copy()
			simulation['folder'] = os.path.join(self._simulations_dir, str(k))

			for setting, value in zip(settings, values):
				simulation.getSetting(setting).value = value

			self._simulations.append(simulation)

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
		'''

		evaluation = self._evaluate(node, arg_to_evaluate)

		if evaluation is None:
			return

		evaluations.append(evaluation)
		output['evaluation'] = evaluation

		test = self._test(node, evaluations)

		if test is None:
			return

		output['test'] = test

	def _mapNode(self, node, prev_settings = [], prev_settings_values = []):
		'''
		Prepare the values of the settings in a node, and then either map the children, or generate the simulations before evaluate.

		Parameters
		----------
		node : dict
			The node to map.

		prev_settings : list
			The previous settings from the parent nodes.

		prev_settings_values : list
			The values of the previous settings.

		Returns
		-------
		output : dict
			Output of the node mapping.
		'''

		map = []
		output = {'settings': node['settings'], 'map': map}

		evaluations = []

		if 'foreach' in node:
			for values in node['values']:
				sub_output = self._mapNode(node['foreach'], prev_settings + node['settings'], prev_settings_values + values)
				simulation = self._simulations[0]

				o = {
					'values': [simulation.getSetting(setting).value for setting in node['settings']],
					'output': sub_output
				}

				self._endNode(node, self._simulations, evaluations, o)
				map.append(o)

		else:
			self._setSimulations(prev_settings + node['settings'], [prev_settings_values + v for v in node['values']])

			for simulation in self._simulations:
				self._generateSimulation(simulation)

				o = {
					'values': [simulation.getSetting(setting).value for setting in node['settings']]
				}

				self._endNode(node, simulation, evaluations, o)
				map.append(o)

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

		output = self._mapNode(self._tree)

		self._deleteSimulations()

		self.events.trigger('map-end')

		return output
