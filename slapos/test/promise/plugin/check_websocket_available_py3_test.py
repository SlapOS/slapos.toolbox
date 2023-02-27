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

# This module contains python3 syntax that can't be parsed by python2
# that's why it is in a separated module

from slapos.grid.promise import PromiseError
from . import TestPromisePluginMixin
from slapos.util import str2bytes

import asyncio
import contextlib
import os
import time
import websocket
from websockets import serve
import multiprocessing


class CheckWebsocketAvailableMixin(TestPromisePluginMixin):


  @classmethod
  def setUpClass(cls):
    SLAPOS_TEST_IPV4 = os.environ.get('SLAPOS_TEST_IPV4', '127.0.0.1')
    SLAPOS_TEST_IPV4_PORT = 57965
    cls.WS_ENDPOINT = "ws://%s:%s/" % (SLAPOS_TEST_IPV4, SLAPOS_TEST_IPV4_PORT)

    async def echo(websocket):
      path = websocket.path.split('/')[-1]

      if '_' in path:
        response, timeout = path.split('_')
        response = response
        timeout = int(timeout)
      else:
        timeout = 0
        response = path

      time.sleep(timeout)
      async for message in websocket:
        if response == "OK":
          await websocket.send(message)
        else:
          await websocket.send("bad")

    async def server():
      async with serve(echo, SLAPOS_TEST_IPV4, SLAPOS_TEST_IPV4_PORT):
        await asyncio.Future()  # run forever

    def main():
      asyncio.run(server())

    cls.server_process = multiprocessing.Process(target=main)
    cls.server_process.start()
    for _ in range(20):
      try:
        with contextlib.closing(websocket.create_connection((SLAPOS_TEST_IPV4, SLAPOS_TEST_IPV4_PORT))):
          break
      except Exception:
        time.sleep(.1)

  @classmethod
  def tearDownClass(cls):
    cls.server_process.terminate()
    cls.server_process.join()

  def setUp(self):
    TestPromisePluginMixin.setUp(self)
    self.promise_name = "check-websocket-available.py"

  def make_content(self, option_dict):
    content = """from slapos.promise.plugin.check_websocket_available import RunPromise

extra_config_dict = {
"""
    for option in option_dict.items():
      content += "\n  '%s': %r," % option

    return content + "\n}"

  def tearDown(self):
    TestPromisePluginMixin.tearDown(self)
