from zope import interface as zope_interface
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise
import os
import requests

class RunPromise(GenericPromise):

  zope_interface.implements(interface.IPromise)

  def __init__(self, config):
    GenericPromise.__init__(self, config)
    # SR can set custom periodicity
    self.setPeriodicity(float(self.getConfig('frequency', 2)))

  def sense(self):
    """
      Check if frontend URL is available
    """

    url = self.getConfig('url')
    timeout = int(self.getConfig('timeout', 20))
    expected_http_code = int(self.getConfig('http_code', '200'))
    ca_cert_file = self.getConfig('ca-cert-file')
    cert_file = self.getConfig('cert-file')
    key_file = self.getConfig('key-file')

    if ca_cert_file:
      verify = ca_cert_file
    else:
      verify = False

    if key_file and cert_file:
      cert = (cert_file, key_file)
    else:
      cert = None

    try:
      result = requests.get(url, verify=verify, allow_redirects=True, timeout=timeout, cert=cert)
    except requests.ConnectionError as e:
      self.logger.error(
        "ERROR connection not possible while accessing %r" % (url, ))
      return
    except Exception, e:
      self.logger.error("ERROR: %s" % (e,))
      return

    http_code = result.status_code
    check_secure = self.getConfig('check-secure')
    
    if http_code == 0:
      self.logger.error("%s is not available (server not reachable)." % url)
    elif http_code == 401 and check_secure == "1":
      self.logger.info("%s is protected (returned %s)." % (url, http_code))

    elif http_code != expected_http_code:
      self.logger.error("%s is not available (returned %s, expected %s)." % (
        url, http_code, expected_http_code))
    else:
      self.logger.info("%s: URL is available" % http_code)

  def anomaly(self):
    return self._test(result_count=3, failure_amount=3)
