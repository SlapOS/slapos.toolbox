##############################################################################
#
# Copyright (c) 2019 Vifib SARL and Contributors. All Rights Reserved.
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

from slapos.grid.promise import PromiseError
from slapos.test.promise.plugin import TestPromisePluginMixin
from slapos.grid.svcbackend import getSupervisorRPC

import tempfile
import os
import unittest
import textwrap


class TestCheckServiceState(TestPromisePluginMixin):

  def setUp(self):
    TestPromisePluginMixin.setUp(self)

    self.script_name = 'test-check-script'
    self.process_state_file = os.path.join(self.partition_dir, '.slapgrid/state', self.script_name)
    self.script_path = os.path.join(self.partition_dir, 'etc/run', self.script_name)

    self.second_script_name = 'test-second-check-script'
    self.second_process_state_file = os.path.join(self.partition_dir, '.slapgrid/state', self.second_script_name)
    self.second_script_path = os.path.join(self.partition_dir, 'etc/run', self.second_script_name)
    
    self.state_dict = {
      "processname": self.script_name,
      "groupname": "slappartX",
      "from_state": "RUNNING",
      "expected": "0",
      "pid": "124356"
    }
    os.makedirs(os.path.dirname(self.process_state_file))
    os.makedirs(os.path.dirname(self.script_path))

    with open(self.script_path, 'w') as f:
      f.write("")

    self.promise_name = 'check-process-state.py'
    self.promise_content = textwrap.dedent(
      """
      from slapos.promise.plugin.check_process_exit_code import RunPromise
      extra_config_dict = {
        'script-directory': %(script-dir)r,
        'state-directory': %(state-dir)r,
      }
      """) % {'script-dir': os.path.dirname(self.process_state_file),
              'state-dir': os.path.dirname(self.script_path)}


  def test_check_process_state(self):
    self.writePromise(self.promise_name, self.promise_content)
    self.state_dict['expected'] = "1"
    with open(self.process_state_file, 'w') as f:
      f.write(json.dumps(self.state_dict))
    self.configureLauncher()
    self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], False)
    self.assertEqual(
      result['result']['message'],
      "Processes exit code are OK"
    )

  def test_check_process_state_fail(self):
    self.writePromise(self.promise_name, self.promise_content)
    self.state_dict['expected'] = "0"
    with open(self.process_state_file, 'w') as f:
      f.write(json.dumps(self.state_dict))
    self.configureLauncher()
    self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], True)
    self.assertEqual(
      result['result']['message'],
      "Process '%s' script exited with unexpected exit code" % self.promise_name
    )

  def test_check_process_state_multiple_process(self):
    self.writePromise(self.promise_name, self.promise_content)
    # enable second process script
    with open(self.second_script_path, 'w') as f:
      f.write("")

    self.state_dict['expected'] = "1"
    with open(self.process_state_file, 'w') as f:
      f.write(json.dumps(self.state_dict))

    with open(self.second_process_state_file, 'w') as f:
      f.write(json.dumps(self.state_dict))
    self.configureLauncher()
    self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], False)
    self.assertEqual(
      result['result']['message'],
      "Processes exit code are OK"
    )

  def test_check_process_state_multiple_process_one_fail(self):
    self.writePromise(self.promise_name, self.promise_content)
    # enable second process script
    with open(self.second_script_path, 'w') as f:
      f.write("")

    self.state_dict['expected'] = "1"
    with open(self.process_state_file, 'w') as f:
      f.write(json.dumps(self.state_dict))

    self.state_dict['expected'] = "0"
    with open(self.second_process_state_file, 'w') as f:
      f.write(json.dumps(self.state_dict))
    self.configureLauncher()
    self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], True)
    self.assertEqual(
      result['result']['message'],
      "Process '%s' script exited with unexpected exit code" % self.second_script_name
    )

  def test_check_process_state_multiple_process_all_fail(self):
    self.writePromise(self.promise_name, self.promise_content)
    # enable second process script
    with open(self.second_script_path, 'w') as f:
      f.write("")

    self.state_dict['expected'] = "0"
    with open(self.process_state_file, 'w') as f:
      f.write(json.dumps(self.state_dict))

    with open(self.second_process_state_file, 'w') as f:
      f.write(json.dumps(self.state_dict))
    self.configureLauncher()
    self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], True)
    self.assertEqual(
      result['result']['message'],
      "Process '%s' script exited with unexpected exit code" % self.second_script_name
    )

if __name__ == '__main__':
  unittest.main()
