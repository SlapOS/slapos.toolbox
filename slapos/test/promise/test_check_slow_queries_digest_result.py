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
from slapos.promise.check_slow_queries_digest_result import checkMariadbDigestResult

class TestCheckSlowQueriesDigestResult(unittest.TestCase):

  def setUp(self):

    _, self.empty_ptdigest_file = tempfile.mkstemp()
    _, self.old_ptdigest_file = tempfile.mkstemp()
    _, self.status_file = tempfile.mkstemp()

    self.base_path = "/".join(data.__file__.split("/")[:-1])

  def test_pass(self):
    self.assertEquals("Thanks for keeping it all clean, total queries are : 3420.0 slowest query time is : 34",
      checkMariadbDigestResult(self.base_path + "/ptdigest.html", self.status_file, 5000, 100))

  def test_empty_file(self):
    self.assertEquals("No result found in the apdex file or the file is corrupted",
      checkMariadbDigestResult(self.empty_ptdigest_file, self.status_file, 60, 100))

  def test_fail(self):
    self.assertEquals("Threshold is lower than expected: \nExpected total queries : 90 and current is: 3420.0\nExpected slowest query : 100 and current is: 34",
      checkMariadbDigestResult(self.base_path + "/ptdigest.html", self.status_file, 90, 100))

  def test_old_file(self):
    os.utime(self.old_ptdigest_file, (time.time() - 202800, time.time() - 202800))
    self.assertEquals("File modification date is greater than 30 hour",
      checkMariadbDigestResult(self.old_ptdigest_file, self.status_file, 60, 100))

if __name__ == '__main__':
  unittest.main()

