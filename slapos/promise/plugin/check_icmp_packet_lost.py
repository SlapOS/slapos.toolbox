from zope import interface as zope_interface
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise
import re
import time
from slapos.networkbench.ping import ping, ping6

class RunPromise(GenericPromise):

  zope_interface.implements(interface.IPromise)

  def __init__(self, config):
    GenericPromise.__init__(self, config)
    # set periodicity to run the promise twice per day
    self.custom_frequency = 720
    self.setPeriodicity(self.custom_frequency)

  def sense(self):
    """
      Check if frontend URL is available
    """
    # Address to ping to
    address = self.getConfig('address')
    if not address:
      raise ValueError("'address' was not set in promise parameters.")
    # Force use ipv4 protocol ?
    ipv4 = self.getConfig('ipv4') in ('True', 'true', '1')
    count = self.getConfig('count', 10)

    if ipv4:
      result = ping(address, count=count)
    else:
      result = ping6(address, count=count)

    message = "%s host=%s code=%s, result=%s, packet_lost_ratio=%s msg=%s" % result
    if result[4] != "0":
      # Packet lost occurred
      self.logger.error(message)
    else:
      self.logger.info(message)

  def anomaly(self):
    # only check the result of the two latest sense call
    return self._test(result_count=2, failure_amount=2, latest_minute=self.custom_frequency*3)
