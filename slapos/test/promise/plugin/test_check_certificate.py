##############################################################################
#
# Copyright (c) 2020 Vifib SARL and Contributors. All Rights Reserved.
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

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from slapos.grid.promise import PromiseError
from slapos.test.promise.plugin import TestPromisePluginMixin
import datetime
import os
import shutil
import tempfile
import unittest
from slapos.util import bytes2str


class TestCheckCertificate(TestPromisePluginMixin):
  same_file = False
  promise_name = 'check-certificate.py'

  def setUp(self):
    super(TestCheckCertificate, self).setUp()
    self.tempdir = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, self.tempdir)
    self.key_path = os.path.join(self.tempdir, 'key.pem')
    if self.same_file:
      self.certificate_path = self.key_path
    else:
      self.certificate_path = os.path.join(self.tempdir, 'certificate.pem')

  def createKey(self):
    key = rsa.generate_private_key(
      public_exponent=65537, key_size=2048, backend=default_backend())
    key_pem = key.private_bytes(
      encoding=serialization.Encoding.PEM,
      format=serialization.PrivateFormat.TraditionalOpenSSL,
      encryption_algorithm=serialization.NoEncryption()
    )
    return key, key_pem

  def createCertificate(self, key, days=30):
    subject = issuer = x509.Name([
      x509.NameAttribute(NameOID.COUNTRY_NAME, u"FR"),
      x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"Nord"),
      x509.NameAttribute(NameOID.LOCALITY_NAME, u"Lille"),
      x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"Nexedi"),
      x509.NameAttribute(NameOID.COMMON_NAME, u"Common"),
    ])
    certificate = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.utcnow()
    ).not_valid_after(
        datetime.datetime.utcnow() + datetime.timedelta(days)
    ).sign(key, hashes.SHA256(), default_backend())
    certificate_pem = certificate.public_bytes(
      encoding=serialization.Encoding.PEM)
    return certificate, certificate_pem

  def createKeyCertificate(self, days=30):
    key, key_pem = self.createKey()
    certificate, certificate_pem = self.createCertificate(key, days)
    with open(self.key_path, 'w') as fh:
      fh.write(bytes2str(key_pem))
    with open(self.certificate_path, 'a') as fh:
      fh.write(bytes2str(certificate_pem))

  def createKeyCertificateNotMatch(self):
    key, key_pem = self.createKey()
    another_key, another_key_pem = self.createKey()
    certificate, certificate_pem = self.createCertificate(key)
    with open(self.key_path, 'w') as fh:
      fh.write(bytes2str(another_key_pem))
    with open(self.certificate_path, 'a') as fh:
      fh.write(bytes2str(certificate_pem))

  def writePromise(self, d=None):
    if d is None:
      d = {}
    content_list = [
      "from slapos.promise.plugin.check_certificate import RunPromise"]
    content_list.append('extra_config_dict = {')
    for k, v in d.items():
      content_list.append("  '%s': '%s'," % (k, v))
    content_list.append('}')
    super(
      TestCheckCertificate, self).writePromise(
        self.promise_name, '\n'.join(content_list))

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

  def test(self):
    self.createKeyCertificate()
    self.writePromise({
      'certificate': self.certificate_path,
      'key': self.key_path
    })
    self.configureLauncher()
    self.launcher.run()
    self.assertPassedMessage(
      self.getPromiseResult(self.promise_name),
      "OK Certificate '%s' and key '%s' are ok" % (
        self.certificate_path, self.key_path)
    )

  def test_no_key(self):
    self.createKeyCertificate()
    nokey_path = os.path.join(self.tempdir, 'nokey.pem')
    self.writePromise({
      'certificate': self.certificate_path,
      'key': nokey_path,
    })
    self.configureLauncher()
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "ERROR Problem loading key '%s', error: [Errno 2] No such file or "
      "directory: '%s'" % (nokey_path, nokey_path))

  def test_no_certificate(self):
    self.createKeyCertificate()
    nocertificate_path = os.path.join(self.tempdir, 'nocertificate.pem')
    self.writePromise({
      'certificate': nocertificate_path,
      'key': self.key_path
    })
    self.configureLauncher()
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "ERROR Problem loading certificate '%s', error: [Errno 2] No such "
      "file or directory: '%s'" % (nocertificate_path, nocertificate_path))

  def test_does_not_match(self):
    self.createKeyCertificateNotMatch()
    self.writePromise({
      'certificate': self.certificate_path,
      'key': self.key_path
    })
    self.configureLauncher()
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "ERROR Certificate '%s' does not match key '%s'" % (
        self.certificate_path, self.key_path)
    )

  def test_expires(self):
    self.createKeyCertificate(days=5)
    self.writePromise({
      'certificate': self.certificate_path,
      'key': self.key_path
    })
    self.configureLauncher()
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "ERROR Certificate '%s' will expire in less than 15 days" % (
        self.certificate_path,)
    )

  def test_expires_custom(self):
    self.createKeyCertificate(days=19)
    self.writePromise({
      'certificate': self.certificate_path,
      'key': self.key_path,
      'certificate-expiration-days': '20'
    })
    self.configureLauncher()
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "ERROR Certificate '%s' will expire in less than 20 days" % (
        self.certificate_path,)
    )

  def test_expires_bad_value(self):
    self.createKeyCertificate(days=14)
    self.writePromise({
      'certificate': self.certificate_path,
      'key': self.key_path,
      'certificate-expiration-days': 'bad'
    })
    self.configureLauncher()
    with self.assertRaises(PromiseError):
      self.launcher.run()
    self.assertFailedMessage(
      self.getPromiseResult(self.promise_name),
      "ERROR certificate-expiration-days is wrong: 'bad'"
    )


class TestCheckCertificateSameFile(TestCheckCertificate):
  same_file = True
  pass


if __name__ == '__main__':
  unittest.main()
