#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil
import copy
import tempfile

from . import string
from .folder import Folder
from .simulation import Simulation
from .maker import Maker, MakerUI
from .events import Events

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

		self.events = Events(['generate-start', 'generate-end', 'evaluate-each-start', 'evaluate-each-progress', 'evaluate-each-end', 'test-values-start', 'test-values-end'])

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

		return self._default_simulation

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
		simulations_settings : dict
			Description of the setting to alter. Must contain the following keys:
				* `setting`: a dict describing the setting (see `Simulation.getSetting()`),
				* `values`: the values of the setting.
		'''

		self._simulations_dir = tempfile.mkdtemp(prefix = 'hateno-explorer_')

		self._simulations = []
		for k, value in enumerate(simulations_settings['values']):
			simulation = copy.deepcopy(self._default_simulation)

			simulation['folder'] = os.path.join(self._simulations_dir, str(k))
			simulation.getSetting(simulations_settings['setting']).value = value

			self._simulations.append(simulation)

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
		self._simulations = None

	def _evaluateEach(self):
		'''
		Call the evaluation function on each simulation of the current set.

		Returns
		-------
		output : list
			Result of the evaluation of each simulation.
		'''

		self.events.trigger('evaluate-each-start', self._simulations)

		output = []
		for simulation in self._simulations:
			output.append(self._evaluation(simulation))
			self.events.trigger('evaluate-each-progress')

		self.events.trigger('evaluate-each-end', self._simulations)

		return output

	def testValues(self, setting, values, evaluation):
		'''
		Evaluate the simulations corresponding to a given list of values for a parameter.

		Parameters
		----------
		setting : dict
			Description of the setting to test. See `Simulation.getSetting()`.

		values : list
			The values to test.

		evaluation : function
			Function used to evaluate a simulation.

		Returns
		-------
		output : list
			Output of the evaluation. Each item is a dict with the following keys:
				* `simulation`: the considered Simulation object,
				* `evaluation`: the result of the evaluation function for this simulation.
		'''

		self.events.trigger('test-values-start', setting, values)

		self._setSimulations({'setting': setting, 'values': values})
		self._evaluation = evaluation

		self._generateSimulations()
		evaluation_result = self._evaluateEach()
		output = [dict(zip(['simulation', 'evaluation'], sim_eval)) for sim_eval in zip(self._simulations, evaluation_result)]
		self._deleteSimulations()

		self.events.trigger('test-values-end', setting, values)

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
		self._explorer.events.addListener('test-values-start', self._testValuesStart)
		self._explorer.events.addListener('test-values-end', self._testValuesEnd)

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

	def _testValuesStart(self, setting, values):
		'''
		Explicit test of given values started.

		Parameters
		----------
		setting : dict
			Description of the tested setting.

		values : list
			The tested values.
		'''

		pass

	def _testValuesEnd(self, setting, values):
		'''
		Explicit test of given values ended.

		Parameters
		----------
		setting : dict
			Description of the tested setting.

		values : list
			The tested values.
		'''

		self._updateState(string.plural(len(values), 'value tested', 'values tested'))
