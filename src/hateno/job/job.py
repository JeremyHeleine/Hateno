#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime
import os
import shlex
import subprocess
import time

from ..utils import LockedFile, jsonfiles, string

class Job():
	'''
	Represent a job to execute a set of command lines.

	Parameters
	----------
	command_lines_filename : str
		Path to the file listing the command lines to execute.

	job_dir : str
		Path to the job directory where the logs are stored.

	poll_delay : float
		Time (in seconds) to wait between each process polling.
	'''

	def __init__(self, command_lines_filename, job_dir, *, poll_delay = 0.1):
		self._command_lines_filename = command_lines_filename

		self._job_dir = job_dir
		self._counter_filename = os.path.join(self._job_dir, 'counter')

		self._log = []

		self._poll_delay = poll_delay

	def __enter__(self):
		'''
		Context manager to automatically call `start()` and `stop()`.
		'''

		self.start()
		return self

	def __exit__(self, *args, **kwargs):
		'''
		Call `stop()` when exiting a context manager.
		'''

		self.stop()

	def start(self):
		'''
		Create the log file and open the command lines file.
		'''

		self._createJobDir()

		self._client_id = string.uniqueID()
		self._client_filename = os.path.join(self._job_dir, f'{self._client_id}.json')
		self._state_filename = os.path.join(self._job_dir, f'{self._client_id}.state')

		self._kill_filename = os.path.join(self._job_dir, f'{self._client_id}.kill')
		self._killall_filename = os.path.join(self._job_dir, 'kill')

		self._alive()

		self._command_lines_file = open(self._command_lines_filename, 'r')
		self._command_lines = (row.strip() for row in self._command_lines_file)
		self._counter = -1

	def stop(self):
		'''
		Close the command lines file.
		'''

		self._command_lines_file.close()

	def _createJobDir(self):
		'''
		Create the job directory if it does not exist yet. Then, create the counter file.
		'''

		try:
			os.makedirs(self._job_dir)

		except FileExistsError:
			pass

		else:
			try:
				# Here we use `os.open()` so we ensure this call is only used to create the file
				counter = os.open(self._counter_filename, os.O_CREAT | os.O_EXCL | os.O_RDWR)

			except FileExistsError:
				pass

			else:
				os.close(counter)

	def _getNext(self):
		'''
		Get the next command line to execute.

		Returns
		-------
		command_line : str
			The next command line to execute, according to the current value of the counter. `None` if there is no command line anymore.
		'''

		with LockedFile(self._counter_filename, 'r+') as counter:
			try:
				n = int(counter.read())

			except ValueError:
				n = 0

			finally:
				counter.seek(0)
				counter.write(str(n+1))

		while self._counter < n:
			try:
				command_line = next(self._command_lines)

			except StopIteration:
				command_line = None
				break

			self._counter += 1

		return command_line

	def _logOutput(self, output):
		'''
		Save the output of a command line.

		Parameters
		----------
		output : dict
			Output to log.
		'''

		self._log.append(output)
		jsonfiles.write(self._log, self._client_filename)

	def _launchNext(self):
		'''
		Launch the next command line.
		'''

		command_line = self._getNext()

		if command_line is not None:
			p = subprocess.Popen(shlex.split(command_line), stdout = subprocess.PIPE, stderr = subprocess.PIPE, encoding = 'utf-8')
			killed = False

			while p.poll() is None:
				if os.path.isfile(self._kill_filename) or os.path.isfile(self._killall_filename):
					p.kill()
					killed = True

				else:
					self._alive(command_line)
					time.sleep(self._poll_delay)

			self._logOutput({
				'exec': command_line,
				'stdout': p.stdout.read(),
				'stderr': p.stderr.read(),
				'success': p.returncode == 0
			})

			if not(killed):
				self._launchNext()

	def _alive(self, command_line = None):
		'''
		Update the state file to indicate the job is still alive.

		Parameters
		----------
		command_line : str
			Current command line executed.
		'''

		state = {}

		if os.path.isfile(self._state_filename):
			state = {
				'exec': command_line,
				'datetime': str(datetime.datetime.now())
			}

		jsonfiles.write(state, self._state_filename)

	def run(self):
		'''
		Run "loop". After the first command line is executed, the next one is launched, and so on.
		'''

		self._launchNext()
