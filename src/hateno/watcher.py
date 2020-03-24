#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import imaplib
import email

from . import jsonfiles
from .errors import *

class Watcher():
	'''
	Watch for events to detect the end of some simulations.

	Parameters
	----------
	remote_folder : RemoteFolder
		A RemoteFolder instance to use to search for notifications.

	states_path : str
		Path to the remote file where the states are stored.

	mail_config : dict
		Configuration of the mailbox.

	mail_notifications_config : dict
		Mails notifications configuration.

	Raises
	------
	WatcherNoConfigFoundError
		Nothing used to configure the watcher.

	WatcherTooManyConfigError
		More than one configuration used.
	'''

	def __init__(self, *, remote_folder = None, states_path = '', mail_config = None, mail_notifications_config = None):
		self._jobs_to_watch = set()
		self._jobs_states = {}

		self._remote_folder = remote_folder
		self._states_path = states_path

		self._mail_config = mail_config
		self._mail_notifications_config_dict = mail_notifications_config
		self._mail_notifications_config_compiled = False
		self._mailbox_instance = None

		if self._remote_folder is None and self._mail_config is None:
			raise WatcherNoConfigFoundError()

		if not(self._remote_folder is None) and not(self._mail_config is None):
			raise WatcherTooManyConfigError()

	@property
	def _mailbox(self):
		'''
		Get or create an object to access the mailbox.

		Raises
		------
		WatcherNoMailConfigError
			No configuration found for the mailbox.

		Returns
		-------
		mailbox : imaplib.IMAP4
			The mailbox object.
		'''

		if self._mailbox_instance is None:
			self._mailbox_instance = imaplib.IMAP4(self._mail_config['host'], self._mail_config['port'])
			self._mailbox_instance.login(self._mail_config['user'], self._mail_config['password'])
			self._mailbox_instance.select('INBOX')

		return self._mailbox_instance

	@property
	def _mail_notifications_config(self):
		'''
		Get or create the dictionary containing the mails notifications configuration.

		Raises
		------
		WatcherNoMailNotificationsConfigError
			No configuration found fot the notifications.

		Returns
		-------
		config : dict
			The mail notifications configuration.
		'''

		if not(self._mail_notifications_config_compiled):
			self._mail_notifications_config_dict['search'] = '"' + self._mail_notifications_config_dict['search'] + '"'
			self._mail_notifications_config_dict['infos_extraction']['subject_regex'] = re.compile(self._mail_notifications_config_dict['infos_extraction']['subject'])

			self._mail_notifications_config_compiled = True

		return self._mail_notifications_config_dict

	def close(self):
		'''
		Close the mailbox if necessary.
		'''

		if not(self._mailbox_instance is None):
			self._mailbox_instance.logout()

	def addJobsToWatch(self, jobs):
		'''
		Add some jobs to watch.

		Parameters
		----------
		jobs : list
			IDs of the jobs.
		'''

		self._jobs_to_watch |= set(jobs)

	def clearJobs(self):
		'''
		Clear the list of jobs to watch.
		'''

		self._jobs_to_watch.clear()
		self._jobs_states.clear()

	def getJobsByStates(self, states):
		'''
		Get the list of jobs which are in a given state.

		Parameters
		----------
		states : list
			List of states to use to filter the jobs.

		Returns
		-------
		jobs : list
			The list of jobs in these states.
		'''

		return [job for job, state in self._jobs_states.items() if state in states]

	def getNumberOfJobsByState(self, state):
		'''
		Return the number of jobs in a given state.

		Parameters
		----------
		state : str
			The state to use to filter the jobs.

		Returns
		-------
		n_jobs : int
			The number of jobs in this state.
		'''

		return len(self.getJobsByStates([state]))

	def getNumberOfJobsByStates(self, states):
		'''
		Return the number of jobs in given states.

		Parameters
		----------
		states : list
			The states to use to filter the jobs.

		Returns
		-------
		n_jobs : dict
			A dictionary with keys equal to the wanted states and values the number of jobs in these states.
		'''

		return {state: self.getNumberOfJobsByState(state) for state in states}

	def setJobsStatesPath(self, states_path):
		'''
		Set the path to the remote file where we can find the jobs states.

		Parameters
		----------
		states_path : str
			Path to the remote file containing the jobs states.

		Raises
		------
		WatcherNoRemoteFolderError
			There is no RemoteFolder set.
		'''

		if self._remote_folder is None:
			raise WatcherNoRemoteFolderError()

		self._states_path = states_path

	def setMailNotificationsConfig(self, config):
		'''
		Set the mails notifications configuration file.

		Parameters
		----------
		config : str
			Path to the file containing the configuration.

		Raises
		------
		WatcherNoMailConfigError
			There is no mailbox set.
		'''

		if self._mail_config is None:
			raise WatcherNoMailConfigError()

		self._mail_notifications_config_file = config

	def _getJobsStatesFromFile(self):
		'''
		Remotely read the current states of the jobs.

		Raises
		------
		WatcherNoStatesPathError
			There is no path to look for the states.

		Returns
		-------
		known_states : dict
			A dictionary listing the current jobs states.
		'''

		if not(self._states_path):
			raise WatcherNoStatesPathError()

		known_states = {}

		try:
			known_states = dict(self._remote_folder.getFileContents(self._states_path, callback = lambda l: tuple(map(lambda s: s.strip(), l.split(':')))))

		except FileNotFoundError:
			pass

		return known_states

	def _getJobsStatesFromMail(self):
		'''
		Search for mail notifications to update the jobs states.

		Returns
		-------
		known_states : dict
			A dictionary listing the current jobs states.
		'''

		known_states = {}

		typ, data_nums = self._mailbox.search(None, 'SUBJECT', self._mail_notifications_config['search'])

		for num in data_nums[0].split():
			typ, data = self._mailbox.fetch(num, '(RFC822)')
			msg = email.message_from_bytes(data[0][1])
			subject = email.header.decode_header(msg['Subject'])[0][0]

			matches = self._mail_notifications_config['infos_extraction']['subject_regex'].match(subject)
			job_id = matches.group('id')

			if job_id in self._jobs_to_watch:
				job_state = matches.group('state')

				try:
					job_state = self._mail_notifications_config['convert'][job_state]

				except KeyError:
					pass

				known_states[job_id] = job_state

				if 'delete' in self._mail_notifications_config and self._mail_notifications_config['delete']:
					self._mailbox.store(num, '+FLAGS', '\\Deleted')

		self._mailbox.expunge()

		return known_states

	def updateJobsStates(self):
		'''
		Read the current states of the jobs.
		'''

		known_states = {}

		if not(self._remote_folder is None):
			known_states = self._getJobsStatesFromFile()

		else:
			known_states = self._getJobsStatesFromMail()

		for job in self._jobs_to_watch & set(known_states.keys()):
			state = known_states[job]

			if state in ['waiting', 'running', 'succeed', 'failed']:
				self._jobs_states[job] = state

		self._jobs_states.update({job: 'waiting' for job in self._jobs_to_watch - set(self._jobs_states.keys())})
