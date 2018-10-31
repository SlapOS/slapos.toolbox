from __future__ import print_function

import argparse
import errno
import glob
import os
import shutil
import subprocess
import sys
import time

from datetime import datetime
from hashlib import sha256
from zc.buildout.configparser import parse


#TODO : Redirect output to log. maybe it can be done at slapos level


os.environ['LC_ALL'] = 'C'
# TODO: check it is the same as umask 077
os.umask(0o77)


class CwdContextManager:
  # Context Manager Class for executing code
  # in a given directory
  # There is no need to provide fallback or basic
  # checks in this code, as these checkes should
  # exist in the code invoking this Context Manager.
  # If someone needs to add checks here, I'm pretty
  # sure it means that they are trying to hide legitimate
  # errors.
  # See tests to see examples of invokation
  def __init__(self, path):
    self.path = path

  def __enter__(self):
    self.oldpath = os.getcwd()
    os.chdir(self.path)

  def __exit__(self, exc_type, exc_value, traceback):
    os.chdir(self.oldpath)


def parseArgumentList():
  parser = argparse.ArgumentParser()
  base_argument_dict = {
    'action': 'store',
    'type': str,
    'required': True,
  }
  parser.add_argument('--srv-path', **base_argument_dict)
  parser.add_argument('--backup-path', **base_argument_dict)
  parser.add_argument('--etc-path', **base_argument_dict)
  parser.add_argument('--tmp-path', **base_argument_dict)
  parser.add_argument('--rsync-binary', **base_argument_dict)
  parser.add_argument('--backup-wait-time', type=int, action='store', required=True)
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
  arg_list.append(source)
  arg_list.append(destination)
  if dry:
    print('DEBUG:', arg_list)
  else:
    rsync_process = subprocess.Popen(arg_list)
    rsync_process.wait()
  # TODO : pipe stdout dans : (egrep -v "$IGNOREOUT" || true) || [ $? = "$IGNOREEXIT" ]
  # with :
  # IGNOREEXIT=24
  # IGNOREOUT='^(file has vanished: |rsync warning: some files vanished before they could be transferred)'


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

  for partition in glob.glob(path + "/instance/slappart*"):
    if not (os.path.exists(partition) and os.path.isdir(partition)):
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


def getSha256Sum(file_path):
  # TODO : introduce reading by chunk,
  # otherwise reading backup files of 5Gb
  # may crash the server.
  # XXX : Use os.open ?
  with open(file_path, 'rb') as f:
    return sha256(f.read()).hexdigest()


def getCustomSignature(signature_script_path, file_path):
  try:
    process = subprocess.Popen([signature_script_path, file_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    process.wait()
  except OSError:
    raise RuntimeError(process.stderr.read())
  return process.stdout.read()


def synchroniseRunnerConfigurationDirectory(config, backup_path):
  rsync(config.rsync_binary, 'config.json', backup_path, dry=config.dry)

  for hidden_file in [
      x for x in os.listdir('.')
      if x[0] == '.'
    ]:
    rsync(config.rsync_binary, hidden_file, backup_path, dry=config.dry)


def synchroniseRunnerWorkingDirectory(config, backup_path):
  if os.path.exists('instance') and os.path.isdir('instance'):
      exclude_list = getExcludePathList('.')
      rsync(
        config.rsync_binary, 'instance', backup_path,
        ["--exclude={}".format(x) for x in exclude_list],
        dry=config.dry,
      )

  for file in ('project', 'public', 'proxy.db'):
    if os.path.exists(file):
      rsync(config.rsync_binary, file, backup_path, dry=config.dry)


def getSlappartSignatureMethodDict():
  slappart_signature_method_dict = {}
  for partition in glob.glob("./instance/slappart*"):
    if os.path.isdir(partition):
      script_path = os.path.join(partition, 'srv', '.backup_identity_script')
      if os.path.exists(script_path):
        slappart_signature_method_dict[partition] = script_path
  return slappart_signature_method_dict


def writeSignatureFile(slappart_signature_method_dict, runner_working_path, signature_file_path='../backup.signature'):
  special_slappart_list = slappart_signature_method_dict.keys()
  signature_list = []

  for dirpath, dirname_list, filename_list in os.walk('.'):
    # Find if special signature function should be applied
    for special_slappart in special_slappart_list:
      if dirpath.startswith(special_slappart):
        signature_function = lambda x: getCustomSignature(os.path.join(runner_working_path, slappart_signature_method_dict[special_slappart]), x)
        break
    else:
      signature_function = getSha256Sum

    # Calculate all signatures
    for filename in filename_list:
      file_path = os.path.join(dirpath, filename)
      signature_list.append("%s  %s" % (signature_function(file_path), os.path.realpath(file_path)))

    # Write the signatures in file
    with open(signature_file_path, 'w+') as signature_file:
      signature_file.write("\n".join(sorted(signature_list)))


def backupFilesWereModifiedDuringExport():
  process = subprocess.Popen(['find', '-cmin',  '0.1', '-type', 'f'], stdout=subprocess.PIPE)
  process.wait()
  changed_file_output = process.stdout.read()
  for line in changed_file_output.split('\n'):
    if '/srv/backup/' in line:
      return True
  return False


def runExport():
  print(datetime.now().isoformat())

  args = parseArgumentList()

  def _rsync(*params):
    return rsync(args.rsync_binary, *params, dry=args.dry)

  runner_working_path = os.path.join(args.srv_path, 'runner')
  backup_runner_path = os.path.join(args.backup_path, 'runner')

  # Synchronise runner's etc directory
  with CwdContextManager(args.etc_path):
    with open('.resilient-timestamp', 'w') as f:
      f.write(datetime.now().strftime("%s"))

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
  with CwdContextManager(backup_runner_path):
    writeSignatureFile(slappart_signature_method_dict, runner_working_path)

  # BBB: clean software folder if it was synchronized
  # in an old instance
  backup_software_path = os.path.join(backup_runner_path, 'software')
  if os.path.exists(backup_software_path) and os.path.isdir(backup_software_path):
    shutil.rmtree(backup_software_path)


  # Wait a little to increase the probability to detect an ongoing backup.
  time.sleep(10)

  # Check that export didn't happen during backup of instances
  with CwdContextManager(backup_runner_path):
    if backupFilesWereModifiedDuringExport():
      print("ERROR: Some backups are not consistent, exporter should be re-run."
            " Let's sleep %s minutes, to let the backup end..." % backup_wait_time)
      time.sleep(backup_wait_time * 60)
      system.exit(1)