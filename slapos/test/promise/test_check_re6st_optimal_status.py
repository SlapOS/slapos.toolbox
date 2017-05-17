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
import os.path
import socket
import time
from slapos.promise.check_re6st_optimal_status import test

class TestCheckRe6stOptimalStatus(unittest.TestCase):

  def test_ipv6_is_faster(self):
    result = test('::1', '8.8.8.8', 5)
    self.assertEquals(result, 'OK')

  def test_ipv4_is_faster(self):
    result = test('2001:67c:1254::1', '127.0.0.1', 5)
    self.assertEquals(result, 'FAIL')

  def test_ipv4_unreacheable_and_ipv6_ok(self):
    result = test('::1', 'couscous', 5)
    self.assertEquals(result, 'OK')

  def test_ipv6_fail(self):
    result = test('couscous', '127.0.0.1', 5)
    self.assertEquals(result, 'FAILED')

if __name__ == '__main__':
  unittest.main()
