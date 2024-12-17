from zope.interface import implementer
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise

import subprocess
import os
import psutil

@implementer(interface.IPromise)
class RunPromise(GenericPromise):

  def __init__(self, config):
    super(RunPromise, self).__init__(config)
    # test load every 3 minutes
    self.setPeriodicity(float(self.getConfig('frequency', 3)))

  def checkCPULoad(self, tolerance=2.2):
    # tolerance=1.5 => accept CPU load up to 1.5 =150%
    load, load5, long_load = psutil.getloadavg()
    core_count = psutil.cpu_count()
    max_load = core_count * tolerance
    if long_load > max_load:
      # display top statistics
      top_result = subprocess.check_output(('top', '-n', '1', '-b'),
                                           universal_newlines=True)
      message = "CPU load is high: %s %s %s\n\n" % (load, load5, long_load)
      i = 0
      result_list = top_result.split('\n')
      # display first 5 lines
      while i < len(result_list) and i < 5:
        message += "\n%s" % result_list[i]
        i += 1
      self.logger.error(message)
    else:
      self.logger.info("CPU load is OK")

  def sense(self):
    load_threshold = self.getConfig('cpu-load-threshold')
    threshold = 0

    if load_threshold is not None:
      try:
        threshold = float(load_threshold)
      except ValueError as e:
        self.logger.error("CPU load threshold %r is not valid: %s" % (load_threshold, e))
        return

    self.checkCPULoad(threshold or 2.2)

  def test(self):
    # fail if load is higher than the threshold for more than 30 minutes
    return self._test(result_count=10, failure_amount=10)

  def anomaly(self):
    """
      Anomaly returns a TestResult instead of AnomalyResult because we don't
      want to call bang when there is a problem of load.
      This will need a human intervention to find where the load come from.

      We fail if load is higher than the threshold for more than 30 minutes.
    """
    return self._test(result_count=10, failure_amount=10)
