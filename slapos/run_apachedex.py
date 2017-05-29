#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os, errno
import subprocess
import argparse
from datetime import date

# run_apachedex.py <apachedex_executable> /srv/etc/output_folder script_name
def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("apachedex_executable", metavar="APACHEDEX_EXECUTABLE")
  parser.add_argument("output_folder", metavar="OUTPUT_FOLDER")
  parser.add_argument("name", metavar="NAME")

  parser.add_argument("-default", metavar="DEFAULT_PARAMETER")
  parser.add_argument("-apache_log_list", nargs='*')
  parser.add_argument("-base_list")
  parser.add_argument("-skip_base_list")
  parser.add_argument("-erp5_base_list")

  args = parser.parse_args()
  base_name = args.name.strip()
  default = args.default.strip()
  apache_log_list = args.apache_log_list
  base_list = None
  skip_base_list = None
  erp5_base_list = None
  if os.path.exists(args.base_list):
    with open(args.base_list, 'r') as f:
      list = f.read().strip();
      base_list = [base.strip().split(' ') for base in
                   list.split(' ') if base]
  if os.path.exists(args.skip_base_list):
    with open(args.skip_base_list, 'r') as f:
      list = f.read().strip();
      skip_base_list = [base.strip().split(' ') for base in
                        list.split(' ')
                        if base]
  if os.path.exists(args.erp5_base_list):
    with open(args.erp5_base_list, 'r') as f:
      list = f.read().strip();
      erp5_base_list = [base.strip().split(' ') for base in
                        list.split(' ')
                        if base]

  output_folder = args.output_folder.strip()
  if not len(apache_log_list):
    return 1
  if not os.path.exists(output_folder) or not os.path.isdir(output_folder):
    print "ERROR: Output folder is not a directory. Exiting..."
    return 1
  today = date.today().strftime("%Y-%m-%d")
  folder_today = os.path.join(output_folder, 'ApacheDex-%s' % today)

  # XXX- don't raise if folder_today exist
  try:
    os.makedirs(folder_today)
  except OSError as exc:
    if exc.errno == errno.EEXIST and os.path.isdir(folder_today):
      pass
    else: raise

  apachedex = args.apachedex_executable.strip()
  argument_list = [apachedex, '--js-embed', '--out',
                   os.path.join(folder_today, 'ApacheDex-%s.html' % base_name)]
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
    for args_list in erp5_base_list:
      argument_list += args_list

  if base_list:
    argument_list.append('--base')
    for args_list in base_list:
      argument_list += args_list

  if skip_base_list:
    argument_list.append('--skip-base')
    for args_list in skip_base_list:
      argument_list += args_list

  argument_list.append('--error-detail')
  argument_list += log_list

  subprocess.check_call(argument_list)
  return 0

if __name__ == "__main__":
  sys.exit(main())

