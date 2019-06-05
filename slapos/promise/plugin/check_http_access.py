from zope import interface as zope_interface
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise

import requests


class RunPromise(GenericPromise):

  zope_interface.implements(interface.IPromise)

  def __init__(self, config):
    GenericPromise.__init__(self, config)
    # check port is listening at least every 2 minutes
    self.setPeriodicity(minute=2)

  def sense(self):
    """
      Simply test if we can connect to specified host:port.
    """
    url = self.getConfig('url')
    verify = self.getConfig('ssl-proxy-verify').lower() == 'true'
    verify_cert = self.getConfig('ssl-proxy-ca-crt-file')
    timeout = int(self.getConfig('timeout', '5'))

    if verify and len(verify_cert):
      verify = verify_cert
    try:
      requests.get(url, verify=verify, timeout=timeout)
    except Exception as e:
      self.logger.error(
        "ERROR {} while accessing url {} with verify {} and verify_cert {} "
        "with timeout {}".format(e, url, verify, verify_cert, timeout))
    else:
      self.logger.info("url {} OK".format(url))

  def anomaly(self):
    """
      There is an anomaly if last 3 senses were bad.
    """
    return self._anomaly(result_count=3, failure_amount=3)
