#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

def evaluate(simulation):
	with open(os.path.join(simulation['folder'], simulation.settings['output'][0]['y-file']), 'r') as f:
		values_sum = sum(map(float, f.readlines()[:-1]))

	return values_sum
