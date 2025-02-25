from click.testing import CliRunner
import hashlib
import os
import pathlib
import shutil
import tempfile
import time
import unittest

import slapos.backup_signature


def sorted_listdir(d):
  return sorted(os.listdir(d))


def invoke(argument):
  return CliRunner().invoke(
    slapos.backup_signature.cli,
    argument.split()
  )


class Test(unittest.TestCase):
  def setUp(self):
    self.workdir = tempfile.mkdtemp()
    self.backupdir = os.path.join(self.workdir, 'backup')
    os.mkdir(self.backupdir)

    self.test_data_00 = 'Some test data'
    self.test_data_00_sum = hashlib.sha256(
      self.test_data_00.encode()).hexdigest()
    self.test_file_00 = 'test file'
    with open(os.path.join(self.backupdir, self.test_file_00), 'w') as fh:
     fh.write(self.test_data_00)

    self.test_data_01 = 'Other test data'
    self.test_data_01_sum = hashlib.sha256(
      self.test_data_01.encode()).hexdigest()
    self.test_file_01 = 'test other file'

  def tearDown(self):
    shutil.rmtree(self.workdir)

  def test_update(self):
    result = invoke(
      f'--action update --directory {self.backupdir} '
      '--signature-file-name backup-signature')
    self.assertEqual(result.exit_code, 0)
    self.assertEqual(
      result.output,
      f"INFO: Updated ./{self.test_file_00}\n"
      f"INFO: Updated {self.backupdir}/backup-signature\n"
    )
    self.assertEqual(
      ['backup-signature', f'{self.test_file_00}'],
      sorted_listdir(self.backupdir)
    )
    with open(os.path.join(self.backupdir, 'backup-signature')) as fh:
      self.assertEqual(
        f'{self.test_data_00_sum}  ./{self.test_file_00}\n', fh.read())

  def test_update_directory_with_slash(self):
    self.assertFalse(self.backupdir.endswith('/'))
    result = invoke(
      f'--action update --directory {self.backupdir}// '
      '--signature-file-name backup-signature')
    self.assertEqual(result.exit_code, 0)
    self.assertEqual(
      result.output,
      f"INFO: Updated ./{self.test_file_00}\n"
      f"INFO: Updated {self.backupdir}/backup-signature\n"
    )
    self.assertEqual(
      ['backup-signature', f'{self.test_file_00}'],
      sorted_listdir(self.backupdir)
    )
    with open(os.path.join(self.backupdir, 'backup-signature')) as fh:
      self.assertEqual(
        f'{self.test_data_00_sum}  ./{self.test_file_00}\n', fh.read())

  def test_update_bad_line(self):
    with open(os.path.join(self.backupdir, 'backup-signature'), 'w') as fh:
     fh.write('badline\n')
    result = invoke(
      f'--action update --directory {self.backupdir} '
      '--signature-file-name backup-signature')
    self.assertEqual(result.exit_code, 0)
    self.assertEqual(
      result.output,
      "WARNING: Bad line badline\n"
      f"INFO: Updated ./{self.test_file_00}\n"
      f"INFO: Updated {self.backupdir}/backup-signature\n"
    )
    self.assertEqual(
      ['backup-signature', f'{self.test_file_00}'],
      sorted_listdir(self.backupdir)
    )
    with open(os.path.join(self.backupdir, 'backup-signature')) as fh:
      self.assertEqual(
        f'{self.test_data_00_sum}  ./{self.test_file_00}\n', fh.read())

  def test_update_create_proof_signature(self):
    proof_signature = os.path.join(self.workdir, 'proof.signature')
    result = invoke(
      f'--action update --directory {self.backupdir} '
      '--signature-file-name backup-signature '
      f'--proof-signature-path {proof_signature}')
    self.assertEqual(result.exit_code, 0)
    self.assertEqual(
      result.output,
      f"INFO: Updated ./{self.test_file_00}\n"
      f"INFO: Updated {proof_signature}\n"
    )
    self.assertEqual(
      [f'{self.test_file_00}'],
      sorted_listdir(self.backupdir)
    )
    with open(proof_signature) as fh:
      self.assertEqual(
        f'{self.test_data_00_sum}  ./{self.test_file_00}\n', fh.read())

  def test_update_deep_signature(self):
    os.mkdir(os.path.join(self.backupdir, 'path'))
    result = invoke(
      f'--action update --directory {self.backupdir} '
      '--signature-file-name path/backup-signature')
    self.assertEqual(result.exit_code, 0)
    self.assertEqual(
      result.output,
      f"INFO: Updated ./{self.test_file_00}\n"
      f"INFO: Updated {self.backupdir}/path/backup-signature\n"
    )
    self.assertEqual(
      ['path', f'{self.test_file_00}'],
      sorted_listdir(self.backupdir)
    )
    with open(os.path.join(self.backupdir, 'path', 'backup-signature')) as fh:
      self.assertEqual(
        f'{self.test_data_00_sum}  ./{self.test_file_00}\n', fh.read())

  def test_update_noop(self):
    self.test_update()
    result = invoke(
      f'--action update --directory {self.backupdir} '
      '--signature-file-name backup-signature')
    self.assertEqual(result.exit_code, 0)
    self.assertEqual(
      result.output,
      f"INFO: Kept ./{self.test_file_00}\n"
      f"INFO: Kept {self.backupdir}/backup-signature\n"
    )
    self.assertEqual(
      ['backup-signature', f'{self.test_file_00}'],
      sorted_listdir(self.backupdir)
    )
    with open(os.path.join(self.backupdir, 'backup-signature')) as fh:
      self.assertEqual(
        f'{self.test_data_00_sum}  ./{self.test_file_00}\n', fh.read())

  def test_update_proof_signature(self):
    self.test_update()
    proof_signature = os.path.join(self.workdir, 'proof.signature')
    result = invoke(
      f'--action update --directory {self.backupdir} '
      '--signature-file-name backup-signature '
      f'--proof-signature-path {proof_signature}')
    self.assertEqual(result.exit_code, 0)
    self.assertEqual(
      result.output,
      f"INFO: Updated ./{self.test_file_00}\n"
      f"INFO: Updated {proof_signature}\n"
    )
    self.assertEqual(
      ['backup-signature', f'{self.test_file_00}'],
      sorted_listdir(self.backupdir)
    )
    with open(os.path.join(self.backupdir, 'backup-signature')) as fh:
      self.assertEqual(
        f'{self.test_data_00_sum}  ./{self.test_file_00}\n', fh.read())

    with open(proof_signature) as fh:
      self.assertEqual(
        f'{self.test_data_00_sum}  ./{self.test_file_00}\n', fh.read())

  def test_update_noop_force(self):
    self.test_update()
    result = invoke(
      f'--action update --force --directory {self.backupdir} '
      '--signature-file-name backup-signature')
    self.assertEqual(result.exit_code, 0)
    self.assertEqual(
      result.output,
      f"INFO: Updated ./{self.test_file_00}\n"
      f"INFO: Updated {self.backupdir}/backup-signature\n"
    )
    self.assertEqual(
      ['backup-signature', f'{self.test_file_00}'],
      sorted_listdir(self.backupdir)
    )
    with open(os.path.join(self.backupdir, 'backup-signature')) as fh:
      self.assertEqual(
        f'{self.test_data_00_sum}  ./{self.test_file_00}\n', fh.read())

  def test_update_change(self):
    self.test_update()
    time.sleep(.5)
    with open(os.path.join(self.backupdir, self.test_file_00), 'w') as fh:
     fh.write(self.test_data_01)
    result = invoke(
      f'--action update --directory {self.backupdir} '
      '--signature-file-name backup-signature')
    self.assertEqual(result.exit_code, 0)
    self.assertEqual(
      result.output,
      f"INFO: Updated ./{self.test_file_00}\n"
      f"INFO: Updated {self.backupdir}/backup-signature\n"
    )
    self.assertEqual(
      ['backup-signature', f'{self.test_file_00}'],
      sorted_listdir(self.backupdir)
    )
    with open(os.path.join(self.backupdir, 'backup-signature')) as fh:
      self.assertEqual(
        f'{self.test_data_01_sum}  ./{self.test_file_00}\n', fh.read())

  def test_update_change_proof_signature(self):
    self.test_update()
    proof_signature = os.path.join(self.workdir, 'proof.signature')
    result = invoke(
      f'--action update --directory {self.backupdir} '
      '--signature-file-name backup-signature '
      f'--proof-signature-path {proof_signature}')
    self.assertEqual(result.exit_code, 0)
    self.assertEqual(
      result.output,
      f"INFO: Updated ./{self.test_file_00}\n"
      f"INFO: Updated {proof_signature}\n"
    )
    self.assertEqual(
      ['backup-signature', f'{self.test_file_00}'],
      sorted_listdir(self.backupdir)
    )
    with open(proof_signature) as fh:
      self.assertEqual(
        f'{self.test_data_00_sum}  ./{self.test_file_00}\n', fh.read())
    time.sleep(.5)
    with open(os.path.join(self.backupdir, self.test_file_00), 'w') as fh:
     fh.write(self.test_data_01)
    result = invoke(
      f'--action update --directory {self.backupdir} '
      '--signature-file-name backup-signature')
    self.assertEqual(result.exit_code, 0)
    self.assertEqual(
      result.output,
      f"INFO: Updated ./{self.test_file_00}\n"
      f"INFO: Updated {self.backupdir}/backup-signature\n"
    )
    self.assertEqual(
      ['backup-signature', f'{self.test_file_00}'],
      sorted_listdir(self.backupdir)
    )
    with open(os.path.join(self.backupdir, 'backup-signature')) as fh:
      self.assertEqual(
        f'{self.test_data_01_sum}  ./{self.test_file_00}\n', fh.read())

    result = invoke(
      f'--action update --directory {self.backupdir} '
      '--signature-file-name backup-signature '
      f'--proof-signature-path {proof_signature}')
    self.assertEqual(result.exit_code, 0)
    self.assertEqual(
      result.output,
      f"INFO: Updated ./{self.test_file_00}\n"
      f"INFO: Updated {proof_signature}\n"
    )
    self.assertEqual(
      ['backup-signature', f'{self.test_file_00}'],
      sorted_listdir(self.backupdir)
    )
    with open(proof_signature) as fh:
      self.assertEqual(
        f'{self.test_data_01_sum}  ./{self.test_file_00}\n', fh.read())

  def test_update_change_older(self):
    self.test_update()
    time.sleep(.5)
    with open(os.path.join(self.backupdir, self.test_file_00), 'w') as fh:
     fh.write(self.test_data_01)
    time.sleep(.5)
    pathlib.Path(os.path.join(self.backupdir, 'backup-signature')).touch()
    result = invoke(
      f'--action update --directory {self.backupdir} '
      '--signature-file-name backup-signature')
    self.assertEqual(result.exit_code, 0)
    self.assertEqual(
      result.output,
      f"INFO: Kept ./{self.test_file_00}\n"
      f"INFO: Kept {self.backupdir}/backup-signature\n"
    )
    self.assertEqual(
      ['backup-signature', f'{self.test_file_00}'],
      sorted_listdir(self.backupdir)
    )
    with open(os.path.join(self.backupdir, 'backup-signature')) as fh:
      self.assertEqual(
        f'{self.test_data_00_sum}  ./{self.test_file_00}\n', fh.read())

    # force is needed
    result = invoke(
      f'--action update --force --directory {self.backupdir} '
      '--signature-file-name backup-signature')
    self.assertEqual(result.exit_code, 0)
    self.assertEqual(
      result.output,
      f"INFO: Updated ./{self.test_file_00}\n"
      f"INFO: Updated {self.backupdir}/backup-signature\n"
    )
    self.assertEqual(
      ['backup-signature', f'{self.test_file_00}'],
      sorted_listdir(self.backupdir)
    )
    with open(os.path.join(self.backupdir, 'backup-signature')) as fh:
      self.assertEqual(
        f'{self.test_data_01_sum}  ./{self.test_file_00}\n', fh.read())

  def test_update_add(self):
    self.test_update()
    with open(os.path.join(self.backupdir, self.test_file_01), 'w') as fh:
     fh.write(self.test_data_01)
    result = invoke(
      f'--action update --directory {self.backupdir} '
      '--signature-file-name backup-signature')
    self.assertEqual(result.exit_code, 0)
    self.assertEqual(
      result.output,
      f"INFO: Kept ./{self.test_file_00}\n"
      f"INFO: Updated ./{self.test_file_01}\n"
      f"INFO: Updated {self.backupdir}/backup-signature\n"
    )
    self.assertEqual(
      ['backup-signature', f'{self.test_file_00}', f'{self.test_file_01}'],
      sorted_listdir(self.backupdir)
    )
    with open(os.path.join(self.backupdir, 'backup-signature')) as fh:
      self.assertEqual(
        f'{self.test_data_00_sum}  ./{self.test_file_00}\n'
        f'{self.test_data_01_sum}  ./{self.test_file_01}\n',
        fh.read())

  def test_update_remove(self):
    self.test_update_add()
    os.unlink(os.path.join(self.backupdir, self.test_file_01))
    result = invoke(
      f'--action update --directory {self.backupdir} '
      '--signature-file-name backup-signature')
    self.assertEqual(result.exit_code, 0)
    self.assertEqual(
      result.output,
      f"INFO: Kept ./{self.test_file_00}\n"
      f"INFO: Updated {self.backupdir}/backup-signature\n"
    )
    self.assertEqual(
      ['backup-signature', f'{self.test_file_00}'],
      sorted_listdir(self.backupdir)
    )
    with open(os.path.join(self.backupdir, 'backup-signature')) as fh:
      self.assertEqual(
        f'{self.test_data_00_sum}  ./{self.test_file_00}\n',
        fh.read())

  def test_validate(self):
    backup_signature = os.path.join(self.backupdir, 'backup-signature')
    with open(backup_signature, 'w') as fh:
     fh.write(f'{self.test_data_00_sum}  ./{self.test_file_00}\n')
    result = invoke(
      f'--action validate --directory {self.backupdir} '
      '--signature-file-name backup-signature')
    self.assertEqual(result.exit_code, 0)
    self.assertEqual(
      result.output,
      f"DEBUG: Calculated ./{self.test_file_00}\n"
      "OK: Signature match.\n"
    )

  def test_validate_bad_line(self):
    backup_signature = os.path.join(self.backupdir, 'backup-signature')
    with open(backup_signature, 'w') as fh:
     fh.write(
       'badline\n'
       f'{self.test_data_00_sum}  ./{self.test_file_00}\n'
     )
    result = invoke(
      f'--action validate --directory {self.backupdir} '
      '--signature-file-name backup-signature')
    self.assertEqual(result.exit_code, 2)
    self.assertEqual(
      result.output,
      "ERROR: Bad line badline\n"
      f"DEBUG: Calculated ./{self.test_file_00}\n"
      "OK: Signature match.\n"
      f"ERROR: Signature {backup_signature} errors: 1\n"
    )

  def test_validate_no_match(self):
    backup_signature = os.path.join(self.backupdir, 'backup-signature')
    with open(backup_signature, 'w') as fh:
     fh.write(f'{self.test_data_00_sum}a  ./{self.test_file_00}\n')
    result = invoke(
      f'--action validate --directory {self.backupdir} '
      '--signature-file-name backup-signature')
    self.assertEqual(result.exit_code, 1)
    self.assertEqual(
      result.output,
      f"DEBUG: Calculated ./{self.test_file_00}\n"
      "ERROR: Signatures do not match, current signature:\n"
      f"{{'./{self.test_file_00}': '{self.test_data_00_sum}a'}}\n"
      "Calculated signature:\n"
      f"{{'./{self.test_file_00}': '{self.test_data_00_sum}'}}\n"
    )

  def test_validate_missing(self):
    result = invoke(
      f'--action validate --directory {self.backupdir} '
      '--signature-file-name backup-signature')
    self.assertEqual(result.exit_code, 1)
    self.assertEqual(
      result.output,
      f"ERROR: Signature file {self.backupdir}/backup-signature not found\n"
    )

  def test_validate_timestamp(self):
    backup_signature = os.path.join(self.backupdir, 'backup-signature')
    validate_timestamp = os.path.join(self.workdir, 'validate-timestamp')
    with open(backup_signature, 'w') as fh:
     fh.write(f'{self.test_data_00_sum}  ./{self.test_file_00}\n')
    time.sleep(0.5)
    result = invoke(
      f'--action validate --directory {self.backupdir} '
      '--signature-file-name backup-signature '
      f'--validate-timestamp-file {validate_timestamp}')
    self.assertEqual(result.exit_code, 0)
    self.assertEqual(
      result.output,
      f"DEBUG: Calculated ./{self.test_file_00}\n"
      "OK: Signature match.\n"
      f"DEBUG: Updated {validate_timestamp}\n"
    )

    result = invoke(
      f'--action validate --directory {self.backupdir} '
      '--signature-file-name backup-signature '
      f'--validate-timestamp-file {validate_timestamp}')
    self.assertEqual(result.exit_code, 0)
    self.assertEqual(
      result.output,
      f"DEBUG: Using {validate_timestamp}\n"
      f"DEBUG: Skipped ./{self.test_file_00}\n"
      "OK: Signature match.\n"
      f"DEBUG: Updated {validate_timestamp}\n"
    )

  def test_validate_timestamp_update(self):
    backup_signature = os.path.join(self.backupdir, 'backup-signature')
    validate_timestamp = os.path.join(self.workdir, 'validate-timestamp')
    self.test_validate_timestamp()
    time.sleep(0.5)
    with open(os.path.join(self.backupdir, self.test_file_01), 'w') as fh:
     fh.write(self.test_data_01)
    with open(backup_signature, 'w') as fh:
     fh.write(
       f'{self.test_data_00_sum}  ./{self.test_file_00}\n'
       f'{self.test_data_01_sum}  ./{self.test_file_01}\n'
     )
    result = invoke(
      f'--action validate --directory {self.backupdir} '
      '--signature-file-name backup-signature '
      f'--validate-timestamp-file {validate_timestamp}')
    self.assertEqual(result.exit_code, 0)
    self.assertEqual(
      result.output,
      f"DEBUG: Using {validate_timestamp}\n"
      f"DEBUG: Skipped ./{self.test_file_00}\n"
      f"DEBUG: Calculated ./{self.test_file_01}\n"
      "OK: Signature match.\n"
      f"DEBUG: Updated {validate_timestamp}\n"
    )

  def test_validate_timestamp_update_force(self):
    self.test_validate_timestamp_update()
    validate_timestamp = os.path.join(self.workdir, 'validate-timestamp')
    result = invoke(
      f'--action validate --directory {self.backupdir} '
      '--force '
      '--signature-file-name backup-signature '
      f'--validate-timestamp-file {validate_timestamp}')
    self.assertEqual(result.exit_code, 0)
    self.assertEqual(
      result.output,
      f"DEBUG: Calculated ./{self.test_file_00}\n"
      f"DEBUG: Calculated ./{self.test_file_01}\n"
      "OK: Signature match.\n"
      f"DEBUG: Updated {validate_timestamp}\n"
    )
