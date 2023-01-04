# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2018 Vifib SARL and Contributors. All Rights Reserved.
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
import os
import time

from collections import namedtuple
from slapos.grid.promise import PromiseError
from slapos.promise.plugin.check_network_transit import RunPromise
from . import TestPromisePluginMixin


class TestCheckNetworkTransit(TestPromisePluginMixin):

  promise_name = "monitor-network-transit.py"

  def setUp(self):
    super(TestCheckNetworkTransit, self).setUp()
    self.network_data = namedtuple('network_data', ['bytes_recv', 'bytes_sent'])

  def writePromise(self, **kw):
    super(TestCheckNetworkTransit, self).writePromise(self.promise_name,
      "from %s import %s\nextra_config_dict = %r\n"
      % (RunPromise.__module__, RunPromise.__name__, kw))

  def runPromise(self, summary=None, failed=False):
    self.configureLauncher(enable_anomaly=True, force=True)
    with mock.patch('psutil.net_io_counters', return_value=summary):
      if failed:
        self.assertRaises(PromiseError, self.launcher.run)
      else:
        self.launcher.run()
    result = self.getPromiseResult(self.promise_name)['result']
    self.assertEqual(result['failed'], failed)
    return result['message']

  def test_network_transit_ok(self):
    message = "Network transit OK"
    mock_stats = {'bytes_recv':1e6, 'bytes_sent':1e6}
    self.writePromise(**{
        'transit-period': 1,
    })
    self.runPromise(self.network_data(**{'bytes_recv':1e3, 'bytes_sent':1e3}))
    time.sleep(0.5)
    self.assertEqual(message, self.runPromise(self.network_data(**mock_stats)))

  def test_network_min_nok(self):
    message = "Network congested, data amount over the last 1 seconds"\
      " reached minimum threshold:    1.4K (threshold is  102.4K)"
    mock_stats = {'bytes_recv':1e3, 'bytes_sent':1e3}
    self.writePromise(**{
        'min-data-amount': 0.1, # MB
        'transit-period': 1,
    })
    self.runPromise(self.network_data(**{'bytes_recv':300, 'bytes_sent':300}))
    time.sleep(0.5)
    self.assertEqual(message, self.runPromise(self.network_data(**mock_stats)))

  def test_network_max_nok(self):
    message = "Network congested, data amount over the last 1 seconds"\
      " reached maximum threshold:    1.1M (threshold is    1.0M)"
    mock_stats = {'bytes_recv':0.7e6, 'bytes_sent':0.5e6}
    self.writePromise(**{
        'max-data-amount': 1, # MB
        'transit-period': 1,
    })
    self.runPromise(self.network_data(**{'bytes_recv':300, 'bytes_sent':300}))
    time.sleep(0.5)
    self.assertEqual(message, self.runPromise(self.network_data(**mock_stats)))

  def test_network_transit_nok(self):
    message = "Network congested, data amount over the last 1 seconds reached minimum threshold:    0.0B (threshold is    0.0B)\n"\
      "Network congested, data amount over the last 1 seconds reached maximum threshold:    0.0B (threshold is    0.0B)"
    mock_stats = {'bytes_recv':1e6, 'bytes_sent':1e6}
    self.writePromise(**{
        'last_transit_file':'last_transit_file',
        'max-data-amount': 0,
        'min-data-amount': 0,
        'transit-period': 1,
    })
    self.runPromise(self.network_data(**{'bytes_recv':1e6, 'bytes_sent':1e6}))
    time.sleep(0.5)
    self.assertEqual(message, self.runPromise(self.network_data(**mock_stats)))

if __name__ == '__main__':
  unittest.main()
