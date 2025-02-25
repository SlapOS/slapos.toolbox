from zope.interface import implementer
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise, TestResult
import re
import time
from slapos.networkbench.ping import ping, ping6

@implementer(interface.IPromise)
class RunPromise(GenericPromise):
  def __init__(self, config):
    super(RunPromise, self).__init__(config)
    # set periodicity to run the promise twice per day
    self.custom_frequency = float(self.getConfig('frequency', 720))
    self.setPeriodicity(self.custom_frequency)
    # Skip test check on this promise
    self.setTestLess()

  def sense(self):
    """
      Check if there ICMP packets lost on given address
    """
    # Address to ping to
    address = self.getConfig('address')
    if not address:
      raise ValueError("'address' was not set in promise parameters.")
    # Force use ipv4 protocol ?
    ipv4 = self.getConfig('ipv4') in ('True', 'true', '1')
    count = int(self.getConfig('count', 10))
    threshold = int(self.getConfig('threshold', 0))
    if threshold < 0:
      raise ValueError("'threshold' value should be greater than 0.")

    if ipv4:
      result = ping(address, count=count)
    else:
      result = ping6(address, count=count)

    message = "%s host=%s code=%s, result=%s, packet_lost_ratio=%s msg=%s" % result
    packet_lost_ratio = int(result[4])
    if packet_lost_ratio == -1 or packet_lost_ratio > threshold:
      # Packet lost occurred
      self.logger.error(message)
    else:
      self.logger.info(message)

  def anomaly(self):
    # only check the result of the two latest sense call
    return self._anomaly(result_count=2, failure_amount=2, latest_minute=self.custom_frequency*3)
