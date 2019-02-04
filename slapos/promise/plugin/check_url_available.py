from zope import interface as zope_interface
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise
import os
import pycurl

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
    curl = pycurl.Curl()
    curl.setopt(pycurl.URL, url)
    curl.setopt(pycurl.TIMEOUT, timeout)
    curl.setopt(pycurl.FOLLOWLOCATION, True)
    curl.setopt(pycurl.SSL_VERIFYPEER, False)
    curl.setopt(pycurl.SSL_VERIFYHOST, False)
    curl.setopt(pycurl.WRITEFUNCTION, lambda x: None)

    ca_cert_file = self.getConfig('ca-cert-file')
    cert_file = self.getConfig('cert-file')
    key_file = self.getConfig('key-file')
    if key_file and cert_file and ca_cert_file:
      # set certificate configuration
      curl.setopt(curl.CAINFO, ca_cert_file)
      curl.setopt(curl.SSLCERT, cert_file)
      curl.setopt(curl.SSLKEY, key_file)

    try:
      curl.perform()
    except pycurl.error, e:
      code, message = e
      self.logger.error("%s: %s" % (code, message))
      return

    http_code = curl.getinfo(pycurl.HTTP_CODE)
    check_secure = self.getConfig('check-secure')
    curl.close()
    
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
