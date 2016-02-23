#!/usr/bin/env python
"""
Check if a process is running with an old version of the modules
found in the defined python paths.

It parses all folders containing an `__init__.py` file and checks if
a file modification date is greater than the start date of the
process.
"""

import sys
import os
import errno

import psutil

def moduleIsModifiedSince(top, last_modified, followlinks=False):
  for root, dir_list, file_list in os.walk(top, followlinks=followlinks):
    if "__init__.py" not in file_list:
      del dir_list[:]
      continue
    for name in file_list:
      path = os.path.join(root, name)
      if last_modified > os.stat(path).st_mtime:
        return True
  return False

def isProcessOlderThanDependencySet(pid, python_path_list):
  start_time = psutil.Process(pid).create_time()
  return any(moduleIsModifiedSince(product_path, start_time) for product_path in python_path_list)

def isProcessFromPidFileOlderThanDependencySet(pid_file_path, python_path_list):
  with open(pid_file_path, "r") as f:
    pid = int(f.readline())
  return isProcessOlderThanDependencySet(pid, python_path_list)

def main():
  pid_file_path, python_path_list = sys.argv[1], sys.argv[2:]
  try:
    if isProcessFromPidFileOlderThanDependencySet(pid_file_path, python_path_list):
      return 1
    return 0
  except (OSError, IOError) as err:
    if err.errno == errno.ENOENT:
      return 0
    raise
  except psutil.NoSuchProcess:
    return 0

if __name__ == "__main__":
  sys.exit(main())
