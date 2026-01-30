from .util import get_json_log_data_interval
from .util import JSONPromise

import json
from zope.interface import implementer
from slapos.grid.promise import interface

@implementer(interface.IPromise)
class RunPromise(JSONPromise):

  def __init__(self, config):
    super(RunPromise, self).__init__(config)
    self.frequency = float(self.getConfig('frequency', 5))
    self.setPeriodicity(self.frequency)
    self.testing = self.getConfig('testing') == "True"
    self.amarisoft_stats_log = self.getConfig('amarisoft-stats-log')
    self.stats_period = int(self.getConfig('stats-period'))
    self.mme_list = json.loads(self.getConfig('mme-list'))
    self.amf_list = json.loads(self.getConfig('amf-list'))

  def sense(self):

    interval = min(self.frequency * 60, self.stats_period * 2)
    data_list = get_json_log_data_interval(self.amarisoft_stats_log, interval)

    disconnected_core_count = []
    for mme in mme_list:
      for s1_list in map(lambda x: x['s1_list'], data_list):
        mme_setup_done = False
        for s1 in s1_list:
          if s1["address"] == mme and s1["state"] == "setup_done":
            mme_setup_done = True
        if not mme_setup_done:
          disconnected_core_count.setdefault(mme, 0)
          disconnected_core_count[mme] += 1
    for amf in amf_list:
      for ng_list in map(lambda x: x['ng_list'], data_list):
        amf_setup_done = False
        for ng in ng_list:
          if ng["address"] == amf and ng["state"] == "setup_done":
            amf_setup_done = True
        if not amf_setup_done:
          disconnected_core_count.setdefault(amf, 0)
          disconnected_core_count[amf] += 1
        
    for core in disconnected_core_count:
      self.logger.error("{} was disconnected for {} minutes the last {} minutes".format(
        mme,
        self.stats_period / 60,
        interval / 60))
    if not disconnected_core_count:
      self.logger.info("All Core Networks were connected")

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
    return self._anomaly(result_count=3, failure_amount=2)
