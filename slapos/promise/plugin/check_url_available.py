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

  def log_success(self, url, authenticated=True, http_code=200,
                  ignore_code=False):
    """
    Log a sensible success message, depending on the request parameters.
    """
    if authenticated:
      request_type = "authenticated"
    else:
      request_type = "non-authenticated"

    if ignore_code:
      message = "return code ignored"
    else:
      message = "returned expected code %d" % http_code

    self.logger.info("%s request to %r was successful (%s)",
                     request_type, url, message)

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
    else:
      credentials = None

    request_options = {
      'allow_redirects': True,
      'timeout': int(self.getConfig('timeout', default_timeout)),
      'verify': verify,
      'cert': cert,
      'auth': credentials,
    }

    try:
      result = requests.get(url, **request_options)
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
      if not ignore_code and result.status_code != expected_http_code:
        self.logger.error("%r is not available (returned %s, expected %s).",
                          url, result.status_code, expected_http_code)
      else:
        self.log_success(url, authenticated=(credentials != None),
                         http_code=result.status_code,
                         ignore_code=ignore_code)

  def anomaly(self):
    return self._test(result_count=3, failure_amount=3)
