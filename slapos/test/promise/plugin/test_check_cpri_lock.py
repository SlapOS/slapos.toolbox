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
from slapos.promise.plugin.check_cpri_lock import RunPromise
from . import TestPromisePluginMixin


class TestCheckCpriLock(TestPromisePluginMixin):

  promise_name = "check-cpri-lock.py"

  def setUp(self):
    super(TestCheckCpriLock, self).setUp()
    self.amarisoft_rf_info_log = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'amarisoft_rf_info.json.log')

    rf_info = \
"""
TRX SDR driver 2023-09-07, API v15/18
PCIe CPRI /dev/sdr2@1:
  Hardware ID: 0x4b12
  DNA: [0x0048248a334a7054]
  Serial: ''
  FPGA revision: 2023-06-23  10:05:24
  FPGA vccint: 0.98 V
  FPGA vccaux: 1.76 V
  FPGA vccbram: 0.98 V
  FPGA temperature: 71.9 °C
  Clock tune: 0.0 ppm
  NUMA: 0
  CPRI_option: '5' (x8) lock=no
  DMA0: TX fifo: 66.67us  Usage=16/32768 (0%)
  DMA0: RX fifo: 66.67us  Usage=16/32768 (0%)
  DMA0 Underflows: 0
  DMA0 Overflows: 0
PCIe CPRI /dev/sdr3@1:
  Hardware ID: 0x4b12
  DNA: [0x0048248a334a7054]
  Serial: ''
  FPGA revision: 2023-06-23  10:05:24
  FPGA vccint: 0.98 V
  FPGA vccaux: 1.77 V
  FPGA vccbram: 0.98 V
  FPGA temperature: 71.7 °C
  Clock tune: 0.0 ppm
  NUMA: 0
  CPRI_option: '5' (x8) lock=HW+SW rx/tx=46.606us
    Port #0: T14=46.606us
  DMA0: TX fifo: 66.67us  Usage=16/32768 (0%)
  DMA0: RX fifo: 66.67us  Usage=16/32768 (0%)
  DMA0 Underflows: 0
  DMA0 Overflows: 0
PCIe SDR /dev/sdr4@0:
  AAA: bbb
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
    super(TestCheckCpriLock, self).writePromise(self.promise_name,
      "from %s import %s\nextra_config_dict = %r\n"
      % (RunPromise.__module__, RunPromise.__name__, kw))

  def test_locked_ok(self):
    self.writeLog(self.rf_info_data)
    self.writePromise(sdr_dev='3', sfp_port='1')
    self.configureLauncher()
    self.launcher.run()

  def test_no_lock(self):
    self.writeLog(self.rf_info_data)
    self.writePromise(sdr_dev='2', sfp_port='1')
    self.configureLauncher()
    with self.assertRaisesRegex(PromiseError, r'(?m)HW Lock is missing\n.*SW Lock is missing'):
      self.launcher.run()

  def test_no_device(self):
    self.writeLog(self.rf_info_data)
    self.writePromise(sdr_dev='1', sfp_port='0')
    self.configureLauncher()
    with self.assertRaisesRegex(PromiseError, 'no device entry'):
      self.launcher.run()

  def test_no_cpri_entry(self):
    self.writeLog(self.rf_info_data)
    self.writePromise(sdr_dev='4', sfp_port='0')
    self.configureLauncher()
    with self.assertRaisesRegex(PromiseError, 'no CPRI feature'):
      self.launcher.run()

  def test_stale_data(self):
    self.writeLog(self.rf_info_data, ago=500)
    self.writePromise(sdr_dev='3', sfp_port='1')
    self.configureLauncher()
    with self.assertRaisesRegex(PromiseError, 'rf_info: stale data'):
      self.launcher.run()

  def test_2022(self):
    # Amarisoft software from 2022 has different format for rf_info
    rf_info_data = self.rf_info_data.copy()
    rf_info_data['rf_info'] = \
"""
TRX SDR driver 2022-10-26, API v15/18
PCIe CPRI /dev/sdr0@0:  
  Hardware ID: 0x4b12
  DNA: [0x000841c20971b05c]
  Serial: ''
  FPGA revision: 2022-10-25  08:58:42
  FPGA vccint: 0.98 V
  FPGA vccaux: 1.77 V
  FPGA vccbram: 0.99 V
  FPGA temperature: 71.9 °C
  Clock tune: -0.1 ppm
  NUMA: 0
  CPRI: x16 HW SW
  DMA0: TX fifo: 66.67us  Usage=16/65536 (0%)
  DMA0: RX fifo: 66.67us  Usage=864/65536 (1%)
  DMA0 Underflows: 0
  DMA0 Overflows: 0
  """   # NOTE extra spaces in the end and trailing spaces after /dev/sdr0@:0
    self.writeLog(rf_info_data)
    self.writePromise(sdr_dev='0', sfp_port='0')
    self.configureLauncher()
    self.launcher.run()

  def test_2024_06_15(self):
    # Amarisoft software from 2024-06-15 has changed format of rf_info
    rf_info_data = self.rf_info_data.copy()
    rf_info_data['rf_info'] = \
"""
TRX SDR driver 2024-06-11, API v15
PCIe CPRI /dev/sdr0@0:
  Hardware ID: 0x4b12
  DNA: [0x0068102442f1b05c]
  Serial: ''
  FPGA revision: 2024-03-14  16:19:27
  FPGA vccint: 0.98 V
  FPGA vccaux: 1.77 V
  FPGA vccbram: 0.99 V
  FPGA temperature: 57.6 °C
Clock tune: 0.2 ppm
  NUMA: 0
  CPRI_option: '5' (x8) signal=yes lock=HW+SW rx/tx=2.433us
    Port #0: T14=2.433us
  DMA0: TX fifo: 66.67us  Usage=16/32768 (0%)
  DMA0: RX fifo: 66.67us  Usage=16/32768 (0%)
  DMA0 Underflows: 0
  DMA0: Overflows: 0
  BUFS: TX idx=53800.99 RX idx=53800.100
PCIe CPRI /dev/sdr1@0:
  Hardware ID: 0x4b12
  DNA: [0x0048b504006af054]
  Serial: ''
  FPGA revision: 2024-03-14  16:19:27
  FPGA vccint: 0.99 V
  FPGA vccaux: 1.78 V
  FPGA vccbram: 0.99 V
  FPGA temperature: 51.6 °C
Clock tune: -4.0 ppm
  NUMA: 1
  CPRI_option: '5' (x8) signal=yes lock=HW+SW rx/tx=1.994us
    Port #0: T14=1.994us
  DMA0: TX fifo: 66.67us  Usage=16/32768 (0%)
  DMA0: RX fifo: 66.67us  Usage=16/32768 (0%)
  DMA0 Underflows: 0
  DMA0: Overflows: 0
  BUFS: TX idx=53800.114 RX idx=53800.115
PCIe CPRI /dev/sdr0@2:
  Hardware ID: 0x4b12
  DNA: [0x0068102442f1b05c]
  Serial: ''
  FPGA revision: 2024-03-14  16:19:27
  FPGA vccint: 0.98 V
  FPGA vccaux: 1.77 V
  FPGA vccbram: 0.98 V
  FPGA temperature: 57.6 °C
Clock tune: 0.2 ppm
  NUMA: 0
  CPRI_option: '5' (x8) signal=yes lock=HW+SW rx/tx=2.393us
    Port #0: T14=2.393us
  DMA0: TX fifo: 66.67us  Usage=16/32768 (0%)
  DMA0: RX fifo: 66.67us  Usage=16/32768 (0%)
  DMA0 Underflows: 0
  DMA0: Overflows: 0
  BUFS: TX idx=53800.133 RX idx=53800.134

GPS info:
  UTC:  2024-10-24 11:51:43
  pos:  lat=12.34567°  long=34.56789°
  height: 118.1m  nb_sats: 10
"""
    self.writeLog(rf_info_data)
    for sdr, port in [(0,0), (1,0), (0,2)]:
        self.writePromise(sdr_dev='%d' % sdr, sfp_port='%d' % port)
    self.configureLauncher()
    self.launcher.run()


if __name__ == '__main__':
  unittest.main()
