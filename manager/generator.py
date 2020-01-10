#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
from string import Template

from manager.folder import Folder
from manager.errors import *

class Generator(Folder):
	'''
	Generate some scripts to create a set of simulations.
	Initialize the list of simulations to generate.

	Parameters
	----------
	folder : str
		The folder to manage. Must contain a settings file.
	'''

	def __init__(self, folder):
		super().__init__(folder)

		self._simulations_to_generate = []

	def add(self, simulations):
		'''
		Add simulations to generate.

		Parameters
		----------
		simulations : list|dict
			List of simulations to add.
		'''

		if type(simulations) is dict:
			self._simulations_to_generate.append(simulations)

		else:
			self._simulations_to_generate += simulations

	def clear(self):
		'''
		Clear the list of simulations to generate.
		'''

		self._simulations_to_generate.clear()

	def parse(self):
		'''
		Parse the current list of simulations to generate the corresponding command lines.

		Returns
		-------
		command_lines : list
			List of command lines, one per simulation to generate
		'''

		return [
			' '.join([self._settings['exec']] + sum(self.generateSettings(simulation['settings'], as_strings = True), []))
			for simulation in self._simulations_to_generate
		]

	def generateScriptFromSkeleton(self, skeleton_name, output_name, lists, variables):
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
		'''

		with open(skeleton_name, 'r') as f:
			skeleton = f.read()

		script_content = ''
		k0 = 0

		for match in re.finditer(r'^[ \t]*#{3} BEGIN_(?P<tag>[A-Z_]+) #{3}$.+?^(?P<content>.+?)^[ \t]*#{3} END_\1 #{3}$.+?^', skeleton, flags = re.MULTILINE | re.DOTALL):
			if match.group('tag') in lists:
				script_content += skeleton[k0:match.start()]

				loop_content_template = Template(match.group('content'))
				for index, value in enumerate(lists[match.group('tag')]):
					script_content += loop_content_template.safe_substitute(ITEM_INDEX = index, ITEM_VALUE = value)

				k0 = match.end()

		script_content += skeleton[k0:]

		script_content = Template(script_content).safe_substitute(**variables)

		with open(output_name, 'w') as f:
			f.write(script_content)

	def generate(self, dest_folder, *, max_simulations = 0, subgroups_skeletons = [], wholegroup_skeletons = []):
		'''
		Generate the scripts to launch the simulations by subgroups.

		Parameters
		----------
		dest_folder : str
			Destination folder where scripts should be stored.

		max_simulations : int
			Maximum number of simulations in each subgroup. If 0, only one subgroup is created.

		subgroups_skeletons : list
			Names of the skeletons to use for each subgroup.

		subgroups_skeletons : list
			Names of the skeletons to use for each subgroup.

		Raises
		------
		EmptyListError
			The list of simulations to generate is empty.

		DestinationFolderExistsError
			The destination folder already exists.
		'''

		if not(self._simulations_to_generate):
			raise EmptyListError()

		if os.path.isdir(dest_folder):
			raise DestinationFolderExistsError()

		os.makedirs(dest_folder)

		command_lines = self.parse()

		if max_simulations <= 0:
			max_simulations = len(command_lines)

		command_lines_sets = [command_lines[k:k+max_simulations] for k in range(0, len(command_lines), max_simulations)]

		data_lists = {}
		data_variables = {}

		skeletons_calls = [
			{
				'command_lines': command_lines_set,
				'skeleton_name_joiner': f'-{k}.',
				'skeletons': subgroups_skeletons
			}
			for k, command_lines_set in enumerate(command_lines_sets)
		]

		skeletons_calls.append({
			'command_lines': command_lines,
			'skeleton_name_joiner': '.',
			'skeletons': wholegroup_skeletons
		})

		for skeletons_call in skeletons_calls:
			data_lists['COMMAND_LINES'] = skeletons_call['command_lines']

			for skeleton_name in skeletons_call['skeletons']:
				skeleton_basename_parts = os.path.basename(skeleton_name).rsplit('.skeleton.', maxsplit = 1)
				skeleton_tag = re.sub('[^A-Z_]+', '_', skeleton_basename_parts[0].upper())
				script_name = os.path.join(dest_folder, skeletons_call['skeleton_name_joiner'].join(skeleton_basename_parts))

				self.generateScriptFromSkeleton(skeleton_name, script_name, data_lists, data_variables)
				data_variables[skeleton_tag] = script_name

				try:
					data_lists[skeleton_tag].append(script_name)

				except KeyError:
					data_lists[skeleton_tag] = [script_name]
