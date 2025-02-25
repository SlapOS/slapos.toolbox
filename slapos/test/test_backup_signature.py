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

    self.test_data_00 = 'Some test data'
    self.test_data_00_sum = hashlib.sha256(
      self.test_data_00.encode()).hexdigest()
    self.test_file_00 = 'somefile'
    with open(os.path.join(self.workdir, self.test_file_00), 'w') as fh:
     fh.write(self.test_data_00)

    self.test_data_01 = 'Other test data'
    self.test_data_01_sum = hashlib.sha256(
      self.test_data_01.encode()).hexdigest()
    self.test_file_01 = 'otherfile'

  def tearDown(self):
    shutil.rmtree(self.workdir)

  def test_create(self):
    result = CliRunner().invoke(
      slapos.backup_signature.cli,
      f'--action update --directory {self.workdir} '
      '--signature-file-name backup-signature'.split())
    self.assertEqual(result.exit_code, 0)
    self.assertEqual(
      result.output,
      f"INFO: Updated ./{self.test_file_00}\nINFO: Updated content "
      f"{self.workdir}/backup-signature\n"
    )
    self.assertEqual(
      [f'{self.test_file_00}', 'backup-signature'],
      os.listdir(self.workdir)
    )
    with open(os.path.join(self.workdir, 'backup-signature')) as fh:
      self.assertEqual(
        f'{self.test_data_00_sum}  ./{self.test_file_00}\n', fh.read())

  def test_update_noop(self):
    self.test_create()
    result = CliRunner().invoke(
      slapos.backup_signature.cli,
      f'--action update --directory {self.workdir} '
      '--signature-file-name backup-signature'.split())
    self.assertEqual(result.exit_code, 0)
    self.assertEqual(
      result.output,
      f"INFO: Kept old ./{self.test_file_00}\nINFO: Kept content "
      f"{self.workdir}/backup-signature\n"
    )
    self.assertEqual(
      [f'{self.test_file_00}', 'backup-signature'],
      os.listdir(self.workdir)
    )
    with open(os.path.join(self.workdir, 'backup-signature')) as fh:
      self.assertEqual(
        f'{self.test_data_00_sum}  ./{self.test_file_00}\n', fh.read())

  def test_update_change(self):
    self.test_create()
    time.sleep(.5)
    with open(os.path.join(self.workdir, self.test_file_00), 'w') as fh:
     fh.write(self.test_data_01)
    result = CliRunner().invoke(
      slapos.backup_signature.cli,
      f'--action update --directory {self.workdir} '
      '--signature-file-name backup-signature'.split())
    self.assertEqual(result.exit_code, 0)
    self.assertEqual(
      result.output,
      f"INFO: Updated ./{self.test_file_00}\nINFO: Updated content "
      f"{self.workdir}/backup-signature\n"
    )
    self.assertEqual(
      [f'{self.test_file_00}', 'backup-signature'],
      os.listdir(self.workdir)
    )
    with open(os.path.join(self.workdir, 'backup-signature')) as fh:
      self.assertEqual(
        f'{self.test_data_01_sum}  ./{self.test_file_00}\n', fh.read())

  def test_update_change_older(self):
    self.test_create()
    time.sleep(.5)
    with open(os.path.join(self.workdir, self.test_file_00), 'w') as fh:
     fh.write(self.test_data_01)
    time.sleep(.5)
    pathlib.Path(os.path.join(self.workdir, 'backup-signature')).touch()
    result = CliRunner().invoke(
      slapos.backup_signature.cli,
      f'--action update --directory {self.workdir} '
      '--signature-file-name backup-signature'.split())
    self.assertEqual(result.exit_code, 0)
    self.assertEqual(
      result.output,
      f"INFO: Kept old ./{self.test_file_00}\n"
      f"INFO: Kept content {self.workdir}/backup-signature\n"
    )
    self.assertEqual(
      [f'{self.test_file_00}', 'backup-signature'],
      os.listdir(self.workdir)
    )
    with open(os.path.join(self.workdir, 'backup-signature')) as fh:
      self.assertEqual(
        f'{self.test_data_00_sum}  ./{self.test_file_00}\n', fh.read())

    # force is needed
    result = CliRunner().invoke(
      slapos.backup_signature.cli,
      f'--action update --force --directory {self.workdir} '
      '--signature-file-name backup-signature'.split())
    self.assertEqual(result.exit_code, 0)
    self.assertEqual(
      result.output,
      f"INFO: Updated ./{self.test_file_00}\nINFO: Updated content "
      f"{self.workdir}/backup-signature\n"
    )
    self.assertEqual(
      [f'{self.test_file_00}', 'backup-signature'],
      os.listdir(self.workdir)
    )
    with open(os.path.join(self.workdir, 'backup-signature')) as fh:
      self.assertEqual(
        f'{self.test_data_01_sum}  ./{self.test_file_00}\n', fh.read())

  def test_add(self):
    self.test_create()
    with open(os.path.join(self.workdir, self.test_file_01), 'w') as fh:
     fh.write(self.test_data_01)
    result = CliRunner().invoke(
      slapos.backup_signature.cli,
      f'--action update --directory {self.workdir} '
      '--signature-file-name backup-signature'.split())
    self.assertEqual(result.exit_code, 0)
    self.assertEqual(
      result.output,
      f"INFO: Updated ./{self.test_file_01}\n"
      f"INFO: Kept old ./{self.test_file_00}\n"
      f"INFO: Updated content {self.workdir}/backup-signature\n"
    )
    self.assertEqual(
      [f'{self.test_file_01}', f'{self.test_file_00}', 'backup-signature'],
      os.listdir(self.workdir)
    )
    with open(os.path.join(self.workdir, 'backup-signature')) as fh:
      self.assertEqual(
        f'{self.test_data_01_sum}  ./{self.test_file_01}\n'
        f'{self.test_data_00_sum}  ./{self.test_file_00}\n',
        fh.read())
