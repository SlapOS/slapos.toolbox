from zope import interface as zope_interface
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise

import socket
import sys

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
    hostname = self.getConfig('hostname')
    port = self.getConfig('port')

    addr = (hostname , port)
    try:
      socket.create_connection(addr).close()
    except (socket.herror, socket.gaierror), e:
      self.logger.error("hostname/port ({}) is not correct: {}".format(addr, e))
    except (socket.error, socket.timeout), e:
      self.logger.error("ERROR while connecting to {}: {}".format(addr, e))
    else:
      self.logger.info("port connection OK ({})".format(addr))

  def test(self):
    """
      Test is failing if last sense was bad.
    """
    return self._test(result_count=1, failure_amount=1)

  def anomaly(self):
    """
      There is an anomaly if last 3 senses were bad.
    """
    return self._test(result_count=3, failure_amount=3)
