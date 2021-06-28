#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import watchdog.observers.polling

class FileWatcher():
	'''
	Monitor files or directories.

	Parameters
	----------
	event_handler : watchdog.events.FileSystemEventHandler
		Object used to handle the events.

	path : str
		Path to the file or directory to monitor.

	timeout : float
		Interval (in seconds) between polling the file system.
	'''

	def __init__(self, event_handler, path, *, timeout = 0.1):
		self._observer = watchdog.observers.polling.PollingObserver(timeout = timeout)
		self._observer.schedule(event_handler, path)

	def __enter__(self):
		'''
		Context manager to call `start()` and `stop()` automatically.
		'''

		self.start()

	def __exit__(self, *args, **kwargs):
		'''
		Ensure `stop()` is called when exiting the context manager.
		'''

		self.stop()

	def start(self):
		'''
		Start the monitoring.
		'''

		self._observer.start()

	def stop(self):
		'''
		Stop the monitoring.
		'''

		self._observer.stop()
		self._observer.join()
