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
import time
import tempfile

from slapos.test.promise import data
from slapos.promise.check_apachedex_result import checkApachedexResult

class TestCheckApacheDigestResult(unittest.TestCase):

  def setUp(self):

    _, self.empty_apachedex_file = tempfile.mkstemp()
    _, self.old_apachedex_file = tempfile.mkstemp()
    _, self.status_file = tempfile.mkstemp()

    self.base_path = "/".join(data.__file__.split("/")[:-1])
    self.status = "ok"

  def test_threshold_is_greater(self):
    result = checkApachedexResult(self.base_path + "/apachedex.html", self.status_file, 60, False)
    self.assertEquals("Thanks for keeping it all clean, result is 80", result['message'])
    self.assertEquals(0, result['status'])

  def test_empty_file(self):
    result = checkApachedexResult(self.empty_apachedex_file, self.status_file, 60, False)
    self.assertEquals("File is empty, Apachedex is yet to run or running", result['message'])
    self.assertEquals(0, result['status'])

  def test_threshold_is_lower(self):
    result = checkApachedexResult(self.base_path + "/apachedex.html", self.status_file, 90, False)
    self.assertEquals("Threshold is lower than expected:  Expected was 90 and current result is 80", result['message'])
    self.assertEquals(1, result['status'])

  def test_old_file(self):
    os.utime(self.old_apachedex_file, (time.time() - 202800, time.time() - 202800))
    f = open('/tmp/ApacheDex-2017-10-05.html', 'w')
    #f.write('hi there\n')
    result = checkApachedexResult(self.old_apachedex_file, self.status_file, 60, False)
    self.assertEquals("No apachedex result since 36 hours", result['message'])
    self.assertEquals(1, result['status'])
    f.close()

  def test_just_deployed(self):
    result = checkApachedexResult(self.base_path + "/apachedex.html", self.status_file, 90, True)
    self.assertEquals("Instance has been just deployed. Skipping check..", result['message'])
    self.assertEquals(0, result['status'])

if __name__ == '__main__':
  unittest.main()

