#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
This script uses the RemoteFolder class to receive files or directory.
'''

import argparse

from utils import jsonfiles
from manager.remote import RemoteFolder

parser = argparse.ArgumentParser(description = 'Receive files or directory from a remote folder.')

parser.add_argument('--delete', action = 'store_true', help = 'delete the original file/directory once received')
parser.add_argument('remote_folder', type = argparse.FileType('r'), help = 'path to the file where the configuration of the remote folder can be found')
parser.add_argument('to_receive', type = str, help = 'path of file/directory to receive')
parser.add_argument('local_path', type = str, nargs = '?', help = 'local path where the file/directory should be stored')

args = parser.parse_args()

remote_folder_conf = jsonfiles.read(args.remote_folder.name)
remote_folder = RemoteFolder(remote_folder_conf)
remote_folder.open()

remote_folder.receive(args.to_receive, args.local_path, delete = args.delete)

remote_folder.close()
