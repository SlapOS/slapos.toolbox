#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os, errno
import subprocess
import argparse
from datetime import date

# run_apachedex.py <apachedex_executable> /srv/etc/output_folder script_name
def build_command(apachedex_executable, output_folder, default,
                  apache_log_list = None,
                  base_list = None,
                  skip_base_list = None,
                  erp5_base_list = None):

  if not len(apache_log_list):
    return 1
  if not os.path.exists(output_folder) or not os.path.isdir(output_folder):
    print "ERROR: Output folder is not a directory. Exiting..."
    return 1

  apachedex = apachedex_executable
  today = date.today().strftime("%Y-%m-%d")
  output_file = os.path.join(output_folder, 'ApacheDex-%s.html' % today)
  argument_list = [apachedex, '--js-embed', '--out', output_file]
  if default:
    argument_list += ['--default', default]

  log_list = []
  for logfile in apache_log_list:
    if not logfile:
      continue
    # Automaticaly replace variable 'date'.
    apache_log = logfile.strip() % {'date': date.today().strftime("%Y%m%d")}
    if not os.path.exists(apache_log):
      print "WARNING: File %s not found..." % apache_log
      continue
    log_list.append(apache_log)
  if not log_list:
    print "WARNING: Log file list to analyse is empty or not provided. Exiting..."
    return 1

  if erp5_base_list:
    argument_list.append('--erp5-base')
    for arg in erp5_base_list:
      argument_list.append(arg)

  if base_list:
    argument_list.append('--base')
    for arg in base_list:
      argument_list.append(arg)

  if skip_base_list:
    argument_list.append('--skip-base')
    for arg in skip_base_list:
      argument_list.append(arg)

  argument_list.append('--error-detail')
  argument_list += log_list

  return argument_list

def _get_list(filename):
  final_list = None
  if os.path.exists(filename):
    with open(filename, 'r') as f:
      list = f.read().strip();
      final_list = [base.strip().split(' ') for base in
                   list.split(' ') if base]
  return final_list

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("apachedex_executable", metavar="APACHEDEX_EXECUTABLE")
  parser.add_argument("output_folder", metavar="OUTPUT_FOLDER")
  parser.add_argument("-default", metavar="DEFAULT_PARAMETER")
  parser.add_argument("-apache_log_list", nargs='*')

  parser.add_argument("-base_list")
  parser.add_argument("-skip_base_list")
  parser.add_argument("-erp5_base_list")
  args = parser.parse_args()

  base_list = _extract_list(args.base_list)
  skip_base_list = _extract_list(args.skip_base_list)
  erp5_base_list = _extract_list(args.erp5_base_list)
  default = _extract_list(args.default)

  argument_list = build_command(args.apachedex_executable.strip(),
                          args.output_folder.strip(),
                          args.default.strip(),
                          args.apache_log_list,
                          base_list,
                          skip_base_list,                
                          erp5_base_list)

  if argument_list is 1:
    return 1

  subprocess.check_call(argument_list)
  with open(output_file, 'r') as f:
    print f.read()

  return 0

if __name__ == "__main__":
  sys.exit(main())

