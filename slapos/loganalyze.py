# coding: utf-8
# Copyright (C) 2025  Nexedi SA and Contributors.
#                     Łukasz Nowak <luke@nexedi.com>
#
# This program is free software: you can Use, Study, Modify and Redistribute
# it under the terms of the GNU General Public License version 3, or (at your
# option) any later version, as published by the Free Software Foundation.
#
# You can also Link and Combine this program with other software covered by
# the terms of any of the Free Software licenses or any of the Open Source
# Initiative approved licenses and Convey the resulting work. Corresponding
# source of such a combination shall include the source code for all other
# software used.
#
# This program is distributed WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See COPYING file for full licensing terms.
# See https://www.nexedi.com/licensing for rationale and options.

import datetime
import gzip
import re
import contextlib
import click

TIMESTAMP_DETECT = re.compile(r'\[(?P<timestamp>.*)\].*')
PROCESSING_DETECT = re.compile(
  r'\[(?P<timestamp>.*)\].* Processing Computer Partition (?P<partition>.*)\.')
ERROR_DETECT = re.compile(
  r'\[(?P<timestamp>.*)\].* ERROR.* Failed to run buildout profile in directo'
  'ry.*')
SOFTWARE_DETECT = re.compile(r'.*Software URL: (?P<software_release>.*)')
VERSION_DETECT = re.compile(r'.*(?P<version>1\.0\.[0-9]+)/.*')


@contextlib.contextmanager
def auto_open(filename, mode):
  if filename.endswith('.gz'):
    with gzip.open(filename, mode) as f:
      yield f
  else:
    with open(filename, mode) as f:
      yield f


@click.command(short_help="Times slapos instance log files")
@click.argument(
  'file_list',
  nargs=-1,
  type=click.Path(),  # can't use click.File, as existence is required and
                      # that increases usage complexity
)
def main(file_list):
  """
  Allows to analyze and time slapos node log files.
  FILE_LIST can be provided in order, then analysis continuity will be kept.
  """
  processing_state = {}
  for filename in file_list:
    with auto_open(filename, mode='rt') as fh:
      for line in fh.readlines():
        line = line.strip()[:500]
        if not line.startswith('['):
          continue
        processing = PROCESSING_DETECT.fullmatch(line)
        if processing:
          run_id = processing.groupdict()['timestamp'].split(',')[0]
          timestamp = datetime.datetime.strptime(
            run_id, '%Y-%m-%d %H:%M:%S').timestamp()
          if 'start' not in processing_state:
            processing_state['run_id'] = run_id
            processing_state['start'] = timestamp
            processing_state['partition'] = processing.groupdict()['partition']
            processing_state['status'] = 'OK'
          else:
            processing_state['end'] = datetime.datetime.strptime(
              processing_state['previous_timestamp'], '%Y-%m-%d %H:%M:%S'
            ).timestamp()
            processing_state['elapsed'] = int(
              processing_state['end'] - processing_state['start'])
            print(
              '%(partition)s;%(run_id)s;%(version)s;%(status)s;%(elapsed)s'
              % processing_state)
            processing_state['run_id'] = run_id
            processing_state['start'] = timestamp
            processing_state['partition'] = processing.groupdict()['partition']
            processing_state['status'] = 'OK'
          continue
        processing_state['previous_timestamp'] = TIMESTAMP_DETECT.fullmatch(
          line).groupdict()['timestamp'].split(',')[0]
        error = ERROR_DETECT.fullmatch(line)
        if error:
          processing_state['status'] = 'ERR'
        software = SOFTWARE_DETECT.fullmatch(line)
        if software:
          software_release = software.groupdict()['software_release']
          version = VERSION_DETECT.fullmatch(software_release)
          if version is not None:
            processing_state['version'] = version['version']
          else:
            processing_state['version'] = software_release
          continue
  else:
    processing_state['end'] = datetime.datetime.strptime(
      processing_state['previous_timestamp'], '%Y-%m-%d %H:%M:%S').timestamp()
    processing_state['elapsed'] = int(
      processing_state['end'] - processing_state['start'])
    if processing_state['status'] != 'ERR':
      processing_state['status'] = 'UNK/LAST'
    print(
      '%(partition)s;%(run_id)s;%(version)s;%(status)s;%(elapsed)s'
      % processing_state)


if __name__ == '__main__':
  main()
