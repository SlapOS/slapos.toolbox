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

import click
import hashlib
import os
import pprint
import sys
import time


def update(force, directory, signature_file_name, proof_signature_path):
  if proof_signature_path is not None:
    signature_file = proof_signature_path
  else:
    signature_file = os.path.join(directory, signature_file_name)
  current_signature = {}
  new_signature = {}
  if force or not os.path.exists(signature_file):
    signature_modification = 0
  else:
    signature_modification = os.path.getmtime(signature_file)
    with open(signature_file) as fh:
      for line in fh.readlines():
        line = line.strip()
        line_split = line.split(maxsplit=1)
        if len(line_split) != 2:
          print(f'WARNING: Bad line {line}')
          continue
        checksum = line_split[0]
        filename = line_split[1]
        current_signature[filename] = checksum
  for root, directory_list, file_list in os.walk(directory):
    for filename in sorted(file_list):
      filepath = os.path.join(root, filename)
      signature_path = filepath.replace(directory, './')
      if signature_path == './' + signature_file_name:
        continue
      file_modification = os.path.getmtime(filepath)
      if file_modification > signature_modification \
         or signature_path not in current_signature:
        with open(filepath, 'rb') as fh:
          file_hash = hashlib.sha256()
          while chunk := fh.read(2**20):
            file_hash.update(chunk)
          new_signature[signature_path] = file_hash.hexdigest()
        print(f'INFO: Updated {signature_path}')
      else:
        print(f'INFO: Kept {signature_path}')
        new_signature[signature_path] = current_signature[signature_path]

  if new_signature != current_signature or not os.path.exists(signature_file):
    with open(signature_file, 'w') as fh:
      for signature_path in sorted(new_signature):
        checksum = new_signature[signature_path]
        fh.write(f'{checksum}  {signature_path}\n')
    print(f'INFO: Updated {signature_file}')
  else:
    print(f'INFO: Kept {signature_file}')


def validate(force, directory, signature_file_name, validate_timestamp_file):
  signature_file = os.path.join(directory, signature_file_name)
  if not os.path.exists(signature_file):
    print(f'ERROR: Signature file {signature_file} not found')
    sys.exit(1)

  if force or validate_timestamp_file is None \
     or not os.path.exists(validate_timestamp_file):
    validate_timestamp = 0
  else:
    print(f'DEBUG: Using {validate_timestamp_file}')
    validate_timestamp = os.path.getmtime(validate_timestamp_file)

  current_signature = {}
  new_signature = {}
  signature_error_count = 0
  with open(signature_file) as fh:
    for line in fh.readlines():
      line = line.strip()
      line_split = line.split(maxsplit=1)
      if len(line_split) != 2:
        print(f'ERROR: Bad line {line}')
        signature_error_count += 1
        continue
      checksum = line_split[0]
      filename = line_split[1]
      current_signature[filename] = checksum

  for root, directory_list, file_list in os.walk(directory):
    for filename in sorted(file_list):
      filepath = os.path.join(root, filename)
      signature_path = filepath.replace(directory, './')
      if signature_path == './' + signature_file_name:
        continue
      file_modification = os.path.getmtime(filepath)
      if signature_path in current_signature \
         and file_modification < validate_timestamp:
        new_signature[signature_path] = current_signature[signature_path]
        print(f'DEBUG: Skipped {signature_path}')
      else:
        with open(filepath, 'rb') as fh:
          file_hash = hashlib.sha256()
          while chunk := fh.read(2**20):
            file_hash.update(chunk)
          new_signature[signature_path] = file_hash.hexdigest()
        print(f'DEBUG: Calculated {signature_path}')

  if new_signature != current_signature:
    print('ERROR: Signatures do not match, current signature:')
    pprint.pprint(current_signature)
    print('Calculated signature:')
    pprint.pprint(new_signature)
    sys.exit(1)
  else:
    print('OK: Signature match.')
    if validate_timestamp_file is not None:
      with open(validate_timestamp_file, 'w') as fh:
        fh.write(str(time.time()))
      print(f'DEBUG: Updated {validate_timestamp_file}')
    if signature_error_count > 0:
      print(
        f'ERROR: Signature {signature_file} errors: {signature_error_count}')
      sys.exit(2)


@click.command(short_help="Backup signature handling")
@click.option(
  '--action',
  type=click.Choice(['update', 'validate'], case_sensitive=False),
  required=True,
  help="Action to take"
)
@click.option(
  '--directory',
  type=click.Path(),
  required=True,
  help="Directory to work in"
)
@click.option(
  '--signature-file-name',
  type=click.Path(),
  required=True,
  help="Name of signature file, expected in top of the --directory"
)
@click.option(
  '--proof-signature-path',
  type=click.Path(),
  help="Path to proof signature, which will be updated instead of "
       "backup signature"
)
@click.option(
  '--validate-timestamp-file',
  type=click.Path(),
  help="Location of file which modification time relates to last validation, "
       "so that only files not validated before will be checksummed"
)
@click.option(
  '--force',
  is_flag=True,
  default=False,
  show_default=True,
  help="Forces full run"
)
def cli(
  action, force, directory, signature_file_name, validate_timestamp_file,
  proof_signature_path):
  """
  Tool to handle backup and validation signatures

  The most useful action is update, which will update the signature-file-name
  inside of the directory. When proof-signature-path is provided, it'll fill
  it of checksums from directory, ignoring signature-file-name.

  The validate action allows to check is files are matching the checksums
  stored in signature-file-name. When validate-timestamp-file is provided this
  file will be used to only check newly appeared files.

  --force option allows to do the check or validate without any optimisation.
  """
  directory = directory.rstrip('/') + '/'
  if action == 'update':
    update(force, directory, signature_file_name, proof_signature_path)
  elif action == 'validate':
    validate(force, directory, signature_file_name, validate_timestamp_file)
