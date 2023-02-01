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
import time
from slapos.grid.promise import PromiseError
from slapos.promise.plugin.check_cpu_temperature import RunPromise
from . import TestPromisePluginMixin


class TestCheckCpuTemperature(TestPromisePluginMixin):

  promise_name = "monitor-cpu-temperature.py"

  def setUp(self):
    super(TestCheckCpuTemperature, self).setUp()

  def writePromise(self, **kw):
    super(TestCheckCpuTemperature, self).writePromise(self.promise_name,
      "from %s import %s\nextra_config_dict = %r\n"
      % (RunPromise.__module__, RunPromise.__name__, kw))

  def runPromise(self, summary, failed=False):
    self.configureLauncher(enable_anomaly=True, force=True)
    with mock.patch('psutil.sensors_temperatures', return_value=summary):
      if failed:
        self.assertRaises(PromiseError, self.launcher.run)
      else:
        self.launcher.run()
    result = self.getPromiseResult(self.promise_name)['result']
    self.assertEqual(result['failed'], failed)
    return result['message']

  def test_temp_ok(self):
    message = "Temperature OK (50 °C)"
    self.writePromise(**{
        'last-avg-computation-file':'last_avg_computation_file',
        'max-spot-temp': 80,
        'max-avg-temp': 100,
    })
    self.assertEqual(message, self.runPromise({'coretemp': [[0, 50]]}))

  def test_spot_critical(self):
    message = "Temperature reached critical threshold: 90 °C (threshold is 80.0 °C)"
    self.writePromise(**{
        'last-avg-computation-file':'last_avg_computation_file',
        'max-spot-temp': 80,
        'max-avg-temp': 100,
    })
    self.assertEqual(message, self.runPromise({'coretemp': [[0, 90]]}))

  def test_avg_critical(self):
    message = "Average temperature over the last 1s reached threshold: 45.0 °C (threshold is 40.0 °C)"
    self.writePromise(**{
        'last-avg-computation-file':'last_avg_computation_file',
        'max-spot-temp': 99999,
        'max-avg-temp': 40,
        'avg-temp-duration': 1,
    })
    m = self.runPromise({'coretemp': [[0, 0]]})
    time.sleep(0.6)
    m = self.runPromise({'coretemp': [[0, 0]]})
    time.sleep(0.5)
    self.assertEqual(message, self.runPromise({'coretemp': [[0, 90]]}))

if __name__ == '__main__':
  unittest.main()
