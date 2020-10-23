#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import enum
import os
import shutil
import copy
import tempfile
import re

from . import string, jsonfiles
from .folder import Folder
from .simulation import Simulation
from .maker import Maker, MakerUI
from .events import Events
from .errors import *

class EvaluationMode(enum.Enum):
	'''
	Evaluation mode (evaluate each simulation or a group).
	'''

	EACH = enum.auto()
	GROUP = enum.auto()

class Explorer():
	'''
	Use the Maker to generate simulations and search for particular settings values.

	Parameters
	----------
	simulations_folder : Folder|str
		The simulations folder. Either a `Folder` instance or a path to a folder with a configuration file.

	config_name : str
		Name of the config to use with the Maker.

	generate_only : bool
		`True` to not add the simulations to the manager.
	'''

	def __init__(self, simulations_folder, config_name, *, generate_only = True):
		self._simulations_folder = simulations_folder if type(simulations_folder) is Folder else Folder(simulations_folder)
		self._config_name = config_name

		self._generate_only = generate_only
		self._maker_instance = None

		self.default_simulation = {}

		self._map = None
		self._map_output = None

		self._simulations_dir = None
		self._simulations = None

		self._evaluation = None
		self._evaluation_mode = EvaluationMode.EACH

		self._save_function = None
		self._save_folder = None

		self.events = Events(['stopped', 'map-start', 'map-end', 'map-component-start', 'map-component-progress', 'map-component-end', 'searches-start', 'searches-end', 'search-start', 'search-iteration', 'search-end'])

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
	def default_simulation(self):
		'''
		Return the current default settings.

		Returns
		-------
		default_simulation : dict
			The default settings.
		'''

		return self._default_simulation.settings

	@default_simulation.setter
	def default_simulation(self, settings):
		'''
		Set the new default settings.

		Parameters
		----------
		settings : dict
			The new settings to use as default.
		'''

		if not('settings' in settings):
			settings = {'settings': settings}

		self._default_simulation = Simulation(self._simulations_folder, settings)

	@property
	def map(self):
		'''
		Get the current map.

		Returns
		-------
		map : dict
			Description of the map.
		'''

		return self._map

	def _normalizeSettings(self, map_component):
		'''
		Normalize the way the settings are defined in a map component.

		Parameters
		----------
		map_component : dict
			The component to alter.
		'''

		if 'setting' in map_component:
			if not('settings' in map_component):
				map_component['settings'] = map_component['setting']

			del map_component['setting']

		if not(type(map_component['settings']) is list):
			map_component['settings'] = [map_component['settings']]

		map_component['settings'] = [{'set_index': 0, **coords} for coords in map_component['settings']]

		if 'foreach' in map_component:
			self._normalizeSettings(map_component['foreach'])

	@map.setter
	def map(self, new_map):
		'''
		Set the map to follow.

		Parameters
		----------
		new_map : dict
			Description of the map.
		'''

		self._map = new_map

		self._normalizeSettings(self._map)

	@property
	def map_depths(self):
		'''
		Extract the different depth levels from the map.

		Returns
		-------
		depths : dict
			The descriptions of the levels.
		'''

		if self._map is None:
			return None

		depth = 0
		depths = {depth: self._map}

		current_depth = self._map
		while 'foreach' in current_depth:
			depth += 1
			current_depth = current_depth['foreach']
			depths[depth] = current_depth

		return depths

	@property
	def evaluation(self):
		'''
		Get the current evaluation function.

		Returns
		-------
		evaluation : function
			Function used to evaluate the simulations.
		'''

		return self._evaluation

	@evaluation.setter
	def evaluation(self, new_evaluation):
		'''
		Set the evaluation function.

		Parameters
		----------
		new_evaluation : function
			The function to use to evaluate the simulations.
		'''

		self._evaluation = new_evaluation

	@property
	def evaluation_mode(self):
		'''
		Get the current evaluation mode.

		Returns
		-------
		evaluation_mode : EvaluationMode
			Current mode.
		'''

		return self._evaluation_mode

	@evaluation_mode.setter
	def evaluation_mode(self, new_mode):
		'''
		Set the evaluation mode.

		Parameters
		----------
		new_mode : EvaluationMode
			Evaluation mode to use.
		'''

		self._evaluation_mode = new_mode

	@property
	def output(self):
		'''
		Get the output of the map exploration.

		Returns
		-------
		map_output : dict
			Output of the exploration.
		'''

		return self._map_output

	@property
	def save_function(self):
		'''
		Get the function currently used to save a simulation.

		Returns
		-------
		save_function : function
			The function.
		'''

		return self._save_function

	@save_function.setter
	def save_function(self, f):
		'''
		Set the function used to save a simulation.

		Parameters
		----------
		f : function
			The function to use. Use `None` to not save anything.
		'''

		self._save_function = f

	@property
	def save_folder(self):
		'''
		Get the folder currently used to save the simulations.

		Returns
		-------
		save_folder : str
			The folder.
		'''

		return self._save_folder

	@save_folder.setter
	def save_folder(self, folder):
		'''
		Set the folder to use to save the simulations.

		Parameters
		----------
		folder : str
			The folder to use.
		'''

		self._save_folder = folder

	def _saveSimulations(self, simulations):
		'''
		Save some simulations using the saving function and folder.

		Parameters
		----------
		simulations : list
			The simulations to save.

		Returns
		-------
		folder : list
			The folders where the files have been saved.
		'''

		if self._save_function is None or self._save_folder is None:
			return None

		try:
			n = len(os.listdir(self._save_folder))

		except FileNotFoundError:
			n = 0

		folder = os.path.join(self._save_folder, str(n))
		folders = []

		for k, simulation in enumerate(simulations):
			subfolder = os.path.join(folder, str(k))
			os.makedirs(subfolder)

			self._save_function(simulation, subfolder)
			simulation.writeSettingsFile('settings.json', folder = subfolder)

			folders.append(subfolder)

		return folders

	def _setSimulations(self, simulations_settings):
		'''
		Set the current set of simulations to consider, based on the default simulation and the given settings.

		Parameters
		----------
		simulations_settings : list
			List of all settings to alter, for each simulation.
			Each item of the list is a list of dict, each dict being a setting with the following keys:
				* `set`: name of the set the setting belongs to,
				* `set_index` (optional): the index of the set,
				* `name`: the name of the setting,
				* `value`: the value of the setting.
		'''

		self._simulations_dir = tempfile.mkdtemp(prefix = 'hateno-explorer_')

		self._simulations = []
		for k, settings in enumerate(simulations_settings):
			simulation = self._default_simulation.copy()
			simulation['folder'] = os.path.join(self._simulations_dir, str(k))

			for setting in settings:
				simulation.getSetting(setting).value = setting['value']

			self._simulations.append(simulation)

		self._simulations_settings = copy.deepcopy(simulations_settings)

	def _generateSimulations(self, simulations = None):
		'''
		Generate some simulations.

		Parameters
		----------
		simulations : list
			The simulations to generate. If `None`, generate the full set defined by `_setSimulations()`.

		Returns
		-------
		saved_folders : list
			The list of folders where the simulations have been saved.
		'''

		if simulations is None:
			simulations = self._simulations

		self.maker.run(simulations)

		return self._saveSimulations(simulations)

	def _deleteSimulations(self):
		'''
		Delete the current set of simulations.
		'''

		try:
			shutil.rmtree(self._simulations_dir)

		except FileNotFoundError:
			pass

		self._simulations_dir = None
		self._simulations = None
		self._simulations_settings = None

	def _checkStopCondition(self, stop_condition, evaluations):
		'''
		If a stop condition is provided, check if it is true or false.
		Access to specific evaluations is possible with indices (e.g. "[0] > [-1]" to check whether the first evaluation is greater than the latest one).
		By default, the condition is tested against the latest evaluation (e.g. "> 0" is then equivalent to "[-1] > 0").
		If we try to access non-existing indices, or if we expect a certain number of evaluations that is not reached yet, always return `False`.

		Parameters
		----------
		stop_condition : str
			Condition to evaluate.

		evaluations : list
			List of evaluations to consider.

		Returns
		-------
		stop : bool
			Result of the test. Always `False` if there is no stop condition.
		'''

		if stop_condition is None:
			return False

		first_operator_match = re.search(r'([<>]=?|[!=]=|in)', stop_condition.strip())

		if first_operator_match and first_operator_match.start() == 0:
			return string.safeEval(f'{evaluations[-1]} {stop_condition}')

		index_regex = re.compile(r'\[(-?[0-9]+)\]')

		# Retrieve the requested indices and first see if the ones which should be different are really different
		# To do that, we "fix" negative indexes so they should be equal to their positive counterparts
		# If they are still negative, it seems that we don't have enough elements in the list: it will be detected in the next part
		# It is important to add the length of the list and to not use the modulo, to be sure we consider different elements

		requested_indices = set(map(int, index_regex.findall(stop_condition)))
		unique_requested_indices = set(map(lambda k: k if k >= 0 else k + len(evaluations), requested_indices))

		if len(unique_requested_indices) < len(requested_indices):
			return False

		try:
			stop_condition = index_regex.sub(lambda m: str(evaluations[int(m.group(1))]), stop_condition)

		except IndexError:
			return False

		else:
			return string.safeEval(stop_condition)

	def _checkAndStoreStopCondition(self, stop_condition, evaluations, output, depth):
		'''
		Check if a stop condition is verified and store the result.

		Parameters
		----------
		stop_condition : str
			Condition to evaluate.

		evaluations : list
			List of evaluations to consider.

		output : dict
			Dictionary in which the ouput should be stored.

		depth : int
			Depth to use in the output.

		Returns
		-------
		stop : bool
			Result of the test.
		'''

		if stop_condition is None:
			return False

		stop_result = self._checkStopCondition(stop_condition, evaluations)

		if not('stops' in output):
			output['stops'] = []

		output['stops'].append({
			'depth': depth,
			'result': stop_result
		})

		return stop_result

	def _evaluateEach(self, depth, stop_condition = None):
		'''
		Call the evaluation function on each simulation of the current set.

		Parameters
		----------
		depth : int
			Current depth in the exploration tree.

		stop_condition : str
			Condition to stop the evaluation.

		Returns
		-------
		output : list
			Result of the evaluation of each simulation. Each item is a dictionary with keys:
				* `settings`: the altered settings of the simulation,
				* `evaluation`: the result of the evaluation of the simulation.
		'''

		output = []
		evaluations = []

		for simulation, settings in zip(self._simulations, self._simulations_settings):
			folders = self._generateSimulations([simulation])

			evaluation = self._evaluation(simulation)
			evaluations.append(evaluation)

			o = {
				'settings': settings,
				'evaluation': evaluation
			}

			if not(folders is None):
				o['save'] = folders[0]

			output.append(o)

			self.events.trigger('map-component-progress', depth)

			if self._checkAndStoreStopCondition(stop_condition, evaluations, o, depth):
				self.events.trigger('stopped')
				break

		return output

	def _evaluateGroup(self):
		'''
		Call the evaluation function on all simulations in the current set, as a group.

		Returns
		-------
		output : dict
			Result of the evaluation of the group. The dictionary has the following keys:
				* `settings`: the altered settings of all simulations for the group,
				* `evaluation`: the result of the evaluation.
		'''

		saved_folders = self._generateSimulations()

		evaluation = self._evaluation(self._simulations)

		output = {
			'settings': self._simulations_settings,
			'evaluation': evaluation
		}

		if not(saved_folders is None):
			output['save'] = os.path.dirname(saved_folders[0])

		return output

	def _buildValues(self, vdesc):
		'''
		Build a list of values from its description.

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
			The complete list of values.
		'''

		if type(vdesc) is list:
			return vdesc

		if type(vdesc['from']) is list:
			return [
				[
					a + k * (b - a) / (vdesc['n'] - 1)
					for a, b in zip(vdesc['from'], vdesc['to'])
				]
				for k in range(0, vdesc['n'])
			]

		return [
			vdesc['from'] + k * (vdesc['to'] - vdesc['from']) / (vdesc['n'] - 1)
			for k in range(0, vdesc['n'])
		]

	def _buildSettings(self, map_component, additional_settings = []):
		'''
		Build a list of settings with their values from a map component.

		Parameters
		----------
		map_component : dict
			The component to interpret.

		additional_settings : list
			List of settings to alter (that are not listed in this component), with their values.

		Returns
		-------
		settings : list
			Each item is the list of all altered settings with their values for one simulation.
		'''

		return [
			additional_settings + [
				{**coords, 'value': value}
				for coords, value in zip(map_component['settings'], values if type(values) is list else [values])
			]
			for values in self._buildValues(map_component['values'])
		]

	def _mapComponent(self, map_component, current_settings = [], depth = 0):
		'''
		Interpret a component of a map.

		Parameters
		----------
		map_component : dict
			The component to interpret.

		current_settings : list
			List of settings to alter (that are not listed in this component), with their values.

		depth : int
			Current depth in the exploration tree.

		Returns
		-------
		result : list
			A list of dict, each one corresponding to a simulation generated by the component. Each dict contains the keys:
				* `settings`: the list of altered settings,
				* `evaluation`: the result of the evaluation function on this simulation.
		'''

		simulations_settings = self._buildSettings(map_component, current_settings)

		self.events.trigger('map-component-start', depth, map_component, simulations_settings)

		output = []

		if 'foreach' in map_component:
			evaluations = []

			for settings in simulations_settings:
				output += self._mapComponent(map_component['foreach'], settings, depth + 1)
				evaluations.append(output[-1]['evaluation'])

				self.events.trigger('map-component-progress', depth)

				if self._checkAndStoreStopCondition(map_component.get('stop'), evaluations, output[-1], depth):
					self.events.trigger('stopped')
					break

		else:
			self._setSimulations(simulations_settings)

			if self._evaluation_mode == EvaluationMode.EACH:
				output = self._evaluateEach(depth, map_component.get('stop'))

			elif self._evaluation_mode == EvaluationMode.GROUP:
				output = [self._evaluateGroup()]

			self._deleteSimulations()

		self.events.trigger('map-component-end', depth, map_component, simulations_settings)

		return output

	def followMap(self):
		'''
		Follow the map to determine which setting(s) to alter and which values to consider.
		'''

		self.events.trigger('map-start')

		self._map_output = {
			'default_settings': self.default_simulation,
			'map': self._map,
			'evaluations': self._mapComponent(self._map)
		}

		self.events.trigger('map-end')

	def findStops(self, depth, *, get_index = False):
		'''
		Find where the stops of a given depth are verified in the current output.
		Return the settings defined until the given depth. Deeper settings are ignored.

		Parameters
		----------
		depth : int
			Depth to find the stops of.

		get_index : bool
			If `True`, the returned list's items are tuples and their second element is the index at which the settings have been found.

		Raises
		------
		ExplorerDepthNotFoundError
			The depth has not been found in the map.

		ExplorerStopNotFoundError
			There is no stop in the description of the given depth.

		Returns
		-------
		settings_with_stop : list
			Settings that led to the verified stop.
		'''

		if self._map_output is None:
			return None

		depths = self.map_depths

		if not(depth in depths):
			raise ExplorerDepthNotFoundError(depth)

		level = depths[depth]

		if not('stop' in level):
			raise ExplorerStopNotFoundError(depth)

		k_max = sum([len(l['settings']) for d, l in depths.items() if d < depth]) + len(level['settings'])

		settings_with_stop = []
		for i, evaluation in enumerate(self._map_output['evaluations']):
			try:
				stops = evaluation['stops']

			except KeyError:
				pass

			else:
				if list(filter(lambda stop: stop['depth'] == depth and stop['result'], stops)):
					settings = evaluation['settings'] if self._evaluation_mode == EvaluationMode.EACH else evaluation['settings'][0]
					settings_with_stop.append(settings[:k_max] if not(get_index) else (settings[:k_max],i))

		return settings_with_stop

	@property
	def searches(self):
		'''
		Get the iterations details of the latest searches.

		Returns
		--------
		searches : list
			Each item represent a search by a dictionary with the following keys:
				* `settings`: the settings of the upper levels,
				* `iterations`: the details of the iterations for this search.

			Each iteration is a dictionary with the following keys:
				* `interval`: the interval considered at this iteration,
				* `evaluations`: the evaluations values for the bounds of the interval.
		'''

		try:
			return self._searches

		except AttributeError:
			return None

	def _searchIteration(self, depth, interval, evaluations, tolerance, itermax):
		'''
		Iteration of the search.

		Parameters
		----------
		depth : int
			The depth to optimize.

		interval : tuple
			Lower and upper bounds of the current search interval.

		evaluations : tuple
			Values of the evaluations at the bounds of the interval.

		tolerance : float
			Length of the interval at which the precision is considered enough.

		itermax : int
			Maximal number of iterations if the tolerance is not reached.

		Returns
		--------
		interval : tuple
			The latest search interval.
		'''

		a, b = interval

		self._searches[-1]['iterations'].append({
			'interval': interval,
			'evaluations': evaluations
		})

		self.events.trigger('search-iteration')

		if abs(b - a) < tolerance or len(self._searches[-1]['iterations']) > itermax:
			return interval

		c = 0.5 * (a + b)

		level = self.map_depths[depth]
		level['values'] = [c]
		self.followMap()

		eval_c = self._map_output['evaluations'][-1]['evaluation']

		if self._checkStopCondition(level['stop'], [evaluations[0], eval_c]):
			return self._searchIteration(depth, (a, c), (evaluations[0], eval_c), tolerance, itermax)

		else:
			return self._searchIteration(depth, (c, b), (eval_c, evaluations[1]), tolerance, itermax)

	def search(self, depth, tolerance = 1E-5, itermax = 100):
		'''
		Search for the best value to verify a stop.
		There must be only one setting at the given depth, as the search is performed using a dichotomy algorithm.
		The stop must involve the last two evaluations.
		The initial values indicated in the map are used to define the search interval: the solution is assumed to be inside it.
		At first, all the initial values are used until the stop is verified.

		Parameters
		----------
		depth : int
			The depth at which the stop should be verified.

		tolerance : float
			Length of the interval at which the precision is considered enough.

		itermax : int
			Maximal number of iterations if the tolerance is not reached.

		Raises
		------
		ExplorerDepthNotFoundError
			The depth has not been found in the map.

		ExplorerStopNotFoundError
			There is no stop in the description of the given depth.

		ExplorerSearchNoSolutionError
			The stop has not been verified with the initial values.
		'''

		if self._map is None:
			return None

		depths = self.map_depths

		if not(depth in depths):
			raise ExplorerDepthNotFoundError(depth)

		level = depths[depth]

		if not('stop' in level):
			raise ExplorerStopNotFoundError(depth)

		if self._map_output is None:
			self.followMap()

		settings_with_stop = self.findStops(depth, get_index = True)

		if not(settings_with_stop):
			raise ExplorerSearchNoSolutionError()

		# Get the first setting combination that led to a stop
		# The stop has been verified at evaluation k
		# Then, the searched value is between evaluation k-1 and evaluation k
		# We also fix the previous settings to the values allowing a solution

		self.events.trigger('searches-start', len(settings_with_stop))

		self._searches = []
		initial_output = self._map_output

		depth_setting_k0 = len(settings_with_stop[0][0]) - 1

		for stopped, k in settings_with_stop:
			self.events.trigger('search-start')

			self._searches.append({
				'previous_settings': stopped[:-1],
				'iterations': []
			})

			a = (initial_output['evaluations'][k-1]['settings'] if self._evaluation_mode == EvaluationMode.EACH else initial_output['evaluations'][k-1]['settings'][-1])[depth_setting_k0]['value']
			b = (initial_output['evaluations'][k]['settings'] if self._evaluation_mode == EvaluationMode.EACH else initial_output['evaluations'][k]['settings'][-1])[depth_setting_k0]['value']

			i0 = 0
			for d in range(0, depth):
				values = [setting['value'] for setting in stopped[i0:i0+len(depths[d]['settings'])]]
				depths[d]['values'] = values if len(values) == 1 else [values]
				i0 += len(depths[d]['settings'])

			self._searchIteration(depth, (a, b), (initial_output['evaluations'][k-1]['evaluation'], initial_output['evaluations'][k]['evaluation']), tolerance, itermax)

			self.events.trigger('search-end')

		self.events.trigger('searches-end')

class ExplorerUI(MakerUI):
	'''
	UI to show the different steps of the Explorer.

	Parameters
	----------
	explorer : Explorer
		Instance of the Explorer from which the event are triggered.
	'''

	def __init__(self, explorer):
		super().__init__(explorer.maker)

		self._explorer = explorer

		self._explorer_state_line = None
		self._explorer_bar = None

		self._components_lines = {}
		self._components_bars = {}

		self._search_started = False

		self._explorer.events.addListener('stopped', self._stopped)
		self._explorer.events.addListener('map-start', self._mapStart)
		self._explorer.events.addListener('map-end', self._mapEnd)
		self._explorer.events.addListener('map-component-start', self._mapComponentStart)
		self._explorer.events.addListener('map-component-progress', self._mapComponentProgress)
		self._explorer.events.addListener('map-component-end', self._mapComponentEnd)
		self._explorer.events.addListener('searches-start', self._searchesStart)
		self._explorer.events.addListener('searches-end', self._searchesEnd)
		self._explorer.events.addListener('search-start', self._searchStart)
		self._explorer.events.addListener('search-iteration', self._searchIteration)
		self._explorer.events.addListener('search-end', self._searchEnd)

		self._explorer.maker.events.addListener('run-end', self._clearMakerState)

	def _updateExplorerState(self, state):
		'''
		Text line to display the current state of the Explorer.

		Parameters
		----------
		state : str
			State to display.
		'''

		if self._explorer_state_line is None:
			self._explorer_state_line = self.addTextLine(state, position = 0)

		else:
			self._explorer_state_line.text = state

	def _clearMakerState(self, *args, **kwargs):
		'''
		We don't need the Maker state anymore: we erase it.
		'''

		self._clearState()

	def clearState(self):
		'''
		Clear the Explorer state.
		'''

		if self._explorer_state_line is not None:
			self.removeItem(self._explorer_state_line)
			self._explorer_state_line = None

	def _stopped(self):
		'''
		A stop condition is verified.
		'''

		pass

	def _mapStart(self):
		'''
		The following of a map is started.
		'''

		if not(self._search_started):
			self._updateExplorerState('Following a map…')

	def _mapEnd(self):
		'''
		The following of a map has ended.
		'''

		if not(self._search_started):
			self._updateExplorerState('Map followed')

	def _mapComponentStart(self, depth, map_component, simulations_settings):
		'''
		The exploration of a new map component has begun.

		Parameters
		----------
		depth : int
			Depth of the component.

		map_component : dict
			Description of the component.

		simulations_settings : list
			Settings of the simulations in the component.
		'''

		if 'foreach' in map_component or self._explorer._evaluation_mode == EvaluationMode.EACH:
			offset = 1 if self._explorer_bar is None else 2
			self._components_lines[depth] = self.addTextLine(f'Component {depth}…', position = offset + 2*depth)
			self._components_bars[depth] = self.addProgressBar(len(simulations_settings), position = offset + 1 + 2*depth)

	def _mapComponentProgress(self, depth):
		'''
		The exploration of a new map component has progressed.

		Parameters
		----------
		depth : int
			Depth of the component.
		'''

		if depth in self._components_bars:
			self._components_bars[depth].counter += 1

	def _mapComponentEnd(self, depth, map_component, simulations_settings):
		'''
		The exploration of a map component has ended.

		Parameters
		----------
		depth : int
			Depth of the component.

		map_component : dict
			Description of the component.

		simulations_settings : list
			Settings of the simulations in the component.
		'''

		if depth in self._components_lines:
			self.removeItem(self._components_bars[depth])
			del self._components_bars[depth]

			self.removeItem(self._components_lines[depth])
			del self._components_lines[depth]

	def _searchesStart(self, n_searches):
		'''
		A search for a best value has begun.

		Parameters
		----------
		n_searches : int
			Number of searches that will be performed.
		'''

		self._search_started = True
		self._updateExplorerState('Searching for the best value…')

		if n_searches > 1:
			self._explorer_bar = self.addProgressBar(n_searches, position = 1)

	def _searchesEnd(self):
		'''
		A search for a best value has ended.
		'''

		self._updateExplorerState('Search finished')

		if self._explorer_bar is not None:
			self.removeItem(self._explorer_bar)
			self._explorer_bar = None

		self._search_started = False

	def _searchStart(self):
		'''
		A search for a best value has begun, with specific previous settings.
		'''

		pass

	def _searchIteration(self):
		'''
		An iteration in the search loop has begun.
		'''

		current_search = self._explorer.searches[-1]
		n_iterations = len(current_search['iterations'])
		interval = current_search['iterations'][-1]['interval']
		self._updateExplorerState(f'Iteration {n_iterations}, interval length: {abs(interval[1] - interval[0])}')

	def _searchEnd(self):
		'''
		A search for a best value has ended, with specific previous settings.
		'''

		if self._explorer_bar is not None:
			self._explorer_bar.counter += 1
