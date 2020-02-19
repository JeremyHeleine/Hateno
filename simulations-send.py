#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
This script uses the RemoteFolder class to send files or directory.
'''

import os
import argparse

from utils import jsonfiles
from manager.remote import RemoteFolder

parser = argparse.ArgumentParser(description = 'Send files or directory to a remote folder.')

parser.add_argument('--delete', action = 'store_true', help = 'delete the original file/directory once sent')
parser.add_argument('remote_folder', type = argparse.FileType('r'), help = 'path to the file where the configuration of the remote folder can be found')
parser.add_argument('to_send', type = str, help = 'path of file/directory to send')
parser.add_argument('remote_path', type = str, nargs = '?', help = 'remote path where the file/directory should be sent')

args = parser.parse_args()

remote_folder_conf = jsonfiles.read(args.remote_folder.name)
remote_folder = RemoteFolder(remote_folder_conf)
remote_folder.open()

remote_folder.send(args.to_send, args.remote_path, delete = args.delete)

remote_folder.close()