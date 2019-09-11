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
import six
from slapos.grid.promise import PromiseError
from slapos.promise.plugin.check_neo_health import RunPromise
from . import TestPromisePluginMixin


class TestCheckNeoHealth(TestPromisePluginMixin):

  promise_name = "monitor-neo-health.py"

  def setUp(self):
    super(TestCheckNeoHealth, self).setUp()
    self.writePromise(neoctl='neoctl')

  def writePromise(self, **kw):
    super(TestCheckNeoHealth, self).writePromise(self.promise_name,
      "from %s import %s\nextra_config_dict = %r\n"
      % (RunPromise.__module__, RunPromise.__name__, kw))

  def runPromise(self, summary, failed=False):
    self.configureLauncher(enable_anomaly=True)
    with mock.patch('subprocess.check_output', return_value=summary):
      if failed:
        self.assertRaises(PromiseError, self.launcher.run)
      else:
        self.launcher.run()
    result = self.getPromiseResult(self.promise_name)['result']
    self.assertEqual(result['failed'], failed)
    return result['message']

  def test_running(self):
    message = "\
RUNNING; UP_TO_DATE=12; ltid=03d0a8a41ea17cb9 (2019-06-26 19:48:07.179095)"
    self.assertEqual(message, self.runPromise("# {}\n%s\n" % message))

  def test_recovering(self):
    message = self.runPromise("""# {"problem": [null]}
RECOVERING; UP_TO_DATE=12; DOWN=1
""", True)
    self.assertEqual(message, "PROBLEM (main)")

  def test_lag(self):
    message = self.runPromise("""# {"warning": ["neo_21"]}
RUNNING; UP_TO_DATE=1; ltid=03d17cd35613ac88 (2019-08-02 13:07:20.174262)

neo_21
    BACKINGUP; UP_TO_DATE=1; ltid=03d17cd35613ac87; lag=ε
""", True)
    self.assertEqual(message, "WARNING (backup: neo_21)")

  def test_out_of_date(self):
    message = self.runPromise("""# {"warning": [null]}
BACKINGUP; OUT_OF_DATE=1, UP_TO_DATE=3; ltid=03d17cd516db69db (2019-08-02 13:09:05.357129)
""", True)
    self.assertEqual(message, "WARNING (main)")

  def test_critical(self):
    message = self.runPromise("ERROR: not connected", True)
    if six.PY3:
      self.assertEqual(message, "Expecting value: line 1 column 1 (char 0)")
      return
    self.assertEqual(message, "No JSON object could be decoded")


if __name__ == '__main__':
  unittest.main()
