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
    self.setPeriodicity(float(self.getConfig('frequency', 1)))
    self.last_transit_file = self.getConfig('last-transit-file', 'last_transit')
    self.max_data_amount = float(self.getConfig('max-data-amount', 10e3))*1048576 #  MB converted into bytes
    self.min_data_amount = float(self.getConfig('min-data-amount', 0.1))*1048576 #  MB converted into bytes
    self.transit_period = int(self.getConfig('transit-period', 600)) # secondes

  def sense(self):
    promise_success = True    
    # Get current network statistics, see https://psutil.readthedocs.io/en/latest/#network
    network_data = psutil.net_io_counters(nowrap=True)
    data_amount = network_data.bytes_recv + network_data.bytes_sent
    # Log data amount
    data = json.dumps({'network_data_amount': data_amount})
    self.json_logger.info("Network data amount", extra={'data': data})

    # Get last timestamp (i.e. last modification) of log file
    try:
      t = os.path.getmtime(self.last_transit_file)
    except OSError:
      t = 0
    # We recalculate every quarter of transit_period since calculate over periodicity
    # can be heavy in computation
    if (time.time() - t) > self.transit_period / 4:
      open(self.last_transit_file, 'w').close()
      temp_list = self.get_json_log_data_interval(self.transit_period)
      if temp_list:
        # If no previous data in log
        if len(temp_list) == 1:
          pass
        else:
          data_diff = temp_list[0]['network_data_amount'] - temp_list[-1]['network_data_amount']
          if data_diff <= self.min_data_amount:
            self.logger.error("Network congested, data amount over the last %s seconds "\
              "reached minimum threshold: %7s (threshold is %7s)" 
              % (self.transit_period, bytes2human(data_diff), bytes2human(self.min_data_amount)))
            promise_success = False
          if data_diff >= self.max_data_amount:
            self.logger.error("Network congested, data amount over the last %s seconds "\
              "reached maximum threshold: %7s (threshold is %7s)" 
              % (self.transit_period, bytes2human(data_diff), bytes2human(self.max_data_amount)))
            promise_success = False
      else:
        self.logger.error("Couldn't read network data from log")
        promise_success = False

    if promise_success:
      self.logger.info("Network transit OK")

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
