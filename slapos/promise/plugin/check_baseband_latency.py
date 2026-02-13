from .util import get_json_log_data_interval
from .util import JSONPromise

from zope.interface import implementer
from slapos.grid.promise import interface

@implementer(interface.IPromise)
class RunPromise(JSONPromise):
  def __init__(self, config):
    super(RunPromise, self).__init__(config)
    self.setPeriodicity(float(self.getConfig('frequency', 1)))
    self.amarisoft_stats_log = self.getConfig('amarisoft-stats-log')
    self.stats_period = int(self.getConfig('stats-period'))
    self.min_rxtx_delay_threshold = float(self.getConfig('min-rxtx-delay', 0))
    self.testing = self.getConfig('testing') == "True"

  def sense(self):

    if self.testing:
        self.logger.info("skipping promise")
        return

    data_list = get_json_log_data_interval(self.amarisoft_stats_log, self.stats_period * 5)

    min_rxtx_delay_it = map(lambda x: float(x['rf']['rxtx_delay_min']), data_list)
    if not min_rxtx_delay_it:
        self.logger.error("No TX/RX diff data available")
    else:
      min_rxtx_delay = min(min_rxtx_delay_it)
      if min_rxtx_delay < self.min_rxtx_delay_threshold:
        self.logger.error("The minimum available time for radio front end processing is lower than the minimum threshold (%s ms)." % (self.min_rxtx_delay_threshold,))
      else:
        self.logger.info("The minimum available time for radio front end processing is higher than the minimum threshold (%s ms)." % (self.min_rxtx_delay_threshold,))

    self.json_logger.info("Min RX TX Delay (ms)",
      extra={'data': {'min_rxtx_delay': min_rxtx_delay}})

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
