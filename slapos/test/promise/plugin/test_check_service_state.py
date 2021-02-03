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
import shutil
import psutil
import textwrap
import subprocess


class TestCheckServiceState(TestPromisePluginMixin):

  def setUp(self):
    TestPromisePluginMixin.setUp(self)
    self._tempdir = tempfile.mkdtemp()
    self._supervisor_socket = os.path.join(self._tempdir, 'sv.sock')
    self._supervisord_log = os.path.join(self._tempdir, 'supervisord.log')
    self._supervisord_pid = os.path.join(self._tempdir, 'supervisord.pid')
    self._supervisor_config = os.path.join(self._tempdir, 'supervisor.conf')
    self._service_name = 'test-service'
    self._test_log = os.path.join(self._tempdir, '%s.log' % (self._service_name,))

    with open(self._supervisor_config, 'w') as f:
      f.write(textwrap.dedent(
        """
        [unix_http_server]
        file = {self._supervisor_socket}

        [supervisorctl]
        serverurl = unix://{self._supervisor_socket}

        [supervisord]
        logfile = {self._supervisord_log}
        pidfile = {self._supervisord_pid}

        [rpcinterface:supervisor]
        supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface

        [program:{self._service_name}]
        command = sleep 10000
        autostart = false
        autorestart = false
        startretries = 0
        startsecs = 0
        redirect_stderr = true
        stdout_logfile = {self._test_log}

        """).format(**locals()))

    subprocess.check_output(
        ['supervisord', '--configuration', self._supervisor_config],
        cwd=self._tempdir,
    )

    self.promise_name = 'check-service-state.py'
    self.base_content = textwrap.dedent(
      """
      from slapos.promise.plugin.check_service_state import RunPromise
      extra_config_dict = {
        'run-directory': %(rundir)r,
        'service': %(service)r,
        'expect': %%(expect)r,
      }
      """) % {'rundir': self._tempdir, 'service': self._service_name}

  def tearDown(self):
    TestPromisePluginMixin.tearDown(self)
    with getSupervisorRPC(self._supervisor_socket) as supervisor:
      supervisor_process = psutil.Process(supervisor.getPID())
      supervisor.stopAllProcesses()
      supervisor.shutdown()
    _, alive = psutil.wait_procs([supervisor_process], timeout=300)
    if alive:
      supervisor_process.kill()
    shutil.rmtree(self._tempdir)

  def test_running_expect_running(self):
    with getSupervisorRPC(self._supervisor_socket) as supervisor:
      supervisor.startProcess(self._service_name)
      assert supervisor.getProcessInfo(self._service_name)['statename'] == 'RUNNING'
    content = self.base_content % {'expect': 'running'}
    self.writePromise(self.promise_name, content)
    self.configureLauncher()
    self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], False)
    self.assertEqual(
      result['result']['message'],
      "OK service %r is in expected state 'running'" % (self._service_name,)
    )

  def test_running_expect_stopped(self):
    with getSupervisorRPC(self._supervisor_socket) as supervisor:
      supervisor.startProcess(self._service_name)
      assert supervisor.getProcessInfo(self._service_name)['statename'] == 'RUNNING'
    content = self.base_content % {'expect': 'stopped'}
    self.writePromise(self.promise_name, content)
    self.configureLauncher()
    with self.assertRaises(PromiseError):
      self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], True)
    self.assertEqual(
      result['result']['message'],
      "ERROR service %r is in state 'running' (expected 'stopped')" % (self._service_name,)
    )

  def test_running_expect_undefined(self):
    with getSupervisorRPC(self._supervisor_socket) as supervisor:
      supervisor.startProcess(self._service_name)
      assert supervisor.getProcessInfo(self._service_name)['statename'] == 'RUNNING'
    content = self.base_content % {'expect': 'undefined'}
    self.writePromise(self.promise_name, content)
    self.configureLauncher()
    self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], False)
    self.assertEqual(
      result['result']['message'],
      "OK service %r is allowed to be in any state (expect = 'undefined')" % (self._service_name,)
    )

  def test_stopped_expect_running(self):
    with getSupervisorRPC(self._supervisor_socket) as supervisor:
      assert supervisor.getProcessInfo(self._service_name)['statename'] == 'STOPPED'
    content = self.base_content % {'expect': 'running'}
    self.writePromise(self.promise_name, content)
    self.configureLauncher()
    with self.assertRaises(PromiseError):
      self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], True)
    self.assertEqual(
      result['result']['message'],
      "ERROR service %r is in state 'stopped' (expected 'running')" % (self._service_name,)
    )

  def test_stopped_expect_stopped(self):
    with getSupervisorRPC(self._supervisor_socket) as supervisor:
      assert supervisor.getProcessInfo(self._service_name)['statename'] == 'STOPPED'
    content = self.base_content % {'expect': 'stopped'}
    self.writePromise(self.promise_name, content)
    self.configureLauncher()
    self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], False)
    self.assertEqual(
      result['result']['message'],
      "OK service %r is in expected state 'stopped'" % (self._service_name,)
    )

  def test_stopped_expect_undefined(self):
    with getSupervisorRPC(self._supervisor_socket) as supervisor:
      assert supervisor.getProcessInfo(self._service_name)['statename'] == 'STOPPED'
    content = self.base_content % {'expect': 'undefined'}
    self.writePromise(self.promise_name, content)
    self.configureLauncher()
    self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], False)
    self.assertEqual(
      result['result']['message'],
      "OK service %r is allowed to be in any state (expect = 'undefined')" % (self._service_name,)
    )

if __name__ == '__main__':
  unittest.main()
