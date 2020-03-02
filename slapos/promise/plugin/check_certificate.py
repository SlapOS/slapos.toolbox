from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise
from slapos.util import str2bytes
from zope.interface import implementer
import datetime


@implementer(interface.IPromise)
class RunPromise(GenericPromise):
  def sense(self):
    """
      Check the certificate
    """

    certificate_file = self.getConfig('certificate')
    key_file = self.getConfig('key')

    try:
      certificate_expiration_days = int(
        self.getConfig('certificate-expiration-days', '15'))
    except ValueError:
      self.logger.error('ERROR certificate-expiration-days is wrong: %r' % (
        self.getConfig('certificate-expiration-days')))
      return

    try:
      with open(certificate_file, 'r') as fh:
        certificate = x509.load_pem_x509_certificate(
          str2bytes(fh.read()), default_backend())
    except Exception as e:
      self.logger.error(
        'ERROR Problem loading certificate %r, error: %s' % (
          certificate_file, e))
      return

    try:
      with open(key_file, 'r') as fh:
        key = serialization.load_pem_private_key(
          str2bytes(fh.read()), None, default_backend())
    except Exception as e:
      self.logger.error(
        'ERROR Problem loading key %r, error: %s' % (key_file, e))
      return

    if certificate.public_key().public_numbers() != \
       key.public_key().public_numbers():
      self.logger.error(
        'ERROR Certificate %r does not match key %r' % (
          certificate_file, key_file))
      return

    if certificate.not_valid_after - datetime.timedelta(
       days=certificate_expiration_days) < datetime.datetime.utcnow():
      self.logger.error(
       'ERROR Certificate %r will expire in less than %s days' % (
         certificate_file, certificate_expiration_days))
      return

    self.logger.info(
      'OK Certificate %r and key %r are ok' % (certificate_file, key_file))
