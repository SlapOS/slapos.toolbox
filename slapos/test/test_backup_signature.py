from click.testing import CliRunner
import hashlib
import os
import pathlib
import shutil
import tempfile
import time
import unittest

import slapos.backup_signature


class Test(unittest.TestCase):
  def setUp(self):
    self.workdir = tempfile.mkdtemp()
    self.backupdir = os.path.join(self.workdir, 'backup')
    os.mkdir(self.backupdir)

    self.test_data_00 = 'Some test data'
    self.test_data_00_sum = hashlib.sha256(
      self.test_data_00.encode()).hexdigest()
    self.test_file_00 = 'somefile'
    with open(os.path.join(self.backupdir, self.test_file_00), 'w') as fh:
     fh.write(self.test_data_00)

    self.test_data_01 = 'Other test data'
    self.test_data_01_sum = hashlib.sha256(
      self.test_data_01.encode()).hexdigest()
    self.test_file_01 = 'otherfile'

  def tearDown(self):
    shutil.rmtree(self.workdir)

  def test_update(self):
    result = CliRunner().invoke(
      slapos.backup_signature.cli,
      f'--action update --directory {self.backupdir} '
      '--signature-file-name backup-signature'.split())
    self.assertEqual(result.exit_code, 0)
    self.assertEqual(
      result.output,
      f"INFO: Updated ./{self.test_file_00}\n"
      f"INFO: Updated content {self.backupdir}/backup-signature\n"
    )
    self.assertEqual(
      [f'{self.test_file_00}', 'backup-signature'],
      os.listdir(self.backupdir)
    )
    with open(os.path.join(self.backupdir, 'backup-signature')) as fh:
      self.assertEqual(
        f'{self.test_data_00_sum}  ./{self.test_file_00}\n', fh.read())

  def test_update_create_proof_signature(self):
    proof_signature = os.path.join(self.workdir, 'proof.signature')
    result = CliRunner().invoke(
      slapos.backup_signature.cli,
      f'--action update --directory {self.backupdir} '
      '--signature-file-name backup-signature '
      f'--proof-signature-path {proof_signature}'.split())
    self.assertEqual(result.exit_code, 0)
    self.assertEqual(
      result.output,
      f"INFO: Updated ./{self.test_file_00}\n"
      f"INFO: Updated content {proof_signature}\n"
    )
    self.assertEqual(
      [f'{self.test_file_00}'],
      os.listdir(self.backupdir)
    )
    with open(proof_signature) as fh:
      self.assertEqual(
        f'{self.test_data_00_sum}  ./{self.test_file_00}\n', fh.read())

  def test_update_deep_signature(self):
    os.mkdir(os.path.join(self.backupdir, 'path'))
    result = CliRunner().invoke(
      slapos.backup_signature.cli,
      f'--action update --directory {self.backupdir} '
      '--signature-file-name path/backup-signature'.split())
    self.assertEqual(result.exit_code, 0)
    self.assertEqual(
      result.output,
      f"INFO: Updated ./{self.test_file_00}\n"
      f"INFO: Updated content {self.backupdir}/path/backup-signature\n"
    )
    self.assertEqual(
      ['path', f'{self.test_file_00}'],
      os.listdir(self.backupdir)
    )
    with open(os.path.join(self.backupdir, 'path', 'backup-signature')) as fh:
      self.assertEqual(
        f'{self.test_data_00_sum}  ./{self.test_file_00}\n', fh.read())

  def test_update_noop(self):
    self.test_update()
    result = CliRunner().invoke(
      slapos.backup_signature.cli,
      f'--action update --directory {self.backupdir} '
      '--signature-file-name backup-signature'.split())
    self.assertEqual(result.exit_code, 0)
    self.assertEqual(
      result.output,
      f"INFO: Kept old ./{self.test_file_00}\n"
      f"INFO: Kept content {self.backupdir}/backup-signature\n"
    )
    self.assertEqual(
      [f'{self.test_file_00}', 'backup-signature'],
      os.listdir(self.backupdir)
    )
    with open(os.path.join(self.backupdir, 'backup-signature')) as fh:
      self.assertEqual(
        f'{self.test_data_00_sum}  ./{self.test_file_00}\n', fh.read())

  def test_update_proof_signature(self):
    self.test_update()
    proof_signature = os.path.join(self.workdir, 'proof.signature')
    result = CliRunner().invoke(
      slapos.backup_signature.cli,
      f'--action update --directory {self.backupdir} '
      '--signature-file-name backup-signature '
      f'--proof-signature-path {proof_signature}'.split())
    self.assertEqual(result.exit_code, 0)
    self.assertEqual(
      result.output,
      f"INFO: Updated ./{self.test_file_00}\n"
      f"INFO: Updated content {proof_signature}\n"
    )
    self.assertEqual(
      [f'{self.test_file_00}', 'backup-signature'],
      os.listdir(self.backupdir)
    )
    with open(os.path.join(self.backupdir, 'backup-signature')) as fh:
      self.assertEqual(
        f'{self.test_data_00_sum}  ./{self.test_file_00}\n', fh.read())

    with open(proof_signature) as fh:
      self.assertEqual(
        f'{self.test_data_00_sum}  ./{self.test_file_00}\n', fh.read())

  def test_update_noop_force(self):
    self.test_update()
    result = CliRunner().invoke(
      slapos.backup_signature.cli,
      f'--action update --force --directory {self.backupdir} '
      '--signature-file-name backup-signature'.split())
    self.assertEqual(result.exit_code, 0)
    self.assertEqual(
      result.output,
      f"INFO: Updated ./{self.test_file_00}\n"
      f"INFO: Updated content {self.backupdir}/backup-signature\n"
    )
    self.assertEqual(
      [f'{self.test_file_00}', 'backup-signature'],
      os.listdir(self.backupdir)
    )
    with open(os.path.join(self.backupdir, 'backup-signature')) as fh:
      self.assertEqual(
        f'{self.test_data_00_sum}  ./{self.test_file_00}\n', fh.read())

  def test_update_change(self):
    self.test_update()
    time.sleep(.5)
    with open(os.path.join(self.backupdir, self.test_file_00), 'w') as fh:
     fh.write(self.test_data_01)
    result = CliRunner().invoke(
      slapos.backup_signature.cli,
      f'--action update --directory {self.backupdir} '
      '--signature-file-name backup-signature'.split())
    self.assertEqual(result.exit_code, 0)
    self.assertEqual(
      result.output,
      f"INFO: Updated ./{self.test_file_00}\n"
      f"INFO: Updated content {self.backupdir}/backup-signature\n"
    )
    self.assertEqual(
      [f'{self.test_file_00}', 'backup-signature'],
      os.listdir(self.backupdir)
    )
    with open(os.path.join(self.backupdir, 'backup-signature')) as fh:
      self.assertEqual(
        f'{self.test_data_01_sum}  ./{self.test_file_00}\n', fh.read())

  def test_update_change_proof_signature(self):
    self.test_update()
    proof_signature = os.path.join(self.workdir, 'proof.signature')
    result = CliRunner().invoke(
      slapos.backup_signature.cli,
      f'--action update --directory {self.backupdir} '
      '--signature-file-name backup-signature '
      f'--proof-signature-path {proof_signature}'.split())
    self.assertEqual(result.exit_code, 0)
    self.assertEqual(
      result.output,
      f"INFO: Updated ./{self.test_file_00}\n"
      f"INFO: Updated content {proof_signature}\n"
    )
    self.assertEqual(
      [f'{self.test_file_00}', 'backup-signature'],
      os.listdir(self.backupdir)
    )
    with open(proof_signature) as fh:
      self.assertEqual(
        f'{self.test_data_00_sum}  ./{self.test_file_00}\n', fh.read())
    time.sleep(.5)
    with open(os.path.join(self.backupdir, self.test_file_00), 'w') as fh:
     fh.write(self.test_data_01)
    result = CliRunner().invoke(
      slapos.backup_signature.cli,
      f'--action update --directory {self.backupdir} '
      '--signature-file-name backup-signature'.split())
    self.assertEqual(result.exit_code, 0)
    self.assertEqual(
      result.output,
      f"INFO: Updated ./{self.test_file_00}\n"
      f"INFO: Updated content {self.backupdir}/backup-signature\n"
    )
    self.assertEqual(
      [f'{self.test_file_00}', 'backup-signature'],
      os.listdir(self.backupdir)
    )
    with open(os.path.join(self.backupdir, 'backup-signature')) as fh:
      self.assertEqual(
        f'{self.test_data_01_sum}  ./{self.test_file_00}\n', fh.read())

    result = CliRunner().invoke(
      slapos.backup_signature.cli,
      f'--action update --directory {self.backupdir} '
      '--signature-file-name backup-signature '
      f'--proof-signature-path {proof_signature}'.split())
    self.assertEqual(result.exit_code, 0)
    self.assertEqual(
      result.output,
      f"INFO: Updated ./{self.test_file_00}\n"
      f"INFO: Updated content {proof_signature}\n"
    )
    self.assertEqual(
      [f'{self.test_file_00}', 'backup-signature'],
      os.listdir(self.backupdir)
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
    result = CliRunner().invoke(
      slapos.backup_signature.cli,
      f'--action update --directory {self.backupdir} '
      '--signature-file-name backup-signature'.split())
    self.assertEqual(result.exit_code, 0)
    self.assertEqual(
      result.output,
      f"INFO: Kept old ./{self.test_file_00}\n"
      f"INFO: Kept content {self.backupdir}/backup-signature\n"
    )
    self.assertEqual(
      [f'{self.test_file_00}', 'backup-signature'],
      os.listdir(self.backupdir)
    )
    with open(os.path.join(self.backupdir, 'backup-signature')) as fh:
      self.assertEqual(
        f'{self.test_data_00_sum}  ./{self.test_file_00}\n', fh.read())

    # force is needed
    result = CliRunner().invoke(
      slapos.backup_signature.cli,
      f'--action update --force --directory {self.backupdir} '
      '--signature-file-name backup-signature'.split())
    self.assertEqual(result.exit_code, 0)
    self.assertEqual(
      result.output,
      f"INFO: Updated ./{self.test_file_00}\n"
      f"INFO: Updated content {self.backupdir}/backup-signature\n"
    )
    self.assertEqual(
      [f'{self.test_file_00}', 'backup-signature'],
      os.listdir(self.backupdir)
    )
    with open(os.path.join(self.backupdir, 'backup-signature')) as fh:
      self.assertEqual(
        f'{self.test_data_01_sum}  ./{self.test_file_00}\n', fh.read())

  def test_update_add(self):
    self.test_update()
    with open(os.path.join(self.backupdir, self.test_file_01), 'w') as fh:
     fh.write(self.test_data_01)
    result = CliRunner().invoke(
      slapos.backup_signature.cli,
      f'--action update --directory {self.backupdir} '
      '--signature-file-name backup-signature'.split())
    self.assertEqual(result.exit_code, 0)
    self.assertEqual(
      result.output,
      f"INFO: Updated ./{self.test_file_01}\n"
      f"INFO: Kept old ./{self.test_file_00}\n"
      f"INFO: Updated content {self.backupdir}/backup-signature\n"
    )
    self.assertEqual(
      [f'{self.test_file_01}', f'{self.test_file_00}', 'backup-signature'],
      os.listdir(self.backupdir)
    )
    with open(os.path.join(self.backupdir, 'backup-signature')) as fh:
      self.assertEqual(
        f'{self.test_data_01_sum}  ./{self.test_file_01}\n'
        f'{self.test_data_00_sum}  ./{self.test_file_00}\n',
        fh.read())

  def test_update_remove(self):
    self.test_update_add()
    os.unlink(os.path.join(self.backupdir, self.test_file_01))
    result = CliRunner().invoke(
      slapos.backup_signature.cli,
      f'--action update --directory {self.backupdir} '
      '--signature-file-name backup-signature'.split())
    self.assertEqual(result.exit_code, 0)
    self.assertEqual(
      result.output,
      f"INFO: Kept old ./{self.test_file_00}\n"
      f"INFO: Updated content {self.backupdir}/backup-signature\n"
    )
    self.assertEqual(
      [f'{self.test_file_00}', 'backup-signature'],
      os.listdir(self.backupdir)
    )
    with open(os.path.join(self.backupdir, 'backup-signature')) as fh:
      self.assertEqual(
        f'{self.test_data_00_sum}  ./{self.test_file_00}\n',
        fh.read())
