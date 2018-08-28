##############################################################################
#
# Copyright (c) 2018 Vifib SARL and Contributors. All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from slapos.test.promise.plugin import TestPromisePluginMixin
from slapos.grid.promise import PromiseError
import os
import sqlite3
from slapos.test.promise import data
from slapos.promise.plugin.check_free_disk_space import getFreeSpace
from slapos.grid.promise import PromiseError

class TestCheckFreeDiskSpace(TestPromisePluginMixin):

  def setUp(self):
    TestPromisePluginMixin.setUp(self)
    log_folder = os.path.join(self.partition_dir, 'var/log')
    os.makedirs(log_folder)

    self.db_file = '/tmp/collector.db'
    self.base_path = "/".join(data.__file__.split("/")[:-1])

    # populate db
    self.conn = sqlite3.connect(self.db_file)
    f = open(self.base_path+"/disktest.sql")
    sql = f.read()
    self.conn.executescript(sql)
    self.conn.close()

    self.promise_name = "check-free-disk-space.py"
    self.th_file = os.path.join(self.partition_dir, 'min-disk-value')
    with open(self.th_file, 'w') as f:
      f.write('2048')

    content = """from slapos.promise.plugin.check_free_disk_space import RunPromise

extra_config_dict = {
  'collectordb': '%(collectordb)s',
  'threshold-file': '%(th_file)s',
  'test-check-date': '2017-10-02',
}
""" % {'collectordb': self.db_file, 'th_file': self.th_file}
    self.writePromise(self.promise_name, content)

  def tearDown(self):
    TestPromisePluginMixin.tearDown(self)
    if os.path.exists(self.db_file):
      os.remove(self.db_file)

  def test_check_disk(self):
    self.assertEquals(288739385344,
      getFreeSpace('/dev/sda1', '/tmp', '2017-10-02', '09:27'))

  def test_check_free_disk_with_unavailable_dates(self):
    self.assertEquals(0, getFreeSpace('/', '/tmp', '18:00', '2017-09-14'))

  def test_disk_space_ok(self):
    self.configureLauncher()
    self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEquals(result['result']['failed'], False)
    self.assertEquals(result['result']['message'], "Disk usage: OK")

  def test_disk_space_nok(self):
    with open(self.th_file, 'w') as f:
      f.write('298927494144')
    self.configureLauncher()
    with self.assertRaises(PromiseError):
      self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEquals(result['result']['failed'], True)
    self.assertEquals(result['result']['message'], "Free disk space low: remaining 269.1 G (threshold: 291921381.0 G)")

if __name__ == '__main__':
  unittest.main()
