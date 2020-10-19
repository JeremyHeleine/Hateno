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

		self.events = Events(['test-values-start', 'test-values-evaluation-start', 'test-values-evaluation-progress', 'test-values-evaluation-end', 'test-values-end'])

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

	def testValues(self, setting, evaluation):
		'''
		Evaluate the simulations corresponding to a given list of values for a parameter.

		Parameters
		----------
		setting : dict
			Description of the setting to test. Must contain at least three keys:
				* `set`: the name of the set the setting belongs to,
				* `setting`: the name of the setting,
				* `values`: the list of values to test.
			The following key is optional:
				* `set_index`: the index of the set where the setting should be looked for, default to 0.

		evaluation : function
			Function used to evaluate a simulation.

		Returns
		-------
		output : list
			Output of the evaluation. Each item is a dict giving access to the evaluation value and to the corresponding Simulation object.
		'''

		if not('set_index' in setting):
			setting['set_index'] = 0

		self.events.trigger('test-values-start', setting)

		simulations_dir = tempfile.mkdtemp(prefix = 'hateno-explorer_')

		simulations = []
		for k, value in enumerate(setting['values']):
			simulation = copy.deepcopy(self._default_simulation)

			simulation['folder'] = os.path.join(simulations_dir, str(k))
			simulation.raw_settings[setting['set']][setting['set_index']][setting['setting']].value = value

			simulations.append(simulation)

		self.maker.run(simulations)

		self.events.trigger('test-values-evaluation-start', simulations)

		output = []
		for simulation in simulations:
			output.append({
				'simulation': simulation,
				'value': simulation.raw_settings[setting['set']][setting['set_index']][setting['setting']].value,
				'evaluation': evaluation(simulation)
			})

			self.events.trigger('test-values-evaluation-progress')

		self.events.trigger('test-values-evaluation-end')

		# shutil.rmtree(simulations_dir)

		self.events.trigger('test-values-end', setting)

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

		self._explorer.events.addListener('test-values-start', self._testValuesStart)
		self._explorer.events.addListener('test-values-evaluation-start', self._testValuesEvaluationStart)
		self._explorer.events.addListener('test-values-evaluation-progress', self._testValuesEvaluationProgress)
		self._explorer.events.addListener('test-values-evaluation-end', self._testValuesEvaluationEnd)
		self._explorer.events.addListener('test-values-end', self._testValuesEnd)

	def _testValuesStart(self, setting):
		'''
		Explicit test of given values started.

		Parameters
		----------
		setting : dict
			Description of the tested setting and its values.
		'''

		pass

	def _testValuesEvaluationStart(self, simulations):
		'''
		Evaluation of some simulations.

		Parameters
		----------
		simulations : list
			The simulations that will be evaluated.
		'''

		self._updateState('Evaluating the simulations…')
		self._main_progress_bar = self.addProgressBar(len(simulations))

	def _testValuesEvaluationProgress(self):
		'''
		A simulation has just been evaluated.
		'''

		self._main_progress_bar.counter += 1

	def _testValuesEvaluationEnd(self):
		'''
		All simulations have been evaluated.
		'''

		self.removeItem(self._main_progress_bar)
		self._main_progress_bar = None
		self._updateState('Simulations evaluated')

	def _testValuesEnd(self, setting):
		'''
		Explicit test of given values ended.

		Parameters
		----------
		setting : dict
			Description of the tested setting and its values.
		'''

		self._updateState(string.plural(len(setting['values']), 'value tested', 'values tested'))
