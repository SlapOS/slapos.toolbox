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

from slapos.test.promise.plugin import TestPromisePluginMixin
from slapos.grid.promise import PromiseError
import unittest


class TestCheckUrlAvailable(TestPromisePluginMixin):

  def setUp(self):
    TestPromisePluginMixin.setUp(self)
    self.promise_name = "check-url-available.py"

    self.base_content = """from slapos.promise.plugin.check_http_access import RunPromise

extra_config_dict = {
  'url': '%(url)s',
  'verify': '%(verify)s',
}
"""

  def tearDown(self):
    TestPromisePluginMixin.tearDown(self)

  def test_check_url(self):
    content = self.base_content % {
      'url': 'https://www.erp5.com/',
      'verify': 'False',
    }
    self.writePromise(self.promise_name, content)
    self.configureLauncher()
    self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], False)
    self.assertEqual(
      "url https://www.erp5.com/ OK",
      result['result']['message'])

  def test_check_url_verify_true(self):
    content = self.base_content % {
      'url': 'https://www.erp5.com/',
      'verify': 'True',
    }
    self.writePromise(self.promise_name, content)
    self.configureLauncher()
    self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], False)
    self.assertEqual(
      "url https://www.erp5.com/ OK",
      result['result']['message'])

  def test_check_url_bad(self):
    content = self.base_content % {
      'url': 'https://',
      'verify': 'False',
    }
    self.writePromise(self.promise_name, content)
    self.configureLauncher()
    with self.assertRaises(PromiseError):
      self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], True)
    self.assertEqual(
      "ERROR 'Invalid URL u'https://': No host supplied' while "
      "accessing url https://",
      result['result']['message'])

  def test_check_url_malformed(self):
    content = self.base_content % {
      'url': '',
      'verify': 'False',
    }
    self.writePromise(self.promise_name, content)
    self.configureLauncher()
    with self.assertRaises(PromiseError):
      self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], True)
    self.assertEqual(
      "ERROR 'Invalid URL '': No schema supplied. Perhaps you "
      "meant http://?' while accessing url",
      result['result']['message'])

  def test_check_url_site_off(self):
    content = content = self.base_content % {
      'url': 'https://localhost:56789/site',
      'verify': 'False',
    }
    self.writePromise(self.promise_name, content)
    self.configureLauncher()
    with self.assertRaises(PromiseError):
      self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], True)
    self.assertEqual(
      "ERROR connection not possible while accessing url "
      "https://localhost:56789/site",
      result['result']['message'])


if __name__ == '__main__':
  unittest.main()
