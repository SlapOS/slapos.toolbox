##############################################################################
#
# Copyright (c) 2015 Vifib SARL and Contributors. All Rights Reserved.
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
from slapos.networkbench.ping import ping, ping6

class TestPing(unittest.TestCase):

  def test_ping_ok(self):
    info = ping("localhost")
    self.assertEqual(info[0], 'PING')
    self.assertEqual(info[1], 'localhost')
    self.assertEqual(info[2], 200)
    self.assertLess(float(info[3]), 0.2)
    self.assertEqual(info[4], '0')
    self.assertTrue(info[5].startswith("min"))

  def test_ping_fail(self):
    info = ping("couscous")
    self.assertEqual(info[0], 'PING')
    self.assertEqual(info[1], 'couscous')
    self.assertEqual(info[2], 600)
    self.assertEqual(info[3], 'failed')
    self.assertEqual(info[4], -1)
    self.assertEqual(info[5], 'Fail to parser ping output')

  def test_ping6_ok(self):
    info = ping6("localhost")
    self.assertEqual(info[0], 'PING6')
    self.assertEqual(info[1], 'localhost')
    self.assertEqual(info[2], 200)
    self.assertLess(float(info[3]), 0.2)
    self.assertEqual(info[4], '0')
    self.assertTrue(info[5].startswith("min"))

  def test_ping6_fail(self):
    info = ping6("couscous")
    self.assertEqual(info[0], 'PING6')
    self.assertEqual(info[1], 'couscous')
    self.assertEqual(info[2], 600)
    self.assertEqual(info[3], 'failed')
    self.assertEqual(info[4], -1)
    self.assertEqual(info[5], 'Fail to parser ping output')
