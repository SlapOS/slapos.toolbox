from .util import get_json_log_data_interval
from .util import JSONPromise

import json
from zope.interface import implementer
from slapos.grid.promise import interface

@implementer(interface.IPromise)
class RunPromise(JSONPromise):

  def __init__(self, config):
    super(RunPromise, self).__init__(config)
    self.setPeriodicity(float(self.getConfig('frequency', 1)))
    self.testing = self.getConfig('testing') == "True"
    self.amarisoft_stats_log = self.getConfig('amarisoft-stats-log')
    self.stats_period = int(self.getConfig('stats-period'))
    self.rx_chan_list = json.loads(self.getConfig('rf-rx-chan-list')) # which rx channels to check
    self.max_rx_sample_db = float(self.getConfig('max-rx-sample-db'))

  def sense(self):

    data_list = get_json_log_data_interval(self.amarisoft_stats_log, self.stats_period * 2)

    max_rx_list = []
    saturated = False

    for rx_antenna_list in map(lambda x: x['samples']['rx'], data_list):
        rx_list = map(lambda x: float(x['max']), [rx_antenna_list[i] for i in self.rx_chan_list])
        if not max_rx_list:
          max_rx_list = list(rx_list)
        for i, rx in enumerate(rx_list):
            max_rx_list[i] = max(max_rx_list[i], rx)
            if rx >= self.max_rx_sample_db:
                saturated = True

    self.json_logger.info("RX maximum sample values (dB)", extra={'data': max_rx_list})

    if not max_rx_list:
        self.logger.error("No RX samples data available")
    elif saturated:
        self.logger.error("RX antennas saturated, please lower rx_gain")
    else:
        self.logger.info("No saturation detected on RX antennas")

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
