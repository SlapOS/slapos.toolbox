from zope.interface import implementer
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise

try:
  import subprocess32 as subprocess
except ImportError:
  import subprocess

@implementer(interface.IPromise)
class RunPromise(GenericPromise):
  def __init__(self, config):
    super(RunPromise, self).__init__(config)
    self.setPeriodicity(minute=int(self.getConfig('frequency', 5)))

  def sense(self):
    """
      Check trafficserver cache availability
    """
    wrapper = self.getConfig('wrapper-path')

    if 'traffic_line' in wrapper:
      args = [wrapper, '-r',  'proxy.node.cache.percent_free']
      message = "Cache not available, availability:"
    elif 'traffic_ctl' in wrapper:
      args = [wrapper, 'metric', 'get', 'proxy.process.cache.percent_full']
      message = "Cache not available, occupation:"
    else:
      self.logger.error("Wrapper %r not supported." % (wrapper,))
      return

    process = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    result = process.communicate()[0].strip()
    if process.returncode == 0:
      self.logger.info("OK")
    else:
      self.logger.error(message, result)

  def anomaly(self):
    """
      There is an anomaly if last 3 senses were bad.
    """
    return self._anomaly(result_count=3, failure_amount=3)