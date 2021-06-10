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

import os
import socket
import time
from slapos.grid.promise import PromiseError
from slapos.promise.plugin.check_socket_listening import RunPromise
from . import TestPromisePluginMixin


SLAPOS_TEST_IPV4 = os.environ.get('SLAPOS_TEST_IPV4', '127.0.0.1')
SLAPOS_TEST_IPV6 = os.environ.get('SLAPOS_TEST_IPV6', '::1')


class TestCheckSocketListening(TestPromisePluginMixin):

  promise_name = "check-socket-listening.py"
  promise_template = "from %s import %s\nextra_config_dict = %%r\n" % (
    RunPromise.__module__, RunPromise.__name__)

  def writePromise(self, **kw):
    super(TestCheckSocketListening, self).writePromise(
      self.promise_name, self.promise_template % kw)

  def test_input_conflict(self):
    for keys in (
        (), ('port',),
        ('host',), ('host', 'pathname'), ('host', 'abstract'),
        ('host', 'abstract', 'pathname'), ('pathname', 'abstract')):
      self.writePromise(**dict.fromkeys(keys, 'a'))
      self.configureLauncher(force=True)
      self.assertRaises(PromiseError, self.launcher.run)

  def test_host_port(self):
    for host, family in ((SLAPOS_TEST_IPV4, socket.AF_INET),
                         (SLAPOS_TEST_IPV6, socket.AF_INET6)):
      s = socket.socket(family)
      try:
        s.bind((host, 0))
        port = s.getsockname()[1]
        self.writePromise(host=host, port=str(port))
        self.configureLauncher(force=True)
        self.assertRaises(PromiseError, self.launcher.run)
        s.listen(5)
        time.sleep(1)
        self.launcher.run()
      finally:
        s.close()

  def test_unix_socket(self):
    name = os.path.join(self.partition_dir, 'test_unix_socket')
    for addr, abstract in ((name, False), (name, True)):
      s = socket.socket(socket.AF_UNIX)
      try:
        if abstract:
          s.bind('\0' + addr)
          self.writePromise(abstract=addr)
        else:
          s.bind(addr)
          self.writePromise(pathname=addr)
        self.configureLauncher(force=True)
        self.assertRaises(PromiseError, self.launcher.run)
        s.listen(5)
        time.sleep(1)
        self.launcher.run()
      finally:
        s.close()
