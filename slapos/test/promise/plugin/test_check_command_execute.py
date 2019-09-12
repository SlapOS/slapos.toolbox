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

import tempfile
import os
import six
import shutil


class TestCheckCommandExecute(TestPromisePluginMixin):
  def _createScript(self, filename, content):
    with open(filename, 'w') as fh:
      fh.write(content)
    os.chmod(filename, 0o755)

  def setUp(self):
    TestPromisePluginMixin.setUp(self)
    self.tempdir = tempfile.mkdtemp()
    self.fail_command = os.path.join(self.tempdir, 'fail')
    self._createScript(self.fail_command, """#/bin/sh
echo failure
echo me 1>&2
exit 1""")
    self.success_command = os.path.join(self.tempdir, 'success')
    self._createScript(self.success_command, """#/bin/sh
echo success
echo me 1>&2
exit 0""")
    self.promise_name = "check-command-execute.py"

    self.base_content = """from slapos.promise.plugin.check_command_execute import RunPromise

extra_config_dict = {
  'command': %(command)r
}
"""

  def tearDown(self):
    TestPromisePluginMixin.tearDown(self)
    shutil.rmtree(self.tempdir)

  def test_check_success(self):
    self.writePromise(self.promise_name, self.base_content % {
      'command': self.success_command})
    self.configureLauncher()
    self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], False)
    self.assertEqual(
      result['result']['message'],
      "OK %r run with success" % (self.success_command,)
    )

  def test_check_failure(self):
    self.writePromise(self.promise_name, self.base_content % {
      'command': self.fail_command})
    self.configureLauncher()
    with self.assertRaises(PromiseError):
      self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], True)
    self.assertEqual(
      result['result']['message'],
      "ERROR %r run with failure, output: %s'failure\\nme\\n'" % (
         self.fail_command, 'b' if six.PY3 else '')
    )
