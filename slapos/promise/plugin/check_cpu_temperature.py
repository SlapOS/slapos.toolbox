import json
import os
import psutil
import time

from .util import JSONPromise

from zope.interface import implementer
from slapos.grid.promise import interface

@implementer(interface.IPromise)
class RunPromise(JSONPromise):
  def __init__(self, config):
    super(RunPromise, self).__init__(config)
    self.setPeriodicity(minute=2)
    self.avg_flag_file = self.getConfig('last-avg-computation-file', 'last_avg')
    self.max_spot_temp = float(self.getConfig('max-spot-temp', 90))
    self.max_avg_temp = float(self.getConfig('max-avg-temp', 80))
    avg_temp_duration_sec = int(self.getConfig('avg-temp-duration-sec', 0))
    if avg_temp_duration_sec:
      self.avg_temp_duration = avg_temp_duration_sec
    else:
      self.avg_temp_duration = 60 * int(self.getConfig('avg-temp-duration', 5))

  def sense(self):
    success = True
    # Get current temperature
    try:
      cpu_temp = psutil.sensors_temperatures()['coretemp'][0][1]
    except (KeyError, IndexError) as e:
      self.logger.error("Could not read core temperature")
      return

    # Check spot temperature
    if cpu_temp > self.max_spot_temp:
      success = False
      self.logger.error(
        "Temperature reached critical threshold: %s °C"
        " (threshold is %s °C)",
        cpu_temp, self.max_spot_temp)

    # Log temperature
    data = json.dumps({'cpu_temperature': cpu_temp})
    self.json_logger.info("Temperature data", extra={'data': data})

    # TODO: promise should compute average only with logs between interval
    # Computer average temperature
    avg_computation_period = self.avg_temp_duration / 4
    try:
      t = os.path.getmtime(self.avg_flag_file)
    except OSError:
      t = 0
    if (time.time() - t) > avg_computation_period:
      open(self.avg_flag_file, 'w').close()
      temp_list = self.getJsonLogDataInterval(self.avg_temp_duration)
      if temp_list:
        avg_temp = sum(x['cpu_temperature'] for x in temp_list) / len(temp_list)
        if avg_temp > self.max_avg_temp:
          success = False
          self.logger.error(
            "Average temperature over the last %ds reached threshold: %s °C"
            " (threshold is %s °C)",
            self.avg_temp_duration, avg_temp, self.max_avg_temp)
      else:
        success = False
        self.logger.error("Couldn't read temperature from log")

    if success:
      self.logger.info("Temperature OK (%s °C)", cpu_temp)

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
