from zope import interface as zope_interface
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise

import requests


class RunPromise(GenericPromise):

  zope_interface.implements(interface.IPromise)

  def __init__(self, config):
    GenericPromise.__init__(self, config)
    self.setPeriodicity(minute=2)

  def sense(self):
    """
      Test HTTP access to the url

      Anything HTTP style is considered ok, no enforcements of the status code.

      ssl-proxy-verify with ssl-proxy-ca-crt-file can be used to validate
      the endpoint SSL certificate.
    """
    url = self.getConfig('url')
    verify = self.getConfig('ssl-proxy-verify', '').lower() == 'true'
    verify_cert = self.getConfig('ssl-proxy-ca-crt-file')
    timeout = int(self.getConfig('timeout', '5'))

    if verify and len(verify_cert):
      verify = verify_cert
    try:
      requests.get(url, verify=verify, timeout=timeout, allow_redirects=False)
    except requests.ConnectionError as e:
      self.logger.error(
        "ERROR connection not possible while accessing url {}".format(url))
    except Exception as e:
      self.logger.error(
        "ERROR '{}' while accessing url {}".format(e, url))
    else:
      self.logger.info("url {} OK".format(url))

  def anomaly(self):
    """
      There is an anomaly if last 3 senses were bad.
    """
    return self._anomaly(result_count=3, failure_amount=3)
