# coding: utf-8
# Copyright (C) 2021  Nexedi SA and Contributors.
#                     Łukasz Nowak <luke@nexedi.com>
#
# This program is free software: you can Use, Study, Modify and Redistribute
# it under the terms of the GNU General Public License version 3, or (at your
# option) any later version, as published by the Free Software Foundation.
#
# You can also Link and Combine this program with other software covered by
# the terms of any of the Free Software licenses or any of the Open Source
# Initiative approved licenses and Convey the resulting work. Corresponding
# source of such a combination shall include the source code for all other
# software used.
#
# This program is distributed WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See COPYING file for full licensing terms.
# See https://www.nexedi.com/licensing for rationale and options.

from click.testing import CliRunner
import dns.resolver
import json
import mock
import os
import shutil
import tempfile
import unittest

from slapos import dnsresolver


class MockAnswer(object):
    def __init__(self, address):
        self.address = address


class Answer(object):
  def __init__(self, address):
    self.address = address


class DNSResolverTestCase(unittest.TestCase):
  def _query(self, h):
    return self._query_answer.get(h, [])

  def setUp(self):
    self.working_directory = tempfile.mkdtemp()
    self.patcher_list = [
      mock.patch.object(dns.resolver.Resolver, "query", new=self._query)
    ]
    [q.start() for q in self.patcher_list]

  def tearDown(self):
    shutil.rmtree(self.working_directory, True)
    [q.stop() for q in self.patcher_list]

  def _fillInput(self, value):
    with tempfile.NamedTemporaryFile(
      dir=self.working_directory,
      delete=False) as fh:
      fh.write(value.encode())
      return fh.name

  def test(self):
    ip = '123.124.125.126'
    input_list = [
      self._fillInput('1.example.com non.example.com\n%s' % (ip,)),
      self._fillInput('2.example.com %s' % (ip,)),
      self._fillInput(''),
    ]
    output = os.path.join(self.working_directory, 'output')

    self._query_answer = {
     '1.example.com': [Answer('127.0.0.1'), Answer('127.0.0.3')],
     '2.example.com': [Answer('127.0.0.2')]
    }

    runner = CliRunner()
    call_list = ['-o', output]
    call_list.extend(input_list)
    result = runner.invoke(dnsresolver.main, call_list)

    self.assertEqual(result.exit_code, 0)
    self.assertEqual(result.stdout, '')
    self.assertTrue(os.path.exists(output))

    with open(output, 'rb') as fh:
      self.assertEqual(
        json.load(fh),
        ['123.124.125.126', '127.0.0.1', '127.0.0.2', '127.0.0.3']
      )
