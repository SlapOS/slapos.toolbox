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
        print(f'INFO: Kept old {signature_path}')
        new_signature[signature_path] = current_signature[signature_path]

  if new_signature != current_signature or not os.path.exists(signature_file):
    with open(signature_file, 'w') as fh:
      for signature_path in sorted(new_signature):
        checksum = new_signature[signature_path]
        fh.write(f'{checksum}  {signature_path}\n')
    print(f'INFO: Updated content {signature_file}')
  else:
    print(f'INFO: Kept content {signature_file}')


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
  with open(signature_file) as fh:
    for line in fh.readlines():
      line = line.strip()
      line_split = line.split(maxsplit=1)
      if len(line_split) != 2:
        print(f'WARNING: Bad line {line}')
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


@click.command(short_help="Backup signature handling")
@click.option(
  '--action',
  type=click.Choice(['update', 'validate'], case_sensitive=False),
  required=True,
  help="Action to take"
)
@click.option(
  '--force',
  is_flag=True,
  default=False,
  show_default=True,
  help="Forces full run"
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
def cli(
  action, force, directory, signature_file_name, validate_timestamp_file,
  proof_signature_path):
  """
  Allow to update and validate backup signature in the backup directory.
  """
  directory = directory.rstrip('/') + '/'
  if action == 'update':
    update(force, directory, signature_file_name, proof_signature_path)
  elif action == 'validate':
    validate(force, directory, signature_file_name, validate_timestamp_file)
