from slapos.grid.promise import PromiseError
from slapos.test.promise.plugin import TestPromisePluginMixin

import os
import shutil
import tempfile


class CheckSurykatkaJSONMixin(TestPromisePluginMixin):
  promise_name = 'check-surykatka-json.py'

  def setUp(self):
    self.working_directory = tempfile.mkdtemp()
    self.json_file = os.path.join(self.working_directory, 'surykatka.json')
    self.addCleanup(shutil.rmtree, self.working_directory)
    TestPromisePluginMixin.setUp(self)

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

  def writeSurykatkaJson(self, content):
    with open(self.json_file, 'w') as fh:
      fh.write(content)

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


class TestCheckSurykatkaJSON(CheckSurykatkaJSONMixin):
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
    self.writeSurykatkaJson('')
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "ERROR loading JSON from '%s'" % (self.json_file,))


class TestCheckSurykatkaJSONUnknownReport(CheckSurykatkaJSONMixin):
  def test(self):
    self.writeSurykatkaPromise(
      {
        'report': 'NOT_EXISTING_ENTRY',
        'json-file': self.json_file,
      }
    )
    self.writeSurykatkaJson("""{
}
""")
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
        'test-utcnow': 'Wed, 13 Dec 2222 09:11:12 -0000'
      }
    )
    self.writeSurykatkaJson("""{
    "bot_status": [
        {
            "date": "Wed, 13 Dec 2222 09:10:11 -0000",
            "text": "loop"
        }
    ]
}
""")
    self.configureLauncher(enable_anomaly=True)
    self.launcher.run()
    self.assertPassedMessage(
      self.getPromiseResult(self.promise_name),
      "bot_status: OK Last bot status from Fri, 13 Dec 2222 08:10:11 -0000"
    )

  def test_no_loop(self):
    self.writeSurykatkaPromise(
      {
        'report': 'bot_status',
        'json-file': self.json_file,
        'test-utcnow': 'Wed, 13 Dec 2222 09:11:12 -0000'
      }
    )
    self.writeSurykatkaJson("""{
    "bot_status": [
        {
            "date": "Wed, 13 Dec 2222 09:10:11 -0000",
            "text": "error"
        }
    ]
}
""")
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
        'test-utcnow': 'Wed, 13 Dec 2222 09:11:12 -0000'
      }
    )
    self.writeSurykatkaJson("""{
    "bot_status": [
        {
            "date": "Wed, 13 Dec 2223 09:10:11 -0000",
            "text": "loop"
        }
    ]
}
""")
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "bot_status: ERROR Last bot datetime Sat, 13 Dec 2223 08:10:11 -0000 is "
      "in future"
    )

  def test_bot_status_old(self):
    self.writeSurykatkaPromise(
      {
        'report': 'bot_status',
        'json-file': self.json_file,
        'test-utcnow': 'Wed, 13 Dec 2223 09:26:12 -0000'
      }
    )
    self.writeSurykatkaJson("""{
    "bot_status": [
        {
            "date": "Wed, 13 Dec 2223 09:10:11 -0000",
            "text": "loop"
        }
    ]
}
""")
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "bot_status: ERROR Last bot datetime Sat, 13 Dec 2223 08:10:11 -0000 is "
      "more than 15 minutes old"
    )

  def test_not_bot_status(self):
    self.writeSurykatkaPromise(
      {
        'report': 'bot_status',
        'json-file': self.json_file,
      }
    )
    self.writeSurykatkaJson("""{
}
""")
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
    self.writeSurykatkaJson("""{
  "bot_status": []
}
""")
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
        'test-utcnow': 'Fri, 27 Dec 2019 15:11:12 -0000'
      }
    )
    self.writeSurykatkaJson("""{
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
            "not_after": "Mon, 13 Jul 2020 12:00:00 -0000"
        },
        {
            "date": "Fri, 27 Dec 2019 14:43:26 -0000",
            "hostname": "www.erp5.com",
            "ip": "127.0.0.2",
            "not_after": "Mon, 13 Jul 2020 12:00:00 -0000"
        }
    ]
}
""")
    self.configureLauncher(enable_anomaly=True)
    self.launcher.run()
    self.assertPassedMessage(
      self.getPromiseResult(self.promise_name),
      "https://www.erp5.com/ : http_query: OK with status code 302 on IPs "
      "127.0.0.1 127.0.0.2 ssl_certificate: OK Certificate on 127.0.0.1 will "
      "expire on Mon, 13 Jul 2020 12:00:00 -0000, which is more than 15 days"
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
        'test-utcnow': 'Fri, 27 Dec 2019 15:11:12 -0000'
      }
    )
    self.writeSurykatkaJson("""{
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
            "not_after": "Mon, 13 Jul 2020 12:00:00 -0000"
        },
        {
            "date": "Fri, 27 Dec 2019 14:43:26 -0000",
            "hostname": "www.erp5.com",
            "ip": "127.0.0.2",
            "not_after": "Mon, 13 Jul 2020 12:00:00 -0000"
        }
    ]
}
""")
    self.configureLauncher(enable_anomaly=True)
    self.launcher.run()
    self.assertPassedMessage(
      self.getPromiseResult(self.promise_name),
      "https://www.erp5.com/ : http_query: OK with status code 302 on IPs "
      "127.0.0.1 127.0.0.2 ssl_certificate: OK Certificate on 127.0.0.1 will "
      "expire on Mon, 13 Jul 2020 12:00:00 -0000, which is more than 15 days "
      "elapsed_time: OK IP 127.0.0.1 replied in 4.00s which is shorter than "
      "maximum 5.00s elapsed_time: OK IP 127.0.0.2 replied in 4.00s which is "
      "shorter than maximum 5.00s"
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
        'test-utcnow': 'Fri, 27 Dec 2019 15:11:12 -0000'
      }
    )
    self.writeSurykatkaJson("""{
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
            "not_after": "Mon, 13 Jul 2020 12:00:00 -0000"
        },
        {
            "date": "Fri, 27 Dec 2019 14:43:26 -0000",
            "hostname": "www.erp5.com",
            "ip": "127.0.0.2",
            "not_after": "Mon, 13 Jul 2020 12:00:00 -0000"
        }
    ]
}
""")
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "https://www.erp5.com/ : elapsed_time: ERROR IP 127.0.0.1 replied in "
      "6.00s which is longer than maximum 5.00s elapsed_time: ERROR IP "
      "127.0.0.2 failed to reply http_query: OK with status code 302 on IPs "
      "127.0.0.1 127.0.0.2 ssl_certificate: OK Certificate on 127.0.0.1 will "
      "expire on Mon, 13 Jul 2020 12:00:00 -0000, which is more than 15 days"
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
        'test-utcnow': 'Fri, 27 Dec 2019 15:11:12 -0000'
      }
    )
    self.writeSurykatkaJson("""{
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
            "not_after": "Mon, 13 Jul 2020 12:00:00 -0000"
        },
        {
            "date": "Fri, 27 Dec 2019 14:43:26 -0000",
            "hostname": "www.erp5.com",
            "ip": "127.0.0.2",
            "not_after": "Mon, 13 Jul 2020 12:00:00 -0000"
        }
    ]
}
""")
    self.configureLauncher(enable_anomaly=True)
    self.launcher.run()
    self.assertPassedMessage(
      self.getPromiseResult(self.promise_name),
      "https://www.erp5.com/ : http_query: OK with status code 302 on IPs "
      "127.0.0.1 127.0.0.2 ssl_certificate: OK Certificate on 127.0.0.1 will "
      "expire on Mon, 13 Jul 2020 12:00:00 -0000, which is more than 15 days"
    )

  def test_http(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'http://www.erp5.com/',
        'status-code': '302',
        'ip-list': '127.0.0.1 127.0.0.2',
        'test-utcnow': 'Fri, 27 Dec 2019 15:11:12 -0000'
      }
    )
    self.writeSurykatkaJson("""{
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
    ]
}
""")
    self.configureLauncher(enable_anomaly=True)
    self.launcher.run()
    self.assertPassedMessage(
      self.getPromiseResult(self.promise_name),
      "http://www.erp5.com/ : http_query: OK with status code 302 on IPs 127.0.0.1 "
      "127.0.0.2"
    )

  def test_http_with_header_dict(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'http://www.erp5.com/',
        'status-code': '200',
        'http-header-dict': '{"Vary": "Accept-Encoding", "Cache-Control": "max-age=300, public"}',
        'test-utcnow': 'Fri, 27 Dec 2019 15:11:12 -0000'
      }
    )
    self.writeSurykatkaJson("""{
    "http_query": [
        {
            "date": "Wed, 11 Dec 2019 09:35:28 -0000",
            "ip": "176.31.129.213",
            "http_header_dict": {"Vary": "Accept-Encoding", "Cache-Control": "max-age=300, public"},
            "status_code": 200,
            "url": "http://www.erp5.com/"
        }
    ],
    "ssl_certificate": [
    ]
}
""")
    self.configureLauncher(enable_anomaly=True)
    self.launcher.run()
    self.assertPassedMessage(
      self.getPromiseResult(self.promise_name),
      "http://www.erp5.com/ : http_query: OK with status code 200 "
      "and HTTP Header dict {\"Cache-Control\": \"max-age=300, public\", \"Vary\": \"Accept-Encoding\"}"
    )

  def test_http_with_bad_header_dict(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'http://www.erp5.com/',
        'status-code': '200',
        'http-header-dict': '{"Vary": "Accept-Encoding", "Cache-Control": "max-age=300, public"}',
        'test-utcnow': 'Fri, 27 Dec 2019 15:11:12 -0000'
      }
    )
    self.writeSurykatkaJson("""{
    "http_query": [
        {
            "date": "Wed, 11 Dec 2019 09:35:28 -0000",
            "ip": "176.31.129.213",
            "http_header_dict": {"Vary": "Accept-Encoding,Cookie", "Cache-Control": "max-age=300, public"},
            "status_code": 200,
            "url": "http://www.erp5.com/"
        }
    ],
    "ssl_certificate": [
    ]
}
""")
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "http://www.erp5.com/ : http_query: ERROR HTTP Header dict was "
      "{\"Cache-Control\": \"max-age=300, public\", \"Vary\": \"Accept-Encoding,Cookie\"} "
      "instead of {\"Cache-Control\": \"max-age=300, public\", \"Vary\": \"Accept-Encoding\"}"
    )

  def test_no_ip_list(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.erp5.com/',
        'status-code': '302',
        'test-utcnow': 'Fri, 27 Dec 2019 15:11:12 -0000'
      }
    )
    self.writeSurykatkaJson("""{
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
            "not_after": "Mon, 13 Jul 2020 12:00:00 -0000"
        },
        {
            "date": "Fri, 27 Dec 2019 14:43:26 -0000",
            "hostname": "www.erp5.com",
            "ip": "127.0.0.2",
            "not_after": "Mon, 13 Jul 2020 12:00:00 -0000"
        }
    ]
}
""")
    self.configureLauncher(enable_anomaly=True)
    self.launcher.run()
    self.assertPassedMessage(
      self.getPromiseResult(self.promise_name),
      "https://www.erp5.com/ : http_query: OK with status code 302 "
      "ssl_certificate: OK Certificate on 127.0.0.1 will expire on Mon, 13 "
      "Jul 2020 12:00:00 -0000, which is more than 15 days"
    )

  def test_good_certificate_2_day(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.erp5.com/',
        'status-code': '302',
        'test-utcnow': 'Fri, 27 Dec 2019 15:11:12 -0000',
        'certificate-expiration-days': '2'
      }
    )
    self.writeSurykatkaJson("""{
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
            "not_after": "Sun, 30 Dec 2019 12:00:00 -0000"
        }
    ]
}
""")
    self.configureLauncher(enable_anomaly=True)
    self.launcher.run()
    self.assertPassedMessage(
      self.getPromiseResult(self.promise_name),
      "https://www.erp5.com/ : http_query: OK with status code 302 "
      "ssl_certificate: OK Certificate on 127.0.0.1 will expire on Sun, 30 "
      "Dec 2019 12:00:00 -0000, which is more than 2 days"
    )

  def test_expired_certificate_2_day(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.erp5.com/',
        'status-code': '302',
        'test-utcnow': 'Fri, 27 Dec 2019 15:11:12 -0000',
        'certificate-expiration-days': '2'
      }
    )
    self.writeSurykatkaJson("""{
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
            "not_after": "Sat, 28 Dec 2019 12:00:00 -0000"
        }
    ]
}
""")
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "https://www.erp5.com/ : ssl_certificate: ERROR Certificate on "
      "127.0.0.1 will expire on Sat, 28 Dec 2019 12:00:00 -0000, which is "
      "less than 2 days http_query: OK with status code 302"
    )

  def test_expired_certificate(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.erp5.com/',
        'status-code': '302',
        'test-utcnow': 'Fri, 27 Dec 2019 15:11:12 -0000'
      }
    )
    self.writeSurykatkaJson("""{
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
            "not_after": "Sat, 28 Dec 2019 12:00:00 -0000"
        }
    ]
}
""")
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "https://www.erp5.com/ : ssl_certificate: ERROR Certificate on "
      "127.0.0.1 will expire on Sat, 28 Dec 2019 12:00:00 -0000, which is "
      "less than 15 days http_query: OK with status code 302"
    )

  def test_expired_certificate_before_today(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.erp5.com/',
        'status-code': '302',
        'test-utcnow': 'Fri, 27 Dec 2019 15:11:12 -0000'
      }
    )
    self.writeSurykatkaJson("""{
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
            "not_after": "Thu, 26 Dec 2019 12:00:00 -0000"
        }
    ]
}
""")
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "https://www.erp5.com/ : ssl_certificate: ERROR Certificate on "
      "127.0.0.1 will expire on Thu, 26 Dec 2019 12:00:00 -0000, which is "
      "less than 15 days http_query: OK with status code 302"
    )

  def test_no_http_query_data(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.erp5.com/',
        'status-code': '302',
        'ip-list': '127.0.0.1 127.0.0.2',
        'test-utcnow': 'Fri, 27 Dec 2019 15:11:12 -0000'
      }
    )
    self.writeSurykatkaJson("""{
    "http_query": [
    ],
    "ssl_certificate": [
        {
            "date": "Fri, 27 Dec 2019 14:43:26 -0000",
            "hostname": "www.erp5.com",
            "ip": "127.0.0.1",
            "not_after": "Mon, 13 Jul 2020 12:00:00 -0000"
        },
        {
            "date": "Fri, 27 Dec 2019 14:43:26 -0000",
            "hostname": "www.erp5.com",
            "ip": "127.0.0.2",
            "not_after": "Mon, 13 Jul 2020 12:00:00 -0000"
        }
    ]
}
""")
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "https://www.erp5.com/ : http_query: ERROR No data elapsed_time: ERROR "
      "No data ssl_certificate: OK Certificate on 127.0.0.1 will expire on "
      "Mon, 13 Jul 2020 12:00:00 -0000, which is more than 15 days"
    )

  def test_no_ssl_certificate_data(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.erp5.com/',
        'status-code': '302',
        'ip-list': '127.0.0.1 127.0.0.2',
        'test-utcnow': 'Fri, 27 Dec 2019 15:11:12 -0000'
      }
    )
    self.writeSurykatkaJson("""{
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
    ]
}
""")
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "https://www.erp5.com/ : ssl_certificate: ERROR No data http_query: "
      "OK with status code 302 on IPs 127.0.0.1 127.0.0.2"
    )

  def test_no_ssl_certificate(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.erp5.com/',
        'status-code': '302',
        'ip-list': '127.0.0.1 127.0.0.2',
        'test-utcnow': 'Fri, 27 Dec 2019 15:11:12 -0000'
      }
    )
    self.writeSurykatkaJson("""{
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
    ]
}
""")
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "https://www.erp5.com/ : ssl_certificate: ERROR No key "
      "'ssl_certificate'. If the error persist, please update surykatka. "
      "http_query: OK with status code 302 on IPs 127.0.0.1 127.0.0.2"
    )

  def test_bad_code(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.erp5.com/',
        'status-code': '301',
        'test-utcnow': 'Fri, 27 Dec 2019 15:11:12 -0000'
      }
    )
    self.writeSurykatkaJson("""{
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
            "not_after": "Mon, 13 Jul 2020 12:00:00 -0000"
        },
        {
            "date": "Fri, 27 Dec 2019 14:43:26 -0000",
            "hostname": "www.erp5.com",
            "ip": "127.0.0.2",
            "not_after": "Mon, 13 Jul 2020 12:00:00 -0000"
        }
    ]
}
""")
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "https://www.erp5.com/ : http_query: ERROR IP 127.0.0.1 got status code "
      "302 instead of 301 ssl_certificate: OK Certificate on 127.0.0.1 will "
      "expire on Mon, 13 Jul 2020 12:00:00 -0000, which is more than 15 days"
    )

  def _test_bad_code_explanation(self, status_code, explanation):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.erp5.com/',
        'status-code': '301',
        'test-utcnow': 'Fri, 27 Dec 2019 15:11:12 -0000'
      }
    )
    self.writeSurykatkaJson("""{
    "http_query": [
        {
            "date": "Wed, 11 Dec 2019 09:35:28 -0000",
            "ip": "127.0.0.1",
            "status_code": %s,
            "url": "https://www.erp5.com/"
        }
    ],
    "ssl_certificate": [
        {
            "date": "Fri, 27 Dec 2019 14:43:26 -0000",
            "hostname": "www.erp5.com",
            "ip": "127.0.0.1",
            "not_after": "Mon, 13 Jul 2020 12:00:00 -0000"
        },
        {
            "date": "Fri, 27 Dec 2019 14:43:26 -0000",
            "hostname": "www.erp5.com",
            "ip": "127.0.0.2",
            "not_after": "Mon, 13 Jul 2020 12:00:00 -0000"
        }
    ]
}
""" % status_code)
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "https://www.erp5.com/ : http_query: ERROR IP 127.0.0.1 got status code "
      "%s instead of 301 ssl_certificate: OK Certificate on 127.0.0.1 will "
      "expire on Mon, 13 Jul 2020 12:00:00 -0000, which is more than 15 days"
      "" % (explanation,)
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
        'test-utcnow': 'Fri, 27 Dec 2019 15:11:12 -0000'
      }
    )
    self.writeSurykatkaJson("""{
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
            "not_after": "Mon, 13 Jul 2020 12:00:00 -0000"
        },
        {
            "date": "Fri, 27 Dec 2019 14:43:26 -0000",
            "hostname": "www.erp5.com",
            "ip": "127.0.0.2",
            "not_after": "Mon, 13 Jul 2020 12:00:00 -0000"
        }
    ]
}
""")
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "https://www.erp5.com/ : http_query: ERROR expected IPs 127.0.0.1 "
      "127.0.0.2 differes from got 127.0.0.1 127.0.0.4 ssl_certificate: "
      "OK Certificate on 127.0.0.1 will expire on Mon, 13 Jul 2020 12:00:00 "
      "-0000, which is more than 15 days"
    )

  def test_bad_ip_status_code(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.erp5.com/',
        'status-code': '301',
        'ip-list': '127.0.0.1 127.0.0.2',
        'test-utcnow': 'Fri, 27 Dec 2019 15:11:12 -0000'
      }
    )
    self.writeSurykatkaJson("""{
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
            "not_after": "Mon, 13 Jul 2020 12:00:00 -0000"
        },
        {
            "date": "Fri, 27 Dec 2019 14:43:26 -0000",
            "hostname": "www.erp5.com",
            "ip": "127.0.0.2",
            "not_after": "Mon, 13 Jul 2020 12:00:00 -0000"
        }
    ]
}
""")
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "https://www.erp5.com/ : http_query: ERROR IP 127.0.0.1 got status code "
      "302 instead of 301 http_query: ERROR expected IPs 127.0.0.1 127.0.0.2 "
      "differes from got 127.0.0.1 127.0.0.4 ssl_certificate: OK Certificate "
      "on 127.0.0.1 will expire on Mon, 13 Jul 2020 12:00:00 -0000, which is "
      "more than 15 days"
    )

  def test_https_no_cert(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.erp5.com/',
        'status-code': '301',
        'ip-list': '127.0.0.1 127.0.0.2',
        'test-utcnow': 'Fri, 27 Dec 2019 15:11:12 -0000'
      }
    )
    self.writeSurykatkaJson("""{
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
            "not_after": null
        },
        {
            "date": "Fri, 27 Dec 2019 14:43:26 -0000",
            "hostname": "www.erp5.com",
            "ip": "127.0.0.2",
            "not_after": null
        }
    ]
}
""")
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "https://www.erp5.com/ : http_query: ERROR IP 127.0.0.1 got status code "
      "302 instead of 301 http_query: ERROR expected IPs 127.0.0.1 127.0.0.2 "
      "differes from got 127.0.0.1 127.0.0.4 ssl_certificate: ERROR No "
      "certificate information for 127.0.0.1 ssl_certificate: ERROR No "
      "certificate information for 127.0.0.2"
    )
