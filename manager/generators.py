#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
In this file, the default variables generators are defined.
A variable generator must admit two parameters and return the result corresponding to these two objects.
Behind the scenes, we use functools.reduce() to apply a generator to the list of objects.

Convention: prefix the name of the function by `generator_`.
'''

def time2seconds(t):
	'''
	Convert a time into a number of seconds.

	Parameters
	----------
	t : int|str
		Number of seconds or string formatted as a time.

	Returns
	-------
	seconds : int
		Total number of seconds.
	'''

	if type(t) is int:
		return t

	t_days = 0

	t_time_str = ''
	t_splitdays = t.split('-')

	try:
		t_time_str = t_splitdays[1]

	except IndexError:
		t_time_str = t_splitdays[0]

	else:
		t_days = int(t_splitdays[0])

	t_time = list(map(int, t_time_str.split(':')))
	t_time += [0] * (3 - len(t_time))

	return 86400 * t_days + 3600 * t_time[0] + 60 * t_time[1] + t_time[2]

def seconds2time(s):
	'''
	Convert a number of seconds into a time string.

	Parameters
	----------
	s : int
		Number of seconds.

	Returns
	-------
	t : str
		String: `D-HH:MM:SS`.
	'''

	decomposition = [s // q % m for m, q in [(60, 1), (60, 60), (24, 3600), (s, 86400)]]
	decomposition.reverse()

	t = ''
	if decomposition[0] > 0:
		t = f'{decomposition[0]}-'

	t += ':'.join(map(lambda d: str(d).zfill(2), decomposition[1:]))

	return t

def generator_sum(a, b):
	'''
	Generate the sum of settings.
	'''

	return a + b

def generator_sumTime(a, b):
	'''
	Generate the sum of two times. The output is a time formatted as `D-HH:MM:SS`. Input can be:
	- a `[D-]HH:MM[:SS]` string,
	- an integer (will be interpreted as a number of seconds).
	'''

	return seconds2time(time2seconds(a) + time2seconds(b))

def generator_first(a, b):
	'''
	Get the first element.
	'''

	return a
