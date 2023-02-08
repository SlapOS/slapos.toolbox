import json
import os
import psutil
import time

from psutil._common import bytes2human
from .util import JSONPromise

from zope.interface import implementer
from slapos.grid.promise import interface

@implementer(interface.IPromise)
class RunPromise(JSONPromise):

  def __init__(self, config):
    super(RunPromise, self).__init__(config)
    # Get reference values
    self.setPeriodicity(float(self.getConfig('frequency', 2)))
    self.last_avg_ram_file = self.getConfig('last-avg-ram-file', 'last_avg')
    self.min_threshold_ram = float(self.getConfig('min-threshold-ram', 500))*1048576 #  MB converted into bytes
    self.min_avg_ram = float(self.getConfig('min-avg-ram', 1e3))*1048576 #  MB converted into bytes
    self.avg_ram_period =  int(self.getConfig('avg-ram-period', 600)) # secondes

  def sense(self):
    promise_success = True
    # Get current RAM usage
    ram_data = psutil.virtual_memory()
    # Check with min threshold and log error if below it
    if ram_data.available <= self.min_threshold_ram:
      self.logger.error("RAM usage reached critical threshold: %7s "\
        " (threshold is %7s)" % (bytes2human(ram_data.available), bytes2human(self.min_threshold_ram)))
      promise_success = False
    
    # Log RAM usage
    data = json.dumps({'available_ram': ram_data.available})
    self.json_logger.info("RAM data", extra={'data': data})

    # Get last timestamp (i.e. last modification) of log file
    try:
      t = os.path.getmtime(self.last_avg_ram_file)
    except OSError:
      t = 0
    # Get last available RAM from log file since avg_ram_period / 4
    if (time.time() - t) > self.avg_ram_period / 4:
      open(self.last_avg_ram_file, 'w').close()
      temp_list = self.get_json_log_data_interval(self.avg_ram_period)
      if temp_list:
        avg_ram = sum(map(lambda x: x['available_ram'], temp_list)) / len(temp_list)
        if avg_ram < self.min_avg_ram:
          self.logger.error("Average RAM usage over the last %s seconds "\
            "reached threshold: %7s (threshold is %7s)" 
            % (self.avg_ram_period, bytes2human(avg_ram), bytes2human(self.min_avg_ram)))
          promise_success = False
      else:
        self.logger.error("Couldn't read available RAM from log")
        promise_success = False

    if promise_success:
      self.logger.info("RAM usage OK")

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
