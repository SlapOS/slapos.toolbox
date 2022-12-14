# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2022 Vifib SARL and Contributors. All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly advised to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
##############################################################################
import mock

from collections import namedtuple
from slapos.grid.promise import PromiseError
from slapos.promise.plugin.check_network import RunPromise
from . import TestPromisePluginMixin


class TestCheckNetwork(TestPromisePluginMixin):

  promise_name = "monitor-network.py"

  def setUp(self):
    super(TestCheckNetwork, self).setUp()

  def writePromise(self, **kw):
    super(TestCheckNetwork, self).writePromise(self.promise_name,
      "from %s import %s\nextra_config_dict = %r\n"
      % (RunPromise.__module__, RunPromise.__name__, kw))

  def runPromise(self, summary, failed=False):
    self.configureLauncher(enable_anomaly=True, force=True)
    with mock.patch('psutil.net_io_counters', return_value=summary):
      if failed:
        self.assertRaises(PromiseError, self.launcher.run)
      else:
        self.launcher.run()
    result = self.getPromiseResult(self.promise_name)['result']
    self.assertEqual(result['failed'], failed)
    return result['message']

  def test_network_ok(self):
    message = "Network statistics OK"
    network_data = namedtuple('network_data', ['errin', 'errout', 'dropin', 'dropout'])
    mock_stats = {'errin':0, 'errout':0, 'dropin':0, 'dropout':0}
    self.writePromise(**{
        'max-lost-packets': 5,
        'max-error-messages': 5,
    })
    self.assertEqual(message, self.runPromise(network_data(**mock_stats)))

  def test_network_dropped_packets_nok(self):
    message = "Network packets lost reached critical threshold: 10  (threshold is 5)"
    network_data = namedtuple('network_data', ['errin', 'errout', 'dropin', 'dropout'])
    mock_stats = {'errin':0, 'errout':0, 'dropin':5, 'dropout':5}
    self.writePromise(**{
        'max-lost-packets': 5,
        'max-error-messages': 5,
    })
    self.assertEqual(message, self.runPromise(network_data(**mock_stats)))

  def test_network_errors_nok(self):
    message = "Network errors reached critical threshold: 10  (threshold is 5)"
    network_data = namedtuple('network_data', ['errin', 'errout', 'dropin', 'dropout'])
    mock_stats = {'errin':5, 'errout':5, 'dropin':0, 'dropout':0}
    self.writePromise(**{
        'max-lost-packets': 5,
        'max-error-messages': 5,
    })
    self.assertEqual(message, self.runPromise(network_data(**mock_stats)))

  def test_network_nok(self):
    message = "Network packets lost reached critical threshold: 10  (threshold is 5)"\
      "\nNetwork errors reached critical threshold: 10  (threshold is 5)"
    network_data = namedtuple('network_data', ['errin', 'errout', 'dropin', 'dropout'])
    mock_stats = {'errin':5, 'errout':5, 'dropin':5, 'dropout':5}
    self.writePromise(**{
        'max-lost-packets': 5,
        'max-error-messages': 5,
    })
    self.assertEqual(message, self.runPromise(network_data(**mock_stats)))

if __name__ == '__main__':
  unittest.main()
