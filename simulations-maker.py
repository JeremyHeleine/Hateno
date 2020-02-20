#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
This script uses the Maker class to extract/generate simulations.
'''

import argparse

from utils import jsonfiles
from manager.maker import Maker

parser = argparse.ArgumentParser(description = 'Extract, and generate if needed, some simulations.')

parser.add_argument('--settings', type = argparse.FileType('r'), required = True, help = 'path to the file where the maker settings are stored')
parser.add_argument('--save-unknown', type = str, help = 'path to the file where simulations that failed to be generated must be stored')
parser.add_argument('folder_path', type = str, help = 'path to the simulations folder')
parser.add_argument('simulations_list', type = argparse.FileType('r'), help = 'path to the file where the simulations list can be found')

args = parser.parse_args()

settings = jsonfiles.read(args.settings.name)
maker_settings = {'ui': True}

try:
	maker_settings.update(settings['settings'])

except KeyError:
	pass

try:
	maker_settings['mail_config'] = settings['mail']['mailbox']
	maker_settings['mail_notifications_config'] = settings['mail']['notifications']

except KeyError:
	pass

simulations = jsonfiles.read(args.simulations_list.name, allow_generator = True)

maker = Maker(args.folder_path, settings['remote_folder'], **maker_settings)
unknown_simulations = maker.run(simulations, settings['generator_recipe'])

if unknown_simulations and args.save_unknown:
	jsonfiles.write(unknown_simulations, args.save_unknown)

maker.close()
