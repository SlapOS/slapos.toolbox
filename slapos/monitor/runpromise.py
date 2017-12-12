#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import subprocess
import json
import psutil
import time
from datetime import datetime
from shutil import copyfile
import glob
import argparse
import traceback
import logging
from slapos.grid.utils import checkPromiseList as _checkPromiseList

# Promise timeout after 20 seconds by default
promise_timeout = 20

def parseArguments():
  """
  Parse arguments for monitor collector instance.
  """
  parser = argparse.ArgumentParser()
  parser.add_argument('--pid_path',
                      help='Path where the pid of this process will be writen.')
  parser.add_argument('--output',
                      help='The Path of file where Json result of this promise will be saved.')
  parser.add_argument('--promise_script',
                      help='Promise script to execute.')
  parser.add_argument('--promise_folder',
                      help='Folder where to find promises to execute. Hide --promise_script and --promise_name')
  parser.add_argument('--monitor_promise_folder',
                      help='Folder where to find Custom monitor promises to execute.')
  parser.add_argument('--promise_name',
                      help='Title to give to this promise.')
  parser.add_argument('--timeout_file',
                      default='',
                      help='File containing Max timeout for each promise run.')
  parser.add_argument('--promise_type',
                      default='status',
                      help='Type of promise to execute. [status, report].')
  parser.add_argument('--monitor_url',
                      help='Monitor Instance website URL.')
  parser.add_argument('--history_folder',
                      help='Path where old result file will be placed before generate a new json result file.')
  parser.add_argument('--instance_name',
                      default='UNKNOWN Software Instance',
                      help='Software Instance name.')
  parser.add_argument('--hosting_name',
                      default='UNKNOWN Hosting Subscription',
                      help='Hosting Subscription name.')
  parser.add_argument('--log_file',
                      help='Path of log file.')

  return parser


class RunPromise(object):

  def __init__(self, config_parser):
    self.config = config_parser
    self.logger = logging.getLogger("RunPromise")
    self.logger.setLevel(logging.DEBUG)

    if not self.config.log_file:
      if len(self.logger.handlers) == 0 or \
          not isinstance(self.logger.handlers[0], logging.StreamHandler):
        self.logger.addHandler(logging.StreamHandler())
    else:
      file_handler = logging.FileHandler(self.config.log_file)
      file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
      self.logger.addHandler(file_handler)

    self.promise_timeout = promise_timeout
    if self.config.timeout_file and \
            os.path.exists(self.config.timeout_file):
      with open(self.config.timeout_file) as tf:
        timeout = tf.read().strip()
        if timeout.isdigit():
          self.promise_timeout = int(timeout)
        else:
          self.logger.warning("%s it not a valid promise-timeout value" % timeout)

  def runPromise(self):

    if self.config.promise_folder:
      # run all promises from the given folder in a synchronous way
      return self.runPromiseSynchronous()

    return self.runSinglePromise()

  def runSinglePromise(self):
    """
      run a single promise in a new process
    """
    if os.path.exists(self.config.pid_path):
      with open(self.config.pid_path, "r") as pidfile:
        try:
          pid = int(pidfile.read(6))
        except ValueError:
          pid = None
        if pid and os.path.exists("/proc/" + str(pid)):
          self.logger.warning("A process is already running with pid " + str(pid))
          return 1
    start_date = datetime.utcnow()
    with open(self.config.pid_path, "w") as pidfile:
      self.logger.info("Running script %s..." % self.config.promise_script)
      process = self.executeCommand(self.config.promise_script)
      ps_process = psutil.Process(process.pid)
      pidfile.write(str(process.pid))

    status_json = self.generateStatusJsonFromProcess(
      process,
      start_date=start_date,
      title=self.config.promise_name
    )

    status_json['_links'] = {"monitor": {"href": self.config.monitor_url}}
    status_json['title'] = self.config.promise_name
    status_json['instance'] = self.config.instance_name
    status_json['hosting_subscription'] = self.config.hosting_name
    status_json['type'] = self.config.promise_type
    status_json['portal-type'] = "promise" if \
        self.config.promise_type == "status" else self.config.promise_type

    # Save the lastest status change date (needed for rss)
    status_json['change-time'] = ps_process.create_time()
    if os.path.exists(self.config.output) and os.stat(self.config.output).st_size:
      with open(self.config.output) as f:
        try:
          last_result = json.loads(f.read())
          if status_json['status'] == last_result['status'] and last_result.has_key('change-time'):
            status_json['change-time'] = last_result['change-time']
        except ValueError:
          pass

    self.updateStatusHistoryFolder(
      self.config.promise_name,
      self.config.output,
      self.config.history_folder,
      self.config.promise_type
    )
    # write the promise in a tmp file the move to promise output file
    # this reduce conflict error on read/write at sametime
    output_tmp = '%s.tmp' % self.config.output
    with open(output_tmp, "w") as outputfile:
      json.dump(status_json, outputfile)
    os.rename(output_tmp, self.config.output)
    os.remove(self.config.pid_path)

  def runPromiseSynchronous(self):
    """
      run all promises in sequential ways
    """
    if os.path.exists(self.config.pid_path):
      # Check if another run promise is running
      with open(self.config.pid_path) as fpid:
        try:
          pid = int(fpid.read(6))
        except ValueError:
          pid = None
        if pid and os.path.exists("/proc/" + str(pid)):
          self.logger.warning("A process is already running with pid " + str(pid))
          return []

    with open(self.config.pid_path, 'w') as fpid:
      fpid.write(str(os.getpid()))

    promise_folder_list = [self.config.promise_folder]
    if self.config.monitor_promise_folder:
      promise_folder_list.append(self.config.monitor_promise_folder)
    status_list = self.checkPromisesList(promise_folder_list)
    promises_status_file = os.path.join(self.config.output, '_promise_status')
    previous_state_dict = {}
    new_state_dict = {}
    base_dict = {
      '_links': {"monitor": {"href": self.config.monitor_url}},
      'instance': self.config.instance_name,
      'hosting_subscription': self.config.hosting_name,
    }

    if os.path.exists(promises_status_file):
      with open(promises_status_file) as f:
        try:
          previous_state_dict = json.loads(f.read())
        except ValueError:
          pass

    for status_dict in status_list:
      status_dict.update(base_dict)
      if previous_state_dict.has_key(status_dict['title']):
        status, change_time = previous_state_dict[status_dict['title']].split('#')
        if status_dict['status'] == status:
          status_dict['change-time'] = float(change_time)

      promise_result_file = os.path.join(self.config.output, 
                                         "%s.status.json" % status_dict['title'])
      # write the promise in a tmp file the move to promise output file
      # this reduce conflict error on read/write at sametime
      promise_tmp_file = '%s.tmp' % promise_result_file
      with open(promise_tmp_file, "w") as outputfile:
        json.dump(status_dict, outputfile)
      os.rename(promise_tmp_file, promise_result_file)

      new_state_dict[status_dict['title']] = '%s#%s' % (status_dict['status'],
                                                        status_dict['change-time'])
      self.updateStatusHistoryFolder(
        status_dict['title'],
        promise_result_file,
        self.config.history_folder,
        'status'
      )

    with open(promises_status_file, "w") as outputfile:
      json.dump(new_state_dict, outputfile)

    os.remove(self.config.pid_path)

  def updateStatusHistoryFolder(self, name, status_file, history_folder, promise_type):
    history_path = os.path.join(history_folder)
    if not os.path.exists(status_file):
      return
    if not os.path.exists(history_folder):
      return
    if not os.path.exists(history_path):
      try:
        os.makedirs(history_path)
      except OSError, e:
        if e.errno == os.errno.EEXIST and os.path.isdir(history_path):
          pass
        else: raise
    with open(status_file, 'r') as sf:
      try:
        status_dict = json.loads(sf.read())
      except ValueError:
        traceback.print_exc()
        return

    if promise_type == 'status':
      filename = '%s.history.json' % name
      history_file = os.path.join(history_path, filename)
      # Remove links from history (not needed)
      status_dict.pop('_links', None)
      if not os.path.exists(history_file) or \
        (os.path.exists(history_file) and not os.stat(history_file).st_size):
        with open(history_file, 'w') as f_history:
          data_dict = {
            "date": time.time(),
            "data": [status_dict]
          }
          f_history.write(json.dumps(data_dict))
      else:
        # Remove useless informations
        status_dict.pop('hosting_subscription', '')
        status_dict.pop('title', '')
        status_dict.pop('instance', '')
        status_dict.pop('type', '')
        status_dict.pop('portal-type', '')

        with open (history_file, mode="r+") as f_history:
          f_history.seek(0,2)
          position = f_history.tell() -2
          f_history.seek(position)
          #f_history.write(',%s]}' % str(status_dict))
          f_history.write('%s}' % ',{}]'.format(json.dumps(status_dict)))
    elif promise_type == 'report':
      # keep_item_amount = 3
      filename = '%s.history.json' % (
        name)

      copyfile(status_file, os.path.join(history_path, filename))

  def generateStatusJsonFromProcess(self, process, start_date=None, title=None):
    stdout, stderr = process.communicate()
    status_json = {}
    if process.returncode != 0:
      status_json["returncode"] = process.returncode
      status_json["status"] = "ERROR"
      if not stdout:
        status_json["message"] = stderr
      else:
        status_json["message"] = stdout
    else:
      status_json["status"] = "OK" 
      status_json["message"] = stdout
      status_json["returncode"] = 0

    if start_date:
      date_diff = (datetime.utcnow() - start_date)
      status_json["start-date"] = start_date.strftime('%Y-%m-%dT%H:%M:%S')
      status_json["execution-time"] = date_diff.total_seconds()
      self.logger.info("Finished execution of %s in %s second(s)." % (
                    title, date_diff.total_seconds()))
    if title:
      status_json["title"] = title
    return status_json

  def executeCommand(self, args):
    return subprocess.Popen(
      args,
      stdin=None,
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE
    )

  def checkPromisesList(self, promise_dir_list):
    """
      Run all promises found into specified folder
    """
    promise_list = []
    self.logger.info("Checking promises...")
    for promise_dir in promise_dir_list:
      promise_list.extend(_checkPromiseList(
        promise_dir,
        self.promise_timeout,
        profile=False,
        raise_on_failure=False,
        logger=self.logger))

    # Check whether every promise is kept
    for i in range(0, len(promise_list)):
      promise_list[i]["status"] = "OK" if promise_list[i]["returncode"] == 0 else "ERROR"
      promise_list[i]["type"] = "status"
      promise_list[i]["portal-type"] = "promise"
      promise_list[i]["change-time"] = time.mktime(promise_list[i]["start-date"].timetuple())
      promise_list[i]["start-date"] = promise_list[i]["start-date"].strftime('%Y-%m-%dT%H:%M:%S')

    self.logger.info("Finished promises.")
    self.logger.info("---")
    return promise_list


def main():
  arg_parser = parseArguments()
  promise_runner = RunPromise(arg_parser.parse_args())
  sys.exit(promise_runner.runPromise())
