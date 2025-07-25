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
import time
from datetime import datetime
from datetime import timedelta
from slapos.grid.promise import PromiseError
from slapos.promise.plugin.check_oru_sync import RunPromise
from . import TestPromisePluginMixin


class TestCheckOruSyncSuccess(TestPromisePluginMixin):

  promise_name = "check-oru-sync.py"

  def setUp(self):
    super(TestCheckOruSyncSuccess, self).setUp()
    self.netconf_log = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'netconf.json.log')

  def writePromise(self, **kw):
    super(TestCheckOruSyncSuccess, self).writePromise(self.promise_name,
      "from %s import %s\nextra_config_dict = %r\n"
      % (RunPromise.__module__, RunPromise.__name__, kw))

  def test_promise_success(self):
    with open(self.netconf_log, 'w+') as f:
      f.write("""{"time": "%s", "log_level": "INFO", "message": "", "data": {"notification": {"@xmlns": "urn:ietf:params:xml:ns:netconf:notification:1.0", "eventTime": "1970-01-01T01:34:04Z", "alarm-notif": {"@xmlns": "urn:o-ran:fm:1.0", "fault-id": "18", "fault-source": "Radio Module", "affected-objects": {"name": "Radio Module"}, "fault-severity": "MAJOR", "is-cleared": "false", "fault-text": "Synchronization Error Alarm", "event-time": "1970-01-01T01:34:04Z"}}}}
{"time": "%s", "log_level": "INFO", "message": "", "data": {"notification": {"@xmlns": "urn:ietf:params:xml:ns:netconf:notification:1.0", "eventTime": "1970-01-01T01:34:28Z", "alarm-notif": {"@xmlns": "urn:o-ran:fm:1.0", "fault-id": "18", "fault-source": "Radio Module", "affected-objects": {"name": "Radio Module"}, "fault-severity": "MAJOR", "is-cleared": "true", "fault-text": "Synchronization Error Alarm", "event-time": "1970-01-01T01:34:28Z"}}}}""" % (
      (datetime.now() - timedelta(seconds=25)).strftime("%Y-%m-%d %H:%M:%S,%f")[:-3],
      (datetime.now() - timedelta(seconds=15)).strftime("%Y-%m-%d %H:%M:%S,%f")[:-3],
      ))
    self.writePromise(**{
        'netconf-log': self.netconf_log,
    })
    self.configureLauncher()
    self.launcher.run()

  def test_promise_fail(self):
    with open(self.netconf_log, 'w+') as f:
      f.write("""{"time": "%s", "log_level": "INFO", "message": "", "data": {"notification": {"@xmlns": "urn:ietf:params:xml:ns:netconf:notification:1.0", "eventTime": "1970-01-01T01:34:04Z", "alarm-notif": {"@xmlns": "urn:o-ran:fm:1.0", "fault-id": "18", "fault-source": "Radio Module", "affected-objects": {"name": "Radio Module"}, "fault-severity": "MAJOR", "is-cleared": "false", "fault-text": "Synchronization Error Alarm", "event-time": "1970-01-01T01:34:04Z"}}}}
{"time": "%s", "log_level": "INFO", "message": "", "data": {"notification": {"@xmlns": "urn:ietf:params:xml:ns:netconf:notification:1.0", "eventTime": "1970-01-01T01:34:28Z", "alarm-notif": {"@xmlns": "urn:o-ran:fm:1.0", "fault-id": "18", "fault-source": "Radio Module", "affected-objects": {"name": "Radio Module"}, "fault-severity": "MAJOR", "is-cleared": "false", "fault-text": "Synchronization Error Alarm", "event-time": "1970-01-01T01:34:28Z"}}}}""" % (
      (datetime.now() - timedelta(seconds=25)).strftime("%Y-%m-%d %H:%M:%S,%f")[:-3],
      (datetime.now() - timedelta(seconds=15)).strftime("%Y-%m-%d %H:%M:%S,%f")[:-3],
      ))
    self.writePromise(**{
        'netconf-log': self.netconf_log,
    })
    self.configureLauncher()
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertEqual("Synchronization Error Alarm is on, affected objects are: {'name': 'Radio Module'}", self.getPromiseResult(self.promise_name)['result']['message'])
