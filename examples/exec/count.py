#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import time
import random

# time.sleep(random.random() * 4)

a = int(sys.argv[sys.argv.index('-from')+1])
b = int(sys.argv[sys.argv.index('-to')+1])
h = int(sys.argv[sys.argv.index('-step')+1])

joiner = '\n'
if '-spaces' in sys.argv:
	joiner = ' '

output = joiner.join(map(str, range(a, b, h)))

dir = sys.argv[sys.argv.index('-dir')+1]
os.makedirs(dir)

with open(os.path.join(dir, sys.argv[sys.argv.index('-file')+1]), 'w') as f:
	f.write(output)
