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

from __future__ import print_function

import os, errno
import subprocess
import argparse
import shlex
from datetime import date

# run_apachedex.py <apachedex_executable> /srv/etc/output_folder script_name
def build_command(apachedex_executable, output_file,
                  apache_log_list,
                  config = None):

  if not len(apache_log_list):
    raise ValueError("apache_log_list is empty")

  today = date.today().strftime("%Y-%m-%d")
  apachedex = apachedex_executable
  argument_list = [apachedex, '--js-embed', '--out', output_file]

  log_list = []
  for logfile in apache_log_list:
    if not logfile:
      continue
    # Automaticaly replace variable 'date'.
    apache_log = logfile.strip() % {'date': today}
    if not os.path.exists(apache_log):
      print("WARNING: File %s not found..." % apache_log)
      continue
    log_list.append(apache_log)
  if not log_list:
    raise ValueError("log_list: no log files to analyse were provided")

  if config:
    argument_list.extend(shlex.split(config))

  argument_list.append('--error-detail')
  argument_list += log_list

  return argument_list

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("apachedex_executable", metavar="APACHEDEX_EXECUTABLE")
  parser.add_argument("output_folder", metavar="OUTPUT_FOLDER")
  parser.add_argument("base_url", metavar="BASE_URL")
  parser.add_argument("--apache-log-list", nargs='*')
  parser.add_argument("--configuration")
  args = parser.parse_args()

  config = args.configuration
  output_folder = args.output_folder.strip()
  base_url = args.base_url.strip()

  if not os.path.exists(output_folder) or not os.path.isdir(output_folder):
    print("ERROR: Output folder is not a directory. Exiting...")
    return 1

  today = date.today().strftime("%Y-%m-%d")
  output_file = os.path.join(output_folder, 'ApacheDex-%s.html' % today)

  try:
    argument_list = build_command(args.apachedex_executable.strip(),
                            output_file,
                            args.apache_log_list,
                            config)
  except ValueError as e:
    print(e)
    return 1

  try:
    subprocess.check_output(argument_list, stderr=subprocess.STDOUT)
  except subprocess.CalledProcessError as e:
    print("Error running apachedex", e.output)
    return 1

  # Check that output_file is a readable file.
  with open(output_file, 'r'):
    print(base_url + '/ApacheDex-%s.html' % today)
  return 0

