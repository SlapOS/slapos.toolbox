from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise
from slapos.util import str2bytes
from zope.interface import implementer
import datetime
import base64
import re
import ssl

from pyasn1.codec.der import decoder
from pyasn1_modules import rfc2459


def load_pem_x509_certificate(pem_data):
  """Extracts and decodes the DER bytes from PEM certificate data."""
  pem_body = re.search(
    "-----BEGIN CERTIFICATE-----"
    "(.*?)"
    "-----END CERTIFICATE-----",
    pem_data,
    re.DOTALL,
  )
  if not pem_body:
    raise ValueError("Invalid PEM encoding")
  der_bytes = base64.b64decode(
    "".join(pem_body.group(1).strip().splitlines()))
  return der_bytes


def get_notAfter_from_certificate(der_bytes):
  """Parses DER certificate and extracts the notAfter field."""
  cert, _ = decoder.decode(der_bytes, asn1Spec=rfc2459.Certificate())
  validity = cert['tbsCertificate']['validity']
  not_after_str = str(validity['notAfter'].getComponent())
  dt = datetime.datetime.strptime(not_after_str, '%y%m%d%H%M%SZ')
  return dt


@implementer(interface.IPromise)
class RunPromise(GenericPromise):
  def sense(self):
    """
      Check the certificate
    """

    certificate_file = self.getConfig('certificate')
    key_file = self.getConfig('key', None)

    try:
      certificate_expiration_days = int(
        self.getConfig('certificate-expiration-days', '15'))
    except ValueError:
      self.logger.error('ERROR certificate-expiration-days is wrong: %r' % (
        self.getConfig('certificate-expiration-days')))
      return

    try:
      with open(certificate_file, 'r') as fh:
        pem_content = fh.read()
      der_bytes = load_pem_x509_certificate(pem_content)
      not_after = get_notAfter_from_certificate(der_bytes)
    except Exception as e:
      self.logger.error(
        'ERROR Problem loading certificate %r, error: %s' % (
          certificate_file, e))
      return

    if not_after - datetime.timedelta(
       days=certificate_expiration_days) < datetime.datetime.utcnow():
      self.logger.error(
       'ERROR Certificate %r will expire in less than %s days' % (
         certificate_file, certificate_expiration_days))
      return

    if key_file is not None:
      try:
        ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_ctx.load_cert_chain(certfile=certificate_file, keyfile=key_file)
      except Exception as e:
        if isinstance(e, ssl.SSLError) and e.reason == 'KEY_VALUES_MISMATCH':
          self.logger.error(
            'ERROR Certificate %r does not match key %r' % (
              certificate_file, key_file))
        else:
          self.logger.error(
            'ERROR Problem loading key %r, error: %s' % (key_file, e))
        return

    if key_file:
      self.logger.info(
        'OK Certificate %r and key %r are ok' % (certificate_file, key_file))
    else:
      self.logger.info(
        'OK Certificate %r is ok, no key provided' % (certificate_file,))
