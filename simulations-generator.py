#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
This script uses the Generator class to generate the scripts corresponding to some simulations.
'''

import argparse

from utils import jsonfiles
from manager.folder import Folder
from manager.generator import Generator
from manager.errors import *

parser = argparse.ArgumentParser(description = 'Generate command lines and scripts to create simulations.')

parser.add_argument('--recipe', type = argparse.FileType('r'), help = 'path to the file where the generator recipe can be found')
parser.add_argument('--output-dir', type = str, help = 'folder to create')
parser.add_argument('--empty-output', action = 'store_true', help = 'ensure the output directory is empty')
parser.add_argument('folder_path', type = str, help = 'path to the simulations folder')
parser.add_argument('simulations_list', type = argparse.FileType('r'), help = 'path to the file where the simulations list can be found')

args = parser.parse_args()

folder = Folder(args.folder_path)
generator = Generator(folder)

simulations = jsonfiles.read(args.simulations_list.name, allow_generator = True)
generator.add(simulations)

if args.recipe is None or args.output_dir is None:
	print('\n'.join(generator.parse()['data_lists']['COMMAND_LINES']))
	exit()

recipe = jsonfiles.read(args.recipe.name)

try:
	generator.generate(args.output_dir, recipe, empty_dest = args.empty_output)

except DestinationFolderExistsError:
	print('The output directory already exists.')
