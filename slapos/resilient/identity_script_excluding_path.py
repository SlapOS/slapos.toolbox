from __future__ import print_function

import argparse
import os
import subprocess
import re

from .runner_utils import *

def parseArgumentList():
  parser = argparse.ArgumentParser()
  parser.add_argument('--exclude-path', action='append', required=True)

  return parser.parse_args()

def calculateSignature():
  args = parseArgumentList()

  file_list = sys.stdin.read()
  file_list = file_list.split('\0')

  if not len(file_list):
    return 0

  result = re.match('^\.\/runner\/instance\/slappart(\d)', file_list[0])
  base_relative_path = result.group()
  excluded_path_list = ['./' + os.path.relpath(os.path.join(base_relative_path, path)) for path in args.exclude_path]
  excluded_path_regex_list = [re.compile(excluded_path) for excluded_path in excluded_path_list]

  filtered_file_list = [
    x for x in file_list
    if not any([re.match(excluded_path_regex, x) for excluded_path_regex in excluded_path_regex_list])
  ]

  print('\n'.join(getSha256Sum(filtered_file_list)))