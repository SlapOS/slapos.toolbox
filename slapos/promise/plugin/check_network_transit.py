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

    self.setPeriodicity(minute=1)
    self.last_transit_file = self.getConfig('last-transit-file', 'last_transit')

  def sense(self):

    promise_success = True
    
    # Get reference values
    min_threshold_recv = float(self.getConfig('min-threshold-recv', 1e2)) # ≈100 bytes
    min_threshold_sent = float(self.getConfig('min-threshold-sent', 1e2)) # ≈100 bytes
    transit_period_sec = int(self.getConfig('transit-period-sec', 0)) # For test
    if transit_period_sec:
      transit_period = transit_period_sec
    else:
      transit_period = 60*int(self.getConfig('transit-period-minutes', 5)) # 5 min
    
    # Get current network statistics, see https://psutil.readthedocs.io/en/latest/#network
    network_data = psutil.net_io_counters(nowrap=True)

    # Log recv and sent bytes
    data = json.dumps({'bytes_recv': network_data.bytes_recv, 
    'bytes_sent': network_data.bytes_sent})
    self.json_logger.info("Network data", extra={'data': data})

    # Get last timestamp (i.e. last modification) of log file
    try:
      t = os.path.getmtime(self.last_transit_file)
    except OSError:
      t = 0
    # Get total bytes recv/sent since transit_period
    if (time.time() - t) > transit_period:
      open(self.last_transit_file, 'w').close()
      temp_list = self.getJsonLogDataInterval(transit_period)
      if temp_list:
        if len(temp_list) == 1: # If no previous data in log
          pass
        else: 
          total_recv = temp_list[0]['bytes_recv'] - temp_list[-1]['bytes_recv']
          total_sent = temp_list[0]['bytes_sent'] - temp_list[-1]['bytes_sent']
          if total_recv <= min_threshold_recv:
            self.logger.error("Network congested, received bytes over the last %s seconds "\
              "reached minimum threshold: %7s (threshold is %7s)" 
              % (transit_period, bytes2human(total_recv), bytes2human(min_threshold_recv)))
            promise_success = False
          if total_sent <= min_threshold_sent:
            self.logger.error("Network congested, sent bytes over the last %s seconds "\
              "reached minimum threshold: %7s (threshold is %7s)" 
              % (transit_period, bytes2human(total_sent), bytes2human(min_threshold_sent)))
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
