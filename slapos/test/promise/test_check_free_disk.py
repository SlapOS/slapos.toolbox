##############################################################################
#
# Copyright (c) 2017 Vifib SARL and Contributors. All Rights Reserved.
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

import unittest
import os
import sqlite3

from slapos.test.promise import data
from slapos.promise.check_free_disk import getFreeSpace

class TestFreeDisk(unittest.TestCase):

  def setUp(self):
    self.base_path = "/".join(data.__file__.split("/")[:-1])
    self.status = "ok"
    self.db_file = '/tmp/collector.db'

    # populate db
    self.conn = sqlite3.connect(self.db_file)
    f = open(self.base_path+"/disktest.sql")
    sql = f.read()
    self.conn.executescript(sql)
    self.conn.close() 

  def test_check_disk(self):
    self.assertEquals(288739385344,
      getFreeSpace('/dev/sda1', '/tmp', '2017-10-02', '09:27'))

  def test_check_free_disk_with_unavailable_dates(self):
    self.assertEquals(0, getFreeSpace('/', '/tmp', '18:00', '2017-09-14'))

  def tearDown(self):
    if os.path.exists(self.db_file):
      os.remove(self.db_file)

if __name__ == '__main__':
  unittest.main()

