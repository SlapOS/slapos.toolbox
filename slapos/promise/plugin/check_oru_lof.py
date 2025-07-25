import errno
import json
import logging
import os

from dateutil import parser
from .util import iter_logrotate_file_handle
from .util import iter_reverse_lines
from .util import JSONPromise

from zope.interface import implementer
from slapos.grid.promise import interface

@implementer(interface.IPromise)
class RunPromise(JSONPromise):

  def __init__(self, config):

    super(RunPromise, self).__init__(config)
    self.setPeriodicity(float(self.getConfig('frequency', 1)))
    self.netconf_log = self.getConfig('netconf-log')
    self.testing = self.getConfig('testing') == "True"

  def sense(self):

    if self.testing:
        self.logger.info("skipping promise")
        return

    for f in iter_logrotate_file_handle(self.netconf_log, 'rb'):
      for line in iter_reverse_lines(f):
        l = json.loads(line)
        alarm_notif = l.get('data', {}).get('notification', {}).get('alarm-notif', None)
        if alarm_notif and alarm_notif['fault-id'] == '1002':
          if alarm_notif['is-cleared'] == 'false':
            affected_objects = alarm_notif.get('affected-objects', {})
            self.logger.error('Loss of Frame (LOF) alarm is on, affected objects are: %s', affected_objects)
            self.json_logger.info("Affected objects", extra={'data': affected_objects})
          else:
            self.logger.info('Loss of Frame (LOF) alarm is off')
          return
    self.logger.info('No Loss of Frame (LOF) alarm received')

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
