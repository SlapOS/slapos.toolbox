"""
Some notable parameters:

  promise-timeout:
    Optional timeout (in seconds) for promise.
  timeout:
    Optional timeout (in seconds) for HTTP request.
  verify, ca-cert-file, cert-file, key-file:
    Optional SSL information. (See Python requests documentation.)
  check-secure:
    (default 0) If set, treat a 401 (forbidden) response as a
    success. You probably don't want this if you're specifying a
    username and password.
  http_code:
    (default 200) The expected response HTTP code.
  ignore-code:
    (default 0) Ignore the response HTTP code.
  username, password:
    If supplied, enables basic HTTP authentication.
  require-auth:
    (default 0) If set, check that the server responds with a 401
    when receiving a request with no credentials. (Redundant if
    you don't specify a username and password.)
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

  def log_success(self, url, expected_code=200, authenticated=False):
    if authenticated:
      self.logger.info(("authenticated request to %r was successful "
                        "(returned expected code %d)"), url, expected_code)
    else:
      self.logger.info(("non-authenticated request to %r was successful "
                        "(returned expected code %d)"), url, expected_code)

  def request_and_check_code(self, url, expected_http_code=None, **kwargs):
    """
      Wrapper around GET requests, to make multiple requests easier. If
      no expected code is given, use the http_code configuration
      parameter, finally defaulting to 200.

      Note: if you specify an expected_http_code here, ignore-code is
      automatically overridden.
    """
    if expected_http_code == None:
      expected_http_code = int(self.getConfig('http_code', '200'))
      ignore_code = int(self.getConfig('ignore-code', 0))
    else:
      ignore_code = 0

    if 'auth' in kwargs and kwargs['auth'] != None:
      authenticated = True
    else:
      authenticated = False

    try:
      result = requests.get(url, allow_redirects=True, **kwargs)
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
      # Check that the returned status code is what we expected
      http_code = result.status_code
      check_secure = int(self.getConfig('check-secure', 0))

      if http_code == 401 and check_secure == 1:
        self.log_success(url, authenticated=authenticated,
                         expected_code=401)
      elif not ignore_code and http_code != expected_http_code:
        self.logger.error("%r is not available (returned %s, expected %s).",
                          url, http_code, expected_http_code)
      else:
        self.log_success(url, authenticated=authenticated,
                         expected_code=expected_http_code)

  def sense(self):
    """
      Check if frontend URL is available.
    """

    url = self.getConfig('url')
    # make default time a max of 5 seconds, a bit smaller than promise-timeout
    # and in the same time at least 1 second
    default_timeout = max(
      1, min(5, int(self.getConfig('promise-timeout', 20)) - 1))
    timeout = int(self.getConfig('timeout', default_timeout))
    ca_cert_file = self.getConfig('ca-cert-file')
    cert_file = self.getConfig('cert-file')
    key_file = self.getConfig('key-file')
    verify = int(self.getConfig('verify', 0))
    username = self.getConfig('username')
    password = self.getConfig('password')
    require_auth = int(self.getConfig('require-auth', 0))

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

    self.request_and_check_code(url, verify=verify, timeout=timeout,
                                cert=cert, auth=credentials)

    # If require-auth is set, verify that we get a 401 when requesting
    # without credentials
    if require_auth == 1:
      self.request_and_check_code(url, expected_http_code=401,
                                  verify=verify, timeout=timeout,
                                  cert=cert, auth=None)

  def anomaly(self):
    return self._test(result_count=3, failure_amount=3)
