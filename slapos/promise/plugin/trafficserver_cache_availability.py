from zope import interface as zope_interface
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise

try:
  import subprocess32 as subprocess
except ImportError:
  import subprocess

class RunPromise(GenericPromise):

  zope_interface.implements(interface.IPromise)

  def __init__(self, config):
    GenericPromise.__init__(self, config)
    self.setPeriodicity(minute=int(self.getConfig('frequency', 5)))

  def sense(self):
    """
      Check trafficserver cache availability
    """
    traffic_line = self.getConfig('wrapper-path')

    process = subprocess.Popen(
        [traffic_line, '-r',  'proxy.node.cache.percent_free'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    result = process.communicate()[0].strip()
    if process.returncode == 0:
      self.logger.info("OK")
    else:
      self.logger.error("Cache not available, availability: %s" % result)

  def anomaly(self):
    """
      There is an anomaly if last 3 senses were bad.
    """
    return self._anomaly(result_count=3, failure_amount=3)