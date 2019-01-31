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
import os
import os.path
import socket

class TestCheckICMPPacketLost(TestPromisePluginMixin):

  def setUp(self):
    TestPromisePluginMixin.setUp(self)
    log_folder = os.path.join(self.partition_dir, 'var/log')
    os.makedirs(log_folder)

    self.promise_name = "check-icmp-packet-lost.py"

    self.base_content = """from slapos.promise.plugin.check_icmp_packet_lost import RunPromise

extra_config_dict = {
  'ipv4': '%(ipv4)s',
  'count': '%(count)s',
  'address': '%(address)s',
}
"""

  def tearDown(self):
    TestPromisePluginMixin.tearDown(self)

  def test_localhost(self):
    content = self.base_content % {
      'address': "localhost",
      'count': 5,
      "ipv4": True
    }
    self.writePromise(self.promise_name, content)

    self.configureLauncher()
    self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], False)
    self.assertEqual(result['result']['message'], "0")

  def test_error(self):
    content = self.base_content % {
      'address': "couscous",
      'count': 5,
      "ipv4": True
    }
    self.writePromise(self.promise_name, content)

    self.configureLauncher()
    self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], True)
    self.assertEqual(result['result']['message'], "-1")

  def test_localhost6_with_ping6(self):
    content = self.base_content % {
      'address': "::1",
      'count': 5,
      "ipv4": False
    }
    self.writePromise(self.promise_name, content)

    self.configureLauncher()
    self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], False)
    self.assertEqual(result['result']['message'], "0")

  def test_localhost6_with_ping4(self):
    content = self.base_content % {
      'address': "::1",
      'count': 5,
      "ipv4": True
    }
    self.writePromise(self.promise_name, content)

    self.configureLauncher()
    self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], False)
    self.assertEqual(result['result']['message'], "0")

  def test_error6(self):
    content = self.base_content % {
      'address': "couscous",
      'count': 5,
      "ipv4": False
    }
    self.writePromise(self.promise_name, content)

    self.configureLauncher()
    self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], True)
    self.assertEqual(result['result']['message'], "-1")

if __name__ == '__main__':
  unittest.main()
