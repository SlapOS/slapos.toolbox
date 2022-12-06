import json
import os
import psutil
import time

from .util import get_data_interval_json_log
from .util import JSONRunPromise

from zope.interface import implementer
from slapos.grid.promise import interface

@implementer(interface.IPromise)
class RunPromise(JSONRunPromise):

  def __init__(self, config):

    super(RunPromise, self).__init__(config)

    self.setPeriodicity(minute=2)
    self.last_avg_computation_file = self.getConfig(
      'last-avg-computation-file', 'last_avg')

  def sense(self):

    promise_success = True

    max_spot_temp = float(self.getConfig('max-spot-temp', 90))
    max_avg_temp = float(self.getConfig('max-avg-temp', 80))
    avg_temp_duration_sec = int(self.getConfig('avg-temp-duration-sec', 0))
    if avg_temp_duration_sec:
      avg_temp_duration = avg_temp_duration_sec
    else:
      avg_temp_duration = 60 * int(self.getConfig('avg-temp-duration', 5))
    testing = self.getConfig('testing') == "True"

    # For theia JHGD
    #testing = True # JHGD

    # Get current temperature
    if testing:
      from random import randint
      cpu_temp = randint(40, 75)
    else:
      data = psutil.sensors_temperatures()
      cpu_temp = data['coretemp'][0][1]
    if cpu_temp > max_spot_temp:
      self.logger.error("Temperature reached critical threshold: %s degrees "\
        "celsius (threshold is %s degrees celsius)" % (cpu_temp, max_spot_temp))
      promise_success = False

    # Log temperature
    data = json.dumps({'cpu_temperature': cpu_temp})
    self.json_logger.info("Temperature data", extra={'data': data})

		# TODO: promise should computer average only with logs between interval
    # Computer average temperature
    avg_computation_period = avg_temp_duration / 4
    try:
      t = os.path.getmtime(self.last_avg_computation_file)
    except OSError:
      t = 0
    if (time.time() - t) > avg_computation_period:
      open(self.last_avg_computation_file, 'w').close()
      temp_list = get_data_interval_json_log(self.log_file, avg_temp_duration)
      if temp_list:
        avg_temp = sum(map(lambda x: x['cpu_temperature'], temp_list)) / len(temp_list)
        if avg_temp > max_avg_temp:
          self.logger.error("Average temperature over the last %s seconds "\
            "reached threshold: %s degrees celsius (threshold is %s degrees "\
            "celsius)" % (avg_temp_duration, avg_temp, max_avg_temp))
          promise_success = False
      else:
        self.logger.error("Couldn't read temperature from log")
        promise_success = False

    if promise_success:
      self.logger.info("Temperature OK")

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
