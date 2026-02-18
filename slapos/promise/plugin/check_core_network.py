from .util import get_json_log_data_interval
from .util import JSONPromise

import json
from zope.interface import implementer
from slapos.grid.promise import interface
from slapos.grid.promise.generic import TestResult

@implementer(interface.IPromise)
class RunPromise(JSONPromise):

  def __init__(self, config):
    super(RunPromise, self).__init__(config)
    self.frequency = float(self.getConfig('frequency', 5))
    self.setPeriodicity(self.frequency)
    self.testing = self.getConfig('testing') == "True"
    self.amarisoft_stats_log = self.getConfig('amarisoft-stats-log')
    self.stats_period = int(self.getConfig('stats-period'))
    self.mme_list = list(self.getConfig('mme-list'))
    self.amf_list = list(self.getConfig('amf-list'))

  def sense(self):

    interval = max(self.frequency * 60, self.stats_period * 2)
    data_list = get_json_log_data_interval(self.amarisoft_stats_log, interval)

    def check_core(addr, port, proto):
      if '.' in addr:
        if ':' not in addr:
          addr = f"{addr}:{port}"
      elif '[' not in addr:
        addr = f"[{addr}]:{port}"
      for core_list in map(lambda x: x[f"{proto}_list"], data_list):
        for core in core_list:
          if core["address"] == addr and core["state"] == "setup_done":
            break
        else:
          disconnected_core_count.setdefault(addr, 0)
          disconnected_core_count[addr] += 1

    disconnected_core_count = {}
    for mme in self.mme_list:
      check_core(mme, 36412, 's1')
    for amf in self.amf_list:
      check_core(amf, 38412, 'ng')
        
    for core in disconnected_core_count:
      duration = int(self.stats_period * disconnected_core_count[core] / 60)
      self.logger.error("{} was disconnected for {} minute{} the last {} minutes".format(
        core,
        duration,
        's' if duration != 1 else '',
        int(interval / 60)))
    if not disconnected_core_count:
      self.logger.info("All Core Networks are connected")

    self.json_logger.info("Disconnected Core Networks count map", 
                          extra={'data': disconnected_core_count})

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
