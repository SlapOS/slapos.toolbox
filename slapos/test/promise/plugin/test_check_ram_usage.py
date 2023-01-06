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
from slapos.promise.plugin.check_ram_usage import RunPromise
from . import TestPromisePluginMixin


class TestCheckRamUsage(TestPromisePluginMixin):

  promise_name = "monitor-ram-usage.py"

  def setUp(self):
    super(TestCheckRamUsage, self).setUp()
    self.ram_data = namedtuple('ram_data', ['available'])

  def writePromise(self, **kw):
    super(TestCheckRamUsage, self).writePromise(self.promise_name,
      "from %s import %s\nextra_config_dict = %r\n"
      % (RunPromise.__module__, RunPromise.__name__, kw))

  def runPromise(self, summary, failed=False):
    self.configureLauncher(enable_anomaly=True, force=True)
    with mock.patch('psutil.virtual_memory', return_value=summary):
      if failed:
        self.assertRaises(PromiseError, self.launcher.run)
      else:
        self.launcher.run()
    result = self.getPromiseResult(self.promise_name)['result']
    self.assertEqual(result['failed'], failed)
    return result['message']

  def test_ram_ok(self):
    message = "RAM usage OK"
    available_ram = {'available':1e9}
    self.writePromise(**{
        'last-avg-ram-file':'last_avg_ram_file',
        'min-threshold-ram': 500, # 500MB
        'min-avg-ram': 100,
    })
    self.assertEqual(message, self.runPromise(self.ram_data(**available_ram)))

  def test_ram_below_threshold_nok(self):
    message = "RAM usage reached critical threshold:  190.7M  (threshold is  500.0M)"
    available_ram = {'available': 200e6}
    self.writePromise(**{
        'last-avg-ram-file':'last_avg_ram_file',
        'min-threshold-ram': 500, # ≈500MB
        'min-avg-ram': 100,
    })
    self.assertEqual(message, self.runPromise(self.ram_data(**available_ram)))

  def test_ram_below_average_nok(self):
    message = "Average RAM usage over the last 1 seconds reached threshold:  190.7M (threshold is  200.0M)"
    available_ram = {'available': 200e6}
    self.writePromise(**{
        'last-avg-ram-file':'last_avg_ram_file',
        'min-threshold-ram': 0,
        'min-avg-ram': 200,
        'avg-ram-period': 1,
    })
    m = self.runPromise(self.ram_data(**{'available': 300e6}))
    m = self.runPromise(self.ram_data(**{'available': 200e6}))
    time.sleep(1)
    self.assertEqual(message, self.runPromise(self.ram_data(**available_ram)))
    

if __name__ == '__main__':
  unittest.main()
