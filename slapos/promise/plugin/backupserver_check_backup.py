from zope import interface as zope_interface
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise

import re
import sys
import pytz
from datetime import datetime
from croniter import croniter
from dateutil.parser import parse

class RunPromise(GenericPromise):

  zope_interface.implements(interface.IPromise)

  def __init__(self, config):
    GenericPromise.__init__(self, config)
    # check backup ran OK every 5 minutes
    self.setPeriodicity(minute=5)

  def sense(self):
    """
      backupserver run rdiff-backup and log everything in a text file.
      At the beginning of the backup, we have "backup running" printed in the text file.
      At the end of the backup, we can have one of the following printed in the text file:
         * "backup failed" -> backup failed
         * "backup success" -> backup succeeded
      A backup is valid only if we have the 2 conditions:
         * we can grep "backup running" in the text file
         * we can't grep "backup failed" in the text file
    """

    status_log = self.getConfig('status_log')
    prev_cron = croniter(self.getConfig('cron_frequency'), datetime.now(pytz.utc)).get_prev(datetime) # date of the previous time cron launched

    # First, parse the log file
    backup_started = False
    backup_ended = False
    for line in open(status_log, 'r'):
      m = re.match(r"(.*), (.*), (.*), backup (.*)$", line)
      if m:
        if m.group(4) == "running":
          backup_started = True
          backup_start = parse(m.group(1))
        elif m.group(4) == "failed":
          backup_ended = True
          backup_failed = True
          backup_end = parse(m.group(1))
        elif m.group(4) == "success":
          backup_ended = True
          backup_failed = False
          backup_end = parse(m.group(1))

    # Then check result
    if backup_ended and backup_failed:
      self.logger.error("Backup FAILED at {} (see log file : {})".format(backup_end, status_log))
    elif not backup_started:
      self.logger.error("Can't find backup start date. Is there a problem with log ? (see log file : {})".format(status_log))
    elif backup_start < prev_cron:
      self.logger.error("Backup didn't start at correct time: it started at {} but should have started after {}. (see log file : {})".format(backup_start, prev_cron, status_log))
    elif not backup_ended:
      self.logger.info("Backup currently running (started at {})".format(backup_start))
    else:
      self.logger.info("Backup OK (started at {} and lasted {})".format(backup_start, backup_end - backup_start))

  # no need to define Test as it is the default implementation
  #def test(self):
  #  """
  #    Test is failing if last sense was bad.
  #  """
  #  return self._test(result_count=1, failure_amount=1)

  def anomaly(self):
    """
      There is never an anomaly as this promise will be checked manually.
    """
    return AnomalyResult(problem=False)
