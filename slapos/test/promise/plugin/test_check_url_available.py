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

import BaseHTTPServer
import json
import multiprocessing
import time
import unittest

SLAPOS_TEST_IPV4 = '127.0.0.1'
SLAPOS_TEST_IPV4_PORT = 57965
HTTPS_ENDPOINT = "http://%s:%s/" % (SLAPOS_TEST_IPV4, SLAPOS_TEST_IPV4_PORT)


class TestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
  def do_GET(self):
    timeout = int(self.headers.dict.get('timeout', '0'))
    time.sleep(timeout)
    response = int(self.path.split('/')[-1])
    self.send_response(response)

    self.send_header("Content-type", "application/json")
    self.end_headers()
    response = {
      'Path': self.path,
    }
    self.wfile.write(json.dumps(response, indent=2))


class TestCheckUrlAvailable(TestPromisePluginMixin):

  @classmethod
  def setUpClass(cls):
    server = BaseHTTPServer.HTTPServer(
      (SLAPOS_TEST_IPV4, SLAPOS_TEST_IPV4_PORT),
      TestHandler)

    cls.server_process = multiprocessing.Process(
      target=server.serve_forever)
    cls.server_process.start()

  @classmethod
  def tearDownClass(cls):
    cls.server_process.terminate()
    cls.server_process.join()

  def setUp(self):
    TestPromisePluginMixin.setUp(self)
    self.promise_name = "check-url-available.py"

    self.base_content = """from slapos.promise.plugin.check_url_available import RunPromise

extra_config_dict = {
  'url': '%(url)s',
  'timeout': %(timeout)s,
  'check-secure': %(check_secure)s,
  'ignore-code': %(ignore_code)s,
}
"""

    self.base_content_http_code = """from slapos.promise.plugin.check_url_available import RunPromise

extra_config_dict = {
  'url': '%(url)s',
  'timeout': %(timeout)s,
  'check-secure': %(check_secure)s,
  'ignore-code': %(ignore_code)s,
  'http_code': %(http_code)s
}
"""

  def tearDown(self):
    TestPromisePluginMixin.tearDown(self)

  def test_check_url_bad(self):
    content = self.base_content % {
      'url': 'https://',
      'timeout': 10,
      'check_secure': 0,
      'ignore_code': 0,
    }
    self.writePromise(self.promise_name, content)
    self.configureLauncher()
    with self.assertRaises(PromiseError):
      self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], True)
    self.assertEqual(
      result['result']['message'],
      "ERROR: Invalid URL u'https://': No host supplied"
    )

  def test_check_url_malformed(self):
    content = self.base_content % {
      'url': '',
      'timeout': 10,
      'check_secure': 0,
      'ignore_code': 0,
    }
    self.writePromise(self.promise_name, content)
    self.configureLauncher()
    with self.assertRaises(PromiseError):
      self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], True)
    self.assertEqual(
      result['result']['message'],
      "ERROR: Invalid URL '': No schema supplied. Perhaps you meant http://?"
    )

  def test_check_url_site_off(self):
    content = self.base_content % {
      'url': 'https://localhost:56789/site',
      'timeout': 10,
      'check_secure': 0,
      'ignore_code': 0,
    }
    self.writePromise(self.promise_name, content)
    self.configureLauncher()
    with self.assertRaises(PromiseError):
      self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], True)
    self.assertEqual(
      result['result']['message'],
      "ERROR connection not possible while accessing "
      "'https://localhost:56789/site'"
    )

  def test_check_200(self):
    url = HTTPS_ENDPOINT + '200'
    content = self.base_content % {
      'url': url,
      'timeout': 10,
      'check_secure': 0,
      'ignore_code': 0,
    }
    self.writePromise(self.promise_name, content)
    self.configureLauncher()
    self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], False)
    self.assertEqual(
      result['result']['message'],
      "%r is available" % (url,)
    )

  def test_check_401(self):
    url = HTTPS_ENDPOINT + '401'
    content = self.base_content % {
      'url': url,
      'timeout': 10,
      'check_secure': 0,
      'ignore_code': 0,
    }
    self.writePromise(self.promise_name, content)
    self.configureLauncher()
    with self.assertRaises(PromiseError):
      self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], True)
    self.assertEqual(
      result['result']['message'],
      "%r is not available (returned 401, expected 200)." % (url,)
    )

  def test_check_401_ignore_code(self):
    url = HTTPS_ENDPOINT + '401'
    content = self.base_content % {
      'url': url,
      'timeout': 10,
      'check_secure': 0,
      'ignore_code': 1,
    }
    self.writePromise(self.promise_name, content)
    self.configureLauncher()
    self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], False)
    self.assertEqual(
      result['result']['message'],
      "%r is available" % (url,)
    )

  def test_check_401_check_secure(self):
    url = HTTPS_ENDPOINT + '401'
    content = self.base_content % {
      'url': url,
      'timeout': 10,
      'check_secure': 1,
      'ignore_code': 0,
    }
    self.writePromise(self.promise_name, content)
    self.configureLauncher()
    self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], False)
    self.assertEqual(
      result['result']['message'],
      "%r is protected (returned 401)." % (url,)
    )

  def test_check_512_http_code(self):
    url = HTTPS_ENDPOINT + '512'
    content = self.base_content_http_code % {
      'url': url,
      'timeout': 10,
      'check_secure': 0,
      'ignore_code': 0,
      'http_code': 512,
    }
    self.writePromise(self.promise_name, content)
    self.configureLauncher()
    self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], False)
    self.assertEqual(
      result['result']['message'],
      "%r is available" % (url,)
    )


if __name__ == '__main__':
  unittest.main()
