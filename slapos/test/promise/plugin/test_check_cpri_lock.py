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
from datetime import datetime
from datetime import timedelta
from slapos.grid.promise import PromiseError
from slapos.promise.plugin.check_cpri_lock import RunPromise
from . import TestPromisePluginMixin


class TestCheckCpriLock(TestPromisePluginMixin):

  promise_name = "check-cpri-lock.py"

  def setUp(self):
    super(TestCheckCpriLock, self).setUp()


  def writePromise(self, **kw):
    super(TestCheckCpriLock, self).writePromise(self.promise_name,
      "from %s import %s\nextra_config_dict = %r\n"
      % (RunPromise.__module__, RunPromise.__name__, kw))

  def test_promise_success(self):
    self.amarisoft_rf_info_log = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'amarisoft_rf_info.json.log')
    if os.path.exists(self.amarisoft_rf_info_log):
      os.remove(self.amarisoft_rf_info_log)
    with open(self.amarisoft_rf_info_log, 'w+') as f:
      f.write(
      """
      {"time": "%s", "log_level": "INFO", "message": "RF info", "data": {'rf_info': "CPRI: x16 HW SW"}}
      """ % ((datetime.now() - timedelta(seconds=5)).strftime("%Y-%m-%d %H:%M:%S")[:-3],))
      self.writePromise(**{
        'amarisoft-rf-info-log': self.amarisoft_rf_info_log,
#        'stats-period': 100,
    })
    self.configureLauncher()
    self.launcher.run()


  def test_promise_fail(self):
    self.amarisoft_rf_info_log = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'amarisoft_rf_info.json.log')
    if os.path.exists(self.amarisoft_rf_info_log):
      os.remove(self.amarisoft_rf_info_log)
    with open(self.amarisoft_rf_info_log, 'w') as f:
      f.write(
      """
      {"time": "%s", "log_level": "INFO", "message": "RF info", "data": {'rf_info': "CPRI: x16\\n"}}
      """ % ((datetime.now() - timedelta(seconds=5)).strftime("%Y-%m-%d %H:%M:%S")[:-3],))
    self.writePromise(**{
        'amarisoft-rf-info-log': self.amarisoft_rf_info_log,
#        'stats-period': 100,
    })
    self.configureLauncher()
    with self.assertRaises(PromiseError):
      self.launcher.run()

if __name__ == '__main__':
  unittest.main()
