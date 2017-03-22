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
from slapos.promise.is_icmp_packet_lost import test

class TestIsICMPPacketLost(unittest.TestCase):

  def test_localhost(self):
    result = test("localhost", True, 5)
    self.assertEquals(result[4], '0')
  
  def test_error(self):
    result = test("couscous", True, 5)
    self.assertEquals(result[4], -1)

  def test_localhost6 (self):
    result = test("::1", False, 5)
    self.assertEquals(result[4], '0')
  
  def test_error6(self):
    result = test("couscous", False, 5)
    self.assertEquals(result[4], -1)

  def test_error_4_6(self):
    result = test("::1", True, 5)
    self.assertEquals(result[4], -1)

if __name__ == '__main__':
  unittest.main()

