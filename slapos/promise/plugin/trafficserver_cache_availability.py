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
      message = "Cache not available, availability: %s"
    elif 'traffic_ctl' in wrapper:
      args = [wrapper, 'metric', 'get', 'proxy.process.cache.percent_full']
      message = "Cache not available, occupation: %s"
    else:
      self.logger.error("Wrapper %r not supported." % (wrapper,))
      return

    try:
      subprocess.check_output(args, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
      result = e.output.strip()
      self.logger.error(message, result if str is bytes else
                                 result.decode('utf-8', 'replace'))
    else:
      self.logger.info("OK")

  def anomaly(self):
    """
      There is an anomaly if last 3 senses were bad.
    """
    return self._anomaly(result_count=3, failure_amount=3)