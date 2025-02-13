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
from slapos.util import str2bytes

import contextlib
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from six.moves import BaseHTTPServer
from base64 import b64encode
import datetime
import ipaddress
import json
import multiprocessing
import os
import six
import socket
import ssl
import tempfile
import time
import unittest

SLAPOS_TEST_IPV4 = os.environ.get('SLAPOS_TEST_IPV4', '127.0.0.1')
SLAPOS_TEST_IPV4_PORT = 57965
HTTPS_ENDPOINT = "https://%s:%s/" % (SLAPOS_TEST_IPV4, SLAPOS_TEST_IPV4_PORT)

# Good and bad username/password for HTTP authentication tests.
TEST_GOOD_USERNAME = 'good username'
TEST_GOOD_PASSWORD = 'good password'
TEST_BAD_USERNAME = 'bad username'
TEST_BAD_PASSWORD = 'bad password'

def createKey():
  key = rsa.generate_private_key(
    public_exponent=65537, key_size=2048, backend=default_backend())
  key_pem = key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.TraditionalOpenSSL,
    encryption_algorithm=serialization.NoEncryption()
  )
  return key, key_pem


def createCSR(common_name, ip=None):
  key, key_pem = createKey()
  subject_alternative_name_list = []
  if ip is not None:
    subject_alternative_name_list.append(
      x509.IPAddress(ipaddress.ip_address(ip))
    )
  csr = x509.CertificateSigningRequestBuilder().subject_name(x509.Name([
     x509.NameAttribute(NameOID.COMMON_NAME, common_name),
  ]))

  if len(subject_alternative_name_list):
    csr = csr.add_extension(
      x509.SubjectAlternativeName(subject_alternative_name_list),
      critical=False
    )

  csr = csr.sign(key, hashes.SHA256(), default_backend())
  csr_pem = csr.public_bytes(serialization.Encoding.PEM)
  return key, key_pem, csr, csr_pem


class CertificateAuthority(object):
  def __init__(self, common_name):
    self.key, self.key_pem = createKey()
    public_key = self.key.public_key()
    builder = x509.CertificateBuilder()
    builder = builder.subject_name(x509.Name([
      x509.NameAttribute(NameOID.COMMON_NAME, common_name),
    ]))
    builder = builder.issuer_name(x509.Name([
      x509.NameAttribute(NameOID.COMMON_NAME, common_name),
    ]))
    builder = builder.not_valid_before(
      datetime.datetime.utcnow() - datetime.timedelta(days=2))
    builder = builder.not_valid_after(
      datetime.datetime.utcnow() + datetime.timedelta(days=30))
    builder = builder.serial_number(x509.random_serial_number())
    builder = builder.public_key(public_key)
    builder = builder.add_extension(
      x509.BasicConstraints(ca=True, path_length=None), critical=True,
    )
    self.certificate = builder.sign(
      private_key=self.key, algorithm=hashes.SHA256(),
      backend=default_backend()
    )
    self.certificate_pem = self.certificate.public_bytes(
      serialization.Encoding.PEM)

  def signCSR(self, csr):
    builder = x509.CertificateBuilder(
      subject_name=csr.subject,
      extensions=csr.extensions,
      issuer_name=self.certificate.subject,
      not_valid_before=datetime.datetime.utcnow() - datetime.timedelta(days=1),
      not_valid_after=datetime.datetime.utcnow() + datetime.timedelta(days=30),
      serial_number=x509.random_serial_number(),
      public_key=csr.public_key(),
    )
    certificate = builder.sign(
      private_key=self.key,
      algorithm=hashes.SHA256(),
      backend=default_backend()
    )
    return certificate, certificate.public_bytes(serialization.Encoding.PEM)


class TestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
  def do_GET(self):
    """
    Respond to a GET request. You can configure the response as follows:
      - Specify the response code in the URL, e.g. /200
      - Optionally, use an underscore to specify a timeout (in seconds)
        to wait before responding, e.g. /200_5
      - Optionally, use an exclamation mark to require HTTP basic
        authentication, using the credentials TEST_GOOD_USERNAME and
        TEST_GOOD_PASSWORD defined at the top of this file, e.g. /!200
        or /!200_5.
    """
    path = self.path.split('/')[-1]

    if path[0] == '!':
      require_auth = True
      path = path[1:]
    else:
      require_auth = False

    if '_' in path:
      response, timeout = path.split('_')
      response = int(response)
      timeout = int(timeout)
    else:
      timeout = 0
      response = int(path)

    key = b64encode(('%s:%s' % (TEST_GOOD_USERNAME,
                                TEST_GOOD_PASSWORD)).encode()).decode()
    try:
      authorization = self.headers['Authorization']
    except KeyError:
      authorization = None

    time.sleep(timeout)
    if require_auth and authorization != 'Basic ' + key:
      self.send_response(401)
      self.send_header('WWW-Authenticate', 'Basic realm="test"')
      self.end_headers()
      self.wfile.write('bad credentials\n'.encode())
    else:
      self.send_response(response)

      self.send_header("Content-type", "application/json")
      self.end_headers()
      response = {
        'Path': self.path,
      }
      self.wfile.write(str2bytes(json.dumps(response, indent=2)))


class CheckUrlAvailableMixin(TestPromisePluginMixin):
  RequestHandler = TestHandler
  @classmethod
  def setUpClass(cls):
    cls.another_server_ca = CertificateAuthority(u"Another Server Root CA")
    cls.test_server_ca = CertificateAuthority(u"Test Server Root CA")
    ip = SLAPOS_TEST_IPV4.decode('utf-8') \
         if isinstance(SLAPOS_TEST_IPV4, bytes) \
         else SLAPOS_TEST_IPV4
    key, key_pem, csr, csr_pem = createCSR(
      u"testserver.example.com", ip)
    _, cls.test_server_certificate_pem = cls.test_server_ca.signCSR(csr)

    cls.test_server_certificate_file = tempfile.NamedTemporaryFile(
      delete=False
    )

    cls.test_server_certificate_file.write(
        cls.test_server_certificate_pem + key_pem
      )
    cls.test_server_certificate_file.close()

    cls.test_server_ca_certificate_file = tempfile.NamedTemporaryFile(
      delete=False
    )
    cls.test_server_ca_certificate_file.write(
       cls.test_server_ca.certificate_pem)
    cls.test_server_ca_certificate_file.close()

    def server():
      server = BaseHTTPServer.HTTPServer(
        (SLAPOS_TEST_IPV4, SLAPOS_TEST_IPV4_PORT),
        cls.RequestHandler)
      context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
      context.load_cert_chain(certfile=cls.test_server_certificate_file.name)
      server.socket = context.wrap_socket(server.socket, server_side=True)
      server.serve_forever()

    cls.server_process = multiprocessing.Process(target=server)
    cls.server_process.start()
    for _ in range(20):
      try:
        with contextlib.closing(socket.create_connection((SLAPOS_TEST_IPV4, SLAPOS_TEST_IPV4_PORT))):
          break
      except Exception:
        time.sleep(.1)

  @classmethod
  def tearDownClass(cls):
    cls.server_process.terminate()
    cls.server_process.join()
    for p in [
      cls.test_server_certificate_file.name,
      cls.test_server_ca_certificate_file.name,
    ]:
      try:
        os.unlink(p)
      except Exception:
        pass

  def setUp(self):
    TestPromisePluginMixin.setUp(self)
    self.promise_name = "check-url-available.py"

    self.success_template = \
      ("non-authenticated request to %r succeeded "
       "(returned expected code %d)")
    self.authenticated_success_template = \
      ("authenticated request to %r succeeded "
       "(returned expected code %d)")
    self.ignored_success_template = \
      ("non-authenticated request to %r succeeded "
       "(return code ignored)")
    self.authenticated_ignored_success_template = \
      ("authenticated request to %r succeeded "
       "(return code ignored)")

  def make_content(self, option_dict):
    content = """from slapos.promise.plugin.check_url_available import RunPromise

extra_config_dict = {
"""
    for option in option_dict.items():
      content += "\n  '%s': %r," % option

    return content + "\n}"

  def tearDown(self):
    TestPromisePluginMixin.tearDown(self)


class TestCheckUrlAvailable(CheckUrlAvailableMixin):

  def test_check_url_bad(self):
    content = self.make_content({
      'url': 'https://',
      'timeout': 10,
      'ignore-code': 0,
    })
    self.writePromise(self.promise_name, content)
    self.configureLauncher()
    with self.assertRaises(PromiseError):
      self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], True)
    self.assertEqual(
      result['result']['message'],
      "ERROR: Invalid URL %s'https://': No host supplied" %
        ('' if six.PY3 else 'u')
    )

  def test_check_url_malformed(self):
    content = self.make_content({
      'url': '',
      'timeout': 10,
      'ignore-code': 0,
    })
    self.writePromise(self.promise_name, content)
    self.configureLauncher()
    with self.assertRaises(PromiseError):
      self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], True)
    self.assertIn(
      result['result']['message'],
      ("ERROR: Invalid URL '': No scheme supplied. Perhaps you meant https://?",
      # BBB requests < 2.28.2
       "ERROR: Invalid URL '': No scheme supplied. Perhaps you meant http://?")
    )

  def test_check_url_site_off(self):
    content = self.make_content({
      'url': 'https://localhost:56789/site',
      'timeout': 10,
      'ignore-code': 0,
    })
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
    content = self.make_content({
      'url': url,
      'timeout': 10,
      'ignore-code': 0,
    })
    self.writePromise(self.promise_name, content)
    self.configureLauncher()
    self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], False)
    self.assertEqual(
      result['result']['message'],
      self.success_template % (url, 200)
    )

  def test_check_200_verify(self):
    url = HTTPS_ENDPOINT + '200'
    content = self.make_content({
      'url': url,
      'timeout': 10,
      'ignore-code': 0,
      'verify': 1,
    })
    try:
      old = os.environ.get('REQUESTS_CA_BUNDLE')
      # simulate system provided CA bundle
      os.environ[
        'REQUESTS_CA_BUNDLE'] = self.test_server_ca_certificate_file.name
      self.writePromise(self.promise_name, content)
      self.configureLauncher()
      self.launcher.run()
    finally:
      if old is None:
        del os.environ['REQUESTS_CA_BUNDLE']
      else:
        os.environ['REQUESTS_CA_BUNDLE'] = old

    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], False)
    self.assertEqual(
      result['result']['message'],
      self.success_template % (url, 200)
    )

  def test_check_200_verify_fail(self):
    url = HTTPS_ENDPOINT + '200'
    content = self.make_content({
      'url': url,
      'timeout': 10,
      'ignore-code': 0,
      'verify': 1,
    })
    self.writePromise(self.promise_name, content)
    self.configureLauncher()
    with self.assertRaises(PromiseError):
      self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], True)
    self.assertEqual(
      result['result']['message'],
      "ERROR SSL verify failed while accessing %r" % (url,)
    )

  def test_check_200_verify_own(self):
    url = HTTPS_ENDPOINT + '200'
    content = self.make_content({
      'url': url,
      'timeout': 10,
      'ignore-code': 0,
      'ca-cert-file': self.test_server_ca_certificate_file.name
    })
    self.writePromise(self.promise_name, content)
    self.configureLauncher()
    self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], False)
    self.assertEqual(
      result['result']['message'],
      self.success_template % (url, 200)
    )

  def test_check_401(self):
    url = HTTPS_ENDPOINT + '401'
    content = self.make_content({
      'url': url,
      'timeout': 10,
      'ignore-code': 0,
    })
    self.writePromise(self.promise_name, content)
    self.configureLauncher()
    with self.assertRaises(PromiseError):
      self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], True)
    self.assertEqual(
      result['result']['message'],
      ("non-authenticated request to %r failed "
       "(returned 401, expected 200)") % (url,)
    )

  def test_check_401_ignore_code(self):
    url = HTTPS_ENDPOINT + '401'
    content = self.make_content({
      'url': url,
      'timeout': 10,
      'ignore-code': 1,
    })
    self.writePromise(self.promise_name, content)
    self.configureLauncher()
    self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], False)
    self.assertEqual(
      result['result']['message'],
      self.ignored_success_template % (url,)
    )

  def test_check_512_http_code(self):
    url = HTTPS_ENDPOINT + '512'
    content = self.make_content({
      'url': url,
      'timeout': 10,
      'ignore-code': 0,
      'http-code': 512,
    })
    self.writePromise(self.promise_name, content)
    self.configureLauncher()
    self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], False)
    self.assertEqual(
      result['result']['message'],
      self.success_template % (url, 512)
    )

  # Test bad HTTP code.
  def test_check_bad_http_code(self):
    url = HTTPS_ENDPOINT + '412'
    content = self.make_content({
      'url': url,
      'timeout': 10,
      'ignore-code': 0,
      'http-code': 732,
    })
    self.writePromise(self.promise_name, content)
    self.configureLauncher()
    with self.assertRaises(PromiseError):
      self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], True)
    self.assertEqual(
      result['result']['message'],
      ("non-authenticated request to %r failed "
       "(returned 412, expected 732)") % (url,)
    )

  # Test normal authentication success.
  def test_check_authenticate_success(self):
    url = HTTPS_ENDPOINT + '!200'
    content = self.make_content({
      'url': url,
      'username': TEST_GOOD_USERNAME,
      'password': TEST_GOOD_PASSWORD,
    })
    self.writePromise(self.promise_name, content)
    self.configureLauncher()
    self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], False)
    self.assertEqual(
      result['result']['message'],
      self.authenticated_success_template % (url, 200)
    )

  # Test that supplying a username/password still succeeds when the
  # server doesn't require them.
  def test_check_authenticate_no_password_needed(self):
    url = HTTPS_ENDPOINT + '200'
    content = self.make_content({
      'url': url,
      'username': TEST_GOOD_USERNAME,
      'password': TEST_GOOD_PASSWORD,
    })
    self.writePromise(self.promise_name, content)
    self.configureLauncher()
    self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], False)
    self.assertEqual(
      result['result']['message'],
      self.authenticated_success_template % (url, 200)
    )

  # Test authentication failure due to bad password.
  def test_check_authenticate_bad_password(self):
    url = HTTPS_ENDPOINT + '!200'
    content = self.make_content({
      'url': url,
      'username': TEST_BAD_USERNAME,
      'password': TEST_BAD_PASSWORD,
    })
    self.writePromise(self.promise_name, content)
    self.configureLauncher()
    with self.assertRaises(PromiseError):
      self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], True)
    self.assertEqual(
      result['result']['message'],
      ("authenticated request to %r failed "
       "(returned 401, expected 200)") % (url,)
    )

  # Test authentication failure due to no password being given to a
  # protected server.
  def test_check_authenticate_no_password_given(self):
    url = HTTPS_ENDPOINT + '!200'
    content = self.make_content({
      'url': url,
    })
    self.writePromise(self.promise_name, content)
    self.configureLauncher()
    with self.assertRaises(PromiseError):
      self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], True)
    self.assertEqual(
      result['result']['message'],
      ("non-authenticated request to %r failed "
       "(returned 401, expected 200)") % (url,)
    )

  # Test that authentication and HTTP code can be used together.
  def test_check_authenticate_http_code(self):
    url = HTTPS_ENDPOINT + '!412'
    content = self.make_content({
      'url': url,
      'username': TEST_GOOD_USERNAME,
      'password': TEST_GOOD_PASSWORD,
      'http-code': 412
    })
    self.writePromise(self.promise_name, content)
    self.configureLauncher()
    self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], False)
    self.assertEqual(
      result['result']['message'],
      self.authenticated_success_template % (url, 412)
    )

  # Test that authentication and igore-code can be used together.
  def test_check_authenticate_ignore_code(self):
    url = HTTPS_ENDPOINT + '!404'
    content = self.make_content({
      'url': url,
      'username': TEST_GOOD_USERNAME,
      'password': TEST_GOOD_PASSWORD,
      'ignore-code': 1
    })
    self.writePromise(self.promise_name, content)
    self.configureLauncher()
    self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], False)
    self.assertEqual(
      result['result']['message'],
      self.authenticated_ignored_success_template % (url,)
    )

class TestCheckUrlAvailableTimeout(CheckUrlAvailableMixin):
  def test_check_200_timeout(self):
    url = HTTPS_ENDPOINT + '200_5'
    content = self.make_content({
      'url': url,
      'timeout': 1,
      'ignore-code': 0,
    })
    self.writePromise(self.promise_name, content)
    self.configureLauncher()
    with self.assertRaises(PromiseError):
      self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], True)
    self.assertEqual(
      result['result']['message'],
      "Error: Promise timed out after 0.5 seconds",
    )


class TestCheckUrlAvailableRedirect(CheckUrlAvailableMixin):
  class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_GET(self):
      if self.path == '/':
        self.send_response(302)
        self.send_header('Location', '/redirected')
        self.end_headers()
        self.wfile.write(b'see /redirected')
      elif self.path == '/redirected':
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'OK')
      else:
        self.send_response(400)
        self.end_headers()
        self.wfile.write(b'Unexepected path: ' + self.path.encode())

  def test_check_redirected_follow_redirect(self):
    url = HTTPS_ENDPOINT
    content = self.make_content({
      'url': url,
      'http-code': '200',
    })
    self.writePromise(self.promise_name, content)
    self.configureLauncher()
    self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], False)
    self.assertEqual(
      result['result']['message'],
      self.success_template % (url, 200)
    )

  def test_check_redirected_not_follow_redirect(self):
    url = HTTPS_ENDPOINT
    content = self.make_content({
      'url': url,
      'allow-redirects': '0',
      'http-code': '302',
    })
    self.writePromise(self.promise_name, content)
    self.configureLauncher()
    self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], False)
    self.assertEqual(
      result['result']['message'],
      self.success_template % (url, 302)
    )


if __name__ == '__main__':
  unittest.main()
