#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import enum
import os
import shutil
import copy
import tempfile

from . import string
from .folder import Folder
from .simulation import Simulation
from .maker import Maker, MakerUI
from .events import Events

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

		self._simulations_dir = None
		self._simulations = None

		self._evaluation = None

		self.events = Events(['evaluate-each-start', 'evaluate-each-progress', 'evaluate-each-end', 'evaluate-group-start', 'evaluate-group-end', 'map-start', 'map-end'])

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

	def _generateSimulations(self):
		'''
		Generate the current set of simulations.
		'''

		self.maker.run(self._simulations)

	def _deleteSimulations(self):
		'''
		Delete the current set of simulations.
		'''

		shutil.rmtree(self._simulations_dir)
		self._simulations_dir = None
		self._simulations = None

	def _evaluateEach(self):
		'''
		Call the evaluation function on each simulation of the current set.

		Returns
		-------
		output : list
			Result of the evaluation of each simulation. Each item is a dictionary with keys:
				* `settings`: the altered settings of the simulation,
				* `evaluation`: the result of the evaluation of the simulation.
		'''

		self.events.trigger('evaluate-each-start', self._simulations)

		output = []
		for simulation, settings in zip(self._simulations, self._simulations_settings):
			output.append({
				'settings': settings,
				'evaluation': self._evaluation(simulation)
			})
			self.events.trigger('evaluate-each-progress')

		self.events.trigger('evaluate-each-end', self._simulations)

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

		self.events.trigger('evaluate-group-start', self._simulations)

		evaluation = self._evaluation(self._simulations)

		self.events.trigger('evaluate-group-end', self._simulations)

		return {
			'settings': self._simulations_settings,
			'evaluation': evaluation
		}

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

		if 'setting' in map_component:
			if not('settings' in map_component):
				map_component['settings'] = map_component['setting']

			del map_component['setting']

		if not(type(map_component['settings']) is list):
			map_component['settings'] = [map_component['settings']]

		return [
			[
				{'set_index': 0, **coords, 'value': value}
				for coords, value in zip(map_component['settings'], values if type(values) is list else [values])
			] + additional_settings
			for values in map_component['values']
		]

	def _mapComponent(self, map_component, current_settings = []):
		'''
		Interpret a component of a map.

		Parameters
		----------
		map_component : dict
			The component to interpret.

		current_settings : list
			List of settings to alter (that are not listed in this component), with their values.

		Returns
		-------
		result : list
			A list of dict, each one corresponding to a simulation generated by the component. Each dict contains the keys:
				* `settings`: the list of altered settings,
				* `evaluation`: the result of the evaluation function on this simulation.
		'''

		simulations_settings = self._buildSettings(map_component, current_settings)

		if 'foreach' in map_component:
			return sum([
				self._mapComponent(map_component['foreach'], settings)
				for settings in simulations_settings
			], [])

		self._setSimulations(simulations_settings)
		self._generateSimulations()

		if self._evaluation_mode == EvaluationMode.EACH:
			output = self._evaluateEach()

		elif self._evaluation_mode == EvaluationMode.GROUP:
			output = [self._evaluateGroup()]

		self._deleteSimulations()

		return output

	def useMap(self, map_description, evaluation, *, evaluation_mode = EvaluationMode.EACH):
		'''
		Follow a map to determine which setting(s) to alter and which values to consider.

		Parameters
		----------
		map_description : dict
			Description of the path to follow.

		evaluation : function
			Function used to evaluate the simulations.

		evaluation_mode : EvaluationMode
			Evaluation mode (one by one, or grouped).

		Returns
		-------
		output : dict
			Output of the evaluations and tests described in the map.
		'''

		self.events.trigger('map-start', map_description)

		self._evaluation = evaluation
		self._evaluation_mode = evaluation_mode

		output = {
			'default_settings': self.default_simulation,
			'map': map_description,
			'evaluations': self._mapComponent(map_description)
		}

		self.events.trigger('map-end', map_description)

		return output

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

		self._explorer.events.addListener('evaluate-each-start', self._evaluateEachStart)
		self._explorer.events.addListener('evaluate-each-progress', self._evaluateEachProgress)
		self._explorer.events.addListener('evaluate-each-end', self._evaluateEachEnd)
		self._explorer.events.addListener('evaluate-group-start', self._evaluateGroupStart)
		self._explorer.events.addListener('evaluate-group-end', self._evaluateGroupEnd)
		self._explorer.events.addListener('map-start', self._mapStart)
		self._explorer.events.addListener('map-end', self._mapEnd)

	def _evaluateEachStart(self, simulations):
		'''
		Evaluation of each simulation.

		Parameters
		----------
		simulations : list
			The simulations that will be evaluated.
		'''

		self._updateState('Evaluating the simulations…')
		self._main_progress_bar = self.addProgressBar(len(simulations))

	def _evaluateEachProgress(self):
		'''
		A simulation has just been evaluated.
		'''

		self._main_progress_bar.counter += 1

	def _evaluateEachEnd(self, simulations):
		'''
		All simulations have been evaluated.

		Parameters
		----------
		simulations : list
			The simulations that have been evaluated.
		'''

		self.removeItem(self._main_progress_bar)
		self._main_progress_bar = None
		self._updateState('Simulations evaluated')

	def _evaluateGroupStart(self, simulations):
		'''
		Evaluation of a group of simulations.

		Parameters
		----------
		simulations : list
			The simulations that will be evaluated.
		'''

		self._updateState('Evaluating the simulations…')

	def _evaluateGroupEnd(self, simulations):
		'''
		The group of simulations have been evaluated.

		Parameters
		----------
		simulations : list
			The simulations that have been evaluated.
		'''

		self._updateState('Simulations evaluated')

	def _mapStart(self, map_description):
		'''
		The following of a map is started.

		Parameters
		----------
		map_description : dict
			Map that will be followed.
		'''

		pass

	def _mapEnd(self, map_description):
		'''
		The following of a map has ended.

		Parameters
		----------
		map_description : dict
			Map that has been followed.
		'''

		pass
