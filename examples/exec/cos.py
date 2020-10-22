#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

from math import factorial

a = float(sys.argv[sys.argv.index('-a')+1])
b = float(sys.argv[sys.argv.index('-b')+1])
n = int(sys.argv[sys.argv.index('-points')+1])

coef = float(sys.argv[sys.argv.index('-coef')+1])
N = int(sys.argv[sys.argv.index('-N')+1])

h = (b - a) / (n - 1)
X = [a + k*h for k in range(0, n)]

Y = [
	sum([(-1)**i * coef**(2*i) * x**(2*i) / factorial(2*i) for i in range(0, N)])
	for x in X
]

dir = sys.argv[sys.argv.index('-dir')+1]
os.makedirs(dir)

with open(os.path.join(dir, sys.argv[sys.argv.index('-x-file')+1]), 'w') as f:
	f.write('\n'.join(map(str, X)))

with open(os.path.join(dir, sys.argv[sys.argv.index('-y-file')+1]), 'w') as f:
	f.write('\n'.join(map(str, Y)))
