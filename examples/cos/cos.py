#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

from math import cos

a = float(sys.argv[sys.argv.index('-a')+1])
b = float(sys.argv[sys.argv.index('-b')+1])
n = int(sys.argv[sys.argv.index('-points')+1])

coef = float(sys.argv[sys.argv.index('-coef')+1])

h = (b - a) / (n - 1)
X = [a + k*h for k in range(0, n)]

Y = [cos(coef*x) for x in X]

dir = sys.argv[sys.argv.index('-dir')+1]
os.makedirs(dir)

try:
	with open(os.path.join(dir, sys.argv[sys.argv.index('-x-file')+1]), 'w') as f:
		f.write('\n'.join(map(str, X)))
except ValueError:
	pass

try:
	with open(os.path.join(dir, sys.argv[sys.argv.index('-y-file')+1]), 'w') as f:
		f.write('\n'.join(map(str, Y)))
except ValueError:
	pass
