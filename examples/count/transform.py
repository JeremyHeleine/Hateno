#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time

import os

def transform(simulation):
	with open(os.path.join(simulation['folder'], simulation.settings['output'][0]['file']), 'r') as f:
		numbers_sum = sum(map(int, f.readlines()))

	with open(os.path.join(simulation['folder'], 'sum.txt'), 'w') as f:
		f.write(str(numbers_sum))
