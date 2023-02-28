from slapos.grid.promise import PromiseError
from slapos.test.promise.plugin import TestPromisePluginMixin

import email
import json
import os
import shutil
import tempfile
import time


class CheckSurykatkaJSONMixin(TestPromisePluginMixin):
  maxDiff = None  # show full diffs for test readability
  promise_name = 'check-surykatka-json.py'

  def setUp(self):
    self.working_directory = tempfile.mkdtemp()
    self.json_file = os.path.join(self.working_directory, 'surykatka.json')
    self.addCleanup(shutil.rmtree, self.working_directory)
    TestPromisePluginMixin.setUp(self)

    now = time.time()
    minute = 60
    day = 24 * 3600
    create_date = email.utils.formatdate
    self.time_past14d = create_date(now - 14 * day)
    self.time_past20m = create_date(now - 20 * minute)
    self.time_past2m = create_date(now - 2 * minute)
    self.time_now = create_date(now)
    self.time_future20m = create_date(now + 20 * minute)
    self.time_future1d = create_date(now + 1 * day)
    self.time_future3d = create_date(now + 3 * day)
    self.time_future14d = create_date(now + 14 * day)
    self.time_future60d = create_date(now + 60 * day)

  def writeSurykatkaPromise(self, d=None):
    if d is None:
      d = {}
    content_list = [
      "from slapos.promise.plugin.check_surykatka_json import RunPromise"]
    content_list.append('extra_config_dict = {')
    for k, v in d.items():
      content_list.append("  '%s': '%s'," % (k, v))
    content_list.append('}')
    self.writePromise(self.promise_name, '\n'.join(content_list))

  def writeSurykatkaJsonDirect(self, content):
    with open(self.json_file, 'w') as fh:
      fh.write(content)

  def writeSurykatkaJson(self, content):
    with open(self.json_file, 'w') as fh:
      json.dump(content, fh, indent=2)

  def assertFailedMessage(self, result, message):
    self.assertEqual(result['result']['failed'], True)
    self.assertEqual(
      result['result']['message'],
      message)

  def assertPassedMessage(self, result, message):
    self.assertEqual(result['result']['failed'], False)
    self.assertEqual(
      result['result']['message'],
      message)


class TestCheckSurykatkaJSONBase(CheckSurykatkaJSONMixin):
  def test_no_config(self):
    self.writeSurykatkaPromise()
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "ERROR File '' does not exists")

  def test_not_existing_file(self):
    self.writeSurykatkaPromise({'json-file': self.json_file})
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "ERROR File '%s' does not exists" % (self.json_file,))

  def test_empty_file(self):
    self.writeSurykatkaPromise({'json-file': self.json_file})
    self.writeSurykatkaJsonDirect('')
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "ERROR loading JSON from '%s'" % (self.json_file,))

  def test(self):
    self.writeSurykatkaPromise(
      {
        'report': 'NOT_EXISTING_ENTRY',
        'json-file': self.json_file,
      }
    )
    self.writeSurykatkaJson({})
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "ERROR Report 'NOT_EXISTING_ENTRY' is not supported")


class TestCheckSurykatkaJSONBotStatus(CheckSurykatkaJSONMixin):
  def test(self):
    self.writeSurykatkaPromise(
      {
        'report': 'bot_status',
        'json-file': self.json_file,
      }
    )
    self.writeSurykatkaJson({
      "bot_status": [
        {
          "date": self.time_past2m,
          "text": "loop"}]})
    self.configureLauncher(enable_anomaly=True)
    self.launcher.run()
    self.assertPassedMessage(
      self.getPromiseResult(self.promise_name),
      "bot_status: OK Last bot status"
    )

  def test_no_loop(self):
    self.writeSurykatkaPromise(
      {
        'report': 'bot_status',
        'json-file': self.json_file,
      }
    )
    self.writeSurykatkaJson({
      "bot_status": [
        {
          "date": "Wed, 13 Dec 2222 09:10:11 -0000",
          "text": "error"}]})
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "bot_status: ERROR bot_status is 'error' instead of 'loop' in '%s'" % (
        self.json_file,)
    )

  def test_bot_status_future(self):
    self.writeSurykatkaPromise(
      {
        'report': 'bot_status',
        'json-file': self.json_file,
      }
    )
    self.writeSurykatkaJson({
      "bot_status": [
        {
          "date": self.time_future20m,
          "text": "loop"}]})
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "bot_status: ERROR Last bot datetime is in future"
    )

  def test_bot_status_old(self):
    self.writeSurykatkaPromise(
      {
        'report': 'bot_status',
        'json-file': self.json_file,
      }
    )
    self.writeSurykatkaJson({
      "bot_status": [
        {
          "date": self.time_past20m,
          "text": "loop"}]})
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "bot_status: ERROR Last bot datetime is more than 15 minutes old"
    )

  def test_not_bot_status(self):
    self.writeSurykatkaPromise(
      {
        'report': 'bot_status',
        'json-file': self.json_file,
      }
    )
    self.writeSurykatkaJson({})
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "bot_status: ERROR 'bot_status' not in '%s'" % (self.json_file,))

  def test_empty_bot_status(self):
    self.writeSurykatkaPromise(
      {
        'report': 'bot_status',
        'json-file': self.json_file,
      }
    )
    self.writeSurykatkaJson({"bot_status": []})
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "bot_status: ERROR 'bot_status' empty in '%s'" % (self.json_file,))


class TestCheckSurykatkaJSONHttpQuery(CheckSurykatkaJSONMixin):
  def test(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.erp5.com/',
        'status-code': '302',
        'ip-list': '127.0.0.1 127.0.0.2',
      }
    )
    self.writeSurykatkaJson({
      "http_query": [
        {
          "date": "Wed, 11 Dec 2019 09:35:28 -0000",
          "ip": "127.0.0.1",
          "status_code": 302,
          "url": "https://www.erp5.com/"
        },
        {
          "date": "Wed, 11 Dec 2019 09:35:28 -0000",
          "ip": "127.0.0.2",
          "status_code": 302,
          "url": "https://www.erp5.com/"
        },
        {
          "date": "Wed, 11 Dec 2019 09:35:28 -0000",
          "ip": "176.31.129.213",
          "status_code": 200,
          "url": "https://www.erp5.org/"
        }
      ],
      "ssl_certificate": [
        {
          "date": "Fri, 27 Dec 2019 14:43:26 -0000",
          "hostname": "www.erp5.com",
          "ip": "127.0.0.1",
          "not_after": self.time_future60d
        },
        {
          "date": "Fri, 27 Dec 2019 14:43:26 -0000",
          "hostname": "www.erp5.com",
          "ip": "127.0.0.2",
          "not_after": self.time_future60d
        }
      ],
      "dns_query": [
        {
            "domain": "www.erp5.com",
            "rdtype": "A",
            "resolver_ip": "1.2.3.4",
            "date": "Tue, 28 Feb 2023 12:40:29 -0000",
            "response": "127.0.0.1, 127.0.0.2"
        },
        {
            "domain": "www.erp5.org",
            "rdtype": "A",
            "resolver_ip": "1.2.3.4",
            "date": "Tue, 28 Feb 2023 12:40:29 -0000",
            "response": "127.0.0.1, 127.0.0.2"
        },
      ],
      "tcp_server": [
        {
            "ip": "127.0.0.1",
            "state": "open",
            "port": 443,
            "date": "Tue, 28 Feb 2023 09:27:26 -0000",
            "domain": "www.erp5.com"
        },
        {
            "ip": "127.0.0.2",
            "state": "open",
            "port": 443,
            "date": "Tue, 28 Feb 2023 09:27:26 -0000",
            "domain": "www.erp5.com"
        },
      ]
    })
    self.configureLauncher(enable_anomaly=True)
    self.launcher.run()
    self.assertPassedMessage(
      self.getPromiseResult(self.promise_name),
      "https://www.erp5.com/ : "
      "dns_query: OK resolver 1.2.3.4 returned expected set of IPs 127.0.0.1 "
      "127.0.0.2 "
      "tcp_server: OK IP 127.0.0.1:443 OK IP 127.0.0.2:443 "
      "http_query: OK IP 127.0.0.1 status_code 302 OK IP 127.0.0.2 "
      "status_code 302 "
      "ssl_certificate: OK IP 127.0.0.1 will expire in > 15 days OK IP "
      "127.0.0.2 will expire in > 15 days"
    )

  def test_maximum_elapsed_time(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.erp5.com/',
        'status-code': '302',
        'ip-list': '127.0.0.1 127.0.0.2',
        'maximum-elapsed-time': '5',
      }
    )
    self.writeSurykatkaJson({
      "http_query": [
        {
          "date": "Wed, 11 Dec 2019 09:35:28 -0000",
          "ip": "127.0.0.1",
          "status_code": 302,
          "url": "https://www.erp5.com/",
          "total_seconds": 4
        },
        {
          "date": "Wed, 11 Dec 2019 09:35:28 -0000",
          "ip": "127.0.0.2",
          "status_code": 302,
          "url": "https://www.erp5.com/",
          "total_seconds": 4
        },
        {
          "date": "Wed, 11 Dec 2019 09:35:28 -0000",
          "ip": "176.31.129.213",
          "status_code": 200,
          "url": "https://www.erp5.org/",
          "total_seconds": 4
        }
      ],
      "ssl_certificate": [
        {
          "date": "Fri, 27 Dec 2019 14:43:26 -0000",
          "hostname": "www.erp5.com",
          "ip": "127.0.0.1",
          "not_after": self.time_future60d
        },
        {
          "date": "Fri, 27 Dec 2019 14:43:26 -0000",
          "hostname": "www.erp5.com",
          "ip": "127.0.0.2",
          "not_after": self.time_future60d
        }
      ],
      "dns_query": [
        {
            "domain": "www.erp5.com",
            "rdtype": "A",
            "resolver_ip": "1.2.3.4",
            "date": "Tue, 28 Feb 2023 12:40:29 -0000",
            "response": "127.0.0.1, 127.0.0.2"
        },
        {
            "domain": "www.erp5.org",
            "rdtype": "A",
            "resolver_ip": "1.2.3.4",
            "date": "Tue, 28 Feb 2023 12:40:29 -0000",
            "response": "127.0.0.1, 127.0.0.2"
        },
      ],
      "tcp_server": [
        {
            "ip": "127.0.0.1",
            "state": "open",
            "port": 443,
            "date": "Tue, 28 Feb 2023 09:27:26 -0000",
            "domain": "www.erp5.com"
        },
        {
            "ip": "127.0.0.2",
            "state": "open",
            "port": 443,
            "date": "Tue, 28 Feb 2023 09:27:26 -0000",
            "domain": "www.erp5.com"
        },
      ]
    })
    self.configureLauncher(enable_anomaly=True)
    self.launcher.run()
    self.assertPassedMessage(
      self.getPromiseResult(self.promise_name),
      "https://www.erp5.com/ : "
      "dns_query: OK resolver 1.2.3.4 returned expected set of IPs 127.0.0.1 "
      "127.0.0.2 "
      "tcp_server: OK IP 127.0.0.1:443 OK IP 127.0.0.2:443 "
      "http_query: OK IP 127.0.0.1 status_code 302 OK IP 127.0.0.2 "
      "status_code 302 "
      "ssl_certificate: OK IP 127.0.0.1 will expire in > 15 days OK IP "
      "127.0.0.2 will expire in > 15 days "
      "elapsed_time: OK IP 127.0.0.1 replied < 5.00s OK IP 127.0.0.2 replied "
      "< 5.00s"
    )

  def test_maximum_elapsed_time_too_long(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.erp5.com/',
        'status-code': '302',
        'ip-list': '127.0.0.1 127.0.0.2',
        'maximum-elapsed-time': '5',
      }
    )
    self.writeSurykatkaJson({
      "http_query": [
        {
          "date": "Wed, 11 Dec 2019 09:35:28 -0000",
          "ip": "127.0.0.1",
          "status_code": 302,
          "url": "https://www.erp5.com/",
          "total_seconds": 6
        },
        {
          "date": "Wed, 11 Dec 2019 09:35:28 -0000",
          "ip": "127.0.0.2",
          "status_code": 302,
          "url": "https://www.erp5.com/",
          "total_seconds": 0
        },
        {
          "date": "Wed, 11 Dec 2019 09:35:28 -0000",
          "ip": "176.31.129.213",
          "status_code": 200,
          "url": "https://www.erp5.org/",
          "total_seconds": 4
        }
      ],
      "ssl_certificate": [
        {
          "date": "Fri, 27 Dec 2019 14:43:26 -0000",
          "hostname": "www.erp5.com",
          "ip": "127.0.0.1",
          "not_after": self.time_future60d
        },
        {
          "date": "Fri, 27 Dec 2019 14:43:26 -0000",
          "hostname": "www.erp5.com",
          "ip": "127.0.0.2",
          "not_after": self.time_future60d
        }
      ],
      "dns_query": [],
      "tcp_server": [],
    })
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "https://www.erp5.com/ : "
      "dns_query: ERROR No data "
      "tcp_server: ERROR No data "
      "http_query: OK IP 127.0.0.1 status_code 302 OK IP 127.0.0.2 "
      "status_code 302 "
      "ssl_certificate: OK IP 127.0.0.1 will expire in > 15 days OK IP "
      "127.0.0.2 will expire in > 15 days "
      "elapsed_time: ERROR IP 127.0.0.1 replied > 5.00s ERROR IP "
      "127.0.0.2 failed to reply"
    )

  def test_maximum_elapsed_time_no_total_seconds(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.erp5.com/',
        'status-code': '302',
        'ip-list': '127.0.0.1 127.0.0.2',
        'maximum-elapsed-time': '5',
      }
    )
    self.writeSurykatkaJson({
      "http_query": [
        {
          "date": "Wed, 11 Dec 2019 09:35:28 -0000",
          "ip": "127.0.0.1",
          "status_code": 302,
          "url": "https://www.erp5.com/"
        },
        {
          "date": "Wed, 11 Dec 2019 09:35:28 -0000",
          "ip": "127.0.0.2",
          "status_code": 302,
          "url": "https://www.erp5.com/"
        },
        {
          "date": "Wed, 11 Dec 2019 09:35:28 -0000",
          "ip": "176.31.129.213",
          "status_code": 200,
          "url": "https://www.erp5.org/"
        }
      ],
      "ssl_certificate": [
        {
          "date": "Fri, 27 Dec 2019 14:43:26 -0000",
          "hostname": "www.erp5.com",
          "ip": "127.0.0.1",
          "not_after": self.time_future60d
        },
        {
          "date": "Fri, 27 Dec 2019 14:43:26 -0000",
          "hostname": "www.erp5.com",
          "ip": "127.0.0.2",
          "not_after": self.time_future60d
        }
      ],
      "dns_query": [
        {
            "domain": "www.erp5.com",
            "rdtype": "A",
            "resolver_ip": "1.2.3.4",
            "date": "Tue, 28 Feb 2023 12:40:29 -0000",
            "response": "127.0.0.1, 127.0.0.2"
        },
        {
            "domain": "www.erp5.org",
            "rdtype": "A",
            "resolver_ip": "1.2.3.4",
            "date": "Tue, 28 Feb 2023 12:40:29 -0000",
            "response": "127.0.0.1, 127.0.0.2"
        },
      ],
      "tcp_server": [
        {
            "ip": "127.0.0.1",
            "state": "open",
            "port": 443,
            "date": "Tue, 28 Feb 2023 09:27:26 -0000",
            "domain": "www.erp5.com"
        },
        {
            "ip": "127.0.0.2",
            "state": "open",
            "port": 443,
            "date": "Tue, 28 Feb 2023 09:27:26 -0000",
            "domain": "www.erp5.com"
        },
      ]
    })
    self.configureLauncher(enable_anomaly=True)
    self.launcher.run()
    self.assertPassedMessage(
      self.getPromiseResult(self.promise_name),
      "https://www.erp5.com/ : "
      "dns_query: OK resolver 1.2.3.4 returned expected set of IPs 127.0.0.1 "
      "127.0.0.2 "
      "tcp_server: OK IP 127.0.0.1:443 OK IP 127.0.0.2:443 "
      "http_query: OK IP 127.0.0.1 status_code 302 OK IP 127.0.0.2 "
      "status_code 302 "
      "ssl_certificate: OK IP 127.0.0.1 will expire in > 15 days OK IP "
      "127.0.0.2 will expire in > 15 days"
    )

  def test_http(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'http://www.erp5.com/',
        'status-code': '302',
        'ip-list': '127.0.0.1 127.0.0.2',
      }
    )
    self.writeSurykatkaJson({
      "http_query": [
        {
          "date": "Wed, 11 Dec 2019 09:35:28 -0000",
          "ip": "127.0.0.1",
          "status_code": 302,
          "url": "http://www.erp5.com/"
        },
        {
          "date": "Wed, 11 Dec 2019 09:35:28 -0000",
          "ip": "127.0.0.2",
          "status_code": 302,
          "url": "http://www.erp5.com/"
        },
        {
          "date": "Wed, 11 Dec 2019 09:35:28 -0000",
          "ip": "176.31.129.213",
          "status_code": 200,
          "url": "http://www.erp5.org/"
        }
      ],
      "ssl_certificate": [
      ],
      "dns_query": [
        {
            "domain": "www.erp5.com",
            "rdtype": "A",
            "resolver_ip": "1.2.3.4",
            "date": "Tue, 28 Feb 2023 12:40:29 -0000",
            "response": "127.0.0.1, 127.0.0.2"
        },
        {
            "domain": "www.erp5.org",
            "rdtype": "A",
            "resolver_ip": "1.2.3.4",
            "date": "Tue, 28 Feb 2023 12:40:29 -0000",
            "response": "127.0.0.1, 127.0.0.2"
        },
      ],
      "tcp_server": [
        {
            "ip": "127.0.0.1",
            "state": "open",
            "port": 80,
            "date": "Tue, 28 Feb 2023 09:27:26 -0000",
            "domain": "www.erp5.com"
        },
        {
            "ip": "127.0.0.2",
            "state": "open",
            "port": 80,
            "date": "Tue, 28 Feb 2023 09:27:26 -0000",
            "domain": "www.erp5.com"
        },
      ]
    })
    self.configureLauncher(enable_anomaly=True)
    self.launcher.run()
    self.assertPassedMessage(
      self.getPromiseResult(self.promise_name),
      "http://www.erp5.com/ : "
      "dns_query: OK resolver 1.2.3.4 returned expected set of IPs "
      "127.0.0.1 127.0.0.2 "
      "tcp_server: OK IP 127.0.0.1:80 OK IP 127.0.0.2:80 "
      "http_query: OK IP 127.0.0.1 status_code 302 OK IP 127.0.0.2 "
      "status_code 302"
    )

  def test_http_with_header_dict(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'http://www.erp5.com/',
        'status-code': '200',
        'http-header-dict': '{"Vary": "Accept-Encoding", "Cache-Control": '
        '"max-age=300, public"}',
      }
    )
    self.writeSurykatkaJson({
      "http_query": [
        {
          "date": "Wed, 11 Dec 2019 09:35:28 -0000",
          "ip": "176.31.129.213",
          "http_header_dict": {
            "Vary": "Accept-Encoding", "Cache-Control": "max-age=300, public"},
          "status_code": 200,
          "url": "http://www.erp5.com/"
        }
      ],
      "ssl_certificate": [
      ],
      "dns_query": [
        {
            "domain": "www.erp5.com",
            "rdtype": "A",
            "resolver_ip": "1.2.3.4",
            "date": "Tue, 28 Feb 2023 12:40:29 -0000",
            "response": "127.0.0.1, 127.0.0.2"
        },
        {
            "domain": "www.erp5.org",
            "rdtype": "A",
            "resolver_ip": "1.2.3.4",
            "date": "Tue, 28 Feb 2023 12:40:29 -0000",
            "response": "127.0.0.1, 127.0.0.2"
        },
      ],
      "tcp_server": [
        {
            "ip": "127.0.0.1",
            "state": "open",
            "port": 80,
            "date": "Tue, 28 Feb 2023 09:27:26 -0000",
            "domain": "www.erp5.com"
        },
        {
            "ip": "127.0.0.2",
            "state": "open",
            "port": 80,
            "date": "Tue, 28 Feb 2023 09:27:26 -0000",
            "domain": "www.erp5.com"
        },
      ]
    })
    self.configureLauncher(enable_anomaly=True)
    self.launcher.run()
    self.assertPassedMessage(
      self.getPromiseResult(self.promise_name),
      'http://www.erp5.com/ : '
      'http_query: OK IP 176.31.129.213 status_code 200 OK IP '
      '176.31.129.213 HTTP Header {"Cache-Control": "max-age=300, public", '
      '"Vary": "Accept-Encoding"}'
    )

  def test_http_with_bad_header_dict(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'http://www.erp5.com/',
        'status-code': '200',
        'http-header-dict': '{"Vary": "Accept-Encoding", "Cache-Control": '
                            '"max-age=300, public"}',
      }
    )
    self.writeSurykatkaJson({
      "http_query": [
        {
          "date": "Wed, 11 Dec 2019 09:35:28 -0000",
          "ip": "176.31.129.213",
          "http_header_dict": {
            "Vary": "Accept-Encoding,Cookie",
            "Cache-Control": "max-age=300, public"},
          "status_code": 200,
          "url": "http://www.erp5.com/"
        }
      ],
      "ssl_certificate": [
      ],
      "dns_query": [
        {
            "domain": "www.erp5.com",
            "rdtype": "A",
            "resolver_ip": "1.2.3.4",
            "date": "Tue, 28 Feb 2023 12:40:29 -0000",
            "response": "127.0.0.1, 127.0.0.2"
        },
        {
            "domain": "www.erp5.org",
            "rdtype": "A",
            "resolver_ip": "1.2.3.4",
            "date": "Tue, 28 Feb 2023 12:40:29 -0000",
            "response": "127.0.0.1, 127.0.0.2"
        },
      ],
      "tcp_server": [
        {
            "ip": "127.0.0.1",
            "state": "open",
            "port": 80,
            "date": "Tue, 28 Feb 2023 09:27:26 -0000",
            "domain": "www.erp5.com"
        },
        {
            "ip": "127.0.0.2",
            "state": "open",
            "port": 80,
            "date": "Tue, 28 Feb 2023 09:27:26 -0000",
            "domain": "www.erp5.com"
        },
      ]
    })
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      'http://www.erp5.com/ : '
      'http_query: OK IP 176.31.129.213 status_code 200 ERROR IP '
      '176.31.129.213 expected HTTP Header {"Cache-Control": "max-age=300, '
      'public", "Vary": "Accept-Encoding"} != of {"Cache-Control": '
      '"max-age=300, public", "Vary": "Accept-Encoding,Cookie"}'
    )

  def test_no_ip_list(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.erp5.com/',
        'status-code': '302',
      }
    )
    self.writeSurykatkaJson({
      "http_query": [
        {
          "date": "Wed, 11 Dec 2019 09:35:28 -0000",
          "ip": "127.0.0.1",
          "status_code": 302,
          "url": "https://www.erp5.com/"
        },
        {
          "date": "Wed, 11 Dec 2019 09:35:28 -0000",
          "ip": "127.0.0.2",
          "status_code": 302,
          "url": "https://www.erp5.com/"
        },
        {
          "date": "Wed, 11 Dec 2019 09:35:28 -0000",
          "ip": "176.31.129.213",
          "status_code": 200,
          "url": "https://www.erp5.org/"
        }
      ],
      "ssl_certificate": [
        {
          "date": "Fri, 27 Dec 2019 14:43:26 -0000",
          "hostname": "www.erp5.com",
          "ip": "127.0.0.1",
          "not_after": self.time_future60d
        },
        {
          "date": "Fri, 27 Dec 2019 14:43:26 -0000",
          "hostname": "www.erp5.com",
          "ip": "127.0.0.2",
          "not_after": self.time_future60d
        }
      ],
      "dns_query": [
        {
            "domain": "www.erp5.com",
            "rdtype": "A",
            "resolver_ip": "1.2.3.4",
            "date": "Tue, 28 Feb 2023 12:40:29 -0000",
            "response": "127.0.0.1, 127.0.0.2"
        },
        {
            "domain": "www.erp5.org",
            "rdtype": "A",
            "resolver_ip": "1.2.3.4",
            "date": "Tue, 28 Feb 2023 12:40:29 -0000",
            "response": "176.31.129.213"
        },
      ],
      "tcp_server": [
        {
            "ip": "127.0.0.1",
            "state": "open",
            "port": 443,
            "date": "Tue, 28 Feb 2023 09:27:26 -0000",
            "domain": "www.erp5.com"
        },
        {
            "ip": "127.0.0.2",
            "state": "open",
            "port": 443,
            "date": "Tue, 28 Feb 2023 09:27:26 -0000",
            "domain": "www.erp5.com"
        },
      ]
    })
    self.configureLauncher(enable_anomaly=True)
    self.launcher.run()
    self.assertPassedMessage(
      self.getPromiseResult(self.promise_name),
      "https://www.erp5.com/ : "
      "http_query: OK IP 127.0.0.1 status_code 302 OK IP 127.0.0.2 "
      "status_code 302 "
      "ssl_certificate: OK IP 127.0.0.1 will expire in > 15 days OK IP "
      "127.0.0.2 will expire in > 15 days"
    )

  def test_good_certificate_2_day(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.erp5.com/',
        'status-code': '302',
        'certificate-expiration-days': '2'
      }
    )
    self.writeSurykatkaJson({
      "http_query": [
        {
          "date": "Wed, 11 Dec 2019 09:35:28 -0000",
          "ip": "127.0.0.1",
          "status_code": 302,
          "url": "https://www.erp5.com/"
        }
      ],
      "ssl_certificate": [
        {
          "date": "Fri, 27 Dec 2019 14:43:26 -0000",
          "hostname": "www.erp5.com",
          "ip": "127.0.0.1",
          "not_after": self.time_future3d
        }
      ],
      "dns_query": [
        {
            "domain": "www.erp5.com",
            "rdtype": "A",
            "resolver_ip": "1.2.3.4",
            "date": "Tue, 28 Feb 2023 12:40:29 -0000",
            "response": "127.0.0.1, 127.0.0.2"
        },
        {
            "domain": "www.erp5.org",
            "rdtype": "A",
            "resolver_ip": "1.2.3.4",
            "date": "Tue, 28 Feb 2023 12:40:29 -0000",
            "response": "127.0.0.1, 127.0.0.2"
        },
      ],
      "tcp_server": [
        {
            "ip": "127.0.0.1",
            "state": "open",
            "port": 443,
            "date": "Tue, 28 Feb 2023 09:27:26 -0000",
            "domain": "www.erp5.com"
        },
        {
            "ip": "127.0.0.2",
            "state": "open",
            "port": 443,
            "date": "Tue, 28 Feb 2023 09:27:26 -0000",
            "domain": "www.erp5.com"
        },
      ]
    })
    self.configureLauncher(enable_anomaly=True)
    self.launcher.run()
    self.assertPassedMessage(
      self.getPromiseResult(self.promise_name),
      "https://www.erp5.com/ : "
      "http_query: OK IP 127.0.0.1 status_code 302 "
      "ssl_certificate: OK IP 127.0.0.1 will expire in > 2 days"
    )

  def test_expired_certificate_2_day(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.erp5.com/',
        'status-code': '302',
        'certificate-expiration-days': '2'
      }
    )
    self.writeSurykatkaJson({
      "http_query": [
        {
          "date": "Wed, 11 Dec 2019 09:35:28 -0000",
          "ip": "127.0.0.1",
          "status_code": 302,
          "url": "https://www.erp5.com/"
        }
      ],
      "ssl_certificate": [
        {
          "date": "Fri, 27 Dec 2019 14:43:26 -0000",
          "hostname": "www.erp5.com",
          "ip": "127.0.0.1",
          "not_after": self.time_future1d
        }
      ],
      "dns_query": [],
      "tcp_server": [],
    })
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "https://www.erp5.com/ : "
      "dns_query: ERROR No data "
      "tcp_server: ERROR No data "
      "http_query: OK IP 127.0.0.1 status_code 302 "
      "ssl_certificate: ERROR IP 127.0.0.1 will expire in < 2 days"
    )

  def test_expired_certificate(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.erp5.com/',
        'status-code': '302',
      }
    )
    self.writeSurykatkaJson({
      "http_query": [
        {
          "date": "Wed, 11 Dec 2019 09:35:28 -0000",
          "ip": "127.0.0.1",
          "status_code": 302,
          "url": "https://www.erp5.com/"
        }
      ],
      "ssl_certificate": [
        {
          "date": "Fri, 27 Dec 2019 14:43:26 -0000",
          "hostname": "www.erp5.com",
          "ip": "127.0.0.1",
          "not_after": self.time_future14d
        }
      ],
      "dns_query": [],
      "tcp_server": [],
    })
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "https://www.erp5.com/ : "
      "dns_query: ERROR No data "
      "tcp_server: ERROR No data "
      "http_query: OK IP 127.0.0.1 status_code 302 "
      "ssl_certificate: ERROR IP 127.0.0.1 will expire in < 15 days"
    )

  def test_expired_certificate_before_today(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.erp5.com/',
        'status-code': '302',
      }
    )
    self.writeSurykatkaJson({
      "http_query": [
        {
          "date": "Wed, 11 Dec 2019 09:35:28 -0000",
          "ip": "127.0.0.1",
          "status_code": 302,
          "url": "https://www.erp5.com/"
        }
      ],
      "ssl_certificate": [
        {
          "date": "Fri, 27 Dec 2019 14:43:26 -0000",
          "hostname": "www.erp5.com",
          "ip": "127.0.0.1",
          "not_after": self.time_past14d
        }
      ],
      "dns_query": [],
      "tcp_server": []
    })
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "https://www.erp5.com/ : "
      "dns_query: ERROR No data "
      "tcp_server: ERROR No data "
      "http_query: OK IP 127.0.0.1 status_code 302 "
      "ssl_certificate: ERROR IP 127.0.0.1 will expire in < 15 days")

  def test_no_http_query_data(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.erp5.com/',
        'status-code': '302',
        'ip-list': '127.0.0.1 127.0.0.2',
      }
    )
    self.writeSurykatkaJson({
      "http_query": [
      ],
      "ssl_certificate": [
        {
          "date": "Fri, 27 Dec 2019 14:43:26 -0000",
          "hostname": "www.erp5.com",
          "ip": "127.0.0.1",
          "not_after": self.time_future60d
        },
        {
          "date": "Fri, 27 Dec 2019 14:43:26 -0000",
          "hostname": "www.erp5.com",
          "ip": "127.0.0.2",
          "not_after": self.time_future60d
        }
      ],
      "dns_query": [],
      "tcp_server": [],
    })
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "https://www.erp5.com/ : "
      "dns_query: ERROR No data "
      "tcp_server: ERROR No data "
      "http_query: ERROR No data "
      "ssl_certificate: OK IP 127.0.0.1 will expire in > 15 days OK IP "
      "127.0.0.2 will expire in > 15 days "
      "elapsed_time: ERROR No data"
    )

  def test_no_http_query_present(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.erp5.com/',
        'status-code': '302',
        'ip-list': '127.0.0.1 127.0.0.2',
      }
    )
    self.writeSurykatkaJson({
      "ssl_certificate": [
        {
          "date": "Fri, 27 Dec 2019 14:43:26 -0000",
          "hostname": "www.erp5.com",
          "ip": "127.0.0.1",
          "not_after": self.time_future60d
        },
        {
          "date": "Fri, 27 Dec 2019 14:43:26 -0000",
          "hostname": "www.erp5.com",
          "ip": "127.0.0.2",
          "not_after": self.time_future60d
        }
      ],
      "dns_query": [],
      "tcp_server": [],
    })
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "https://www.erp5.com/ : "
      "dns_query: ERROR No data "
      "tcp_server: ERROR No data "
      "http_query: ERROR 'http_query' not in %(json_file)r "
      "ssl_certificate: OK IP 127.0.0.1 will expire in > 15 days OK IP "
      "127.0.0.2 will expire in > 15 days "
      "elapsed_time: ERROR No key 'http_query'. If the error persist, please "
      "update surykatka." % {'json_file': self.json_file}
    )

  def test_no_ssl_certificate_data(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.erp5.com/',
        'status-code': '302',
        'ip-list': '127.0.0.1 127.0.0.2',
      }
    )
    self.writeSurykatkaJson({
      "http_query": [
        {
          "date": "Wed, 11 Dec 2019 09:35:28 -0000",
          "ip": "127.0.0.1",
          "status_code": 302,
          "url": "https://www.erp5.com/"
        },
        {
          "date": "Wed, 11 Dec 2019 09:35:28 -0000",
          "ip": "127.0.0.2",
          "status_code": 302,
          "url": "https://www.erp5.com/"
        },
        {
          "date": "Wed, 11 Dec 2019 09:35:28 -0000",
          "ip": "176.31.129.213",
          "status_code": 200,
          "url": "https://www.erp5.org/"
        }
      ],
      "ssl_certificate": [
      ],
      "dns_query": [
      ],
      "tcp_server": []
    })
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "https://www.erp5.com/ : "
      "dns_query: ERROR No data "
      "tcp_server: ERROR No data "
      "http_query: OK IP 127.0.0.1 status_code 302 OK IP 127.0.0.2 "
      "status_code 302 "
      "ssl_certificate: ERROR No data"
    )

  def test_no_ssl_certificate(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.erp5.com/',
        'status-code': '302',
        'ip-list': '127.0.0.1 127.0.0.2',
      }
    )
    self.writeSurykatkaJson({
      "http_query": [
        {
          "date": "Wed, 11 Dec 2019 09:35:28 -0000",
          "ip": "127.0.0.1",
          "status_code": 302,
          "url": "https://www.erp5.com/"
        },
        {
          "date": "Wed, 11 Dec 2019 09:35:28 -0000",
          "ip": "127.0.0.2",
          "status_code": 302,
          "url": "https://www.erp5.com/"
        },
        {
          "date": "Wed, 11 Dec 2019 09:35:28 -0000",
          "ip": "176.31.129.213",
          "status_code": 200,
          "url": "https://www.erp5.org/"
        }
      ],
      "dns_query": [],
      "tcp_server": []
    })
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "https://www.erp5.com/ : "
      "dns_query: ERROR No data "
      "tcp_server: ERROR No data "
      "http_query: OK IP 127.0.0.1 status_code 302 OK IP 127.0.0.2 "
      "status_code 302 "
      "ssl_certificate: ERROR No key 'ssl_certificate'. If the error "
      "persist, please update surykatka."
    )

  def test_bad_code(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.erp5.com/',
        'status-code': '301',
      }
    )
    self.writeSurykatkaJson({
      "http_query": [
        {
          "date": "Wed, 11 Dec 2019 09:35:28 -0000",
          "ip": "127.0.0.1",
          "status_code": 302,
          "url": "https://www.erp5.com/"
        },
        {
          "date": "Wed, 11 Dec 2019 09:35:28 -0000",
          "ip": "127.0.0.2",
          "status_code": 301,
          "url": "https://www.erp5.com/"
        },
        {
          "date": "Wed, 11 Dec 2019 09:35:28 -0000",
          "ip": "176.31.129.213",
          "status_code": 200,
          "url": "https://www.erp5.org/"
        }
      ],
      "ssl_certificate": [
        {
          "date": "Fri, 27 Dec 2019 14:43:26 -0000",
          "hostname": "www.erp5.com",
          "ip": "127.0.0.1",
          "not_after": self.time_future60d
        },
        {
          "date": "Fri, 27 Dec 2019 14:43:26 -0000",
          "hostname": "www.erp5.com",
          "ip": "127.0.0.2",
          "not_after": self.time_future60d
        }
      ],
      "dns_query": [],
      "tcp_server": []
    })
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "https://www.erp5.com/ : "
      "dns_query: ERROR No data "
      "tcp_server: ERROR No data "
      "http_query: ERROR IP 127.0.0.1 expected status_code 302 != 301 OK IP "
      "127.0.0.2 status_code 301 "
      "ssl_certificate: OK IP 127.0.0.1 will expire in > 15 days OK IP "
      "127.0.0.2 will expire in > 15 days"
    )

  def _test_bad_code_explanation(self, status_code, explanation):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.erp5.com/',
        'status-code': '301',
      }
    )
    self.writeSurykatkaJson({
      "http_query": [
        {
          "date": "Wed, 11 Dec 2019 09:35:28 -0000",
          "ip": "127.0.0.1",
          "status_code": status_code,
          "url": "https://www.erp5.com/"
        }
      ],
      "ssl_certificate": [
        {
          "date": "Fri, 27 Dec 2019 14:43:26 -0000",
          "hostname": "www.erp5.com",
          "ip": "127.0.0.1",
          "not_after": self.time_future60d
        },
        {
          "date": "Fri, 27 Dec 2019 14:43:26 -0000",
          "hostname": "www.erp5.com",
          "ip": "127.0.0.2",
          "not_after": self.time_future60d
        }
      ],
      "dns_query": [],
      "tcp_server": [],
    })
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "https://www.erp5.com/ : "
      "dns_query: ERROR No data "
      "tcp_server: ERROR No data "
      "http_query: ERROR IP 127.0.0.1 expected status_code %s != 301 "
      "ssl_certificate: OK IP 127.0.0.1 will expire in > 15 days OK IP "
      "127.0.0.2 will expire in > 15 days" % (explanation,)
    )

  def test_bad_code_explanation_520(self):
    self._test_bad_code_explanation(520, '520 (Too many redirects)')

  def test_bad_code_explanation_523(self):
    self._test_bad_code_explanation(523, '523 (Connection error)')

  def test_bad_code_explanation_524(self):
    self._test_bad_code_explanation(524, '524 (Connection timeout)')

  def test_bad_code_explanation_526(self):
    self._test_bad_code_explanation(526, '526 (SSL Error)')

  def test_bad_ip(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.erp5.com/',
        'status-code': '301',
        'ip-list': '127.0.0.1 127.0.0.2',
      }
    )
    self.writeSurykatkaJson({
      "http_query": [
        {
          "date": "Wed, 11 Dec 2019 09:35:28 -0000",
          "ip": "127.0.0.1",
          "status_code": 301,
          "url": "https://www.erp5.com/"
        },
        {
          "date": "Wed, 11 Dec 2019 09:35:28 -0000",
          "ip": "127.0.0.4",
          "status_code": 301,
          "url": "https://www.erp5.com/"
        },
        {
          "date": "Wed, 11 Dec 2019 09:35:28 -0000",
          "ip": "176.31.129.213",
          "status_code": 200,
          "url": "https://www.erp5.org/"
        }
      ],
      "ssl_certificate": [
        {
          "date": "Fri, 27 Dec 2019 14:43:26 -0000",
          "hostname": "www.erp5.com",
          "ip": "127.0.0.1",
          "not_after": self.time_future60d
        },
        {
          "date": "Fri, 27 Dec 2019 14:43:26 -0000",
          "hostname": "www.erp5.com",
          "ip": "127.0.0.2",
          "not_after": self.time_future60d
        }
      ],
      "dns_query": [],
      "tcp_server": [],
    })
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "https://www.erp5.com/ : "
      "dns_query: ERROR No data "
      "tcp_server: ERROR No data "
      "http_query: OK IP 127.0.0.1 status_code 301 OK IP 127.0.0.4 "
      "status_code 301 "
      "ssl_certificate: OK IP 127.0.0.1 will expire in > 15 days OK IP "
      "127.0.0.2 will expire in > 15 days"
    )

  def test_bad_ip_status_code(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.erp5.com/',
        'status-code': '301',
        'ip-list': '127.0.0.1 127.0.0.2',
      }
    )
    self.writeSurykatkaJson({
      "http_query": [
        {
          "date": "Wed, 11 Dec 2019 09:35:28 -0000",
          "ip": "127.0.0.1",
          "status_code": 302,
          "url": "https://www.erp5.com/"
        },
        {
          "date": "Wed, 11 Dec 2019 09:35:28 -0000",
          "ip": "127.0.0.4",
          "status_code": 301,
          "url": "https://www.erp5.com/"
        },
        {
          "date": "Wed, 11 Dec 2019 09:35:28 -0000",
          "ip": "176.31.129.213",
          "status_code": 200,
          "url": "https://www.erp5.org/"
        }
      ],
      "ssl_certificate": [
        {
          "date": "Fri, 27 Dec 2019 14:43:26 -0000",
          "hostname": "www.erp5.com",
          "ip": "127.0.0.1",
          "not_after": self.time_future60d
        },
        {
          "date": "Fri, 27 Dec 2019 14:43:26 -0000",
          "hostname": "www.erp5.com",
          "ip": "127.0.0.2",
          "not_after": self.time_future60d
        }
      ],
      "dns_query": [],
      "tcp_server": [],
    })
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "https://www.erp5.com/ : "
      "dns_query: ERROR No data "
      "tcp_server: ERROR No data "
      "http_query: ERROR IP 127.0.0.1 expected status_code 302 != 301 OK IP "
      "127.0.0.4 status_code 301 "
      "ssl_certificate: OK IP 127.0.0.1 will expire in > 15 days OK IP "
      "127.0.0.2 will expire in > 15 days"
    )

  def test_https_no_cert(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.erp5.com/',
        'status-code': '301',
        'ip-list': '127.0.0.1 127.0.0.2',
      }
    )
    self.writeSurykatkaJson({
      "http_query": [
        {
          "date": "Wed, 11 Dec 2019 09:35:28 -0000",
          "ip": "127.0.0.1",
          "status_code": 302,
          "url": "https://www.erp5.com/"
        },
        {
          "date": "Wed, 11 Dec 2019 09:35:28 -0000",
          "ip": "127.0.0.4",
          "status_code": 301,
          "url": "https://www.erp5.com/"
        }
      ],
      "ssl_certificate": [
        {
          "date": "Fri, 27 Dec 2019 14:43:26 -0000",
          "hostname": "www.erp5.com",
          "ip": "127.0.0.1",
          "not_after": None
        },
        {
          "date": "Fri, 27 Dec 2019 14:43:26 -0000",
          "hostname": "www.erp5.com",
          "ip": "127.0.0.2",
          "not_after": None
        }
      ],
      "dns_query": [],
      "tcp_server": [],
    })
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "https://www.erp5.com/ : "
      "dns_query: ERROR No data "
      "tcp_server: ERROR No data "
      "http_query: ERROR IP 127.0.0.1 expected status_code 302 != 301 OK IP "
      "127.0.0.4 status_code 301 "
      "ssl_certificate: ERROR IP 127.0.0.1 no information ERROR IP 127.0.0.2 "
      "no information"
    )

  def test_dns_query_no_entry(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.erp5.com/',
        'status-code': '301',
        'ip-list': '127.0.0.1 127.0.0.2',
      }
    )
    self.writeSurykatkaJson({
      "http_query": [
      ],
      "ssl_certificate": [
      ],
      "dns_query": [],
      "tcp_server": [],
    })
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "https://www.erp5.com/ : "
      "dns_query: ERROR No data "
      "tcp_server: ERROR No data "
      "http_query: ERROR No data "
      "ssl_certificate: ERROR No data "
      "elapsed_time: ERROR No data"
    )

  def test_dns_query_no_key(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.erp5.com/',
        'status-code': '301',
        'ip-list': '127.0.0.1 127.0.0.2',
      }
    )
    self.writeSurykatkaJson({
      "http_query": [
      ],
      "ssl_certificate": [
      ],
      "tcp_server": []
    })
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "https://www.erp5.com/ : "
      "dns_query: ERROR 'dns_query' not in %(json_file)r "
      "tcp_server: ERROR No data "
      "http_query: ERROR No data "
      "ssl_certificate: ERROR No data "
      "elapsed_time: ERROR No data" % {'json_file': self.json_file}
    )

  def test_dns_query_mismatch(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.erp5.com/',
        'status-code': '301',
        'ip-list': '127.0.0.1 127.0.0.2',
      }
    )
    self.writeSurykatkaJson({
      "http_query": [
      ],
      "ssl_certificate": [
      ],
      "dns_query": [
        {
            "domain": "www.erp5.com",
            "rdtype": "A",
            "resolver_ip": "1.2.3.4",
            "date": "Tue, 28 Feb 2023 12:40:29 -0000",
            "response": "127.0.0.2, 127.0.0.3"
        },
        {
            "domain": "www.erp5.org",
            "rdtype": "A",
            "resolver_ip": "1.2.3.4",
            "date": "Tue, 28 Feb 2023 12:40:29 -0000",
            "response": "127.0.0.1, 127.0.0.2"
        },
      ],
      "tcp_server": []
    })
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "https://www.erp5.com/ : "
      "dns_query: ERROR resolver 1.2.3.4 expected 127.0.0.1 127.0.0.2 != "
      "127.0.0.2 127.0.0.3 "
      "tcp_server: ERROR No data "
      "http_query: ERROR No data "
      "ssl_certificate: ERROR No data "
      "elapsed_time: ERROR No data"
    )

  def test_dns_query_no_reply(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.erp5.com/',
        'status-code': '301',
        'ip-list': '127.0.0.1 127.0.0.2',
      }
    )
    self.writeSurykatkaJson({
      "http_query": [
      ],
      "ssl_certificate": [
      ],
      "dns_query": [
        {
            "domain": "www.erp5.com",
            "rdtype": "A",
            "resolver_ip": "1.2.3.4",
            "date": "Tue, 28 Feb 2023 12:40:29 -0000",
            "response": ""
        },
        {
            "domain": "www.erp5.org",
            "rdtype": "A",
            "resolver_ip": "1.2.3.4",
            "date": "Tue, 28 Feb 2023 12:40:29 -0000",
            "response": "127.0.0.1, 127.0.0.2"
        },
      ],
      "tcp_server": [
        {
            "ip": "127.0.0.1",
            "state": "open",
            "port": 443,
            "date": "Tue, 28 Feb 2023 09:27:26 -0000",
            "domain": "www.erp5.com"
        },
        {
            "ip": "127.0.0.2",
            "state": "open",
            "port": 443,
            "date": "Tue, 28 Feb 2023 09:27:26 -0000",
            "domain": "www.erp5.com"
        },
      ]
    })
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "https://www.erp5.com/ : "
      "dns_query: ERROR resolver 1.2.3.4 expected 127.0.0.1 127.0.0.2 != "
      "empty-reply "
      "tcp_server: OK IP 127.0.0.1:443 OK IP 127.0.0.2:443 "
      "http_query: ERROR No data "
      "ssl_certificate: ERROR No data "
      "elapsed_time: ERROR No data"
    )

  def test_tcp_server_no_ip(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.erp5.com/',
        'status-code': '301',
        'ip-list': '127.0.0.1 127.0.0.2',
      }
    )
    self.writeSurykatkaJson({
      "http_query": [
      ],
      "ssl_certificate": [
      ],
      "dns_query": [
      ],
      "tcp_server": [
        {
            "ip": "127.0.0.3",
            "state": "filtered",
            "port": 443,
            "date": "Tue, 28 Feb 2023 09:27:26 -0000",
            "domain": "www.erp5.com"
        },
        {
            "ip": "127.0.0.4",
            "state": "open",
            "port": 80,
            "date": "Tue, 28 Feb 2023 09:27:26 -0000",
            "domain": "www.erp5.com"
        },
      ]
    })
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "https://www.erp5.com/ : "
      "dns_query: ERROR No data "
      "tcp_server: ERROR IP 127.0.0.1:443 ERROR IP 127.0.0.2:443 "
      "http_query: ERROR No data "
      "ssl_certificate: ERROR No data "
      "elapsed_time: ERROR No data"
    )

  def test_tcp_server_mismatch(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.erp5.com/',
        'status-code': '301',
        'ip-list': '127.0.0.1 127.0.0.2',
      }
    )
    self.writeSurykatkaJson({
      "http_query": [
      ],
      "ssl_certificate": [
      ],
      "dns_query": [
      ],
      "tcp_server": [
        {
            "ip": "127.0.0.1",
            "state": "filtered",
            "port": 443,
            "date": "Tue, 28 Feb 2023 09:27:26 -0000",
            "domain": "www.erp5.com"
        },
        {
            "ip": "127.0.0.2",
            "state": "open",
            "port": 80,
            "date": "Tue, 28 Feb 2023 09:27:26 -0000",
            "domain": "www.erp5.com"
        },
      ]
    })
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "https://www.erp5.com/ : "
      "dns_query: ERROR No data "
      "tcp_server: ERROR IP 127.0.0.1:443 ERROR IP 127.0.0.2:443 "
      "http_query: ERROR No data "
      "ssl_certificate: ERROR No data "
      "elapsed_time: ERROR No data"
    )

  def test_tcp_server_no_entry(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.erp5.com/',
        'status-code': '301',
        'ip-list': '127.0.0.1 127.0.0.2',
      }
    )
    self.writeSurykatkaJson({
      "http_query": [
      ],
      "ssl_certificate": [
      ],
      "dns_query": [
      ],
      "tcp_server": [
      ]
    })
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "https://www.erp5.com/ : "
      "dns_query: ERROR No data "
      "tcp_server: ERROR No data "
      "http_query: ERROR No data "
      "ssl_certificate: ERROR No data "
      "elapsed_time: ERROR No data"
    )

  def test_tcp_server_no_key(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.erp5.com/',
        'status-code': '301',
        'ip-list': '127.0.0.1 127.0.0.2',
      }
    )
    self.writeSurykatkaJson({
      "http_query": [
      ],
      "ssl_certificate": [
      ],
      "dns_query": [
      ],
    })
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "https://www.erp5.com/ : "
      "dns_query: ERROR No data "
      "tcp_server: ERROR 'tcp_server' not in %(json_file)r "
      "http_query: ERROR No data "
      "ssl_certificate: ERROR No data "
      "elapsed_time: ERROR No data" % {'json_file': self.json_file}
    )
