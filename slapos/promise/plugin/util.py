import itertools
import json
import logging
import os
import textwrap

from dateutil import parser as dateparser
from datetime import datetime
from slapos.grid.promise.generic import GenericPromise


def iter_reverse_lines(f):
  """
    Read lines from the end of the file
  """
  f.seek(0, os.SEEK_END)
  while True:
    try:
      while f.seek(-2, os.SEEK_CUR) and f.read(1) != b'\n':
        pass
    except OSError:
      return
    pos = f.tell()
    yield f.readline()
    f.seek(pos, os.SEEK_SET)


def iter_logrotate_file_handle(path, mode='r'):
  """
    Yield successive file handles for rotated logs
    (XX.log, XX.log.1, XX.log.2, ...)
  """
  for i in itertools.count():
    path_i = path + str(i or '')
    try:
      with open(path_i, mode) as f:
        yield f
    except OSError:
      break

def get_json_log_data_interval(json_log_file, interval):
  """
    Get all data in the last "interval" seconds from JSON log
    Reads rotated logs too (XX.log, XX.log.1, XX.log.2, ...)
  """
  current_time = datetime.now()
  data_list = []
  for f in iter_logrotate_file_handle(json_log_file, 'rb'):
    for line in iter_reverse_lines(f):
      l = json.loads(line)
      timestamp = dateparser.parse(l['time'])
      if (current_time - timestamp).total_seconds() > interval:
        return data_list
      data_list.append(l['data'])
  return data_list

def get_json_log_latest_timestamp(json_log_file):
  """
    Get latest timestamp from JSON log
    Reads rotated logs too (XX.log, XX.log.1, XX.log.2, ...)
  """
  for f in iter_logrotate_file_handle(json_log_file, 'rb'):
    for line in iter_reverse_lines(f):
      l = json.loads(line)
      return dateparser.parse(l['time']).timestamp()
  return 0


class JSONPromise(GenericPromise):
  def __init__(self, config):
    self.__name = config.get('name', None)
    self.__log_folder = config.get('log-folder', None)

    super(JSONPromise, self).__init__(config)
    json_log_name = os.path.splitext(self.__name)[0] + '.json.log'
    self.__json_log_file = os.path.join(self.__log_folder, json_log_name)
    self.json_logger = self.__make_json_logger(self.__json_log_file)

  def __make_json_logger(self, json_log_file):
    logger = logging.getLogger('json-logger')
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(json_log_file)
    formatter = logging.Formatter(
      '{"time": "%(asctime)s", "log_level": "%(levelname)s"'
      ', "message": "%(message)s", "data": %(data)s}'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

  def get_json_log_data_interval(self, interval):
    return get_json_log_data_interval(self.__json_log_file, interval)

def tail_file(file_path, line_count=10):
  """
  Returns the last lines of file.
  """
  line_list = []
  with open(file_path, 'rb') as f:
    BUFSIZ = 1024
    f.seek(0, 2)
    bytes = f.tell()
    size = line_count + 1
    block = -1
    while size > 0 and bytes > 0:
      if bytes - BUFSIZ > 0:
          # Seek back one whole BUFSIZ
          f.seek(block * BUFSIZ, 2)
          line_list.insert(0, f.read(BUFSIZ).decode())
      else:
          f.seek(0, 0)
          # only read what was not read
          line_list.insert(0, f.read(bytes).decode())
      line_len = line_list[0].count('\n')
      size -= line_len
      bytes -= BUFSIZ
      block -= 1
  return '\n'.join(''.join(line_list).splitlines()[-line_count:])
