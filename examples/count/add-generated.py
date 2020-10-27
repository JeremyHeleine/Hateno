#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def generate(n = 1):
	n = int(n)

	return [
		{
			'folder': f'test/{k}',
			'settings': {
				'range': {
					'from': 10*k,
					'to': 10*(k+1)
				}
			}
		}
		for k in range(0, 10, n)
	]
