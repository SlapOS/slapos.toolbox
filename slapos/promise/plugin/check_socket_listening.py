from zope.interface import implementer
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise

import socket

ADDRESS_USAGE = (
  "Address must be specified in 1 of the following 3 forms:"
  " (host, port), path or abstract")

@implementer(interface.IPromise)
class RunPromise(GenericPromise):
  def __init__(self, config):
    super(RunPromise, self).__init__(config)
    self.setPeriodicity(float(self.getConfig('frequency', 2)))
    self.result_count = int(self.getConfig('result-count', 3))
    self.failure_amount = int(self.getConfig('failure-amount', 3))


  def sense(self):
    """
      Check the state of a socket.
    """
    host = self.getConfig('host')
    port = self.getConfig('port')
    path = self.getConfig('pathname')
    abstract = self.getConfig('abstract')

    if host:
      if path or abstract or not port:
        self.logger.error(ADDRESS_USAGE)
        return
      # type of port must be int or str, unicode is not accepted.
      family, _, _, _, addr = socket.getaddrinfo(host, int(port))[0]
    else:
      if bool(path) == bool(abstract):
        self.logger.error(ADDRESS_USAGE)
        return
      family = socket.AF_UNIX
      addr = path or '\0' + abstract

    s = socket.socket(family, socket.SOCK_STREAM)
    try:
      s.connect(addr)
    except socket.error as e:
      self.logger.error('%s: %s', type(e).__name__, e)
    else:
      self.logger.info("socket connection OK %r", addr)
    finally:
      s.close()


  def anomaly(self):
    """
      By default, there is an anomaly if last 3 senses were bad.
    """
    return self._anomaly(result_count=self.result_count, failure_amount=self.failure_amount)
