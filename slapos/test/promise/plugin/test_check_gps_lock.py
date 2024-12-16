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
import json
from datetime import datetime
from datetime import timedelta
from slapos.grid.promise import PromiseError
from slapos.promise.plugin.check_gps_lock import RunPromise
from . import TestPromisePluginMixin


class TestCheckGPSLock(TestPromisePluginMixin):

  promise_name = "check-gps-lock.py"

  def setUp(self):
    super(TestCheckGPSLock, self).setUp()
    self.amarisoft_rf_info_log = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'amarisoft_rf_info.json.log')

    rf_info = \
"""
TRX SDR driver 2024-11-20, API v15
PCIe RFIC /dev/sdr0:
  Hardware ID: 0x4b01
  DNA: [0x0070b5443f4a2854]
  Serial: ''
  FPGA revision: 2021-10-08  15:38:12
  FPGA vccint: 1.01 V
  FPGA vccaux: 1.78 V
  FPGA vccbram: 1.01 V
  FPGA temperature: 55.5 °C
  AD9361 temperature: 37 °C
  AGC: Off
  Sync: gps (locked)
  Clock: internal (locked)
  Clock tune: -0.2 ppm
  NUMA: -1
  Caps: 
  TX channels: 2;  RX channels: 2
  DMA: 1 ch, 32 bits, SMem index: Off, RX Headers: Off
  DMA0: TX fifo: 33.33us  Usage=8/12288 (0%)
  DMA0: RX fifo: 33.33us  Usage=8/12288 (0%)
  DMA0: TX_Underflows: 0  RX_Overflows: 0
  BUFS: bps=32 TX idx=9293176/52600.113 (33.3us) RX: idx=9293176/52600.111 (33.3us)

GPS info:
  UTC:  2024-11-29 10:21:54
  pos:  lat=50.64428°  long=3.07739°
  height: 39.1m  nb_sats: 12
"""
    self.rf_info_data = {'message': 'rf', 'rf_info': rf_info}


  def writeLog(self, data, ago=5):
    with open(self.amarisoft_rf_info_log, 'w') as f:
      f.write(
      """{"time": "%s", "log_level": "INFO", "message": "RF info", "data": %s}""" %
        ((datetime.now() - timedelta(seconds=ago)).strftime("%Y-%m-%d %H:%M:%S")[:-3], json.dumps(data)))

  def writePromise(self, **kw):
    kw.update({'amarisoft-rf-info-log': self.amarisoft_rf_info_log,
               'stats-period':          100})
    super(TestCheckGPSLock, self).writePromise(self.promise_name,
      "from %s import %s\nextra_config_dict = %r\n"
      % (RunPromise.__module__, RunPromise.__name__, kw))

  def test_locked_ok(self):
    self.writeLog(self.rf_info_data)
    self.writePromise()
    self.configureLauncher()
    self.launcher.run()

  def test_stale_data(self):
    self.writeLog(self.rf_info_data, ago=500)
    self.writePromise()
    self.configureLauncher()
    with self.assertRaisesRegex(PromiseError, 'rf_info: stale data'):
      self.launcher.run()

if __name__ == '__main__':
  unittest.main()
