#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil
import stat
import re
import functools
import copy
from math import ceil
from string import Template

from . import string, jsonfiles
from .errors import *
from .fcollection import FCollection
from .folder import Folder
from .simulation import Simulation
from . import generators as default_generators

class Generator():
	'''
	Generate some scripts to create a set of simulations.
	Initialize the list of simulations to generate.

	Parameters
	----------
	folder : Folder|str
		The folder to manage. Either a `Folder` instance or the path to the folder (used to create a `Folder` instance).
	'''

	def __init__(self, folder):
		self._folder = folder if type(folder) is Folder else Folder(folder)

		self._simulations_to_generate = []

		self._lists_regex_compiled = None
		self._lists_items_regex_compiled = None

		self._variables_generators = None

	@property
	def folder(self):
		'''
		Return the `Folder` instance.

		Returns
		-------
		folder : Folder
			The instance used by the generator.
		'''

		return self._folder

	@property
	def _lists_regex(self):
		'''
		Regex to detect the presence of lists blocks in a skeleton.

		Returns
		-------
		regex : re.Pattern
			The lists regex.
		'''

		if self._lists_regex_compiled is None:
			self._lists_regex_compiled = re.compile(r'^[ \t]*#{3} BEGIN_(?P<tag>[A-Z_]+) #{3}$.+?^(?P<content>.+?)^[ \t]*#{3} END_\1 #{3}$.+?^', flags = re.MULTILINE | re.DOTALL)

		return self._lists_regex_compiled

	@property
	def _lists_items_regex(self):
		'''
		Regex to detect the presence of lists items as variables names.

		Returns
		-------
		regex : re.Pattern
			The lists items regex.
		'''

		if self._lists_items_regex_compiled is None:
			self._lists_items_regex_compiled = re.compile(r'^(?P<list>[A-Z_]+)__(?P<index>[0-9]+)$')

		return self._lists_items_regex_compiled

	@property
	def variables_generators(self):
		'''
		Get the list of available variables generators.

		Returns
		-------
		generators : FCollection
			The collection of generators.
		'''

		if self._variables_generators is None:
			self._variables_generators = FCollection(filter_regex = r'^generator_(?P<name>[A-Za-z0-9_]+)$')
			self._variables_generators.loadFromModule(default_generators)

		return self._variables_generators

	def add(self, simulations):
		'''
		Add simulations to generate.

		Parameters
		----------
		simulations : list|dict|Simulation
			List of simulations to add.
		'''

		if type(simulations) is list:
			for simulation in simulations:
				self._simulations_to_generate.append(Simulation.ensureType(simulation, self._folder))

		else:
			self.add([simulations])

	def clear(self):
		'''
		Clear the list of simulations to generate.
		'''

		self._simulations_to_generate.clear()

	def parse(self, simulations_set = None):
		'''
		Parse a set of simulations to generate the corresponding command lines and other variables.

		Parameters
		----------
		simulations_set : list
			The set of simulations to parse. If `None`, default to the whole list.

		Returns
		-------
		variables : dict
			The list of command lines, and variables corresponding to the simulations' global settings.
		'''

		if simulations_set is None:
			simulations_set = self._simulations_to_generate

		command_lines = [simulation.command_line for simulation in simulations_set]

		globalsettings = self._folder.settings['globalsettings']

		variables = {
			'data_lists': {'COMMAND_LINES': command_lines},
			'data_variables': {'COMMAND_LINES_LENGTH': len(command_lines)}
		}

		for globalsetting in self._folder.settings['globalsettings']:
			name_upper = 'GLOBALSETTING_'+globalsetting['name'].upper()
			variables['data_lists'][name_upper] = [simulation[globalsetting['name']] for simulation in simulations_set]

			if 'generators' in globalsetting:
				for generator_name in globalsetting['generators']:
					try:
						generator = self.variables_generators.get(generator_name)

					except FCollectionFunctionNotFoundError:
						raise VariableGeneratorNotFoundError(generator_name)

					else:
						variables['data_variables'][generator_name.upper()+'_'+name_upper] = functools.reduce(generator, variables['data_lists'][name_upper])

		return variables

	def generateScriptFromSkeleton(self, skeleton_name, output_name, lists, variables, *, make_executable = True):
		'''
		Generate a script from a skeleton, using a given set of command lines.

		Parameters
		----------
		skeleton_name : str
			Name of the skeleton file.

		output_name : str
			Name of the script to write.

		lists : dict
			Lists we can use to loop through.

		variables : dict
			Variables we can use in the whole script template.

		make_executable : boolean
			`True` to add the 'exec' permission to the script.
		'''

		with open(skeleton_name, 'r') as f:
			skeleton = f.read()

		def replaceListBlock(match):
			'''
			Replace a list block by the content of the right list.
			To be called by `re.sub()`.

			Parameters
			----------
			match : re.Match
				Match object corresponding to a list block.

			Returns
			-------
			list_content : str
				The content of the list, formatted as asked.
			'''

			try:
				list_content = ''
				loop_content_template = Template(match.group('content'))

				for index, value in enumerate(lists[match.group('tag')]):
					list_content += loop_content_template.safe_substitute(ITEM_INDEX = index, ITEM_VALUE = value)

				return list_content

			except KeyError:
				return match.group(0)

		script_content = self._lists_regex.sub(replaceListBlock, skeleton)

		variables = copy.deepcopy(variables)
		script_content_template = Template(script_content)

		for match in script_content_template.pattern.finditer(script_content_template.template):
			if match.group('braced'):
				submatch = self._lists_items_regex.match(match.group('braced'))

				if submatch:
					variables[submatch.group(0)] = lists[submatch.group('list')][int(submatch.group('index'))]

		script_content = script_content_template.safe_substitute(**variables)

		with open(output_name, 'w') as f:
			f.write(script_content)

		if make_executable:
			os.chmod(output_name, os.stat(output_name).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

	def _createDestinationFolder(self, dest_folder, *, empty_dest = False):
		'''
		Create the folder where the scripts will be stored.

		Parameters
		----------
		dest_folder : str
			Destination folder where scripts should be stored.

		empty_dest : boolean
			If `True` and if the destination folder already exists, empty it before generating the scripts. If `False` the existence of the folder raises an error.

		Raises
		------
		DestinationFolderExistsError
			The destination folder already exists.
		'''

		if os.path.isdir(dest_folder):
			if empty_dest:
				for entry in [os.path.join(dest_folder, e) for e in os.listdir(dest_folder)]:
					(shutil.rmtree if os.path.isdir(entry) else os.unlink)(entry)

			else:
				raise DestinationFolderExistsError()

		else:
			os.makedirs(dest_folder)

	def _loadRecipe(self, config_name = None):
		'''
		Load the recipe to use to generate the scripts.

		Parameters
		----------
		config_name : str
			Name of the config folder where `generator.json` will be found.
		'''

		self._recipe = self._folder.config('generator', config_name)

	def _splitSimulationsList(self):
		'''
		Split the simulations list into subgroups, according to the recipe.

		Returns
		-------
		subgroups : list
			The subgroups of simulations.
		'''

		simulations_per_group = len(self._simulations_to_generate)

		if 'max_simulations' in self._recipe:
			if self._recipe['max_simulations'] > 0:
				simulations_per_group = self._recipe['max_simulations']

			if 'max_subgroups' in self._recipe and len(self._simulations_to_generate) / simulations_per_group > self._recipe['max_subgroups']:
				simulations_per_group = ceil(len(self._simulations_to_generate) / self._recipe['max_subgroups'])

		elif 'max_subgroups' in self._recipe:
			simulations_per_group = ceil(len(self._simulations_to_generate) / self._recipe['max_subgroups'])

		return [self._simulations_to_generate[k:k+simulations_per_group] for k in range(0, len(self._simulations_to_generate), simulations_per_group)]

	def _dataVariables(self):
		'''
		Use the recipe to define the data variables and lists.

		Returns
		-------
		variables : tuple
			A tuple with (in this order) the data variables, and the data lists.
		'''

		data_variables = {}
		data_lists = {}

		if 'data_lists' in self._recipe:
			data_lists.update(self._recipe['data_lists'])

		if 'data_variables' in self._recipe:
			data_variables.update(self._recipe['data_variables'])

		return (data_variables, data_lists)

	def _scriptToLaunch(self, generated_scripts, skeletons):
		'''
		Use the recipe to determine which generated should be called to launch the whole thing.

		Parameters
		----------
		generated_scripts : list
			The list of generated scripts where the one to launch will be picked.

		skeletons : list
			Full list of skeletons.

		Returns
		-------
		script_to_launch : str
			The path to the script to launch.
		'''

		script_to_launch = self._folder.skeletons(self._recipe['skeletons'])['script_to_launch']

		possible_skeletons_to_launch = [
			k
			for k, s in enumerate(skeletons)
			if s == script_to_launch['name']
		]

		return generated_scripts[possible_skeletons_to_launch[script_to_launch['coords'][0]]][script_to_launch['coords'][1]]['finalpath']

	def generate(self, dest_folder, config_name = None, *, empty_dest = False, basedir = None):
		'''
		Generate the scripts to launch the simulations by subgroups.

		Parameters
		----------
		dest_folder : str
			Destination folder where scripts should be stored.

		config_name : str
			Name of the config to use.

		empty_dest : boolean
			If `True` and if the destination folder already exists, empty it before generating the scripts. If `False` the existence of the folder raises an error.

		basedir : str
			Path to the "final" directory from which the scripts will be executed.

		Raises
		------
		EmptyListError
			The list of simulations to generate is empty.

		Returns
		-------
		generated_scripts, script_to_launch : tuple
			List of generated scripts, separated: one list per skeleton, in the order they are called. Second output is the "final" path of the script to launch.
		'''

		if not(self._simulations_to_generate):
			raise EmptyListError()

		self._createDestinationFolder(dest_folder, empty_dest = empty_dest)

		self._loadRecipe(config_name)
		simulations_sets = self._splitSimulationsList()
		data_variables, data_lists = self._dataVariables()
		skeletons = self._folder.skeletons(self._recipe['skeletons'])

		skeletons_calls = []
		generated_scripts = [[]] * (len(skeletons['subgroups']) + len(skeletons['wholegroup']))

		jobs_ids = [f'job-{k}' for k in range(0, len(simulations_sets))]

		skeletons_calls += [
			{
				'skeleton_name_joiner': f'-{k}.',
				'skeletons': enumerate(skeletons['subgroups']),
				'job_id': jobs_ids[k],
				'jobs_ids': jobs_ids,
				**self.parse(simulations_set)
			}
			for k, simulations_set in enumerate(simulations_sets)
		]

		skeletons_calls.append({
			'skeleton_name_joiner': '.',
			'skeletons': [(len(skeletons['subgroups']) + j, s) for j, s in enumerate(skeletons['wholegroup'])],
			'job_id': '',
			'jobs_ids': jobs_ids,
			**self.parse()
		})

		scripts_basedir = basedir or dest_folder

		for skeletons_call in skeletons_calls:
			data_lists.update(skeletons_call['data_lists'])
			data_variables.update(skeletons_call['data_variables'])

			data_variables['JOB_ID'] = skeletons_call['job_id']
			data_lists['JOBS_IDS'] = skeletons_call['jobs_ids']

			if 'data_variables_cases' in self._recipe:
				for varname, varparams in self._recipe['data_variables_cases'].items():
					vartest = data_variables[varparams['variable']]
					data_variables[varname] = [value for bound, value in zip(varparams['bounds'], varparams['values']) if bound <= vartest][-1]

			for j, skeleton_name in skeletons_call['skeletons']:
				skeleton_basename_parts = os.path.basename(skeleton_name).rsplit('.skeleton.', maxsplit = 1)
				skeleton_tag = re.sub('[^A-Z_]+', '_', skeleton_basename_parts[0].upper())
				script_name = skeletons_call['skeleton_name_joiner'].join(skeleton_basename_parts)
				script_localpath = os.path.join(dest_folder, script_name)
				script_finalpath = os.path.join(scripts_basedir, script_name)

				self.generateScriptFromSkeleton(skeleton_name, script_localpath, data_lists, data_variables)
				data_variables[skeleton_tag] = script_finalpath

				try:
					data_lists[skeleton_tag].append(script_finalpath)

				except KeyError:
					data_lists[skeleton_tag] = [script_finalpath]

				generated_scripts[j].append({'name': script_name, 'localpath': script_localpath, 'finalpath': script_finalpath})

		return (generated_scripts, self._scriptToLaunch(generated_scripts, skeletons['subgroups'] + skeletons['wholegroup']))
