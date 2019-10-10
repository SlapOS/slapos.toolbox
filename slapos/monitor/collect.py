# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2010-2014 Vifib SARL and Contributors.
# All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public License
# as published by the Free Software Foundation; either version 2.1
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from __future__ import division

import sqlite3
import os
import pwd
import time
import json
import argparse
import psutil
from time import strftime
from datetime import datetime, timedelta

from slapos.collect.db import Database
from slapos.collect.reporter import ConsumptionReportBase

def parseArguments():
  """
  Parse arguments for monitor collector instance.
  """
  parser = argparse.ArgumentParser()
  parser.add_argument('--output_folder',
                      help='Path of the folder where output files should be written.')
  parser.add_argument('--pid_file',
                      help='Path where should be written the pid of process.')
  parser.add_argument('--partition_id',
                      help='ID of the computer partition to collect data from.')
  parser.add_argument('--collector_db',
                      help='The path of slapos collect database.')

  return parser.parse_args()

class ResourceCollect(ConsumptionReportBase):

  def __init__(self, db_path = None):
    # If the database is locked, wait until 15 seconds
    # Do not try to created or update tables, access will be refused
    self.db = Database(db_path, create=False, timeout=15)

def main():
  parser = parseArguments()
  if not os.path.exists(parser.output_folder) and os.path.isdir(parser.output_folder):
    raise Exception("Invalid ouput folder: %s" % parser.output_folder)

  if parser.pid_file:
    # Check that this process is not running
    if os.path.exists(parser.pid_file):
      with open(parser.pid_file, "r") as pidfile:
        try:
          pid = int(pidfile.read(6))
        except ValueError:
          pid = None
        if pid and os.path.exists("/proc/" + str(pid)):
          print("A process is already running with pid " + str(pid))
          exit(1)
    with open(parser.pid_file, "w") as pidfile:
      pidfile.write('%s' % os.getpid())

  # Consumption global status
  process_file = os.path.join(parser.output_folder, 'monitor_resource_process.data.json')
  mem_file = os.path.join(parser.output_folder, 'monitor_resource_memory.data.json')
  io_file = os.path.join(parser.output_folder, 'monitor_resource_io.data.json')
  resource_file = os.path.join(parser.output_folder, 'monitor_process_resource.status.json')
  status_file = os.path.join(parser.output_folder, 'monitor_resource.status.json')

  if not os.path.exists(parser.collector_db):
    print("Collector database not found...")
    initDataFile(process_file, ["date, total process, CPU percent, CPU time, CPU threads"])
    initDataFile(mem_file, ["date, memory used percent, memory used"])
    initDataFile(io_file,  ["date, io rw counter, io cycles counter, disk used"])
    with open(status_file, "w") as status_file:
      status_file.write(json.dumps({
        "cpu_time": 0,
        "cpu_percent": 0,
        "memory_rss": 0,
        "memory_percent": 0,
        "io_rw_counter": 0,
        "date": "",
        "total_process": 0,
        "disk_used": 0,
        "io_cycles_counter": 0,
        "cpu_num_threads": 0
      }))
    with open(resource_file, "w") as resource_file:
      resource_file.write('[]')
    exit(1)

  collector = ResourceCollect(parser.collector_db)

  date_scope = datetime.now().strftime('%Y-%m-%d')
  stat_info = os.stat(parser.output_folder)
  partition_user = pwd.getpwuid(stat_info.st_uid)[0]

  process_result, memory_result, io_result = collector.getPartitionConsumptionStatus(partition_user)

  label_list = ['date', 'total_process', 'cpu_percent', 'cpu_time', 'cpu_num_threads',
                  'memory_percent', 'memory_rss', 'io_rw_counter', 'io_cycles_counter',
                  'disk_used']
  resource_status_dict = {}
  if process_result and process_result['total_process'] != 0.0:
    appendToJsonFile(process_file, ", ".join(
      str(process_result[key]) for key in label_list if key in process_result)
    )
    resource_status_dict.update(process_result)
  if memory_result and memory_result['memory_rss'] != 0.0:
    appendToJsonFile(mem_file, ", ".join(
      str(memory_result[key]) for key in label_list if key in memory_result)
    )
    resource_status_dict.update(memory_result)
  if io_result and io_result['io_rw_counter'] != 0.0:
    appendToJsonFile(io_file, ", ".join(
      str(io_result[key]) for key in label_list if key in io_result)
    )
    resource_status_dict.update(io_result)

  with open(status_file, 'w') as fp:
    fp.write(json.dumps(resource_status_dict))

  # Consumption Resource
  resource_process_status_list = collector.getPartitionConsumption(partition_user)
  if resource_process_status_list:
    with open(resource_file, 'w') as rf:
      rf.write(json.dumps(resource_process_status_list))

  if os.path.exists(parser.pid_file):
    os.unlink(parser.pid_file)
