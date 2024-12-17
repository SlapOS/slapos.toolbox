"""
Some notable parameters:

  promise-timeout:
    Optional timeout (in seconds) for promise.
  timeout:
    Optional timeout (in seconds) for HTTP request.
  verify, ca-cert-file, cert-file, key-file:
    Optional SSL information. (See Python requests documentation.)
  http-code:
    (default 200) The expected response HTTP code.
  ignore-code:
    (default 0) If set to 1, ignore the response HTTP code.
  allow-redirects:
    (default 1) If set to 1, follow Location header on HTTP redirect status code.
    If set to 0, does not follow and use the redirect response.
  username, password:
    If supplied, enables basic HTTP authentication.
"""

from zope.interface import implementer
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise

import requests


@implementer(interface.IPromise)
class RunPromise(GenericPromise):
  def __init__(self, config):
    super(RunPromise, self).__init__(config)
    # SR can set custom periodicity
    self.setPeriodicity(float(self.getConfig('frequency', 2)))

  def sense(self):
    """
      Check if frontend URL is available.
    """

    url = self.getConfig('url')
    # make default time a max of 5 seconds, a bit smaller than promise-timeout
    # and in the same time at least 1 second
    default_timeout = max(
      1, min(5, int(self.getConfig('promise-timeout', 20)) - 1))
    expected_http_code = int(self.getConfig('http-code', 200))
    ca_cert_file = self.getConfig('ca-cert-file')
    cert_file = self.getConfig('cert-file')
    key_file = self.getConfig('key-file')
    verify = int(self.getConfig('verify', 0))
    username = self.getConfig('username')
    password = self.getConfig('password')

    if int(self.getConfig('ignore-code', 0)) == 1:
      ignore_code = True
    else:
      ignore_code = False

    if ca_cert_file:
      verify = ca_cert_file
    elif verify:
      verify = True
    else:
      verify = False

    if key_file and cert_file:
      cert = (cert_file, key_file)
    else:
      cert = None

    if username and password:
      credentials = (username, password)
      request_type = "authenticated"
    else:
      credentials = None
      request_type = "non-authenticated"

    request_options = {
      'allow_redirects': bool(int(self.getConfig('allow-redirects', 1))),
      'timeout': int(self.getConfig('timeout', default_timeout)),
      'verify': verify,
      'cert': cert,
      'auth': credentials,
    }

    try:
      response = requests.get(url, **request_options)
    except requests.exceptions.SSLError as e:
      if 'certificate verify failed' in str(e):
        self.logger.error(
          "ERROR SSL verify failed while accessing %r", url)
      else:
        self.logger.error(
          "ERROR Unknown SSL error %r while accessing %r", e, url)
    except requests.ConnectionError as e:
      self.logger.error(
        "ERROR connection not possible while accessing %r", url)
    except Exception as e:
      self.logger.error("ERROR: %s", e)

    else:
      # Log a sensible message, depending on the request/response
      # parameters.
      if ignore_code:
        log = self.logger.info
        result = "succeeded"
        message = "return code ignored"
      elif response.status_code == expected_http_code:
        log = self.logger.info
        result = "succeeded"
        message = "returned expected code %d" % expected_http_code
      else:
        log = self.logger.error
        result = "failed"
        message = "returned %d, expected %d" % (response.status_code,
                                                expected_http_code)

      log("%s request to %r %s (%s)", request_type, url, result, message)

  def anomaly(self):
    return self._anomaly(result_count=3, failure_amount=3)
