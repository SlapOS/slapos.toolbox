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
    self.time_past29d = create_date(now - 29 * day)
    self.time_past20m = create_date(now - 20 * minute)
    self.time_past2m = create_date(now - 2 * minute)
    self.time_future20m = create_date(now + 20 * minute)
    self.time_future3d = create_date(now + 3 * day)
    self.time_future14d = create_date(now + 14 * day)
    self.time_future29d = create_date(now + 29 * day)
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
  def setUp(self):
    super().setUp()
    self.writeSurykatkaJson({
      "http_query": [
        {
          "ip": "127.0.0.1",
          "status_code": 302,
          "url": "https://www.allok.com/",
          "total_seconds": 4
        },
        {
          "ip": "127.0.0.2",
          "status_code": 302,
          "url": "https://www.allok.com/",
          "total_seconds": 4
        },
        {
          "ip": "127.0.0.1",
          "status_code": 302,
          "url": "http://www.httpallok.com/",
          "total_seconds": 4
        },
        {
          "ip": "127.0.0.2",
          "status_code": 302,
          "url": "http://www.httpallok.com/",
          "total_seconds": 4
        },
        {
          "ip": "127.0.0.1",
          "status_code": 302,
          "url": "https://www.elapsedtoolong.com/",
          "total_seconds": 6
        },
        {
          "ip": "127.0.0.1",
          "status_code": 302,
          "url": "https://www.elapsednototal.com/",
        },
        {
          "ip": "127.0.0.1",
          "status_code": 200,
          "url": "http://www.httpheader.com/",
          "http_header_dict": {
            "Vary": "Accept-Encoding", "Cache-Control": "max-age=300, public"},
        },
        {
          "ip": "127.0.0.1",
          "status_code": 302,
          "url": "https://www.cert3.com/",
          "total_seconds": 4
        },
        {
          "ip": "127.0.0.1",
          "status_code": 302,
          "url": "https://www.cert14.com/",
          "total_seconds": 4
        },
        {
          "ip": "127.0.0.1",
          "status_code": 302,
          "url": "https://www.certminus14.com/",
          "total_seconds": 4
        },
        {
          "ip": "127.0.0.1",
          "status_code": 302,
          "url": "https://www.nosslcertificatedata.com/",
        },
        {
          "ip": "127.0.0.1",
          "status_code": 302,
          "url": "http://www.badip.com/",
        },
        {
          "ip": "127.0.0.4",
          "status_code": 302,
          "url": "http://www.badip.com/",
        },
        {
          "ip": "127.0.0.1",
          "status_code": 301,
          "url": "https://www.sslcertnoinfo.com/",
        },
      ],
      "ssl_certificate": [
        {
          "hostname": "www.allok.com",
          "ip": "127.0.0.1",
          "not_after": self.time_future60d
        },
        {
          "hostname": "www.allok.com",
          "ip": "127.0.0.2",
          "not_after": self.time_future60d
        },
        {
          "hostname": "www.cert3.com",
          "ip": "127.0.0.1",
          "not_after": self.time_future3d
        },
        {
          "hostname": "www.cert14.com",
          "ip": "127.0.0.1",
          "not_after": self.time_future14d
        },
        {
          "hostname": "www.certminus14.com",
          "ip": "127.0.0.1",
          "not_after": self.time_past14d
        },
        {
          "hostname": "www.sslcertnoinfo.com",
          "ip": "127.0.0.1",
          "not_after": None
        },
      ],
      "dns_query": [
        {
            "domain": "www.allok.com",
            "rdtype": "A",
            "resolver_ip": "1.2.3.4",
            "response": "127.0.0.1, 127.0.0.2"
        },
        {
            "domain": "www.httpallok.com",
            "rdtype": "A",
            "resolver_ip": "1.2.3.4",
            "response": "127.0.0.1, 127.0.0.2"
        },
        {
            "domain": "www.badip.com",
            "rdtype": "A",
            "resolver_ip": "1.2.3.4",
            "response": "127.0.0.1, 127.0.0.4"
        },
        {
            "domain": "www.dnsquerynoreply.com",
            "rdtype": "A",
            "resolver_ip": "1.2.3.4",
            "response": ""
        },
      ],
      "tcp_server": [
        {
            "ip": "127.0.0.1",
            "state": "open",
            "port": 443,
            "domain": "www.allok.com"
        },
        {
            "ip": "127.0.0.2",
            "state": "open",
            "port": 443,
            "domain": "www.allok.com"
        },
        {
            "ip": "127.0.0.1",
            "state": "open",
            "port": 80,
            "domain": "www.httpallok.com"
        },
        {
            "ip": "127.0.0.2",
            "state": "open",
            "port": 80,
            "domain": "www.httpallok.com"
        },
        {
            "ip": "127.0.0.1",
            "state": "open",
            "port": 80,
            "domain": "www.httpheader.com"
        },
        {
            "ip": "127.0.0.1",
            "state": "open",
            "port": 80,
            "domain": "www.badip.com"
        },
        {
            "ip": "127.0.0.4",
            "state": "open",
            "port": 80,
            "domain": "www.badip.com"
        },
        {
            "ip": "127.0.0.2",
            "state": "open",
            "port": 80,
            "domain": "www.tcpservernoip.com"
        },
        {
            "ip": "127.0.0.1",
            "state": "filtered",
            "port": 80,
            "domain": "www.tcpserverfiltered.com"
        },
      ],
      "whois": [
        {
            "domain": "allok.com",
            "expiration_date": self.time_future60d,
        },
        {
            "domain": "httpallok.com",
            "expiration_date": self.time_future60d,
        },
        {
            "domain": "httpheader.com",
            "expiration_date": self.time_future60d,
        },
        {
            "domain": "whois3.com",
            "expiration_date": self.time_future3d,
        },
        {
            "domain": "whois29.com",
            "expiration_date": self.time_future29d
        },
        {
            "domain": "whoisminus29.com",
            "expiration_date": self.time_past29d
        },
      ]
    })

  def runAndAssertPassedMessage(self, message):
    self.configureLauncher(enable_anomaly=True)
    self.launcher.run()
    self.assertPassedMessage(
      self.getPromiseResult(self.promise_name),
      message
    )

  def runAndAssertFailedMessage(self, message):
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      message
    )

  def test_all_ok(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.allok.com/',
        'status-code': '302',
        'ip-list': '127.0.0.1 127.0.0.2',
        'maximum-elapsed-time': '5',
      }
    )
    self.runAndAssertPassedMessage(
      "https://www.allok.com/ : "
      "dns_query: OK resolver's 1.2.3.4: 127.0.0.1 127.0.0.2 "
      "whois: OK allok.com expires in > 30 days "
      "tcp_server: OK IP 127.0.0.1:443 OK IP 127.0.0.2:443 "
      "http_query: OK IP 127.0.0.1 status_code 302 OK IP 127.0.0.2 "
      "status_code 302 "
      "ssl_certificate: OK IP 127.0.0.1 expires in > 15 days OK IP "
      "127.0.0.2 expires in > 15 days "
      "elapsed_time: OK IP 127.0.0.1 replied < 5.00s OK IP 127.0.0.2 replied "
      "< 5.00s"
    )

  def test_maximum_elapsed_time_too_long(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.elapsedtoolong.com/',
        'ip-list': '127.0.0.1',
        'maximum-elapsed-time': '5',
        'enabled-sense-list': 'elapsed_time'
      }
    )
    self.runAndAssertFailedMessage(
      "https://www.elapsedtoolong.com/ : "
      "elapsed_time: ERROR IP 127.0.0.1 replied > 5.00s"
    )

  def test_maximum_elapsed_no_match(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.elapsednototal.com/',
        'ip-list': '127.0.0.1',
        'maximum-elapsed-time': '5',
        'enabled-sense-list': 'elapsed_time'
      }
    )
    self.runAndAssertFailedMessage(
      "https://www.elapsednototal.com/ : "
      "elapsed_time: ERROR No entry with total_seconds found. If the error "
      "persist, please update surykatka"
    )

  def test_http_all_ok(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'http://www.httpallok.com/',
        'status-code': '302',
        'ip-list': '127.0.0.1 127.0.0.2',
        'maximum-elapsed-time': '5',
      }
    )
    self.runAndAssertPassedMessage(
      "http://www.httpallok.com/ : "
      "dns_query: OK resolver's 1.2.3.4: 127.0.0.1 127.0.0.2 "
      "whois: OK httpallok.com expires in > 30 days "
      "tcp_server: OK IP 127.0.0.1:80 OK IP 127.0.0.2:80 "
      "http_query: OK IP 127.0.0.1 status_code 302 OK IP 127.0.0.2 "
      "status_code 302 "
      "ssl_certificate: OK No check needed "
      "elapsed_time: OK IP 127.0.0.1 replied < 5.00s OK IP 127.0.0.2 replied "
      "< 5.00s"
    )

  def test_http_query_header_dict(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'http://www.httpheader.com/',
        'status-code': '200',
        'http-header-dict': '{"Vary": "Accept-Encoding", "Cache-Control": '
        '"max-age=300, public"}',
        'enabled-sense-list': 'http_query'
      }
    )
    self.runAndAssertPassedMessage(
      'http://www.httpheader.com/ : '
      'http_query: OK IP 127.0.0.1 status_code 200 OK IP 127.0.0.1 HTTP '
      'Header {"Cache-Control": "max-age=300, public", "Vary": '
      '"Accept-Encoding"}'
    )

  def test_http_query_header_dict_mismatch(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'http://www.httpheader.com/',
        'status-code': '200',
        'http-header-dict': '{"Vary": "Accept-Encoding", "Cache-Control": '
        '"max-age=300"}',
        'enabled-sense-list': 'http_query'
      }
    )
    self.runAndAssertFailedMessage(
      'http://www.httpheader.com/ : '
      'http_query: OK IP 127.0.0.1 status_code 200 ERROR IP 127.0.0.1 '
      'HTTP Header {"Cache-Control": "max-age=300", "Vary": '
      '"Accept-Encoding"} != {"Cache-Control": "max-age=300, public", "Vary": '
      '"Accept-Encoding"}'
    )

  def test_configuration_no_ip_list(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.allok.com/',
        'status-code': '302',
      }
    )
    self.runAndAssertPassedMessage(
      "https://www.allok.com/ : "
      "dns_query: OK No check configured "
      "whois: OK allok.com expires in > 30 days "
      "tcp_server: OK No check configured "
      "http_query: OK IP 127.0.0.1 status_code 302 OK IP 127.0.0.2 "
      "status_code 302 "
      "ssl_certificate: OK IP 127.0.0.1 expires in > 15 days OK IP "
      "127.0.0.2 expires in > 15 days "
      "elapsed_time: OK No check configured"
    )

  def test_ssl_certificate_good_certificate_2_day(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.cert3.com/',
        'certificate-expiration-days': '2',
        'enabled-sense-list': 'ssl_certificate',
      }
    )
    self.runAndAssertPassedMessage(
      "https://www.cert3.com/ : "
      "ssl_certificate: OK IP 127.0.0.1 expires in > 2 days"
    )

  def test_ssl_certificate_expired_certificate_4_day(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.cert3.com/',
        'certificate-expiration-days': '4',
        'enabled-sense-list': 'ssl_certificate',
      }
    )

    self.runAndAssertFailedMessage(
      "https://www.cert3.com/ : "
      "ssl_certificate: ERROR IP 127.0.0.1 expires in < 4 days"
    )

  def test_ssl_certificate_expired_certificate(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.cert14.com/',
        'enabled-sense-list': 'ssl_certificate',
      }
    )
    self.runAndAssertFailedMessage(
      "https://www.cert14.com/ : "
      "ssl_certificate: ERROR IP 127.0.0.1 expires in < 15 days"
    )

  def test_expired_certificate_before_today(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.certminus14.com/',
        'enabled-sense-list': 'ssl_certificate',
      }
    )
    self.runAndAssertFailedMessage(
      "https://www.certminus14.com/ : "
      "ssl_certificate: ERROR IP 127.0.0.1 expires in < 15 days"
    )

  def test_no_http_query_data(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'http://www.httpquerynodata.com/',
        'status-code': '302',
        'enabled-sense-list': 'http_query'
      }
    )
    self.runAndAssertFailedMessage(
      "http://www.httpquerynodata.com/ : "
      "http_query: ERROR No data"
    )

  def test_no_http_query_present(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'http://www.httpquerynopresent.com/',
        'status-code': '302',
        'enabled-sense-list': 'http_query'
      }
    )
    self.writeSurykatkaJson({
      "ssl_certificate": [],
      "dns_query": [],
      "tcp_server": [],
    })
    self.runAndAssertFailedMessage(
      "http://www.httpquerynopresent.com/ : "
      "http_query: ERROR 'http_query' not in %(json_file)r" % {
        'json_file': self.json_file}
    )

  def test_no_ssl_certificate_data(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.nosslcertificatedata.com/',
        'enabled-sense-list': 'ssl_certificate'
      }
    )
    self.runAndAssertFailedMessage(
      "https://www.nosslcertificatedata.com/ : "
      "ssl_certificate: ERROR No data"
    )

  def test_no_ssl_certificate(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.nosslcertificate.com/',
        'enabled-sense-list': 'ssl_certificate',
      }
    )
    self.writeSurykatkaJson({
      "http_query": [
        {
          "ip": "127.0.0.1",
          "status_code": 302,
          "url": "https://www.nosslcertificate.com/"
        },
      ],
      "dns_query": [],
      "tcp_server": [],
      "whois": []
    })
    self.runAndAssertFailedMessage(
      "https://www.nosslcertificate.com/ : "
      "ssl_certificate: ERROR 'ssl_certificate' not in %(json_file)r" % {
        'json_file': self.json_file}
    )

  def test_bad_code(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.allok.com/',
        'status-code': '301',
        'enabled-sense-list': 'http_query'
      }
    )
    self.runAndAssertFailedMessage(
      "https://www.allok.com/ : "
      "http_query: ERROR IP 127.0.0.1 status_code 302 != 301 ERROR "
      "IP 127.0.0.2 status_code 302 != 301"
    )

  def _test_bad_code_explanation(self, status_code, explanation):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'http://www.statuscode.com/',
        'status-code': '301',
        'enabled-sense-list': 'http_query',
      }
    )
    self.writeSurykatkaJson({
      "http_query": [
        {
          "ip": "127.0.0.1",
          "status_code": status_code,
          "url": "http://www.statuscode.com/"
        }
      ],
      "ssl_certificate": [],
      "dns_query": [],
      "tcp_server": [],
    })
    self.runAndAssertFailedMessage(
      "http://www.statuscode.com/ : "
      "http_query: ERROR IP 127.0.0.1 status_code %s != 301" % (explanation,)
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
        'url': 'http://www.badip.com/',
        'status-code': '302',
        'ip-list': '127.0.0.1 127.0.0.2',
        'enabled-sense-list': 'dns_query',
      }
    )
    self.configureLauncher(enable_anomaly=True)
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "http://www.badip.com/ : "
      "dns_query: ERROR resolver's 1.2.3.4: 127.0.0.1 127.0.0.2 != "
      "127.0.0.1 127.0.0.4"
    )

  def test_https_no_cert(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.sslcertnoinfo.com/',
        'enabled-sense-list': 'ssl_certificate',
      }
    )
    self.runAndAssertFailedMessage(
      "https://www.sslcertnoinfo.com/ : "
      "ssl_certificate: ERROR IP 127.0.0.1 no information"
    )

  def test_dns_query_no_entry(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'http://www.dnsquerynoentry.com/',
        'ip-list': '127.0.0.1',
        'enabled-sense-list': 'dns_query',
      }
    )
    self.runAndAssertFailedMessage(
      "http://www.dnsquerynoentry.com/ : "
      "dns_query: ERROR No data"
    )

  def test_dns_query_no_key(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'http://www.dnsquerynokey.com/',
        'ip-list': '127.0.0.1',
        'enabled-sense-list': 'dns_query',
      }
    )
    self.writeSurykatkaJson({
      "http_query": [
      ],
      "ssl_certificate": [
      ],
      "tcp_server": []
    })
    self.runAndAssertFailedMessage(
      "http://www.dnsquerynokey.com/ : "
      "dns_query: ERROR 'dns_query' not in %(json_file)r" % {
        'json_file': self.json_file}
    )

  def test_dns_query_mismatch(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'http://www.httpallok.com/',
        'ip-list': '127.0.0.1 127.0.0.9',
        'enabled-sense-list': 'dns_query',
      }
    )
    self.runAndAssertFailedMessage(
      "http://www.httpallok.com/ : "
      "dns_query: ERROR resolver's 1.2.3.4: 127.0.0.1 127.0.0.9 != "
      "127.0.0.1 127.0.0.2"
    )

  def test_dns_query_no_reply(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'http://www.dnsquerynoreply.com/',
        'ip-list': '127.0.0.1',
        'enabled-sense-list': 'dns_query',
      }
    )
    self.runAndAssertFailedMessage(
      "http://www.dnsquerynoreply.com/ : "
      "dns_query: ERROR resolver's 1.2.3.4: 127.0.0.1 != empty-reply"
    )

  def test_tcp_server_no_ip(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'http://www.tcpservernoip.com/',
        'status-code': '301',
        'ip-list': '127.0.0.1',
        'enabled-sense-list': 'tcp_server',
      }
    )
    self.runAndAssertFailedMessage(
      "http://www.tcpservernoip.com/ : "
      "tcp_server: ERROR IP 127.0.0.1:80"
    )

  def test_tcp_server_filtered(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'http://www.tcpserverfiltered.com/',
        'ip-list': '127.0.0.1',
        'enabled-sense-list': 'tcp_server',
      }
    )
    self.runAndAssertFailedMessage(
      "http://www.tcpserverfiltered.com/ : "
      "tcp_server: ERROR IP 127.0.0.1:80"
    )

  def test_tcp_server_no_entry(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'http://www.tcpservernoentry.com/',
        'ip-list': '127.0.0.1',
        'enabled-sense-list': 'tcp_server',
      }
    )
    self.runAndAssertFailedMessage(
      "http://www.tcpservernoentry.com/ : "
      "tcp_server: ERROR No data"
    )

  def test_tcp_server_no_key(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'http://www.tcpservernokey.com/',
        'ip-list': '127.0.0.1',
        'enabled-sense-list': 'tcp_server',
      }
    )
    self.writeSurykatkaJson({
      "dns_query": [
      ],
    })
    self.runAndAssertFailedMessage(
      "http://www.tcpservernokey.com/ : "
      "tcp_server: ERROR 'tcp_server' not in %(json_file)r" % {
        'json_file': self.json_file}
    )

  def test_all_ok_nothing_enabled(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.allok.com/',
        'status-code': '302',
        'ip-list': '127.0.0.1 127.0.0.2',
        'maximum-elapsed-time': '5',
        'enabled-sense-list': '',
      }
    )
    self.runAndAssertPassedMessage(
      "https://www.allok.com/ :"
    )

  def test_all_ok_no_ssl_certificate(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.allok.com/',
        'status-code': '302',
        'ip-list': '127.0.0.1 127.0.0.2',
        'maximum-elapsed-time': '5',
        'enabled-sense-list': 'dns_query whois tcp_server http_query '
                              'elapsed_time',
      }
    )
    self.runAndAssertPassedMessage(
      "https://www.allok.com/ : "
      "dns_query: OK resolver's 1.2.3.4: 127.0.0.1 127.0.0.2 "
      "whois: OK allok.com expires in > 30 days "
      "tcp_server: OK IP 127.0.0.1:443 OK IP 127.0.0.2:443 "
      "http_query: OK IP 127.0.0.1 status_code 302 OK IP 127.0.0.2 "
      "status_code 302 "
      "elapsed_time: OK IP 127.0.0.1 replied < 5.00s OK IP 127.0.0.2 replied "
      "< 5.00s"
    )

  def test_all_ok_only_ssl_certificate(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.allok.com/',
        'status-code': '302',
        'ip-list': '127.0.0.1 127.0.0.2',
        'maximum-elapsed-time': '5',
        'enabled-sense-list': 'ssl_certificate',
      }
    )
    self.runAndAssertPassedMessage(
      "https://www.allok.com/ : "
      "ssl_certificate: OK IP 127.0.0.1 expires in > 15 days OK IP "
      "127.0.0.2 expires in > 15 days"
    )

  def test_whois_no_entry(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'http://www.whoisnoentry.com/',
        'ip-list': '127.0.0.1',
        'enabled-sense-list': 'whois',
      }
    )
    self.runAndAssertFailedMessage(
      "http://www.whoisnoentry.com/ : "
      "whois: ERROR No data"
    )

  def test_whois_no_key(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'http://www.whoisnokey.com/',
        'ip-list': '127.0.0.1',
        'enabled-sense-list': 'whois',
      }
    )
    self.writeSurykatkaJson({
      "dns_query": [
      ],
    })
    self.runAndAssertFailedMessage(
      "http://www.whoisnokey.com/ : "
      "whois: ERROR 'whois' not in %(json_file)r" % {
        'json_file': self.json_file}
    )

  def test_whois_expires_2_day(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.whois3.com/',
        'domain-expiration-days': '2',
        'enabled-sense-list': 'whois',
      }
    )
    self.runAndAssertPassedMessage(
      "https://www.whois3.com/ : "
      "whois: OK whois3.com expires in > 2 days"
    )

  def test_whois_expired_expires_2_day(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.whois3.com/',
        'domain-expiration-days': '4',
        'enabled-sense-list': 'whois',
      }
    )
    self.runAndAssertFailedMessage(
      "https://www.whois3.com/ : "
      "whois: ERROR whois3.com expires in < 4 days"
    )

  def test_whois_expired(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.whois29.com/',
        'enabled-sense-list': 'whois',
      }
    )
    self.runAndAssertFailedMessage(
      "https://www.whois29.com/ : "
      "whois: ERROR whois29.com expires in < 30 days"
    )

  def test_whois_expired_before_today(self):
    self.writeSurykatkaPromise(
      {
        'report': 'http_query',
        'json-file': self.json_file,
        'url': 'https://www.whoisminus29.com/',
        'enabled-sense-list': 'whois',
      }
    )
    self.runAndAssertFailedMessage(
      "https://www.whoisminus29.com/ : "
      "whois: ERROR whoisminus29.com expires in < 30 days"
    )
