import errno
import json
import logging
import os

from dateutil import parser
from .util import JSONPromise, get_json_log_data_interval

from zope.interface import implementer
from slapos.grid.promise import interface

@implementer(interface.IPromise)
class RunPromise(JSONPromise):
  def __init__(self, config):
    super(RunPromise, self).__init__(config)
    self.setPeriodicity(minute=1)
    self.amarisoft_rf_info_log = self.getConfig('amarisoft-rf-info-log')
    self.stats_period = int(self.getConfig('stats-period'))
    self.testing = self.getConfig('testing') == "True"

  def sense(self):
      if self.testing:
          self.logger.info("skipping promise")
          return
  
      data_list = get_json_log_data_interval(self.amarisoft_rf_info_log, self.stats_period * 2)
      if len(data_list) < 1:
        self.logger.error("rf_info: stale data")
        return

      rf_info_text = data_list[0]['rf_info']
      if "CPRI" not in rf_info_text:
          self.logger.info("No CPRI feature")
      else:
          if "HW" in rf_info_text and "SW" in rf_info_text:
              self.logger.info("CPRI locked")
          else:
              if "HW" not in rf_info_text:
                  self.logger.error("HW Lock is missing")
              if "SW" not in rf_info_text:
                  self.logger.error("SW Lock is missing")
    
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
