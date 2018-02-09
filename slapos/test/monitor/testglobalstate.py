# -*- coding: utf-8 -*-
import os, time
import sys
import shutil
import tempfile
import unittest
import json

from slapos.monitor import globalstate
from slapos.monitor.runpromise import RunPromise, parseArguments
from slapos.monitor.monitor import Monitoring

class MonitorGlobalTest(unittest.TestCase):

  def setUp(self):
    self.base_dir = tempfile.mkdtemp()
    os.mkdir(os.path.join(self.base_dir, 'promise'))
    os.mkdir(os.path.join(self.base_dir, 'monitor-promise'))
    os.mkdir(os.path.join(self.base_dir, 'public'))
    os.mkdir(os.path.join(self.base_dir, 'private'))
    os.mkdir(os.path.join(self.base_dir, 'cron.d'))
    os.mkdir(os.path.join(self.base_dir, 'logrotate.d'))
    os.mkdir(os.path.join(self.base_dir, 'monitor-report'))
    os.mkdir(os.path.join(self.base_dir, 'webdav'))
    os.mkdir(os.path.join(self.base_dir, 'run'))
    self.writeContent(os.path.join(self.base_dir, 'param'), '12345')
    self.writeContent(os.path.join(self.base_dir, '.monitor_pwd'), 'bcuandjy')
    self.writeContent(os.path.join(self.base_dir, 'test-httpd-cors.cfg'), '')
    self.writeContent(os.path.join(self.base_dir, 'monitor-htpasswd'), '12345')
    self.writeContent(os.path.join(self.base_dir, 'instance.cfg'), """[instance]
name = Monitor
root-name = Monitor ROOT
computer = COMP-1234
ipv4 = 10.0.151.118
ipv6 = 2001:34c:1254:df3:89::5df3
software-release = http://some.url.com/software.cfg
software-type = default
partition = slappart10""")

    self.monitor_config_file = os.path.join(self.base_dir, 'monitor.conf')
    self.public_dir = os.path.join(self.base_dir, 'public')
    self.private_dir = os.path.join(self.base_dir, 'private')

    self.monitor_config_dict = dict(
      base_dir=self.base_dir,
      root_title="Monitor ROOT",
      title="Monitor",
      url_list="",
      base_url="https://monitor.test.com",
      monitor_promise_folder=os.path.join(self.base_dir, 'monitor-promise'),
      promise_folder=os.path.join(self.base_dir, 'promise'),
      promise_runner_pid=os.path.join(self.base_dir, 'run', 'monitor-promises.pid'),
      public_folder=os.path.join(self.base_dir, 'public'),
      public_path_list="",
      private_path_list="",
      promise_run_script="/bin/echo",
      collect_run_script="/bin/echo",
      statistic_script="/bin/echo"
    )
    self.monitor_conf = """[monitor]
parameter-file-path = %(base_dir)s/knowledge0.cfg
promise-folder = %(base_dir)s/promise
service-pid-folder = %(base_dir)s/run
monitor-promise-folder = %(base_dir)s/monitor-promise
private-folder = %(base_dir)s/private
public-folder = %(base_dir)s/public
public-path-list = %(public_path_list)s
private-path-list = %(private_path_list)s
crond-folder = %(base_dir)s/cron.d
logrotate-folder = %(base_dir)s/logrotate.d
report-folder = %(base_dir)s/monitor-report
root-title = %(root_title)s
pid-file =  %(base_dir)s/monitor.pid
parameter-list = 
  raw monitor-user admin
  file sample %(base_dir)s/param
  htpasswd monitor-password %(base_dir)s/.monitor_pwd admin %(base_dir)s/monitor-htpasswd
  httpdcors cors-domain %(base_dir)s/test-httpd-cors.cfg /bin/echo

webdav-folder = %(base_dir)s/webdav
collect-script = %(collect_run_script)s
statistic-script = %(statistic_script)s
python = python
monitor-url-list = %(url_list)s
collector-db = 
base-url = %(base_url)s
title = %(title)s
service-pid-folder = %(base_dir)s/run
promise-output-file = %(base_dir)s/monitor-bootstrap-status
promise-runner = %(promise_run_script)s
randomsleep = /bin/echo sleep
"""

  def tearDown(self):
    if os.path.exists(self.base_dir):
      shutil.rmtree(self.base_dir)

  def writeContent(self, file_path, config):
    with open(file_path, 'w') as cfg:
      cfg.write(config)

  def writePromise(self, name, success=True):
    if success:
      result_dict = {'output': 'success', 'code': 0}
    else:
      result_dict = {'output': 'error', 'code': 1}
    content = """#!/bin/sh

echo "%(output)s"
exit %(code)s
""" % result_dict
    promise_path = os.path.join(self.base_dir, 'promise', name)
    self.writeContent(promise_path, content)
    os.chmod(promise_path, 0755)
    return promise_path

  def getPromiseParser(self):
    pid_path = os.path.join(self.base_dir, 'run', 'monitor-promise.pid')

    promise_cmd = [
      '--pid_path',
      '%s' % pid_path, '--output', os.path.join(self.base_dir, 'public'),
      '--promise_folder', os.path.join(self.base_dir, 'promise'),
      '--monitor_promise_folder', os.path.join(self.base_dir, 'monitor-promise'),
      '--promise_type', 'status',
      '--monitor_url', 'https://monitor.test.com/share/private/',
      '--history_folder', os.path.join(self.base_dir, 'public'),
      '--instance_name', 'Monitor', '--hosting_name', 'Monitor ROOT']
    arg_parser = parseArguments()
    return arg_parser.parse_args(promise_cmd)

  def test_monitor_instance_state(self):
    config_content = self.monitor_conf % self.monitor_config_dict
    self.writeContent(self.monitor_config_file, config_content)

    instance = Monitoring(self.monitor_config_file)
    instance.bootstrapMonitor()

    self.writePromise('promise_1')
    self.writePromise('promise_2', success=False)
    self.writePromise('promise_3', success=False)
    self.writePromise('promise_4')
    parser = self.getPromiseParser()
    promise_runner = RunPromise(parser)
    promise_runner.runPromise()

    self.assertTrue(os.path.exists(os.path.join(self.public_dir, 'promise_1.status.json')))
    self.assertTrue(os.path.exists(os.path.join(self.public_dir, 'promise_2.status.json')))
    self.assertTrue(os.path.exists(os.path.join(self.public_dir, 'promise_3.status.json')))
    self.assertTrue(os.path.exists(os.path.join(self.public_dir, 'promise_4.status.json')))

    # generate instance state files
    globalstate.run([self.monitor_config_file, os.path.join(self.base_dir, 'instance.cfg')])
    self.assertTrue(os.path.exists(os.path.join(self.public_dir, 'feed')))
    self.assertTrue(os.path.exists(os.path.join(self.public_dir, 'monitor.global.json')))
    self.assertTrue(os.path.exists(os.path.join(self.private_dir, 'monitor.global.json')))
    expected_result = """{
	"status": "ERROR",
	"_embedded": {
		"instance": {
			"partition": "slappart10",
			"ipv6": "2001:34c:1254:df3:89::5df3",
			"computer": "COMP-1234",
			"ipv4": "10.0.151.118",
			"software-release": "http://some.url.com/software.cfg",
			"software-type": "default"
		}
	},
	"parameters": [{
		"key": "",
		"value": "admin",
		"title": "monitor-user"
	}, {
		"key": "sample",
		"value": "12345",
		"title": "sample"
	}, {
		"key": "monitor-password",
		"value": "bcuandjy",
		"title": "monitor-password"
	}, {
		"key": "cors-domain",
		"value": "",
		"title": "cors-domain"
	}],
	"title": "Monitor",
	"data": {
		"process_state": "monitor_process_resource.status",
		"io_resource": "monitor_resource_io.data",
		"state": "monitor_state.data",
		"memory_resource": "monitor_resource_memory.data",
		"process_resource": "monitor_resource_process.data",
		"monitor_process_state": "monitor_resource.status"
	},
	"portal_type": "Software Instance",
	"state": {
		"success": 2,
		"error": 2
	},
	"_links": {
		"rss_url": {
			"href": "https://monitor.test.com/public/feed"
		},
		"public_url": {
			"href": "https://monitor.test.com/share/public/"
		},
		"private_url": {
			"href": "https://monitor.test.com/share/private/"
		}
	},
	"aggregate_reference": "COMP-1234",
	"type": "global",
	"specialise_title": "Monitor ROOT"
}"""

    with open(os.path.join(self.private_dir, 'monitor.global.json')) as r:
      result = json.loads(r.read().decode("utf-8"))
      result.pop("date")
      self.assertEquals(result,
        json.loads(expected_result))

    # all promises are OK now
    self.writePromise('promise_2', success=True)
    self.writePromise('promise_3', success=True)
    promise_runner.runPromise()
    globalstate.run([self.monitor_config_file, os.path.join(self.base_dir, 'instance.cfg')])

    expected_result_dict = json.loads(expected_result)
    expected_result_dict["status"] = "OK"
    expected_result_dict["state"] = {'error': 0, 'success': 4}
    with open(os.path.join(self.private_dir, 'monitor.global.json')) as r:
      result = json.loads(r.read().decode("utf-8"))
      result.pop("date")
      self.assertEquals(result,
        expected_result_dict)

