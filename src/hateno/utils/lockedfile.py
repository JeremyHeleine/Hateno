#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time

class LockedFile:
	'''
	Lock a file so only one access at a time is allowed.

	Parameters
	----------
	filename : str
		Path to the file to lock.

	mode : str
		Mode to use to open the file.
	'''

	def __init__(self, filename, mode):
		self._filename = filename
		self._mode = mode

		self._lock_name = f'{filename}.lock'
		self._is_locked = False

	def __enter__(self):
		'''
		Context manager to automatically acquire and release the lock.
		'''

		return self.acquire()

	def __exit__(self, *args, **kwargs):
		'''
		Release the lock.
		'''

		self.release()

	def __del__(self):
		'''
		Ensure the file is released if the lock is deleted.
		'''

		self.release()

	def acquire(self):
		'''
		Lock the file.

		Returns
		-------
		file : file-like object
			The file, opened while locked. `None` if the lock can't be acquired.
		'''

		if self._is_locked:
			return None

		while True:
			try:
				self._lock_file = os.open(self._lock_name, os.O_CREAT | os.O_EXCL | os.O_RDWR)
				self._is_locked = True

				self._file = open(self._filename, self._mode)
				return self._file

			except FileExistsError:
				time.sleep(0.1)

	def release(self):
		'''
		Release the file.
		'''

		if self._is_locked:
			self._file.close()
			os.close(self._lock_file)
			os.unlink(self._lock_name)
			self._is_locked = False
