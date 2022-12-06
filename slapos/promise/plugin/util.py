import json
import logging
import os

from dateutil import parser
from slapos.grid.promise.generic import GenericPromise

def tail_file(file_path, line_count=10):
  """
  Returns the last lines of file.
  """

  line_list = []
  with open(file_path) as f:
    BUFSIZ = 1024
    f.seek(0, 2)
    bytes = f.tell()
    size = line_count + 1
    block = -1
    while size > 0 and bytes > 0:
      if bytes - BUFSIZ > 0:
          # Seek back one whole BUFSIZ
          f.seek(block * BUFSIZ, 2)
          line_list.insert(0, f.read(BUFSIZ))
      else:
          f.seek(0, 0)
          # only read what was not read
          line_list.insert(0, f.read(bytes))
      line_len = line_list[0].count('\n')
      size -= line_len
      bytes -= BUFSIZ
      block -= 1

  return '\n'.join(''.join(line_list).splitlines()[-line_count:])

class JSONRunPromise(GenericPromise):

  def __init__(self, config):

    self.__name = config.get('name', None)
    self.__log_folder = config.get('log-folder', None)
    super(JSONRunPromise, self).__init__(config)

    self.__title = os.path.splitext(self.__name)[0]
    self.log_file = os.path.join(self.__log_folder, '%s.json.log' % self.__title)

    self.json_logger = logging.getLogger('json_logger')
    self.json_logger.setLevel(logging.INFO)
    handler = logging.FileHandler(self.log_file)
    formatter = logging.Formatter('{"time": "%(asctime)s", "log_level": '\
      '"%(levelname)s", "message": "%(message)s", "data": %(data)s}')
    handler.setFormatter(formatter)
    self.json_logger.addHandler(handler)

def get_data_interval_json_log(log, interval):
  """
    Get all data in the last "interval" seconds from JSON log
    Reads rotated logs too (XX.log, XX.log.1, XX.log.2, ...)
  """

  log_number = 0
  latest_timestamp = 0
  data_list = []

  while True:
    try:
      f = open("{}.{}".format(log, log_number) if log_number else log, "rb")
    except OSError:
      return data_list
    try:
      f.seek(0, os.SEEK_END)
      while True:
        try:
          while f.seek(-2, os.SEEK_CUR) and f.read(1) != b'\n':
            pass
        except OSError:
          break
        pos = f.tell()
        l = json.loads(f.readline().decode().replace("'", '"'))
        timestamp = parser.parse(l['time'])
        data_list.append(l['data'])
        if not latest_timestamp:
          latest_timestamp = timestamp
        if (latest_timestamp - timestamp).total_seconds() > interval:
          return data_list
        f.seek(pos, os.SEEK_SET)
    finally:
      f.close()
    log_number += 1

def get_latest_timestamp_json_log(log):
  """
    Get latest timestamp from JSON log                                                                                                                                                              
    Reads rotated logs too (XX.log, XX.log.1, XX.log.2, ...)
  """

  log_number = 0

  while True:
    try:
      f = open("{}.{}".format(log, log_number) if log_number else log, "rb")
    except OSError:
      return 0
    try:
      f.seek(0, os.SEEK_END)
      try:
        while f.seek(-2, os.SEEK_CUR) and f.read(1) != b'\n':
          pass
      except OSError:
        break
      l = json.loads(f.readline().decode().replace("'", '"'))
      return parser.parse(l['time'])
    finally:
      f.close()
    log_number += 1
  return 0
