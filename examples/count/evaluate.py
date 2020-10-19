#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

def evaluate(simulation):
	with open(os.path.join(simulation['folder'], simulation.settings['output'][0]['file']), 'r') as f:
		numbers_sum = sum(map(int, f.readlines()))

	return numbers_sum
