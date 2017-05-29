# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2010, 2015 Nexedi SA and Contributors. All Rights Reserved.
#                    Hardik Juneja <hardik.juneja@nexedi.com>
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import os, errno
import subprocess
import argparse
import time
from datetime import date

# run_apachedex.py <apachedex_executable> /srv/etc/output_folder script_name
def build_command(apachedex_executable, output_file, default,
                  apache_log_list,
                  base_list = None,
                  skip_base_list = None,
                  erp5_base_list = None):

  if not len(apache_log_list):
    raise ValueError("apache_log_list is empty")

  today = date.today().strftime("%Y-%m-%d")
  apachedex = apachedex_executable
  argument_list = [apachedex, '--js-embed', '--out', output_file]
  if default:
    argument_list += ['--default', default]

  log_list = []
  for logfile in apache_log_list:
    if not logfile:
      continue
    # Automaticaly replace variable 'date'.
    apache_log = logfile.strip() % {'date': today}
    if not os.path.exists(apache_log):
      print "WARNING: File %s not found..." % apache_log
      continue
    log_list.append(apache_log)
  if not log_list:
    raise ValueError("log_list: no log files to analyse were provided")

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

def _extract_list(filename):
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
  parser.add_argument("--default", metavar="DEFAULT_PARAMETER")
  parser.add_argument("--apache-log-list", dest="apache_log_list", nargs='*')

  parser.add_argument("--base-list", dest="base_list")
  parser.add_argument("--skip-base-list", dest="skip_base_list")
  parser.add_argument("--erp5-base-list", dest="erp5_base_list")
  args = parser.parse_args()

  base_list = _extract_list(args.base_list)
  skip_base_list = _extract_list(args.skip_base_list)
  erp5_base_list = _extract_list(args.erp5_base_list)
  default = _extract_list(args.default)
  output_folder = args.output_folder.strip()

  if not os.path.exists(output_folder) or not os.path.isdir(output_folder):
    print "ERROR: Output folder is not a directory. Exiting..."
    return 1

  today = date.today().strftime("%Y-%m-%d")
  output_file = os.path.join(output_folder, 'ApacheDex-%s.html' % today)

  try:
    argument_list = build_command(args.apachedex_executable.strip(),
                            output_file,
                            args.default.strip(),
                            args.apache_log_list,
                            base_list,
                            skip_base_list,                
                            erp5_base_list)
  except ValueError as e:
    print e
    return 1

  process_handler = subprocess.Popen(argument_list,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE,
                                     )

  stdout, stderr = process_handler.communicate()
  if process_handler.returncode != 0:
    if stderr:
      print stderr
    return 1
  
  with open(output_file, 'r') as f:
    print f.read()
  return 0

if __name__ == "__main__":
  sys.exit(main())

