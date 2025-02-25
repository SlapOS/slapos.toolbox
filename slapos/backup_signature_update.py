import click
import os
import hashlib


@click.command(short_help="Times slapos instance log files")
@click.argument(
  'directory',
  nargs=1,
  type=click.Path(),
)
@click.argument(
  'signature_file_name',
  nargs=1,
  type=click.Path(),
)
def cli(directory, signature_file_name):
  """
  Updates SIGNATURE_FILE_NAME in DIRECTORY with sha256 sums of DIRECTORY
  contents.
  """
  directory = directory.rstrip('/') + '/'
  signature_file = os.path.join(directory, signature_file_name)
  current_signature = {}
  new_signature = {}
  if os.path.exists(signature_file):
    signature_modification = os.path.getmtime(signature_file)
    with open(signature_file) as fh:
      for line in fh.readlines():
        checksum, filename = line.strip().split()
        current_signature[filename] = checksum
  else:
    signature_modification = 0
  for root, directory_list, file_list in os.walk(directory):
    for filename in file_list:
      filepath = os.path.join(root, filename)
      signature_path = filepath.replace(directory, './')
      if signature_path == './' + signature_file_name:
        continue
      file_modification = os.path.getmtime(filepath)
      if file_modification > signature_modification:
        with open(filepath, 'rb') as fh:
          file_hash = hashlib.sha256()
          while chunk := fh.read(2**20):
            file_hash.update(chunk)
          new_signature[signature_path] = file_hash.hexdigest()
        print(f'Updated {signature_path}')
      else:
        print(f'Kept old {signature_path}')
        new_signature[signature_path] = current_signature[signature_path]

  if new_signature != current_signature or not os.path.exists(signature_file):
    with open(signature_file, 'w') as fh:
      for signature_path in sorted(new_signature):
        checksum = new_signature[signature_path]
        fh.write(f'{checksum}  {signature_path}\n')
    print(f'Updated content {signature_file}')
  else:
    print(f'Kept content {signature_file}')
