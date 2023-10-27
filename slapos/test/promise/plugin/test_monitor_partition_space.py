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
import psutil
from slapos.grid.promise import PromiseError

class TestMonitorPartitionSpace(TestPromisePluginMixin):

  def setUp(self):
    TestPromisePluginMixin.setUp(self)
    log_folder = os.path.join(self.partition_dir, 'var/log')
    os.makedirs(log_folder)

    # get disk partition name
    disk_partition = ""
    path = os.path.join(self.partition_dir, "") + "extrafolder"
    partitions = psutil.disk_partitions()
    while path != '/':
      if not disk_partition:
        path = os.path.dirname(path)
      else:
        break
      for p in partitions:
        if p.mountpoint == path:
          disk_partition = p.device
          break

    self.db_file = '/tmp/collector.db'

    # populate db
    self.conn = sqlite3.connect(self.db_file)
    with open(self.base_path+"/folder_disk_test.sql") as f:
      sql = f.read()
    # replace every disk_partition_name string with disk partition name
    sql = sql.replace('disk_partition_name', disk_partition)
    self.conn.executescript(sql)
    self.conn.close()

    self.promise_name = "monitor-partition-space.py"

    content = """from slapos.promise.plugin.monitor_partition_space import RunPromise

extra_config_dict = {
  'collectordb': '%(collectordb)s',
  'test-check-date': '2017-10-02',
}
""" % {'collectordb': self.db_file}
    self.writePromise(self.promise_name, content)

  def tearDown(self):
    TestPromisePluginMixin.tearDown(self)
    if os.path.exists(self.db_file):
      os.remove(self.db_file)

  def test_no_data_for_a_partition(self):
    content = """from slapos.promise.plugin.monitor_partition_space import RunPromise

extra_config_dict = {
  'collectordb': '%(collectordb)s',
  'test-check-date': '2017-10-02',
  'test-partition': 'slapuser1'
}
""" % {'collectordb': self.db_file}

    self.writePromise(self.promise_name, content)

    self.configureLauncher(timeout=20)
    self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], False)
    self.assertEqual(result['result']['message'], 
      "No result from collector database for the user slapuser1: skipped")

  def test_no_recent_data(self):
    content = """from slapos.promise.plugin.monitor_partition_space import RunPromise

extra_config_dict = {
  'collectordb': '%(collectordb)s',
  'test-check-date': '2017-10-04'
}
""" % {'collectordb': self.db_file}

    self.writePromise(self.promise_name, content)

    self.configureLauncher(force=True, timeout=20)
    self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], False)
    self.assertEqual(result['result']['message'], "Not enough recent data to detect anomalies: skipped")

  def test_no_enough_data(self):
    content = """from slapos.promise.plugin.monitor_partition_space import RunPromise

extra_config_dict = {
  'collectordb': '%(collectordb)s',
  'test-check-date': '2017-09-24'
}
""" % {'collectordb': self.db_file}

    self.writePromise(self.promise_name, content)

    self.configureLauncher(force=True, timeout=20)
    self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], False)
    self.assertEqual(result['result']['message'], 
      "Not enough data to detect anomalies: skipped")

  def test_no_anomalies(self):
    content = """from slapos.promise.plugin.monitor_partition_space import RunPromise

extra_config_dict = {
  'collectordb': '%(collectordb)s',
  'test-check-date': '2017-10-02',
  'threshold-ratio': '0.70'
}
""" % {'collectordb': self.db_file}

    self.writePromise(self.promise_name, content)

    self.configureLauncher(force=True, timeout=20)
    self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], False)
    self.assertIn("No anomaly detected (last date checked: 2017-10-02 09:30:00)",
                  result['result']['message'])

  def test_presence_of_anomalies(self):
    self.configureLauncher(force=True, timeout=20)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], True)
    msg = "Anomaly detected on 2017-10-02 09:30:00. Space used by slapuser0: %.2f G."
    self.assertIn(msg % (87533020.0/(1024*1024)), result['result']['message'])


if __name__ == '__main__':
  unittest.main()