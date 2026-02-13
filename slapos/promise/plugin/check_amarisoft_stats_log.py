import time

from .util import get_json_log_latest_timestamp

from zope.interface import implementer
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise

@implementer(interface.IPromise)
class RunPromise(GenericPromise):

  def __init__(self, config):

    super(RunPromise, self).__init__(config)
    self.setPeriodicity(float(self.getConfig('frequency', 1)))
    self.amarisoft_stats_log = self.getConfig('amarisoft-stats-log')
    self.stats_period = int(self.getConfig('stats-period'))

  def sense(self):

    latest_timestamp = get_json_log_latest_timestamp(self.amarisoft_stats_log)
    delta = time.time() - latest_timestamp
    if delta > self.stats_period * 2:
        self.logger.error("Latest entry from amarisoft statistics log is more"\
                          "than %s seconds old" % (self.stats_period * 2,))
    else:
        self.logger.info("Latest entry from amarisoft statistics is less"\
                          "than %s seconds old" % (self.stats_period * 2,))

  def test(self):
    """
      Called after sense() if the instance is still converging.
      Returns success or failure based on sense results.

      In this case, fail if the previous sensor result is negative.
    """
    return self._test(result_count=1, failure_amount=1)

  def anomaly(self):
    """
      Called after sense() if the instance has finished converging.
      Returns success or failure based on sense results.
      Failure signals the instance has diverged.

      In this case, fail if two out of the last three results are negative.
    """
    return self._anomaly(result_count=1, failure_amount=1)
