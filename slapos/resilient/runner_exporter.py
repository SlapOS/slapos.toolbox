from __future__ import print_function

import argparse
import errno
import glob
import itertools
import os
import re
import shutil
import subprocess
import sys
import time

from contextlib import contextmanager
from datetime import datetime
from hashlib import sha256
from zc.buildout.configparser import parse


os.environ['LC_ALL'] = 'C'
os.umask(0o77)


def read_file_by_chunk(path, chunk_size=1024 * 1024):
  with open(path, 'rb') as f:
    chunk = f.read(chunk_size)
    while chunk:
      yield chunk
      chunk = f.read(chunk_size)


@contextmanager
def CwdContextManager(path):
  """
  Context Manager for executing code in a given directory.
  There is no need to provide fallback or basic checks
  in this code, as these checkes should exist in the code
  invoking this Context Manager.
  If someone needs to add checks here, I'm pretty sure
  it means that they are trying to hide legitimate errors.
  See tests to see examples of invokation
  """
  old_path = os.getcwd()
  try:
    os.chdir(path)
    yield
  finally:
    os.chdir(old_path)


def parseArgumentList():
  parser = argparse.ArgumentParser()
  parser.add_argument('--srv-path', required=True)
  parser.add_argument('--backup-path', required=True)
  parser.add_argument('--etc-path', required=True)
  parser.add_argument('--rsync-binary', default='rsync')
  parser.add_argument('--backup-wait-time', type=int, required=True)
  parser.add_argument('-n', action='store_true', dest='dry', default=False)

  return parser.parse_args()


def rsync(rsync_binary, source, destination, extra_args=None, dry=False):
  arg_list = [
    rsync_binary,
    '-rlptgov',
    '--stats',
    '--safe-links',
    '--ignore-missing-args',
    '--delete',
    '--delete-excluded'
  ]
  if isinstance(extra_args, list):
    arg_list.extend(extra_args)
  if isinstance(source, list):
    arg_list.extend(source)
  else:
    arg_list.append(source)
  arg_list.append(destination)

  if dry:
    print('DEBUG:', arg_list)
    return

  try:
    print(subprocess.check_output(arg_list))
  except subprocess.CalledProcessError as e:
    # All rsync errors are not to be considered as errors
    allowed_error_message_list = \
      '^(file has vanished: |rsync warning: some files vanished before they could be transferred)'
    if e.returncode != 24 or \
        re.search(allowed_error_message_regex, e.output, re.M) is None:
      raise


def getExcludePathList(path):
  excluded_path_list = [
    "*.sock",
    "*.socket",
    "*.pid",
    ".installed*.cfg",
  ]

  def append_relative(path_list):
    for p in path_list:
      p = p.strip()
      if p:
        excluded_path_list.append(os.path.relpath(p, path))

  for partition in glob.glob(os.path.join(path, "instance", "slappart*")):
    if not os.path.isdir(partition):
      continue

    with CwdContextManager(partition):
      try:
        with open("srv/exporter.exclude") as f:
          exclude = f.readlines()
      except IOError as e:
        if e.errno != errno.ENOENT:
          raise
      else:
        append_relative(exclude)
      for installed in glob.glob(".installed*.cfg"):
        try:
          with open(installed) as f:
            installed = parse(f, installed)
        except IOError as e:
          if e.errno != errno.ENOENT:
            raise
        else:
          for section in installed.itervalues():
            append_relative(section.get(
              '__buildout_installed__', '').splitlines())

  return excluded_path_list


def getSha256Sum(file_path_list):
  result_list = []

  for file_path in file_path_list:
    hash_sum = sha256()
    for chunk in read_file_by_chunk(file_path):
      hash_sum.update(chunk)
    result_list.append("%s  %s" % (hash_sum.hexdigest(), file_path))

  return result_list


def synchroniseRunnerConfigurationDirectory(config, backup_path):
  if not os.path.exists(backup_path):
    os.makedirs(backup_path)

  file_list = ['config.json']
  for hidden_file in os.listdir('.'):
    if hidden_file[0] == '.':
      file_list.append(hidden_file)
  rsync(config.rsync_binary, file_list, backup_path, dry=config.dry)


def synchroniseRunnerWorkingDirectory(config, backup_path):
  file_list = []
  exclude_list = []

  if os.path.isdir('instance'):
    file_list.append('instance')
    exclude_list = getExcludePathList(os.getcwd())

  # XXX: proxy.db should be properly dumped to leverage its
  # atomic properties
  for file in ('project', 'public', 'proxy.db'):
    if os.path.exists(file):
      file_list.append(file)

  if file_list:
    rsync(
      config.rsync_binary, file_list, backup_path,
      ["--exclude={}".format(x) for x in exclude_list],
      dry=config.dry
    )


def getSlappartSignatureMethodDict():
  slappart_signature_method_dict = {}
  for partition in glob.glob("./instance/slappart*"):
    if os.path.isdir(partition):
      script_path = os.path.join(partition, 'srv', '.backup_identity_script')
      if os.path.exists(script_path):
        slappart_signature_method_dict[partition] = script_path
  return slappart_signature_method_dict


def writeSignatureFile(slappart_signature_method_dict, runner_working_path, signature_file_path='backup.signature'):
  special_slappart_list = slappart_signature_method_dict.keys()
  signature_list = []

  for dirpath, dirname_list, filename_list in os.walk('.'):
    if dirpath == '.' or not filename_list:
      continue

    # Find if special signature function should be applied
    for special_slappart in special_slappart_list:
      backup_identity_script_path = os.path.join(
        runner_working_path,
        slappart_signature_method_dict[special_slappart]
      )

      if dirpath.startswith(special_slappart):
        signature_process = subprocess.Popen(
          backup_identity_script_path,
          stdin=subprocess.PIPE,
          stdout=subprocess.PIPE,
        )

        for filename in filename_list:
          signature_process.stdin.write(os.path.join(dirpath, filename) + '\0')
        signature_process.stdin.close()

        output = signature_process.stdout.read()
        while signature_process.poll() is None:
          time.sleep(1)
          output += signature_process.stdout.read()
        output += signature_process.stdout.read()

        if signature_process.returncode != 0:
          print(
            "An issue occured when calculating the custom signature"
            " with %s :\n%s" % (
              backup_identity_script_path, signature_process.stderr.read()
            )
          )
          system.exit(1)

        # We have to rstrip as most programs return an empty line
        # at the end of their output
        signature_list.extend(output.strip('\n').split('\n'))
      else:
        signature_list.extend(
          getSha256Sum([
            os.path.join(dirpath, filename)
            for filename in filename_list
          ])
        )

    # Write the signatures in file
    with open(signature_file_path, 'w+') as signature_file:
      signature_file.write("\n".join(sorted(signature_list)))


def backupFilesWereModifiedDuringExport(export_start_date):
  export_time = time.time() - export_start_date
  return bool(
    subprocess.check_output((
      'find', '-cmin',  str(export_time / 60.), '-type', 'f', '-path', '*/srv/backup/*'
    ))
  )


def runExport():
  export_start_date = int(time.time())
  print(datetime.fromtimestamp(export_start_date).isoformat())

  args = parseArgumentList()

  def _rsync(*params):
    return rsync(args.rsync_binary, *params, dry=args.dry)

  runner_working_path = os.path.join(args.srv_path, 'runner')
  backup_runner_path = os.path.join(args.backup_path, 'runner')

  # Synchronise runner's etc directory
  with CwdContextManager(args.etc_path):
    with open('.resilient-timestamp', 'w') as f:
      f.write(str(export_start_date))

    # "+ '/'" is mandatory otherwise rsyncing the etc directory
    # will create in the backup_etc_path only a file called etc
    backup_etc_path = os.path.join(args.backup_path, 'etc') + '/'
    synchroniseRunnerConfigurationDirectory(args, backup_etc_path)

  # Synchronise runner's working directory
  # and aggregate signature functions as we are here
  with CwdContextManager(runner_working_path):
    synchroniseRunnerWorkingDirectory(args, backup_runner_path)
    slappart_signature_method_dict = getSlappartSignatureMethodDict()

  # Calculate signature of synchronised files
  with CwdContextManager(args.backup_path):
    writeSignatureFile(slappart_signature_method_dict, runner_working_path)

  # BBB: clean software folder if it was synchronized
  # in an old instance
  backup_software_path = os.path.join(backup_runner_path, 'software')
  if os.path.isdir(backup_software_path):
    shutil.rmtree(backup_software_path)


  # Wait a little to increase the probability to detect an ongoing backup.
  time.sleep(10)

  # Check that export didn't happen during backup of instances
  with CwdContextManager(backup_runner_path):
    if backupFilesWereModifiedDuringExport(export_start_date):
      print("ERROR: Some backups are not consistent, exporter should be re-run."
            " Let's sleep %s minutes, to let the backup end..." % backup_wait_time)
      time.sleep(backup_wait_time * 60)
      system.exit(1)