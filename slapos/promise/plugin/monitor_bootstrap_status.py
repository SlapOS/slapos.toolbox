from zope import interface as zope_interface
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise
import os
import time
import psutil
from slapos.runner.utils import tail

PROCESS_PID_FILE = ""
PROCESS_NAME = ""
STATUS_FILE = ""

class RunPromise(GenericPromise):

  zope_interface.implements(interface.IPromise)

  def __init__(self, config):
    GenericPromise.__init__(self, config)
    self.setPeriodicity(minute=2)

  def sense(self):
    if PROCESS_PID_FILE == "" or PROCESS_NAME == "" or STATUS_FILE == "":
      self.logger.info("")
      return

    if not os.path.exists(PROCESS_PID_FILE):
      self.logger.info("Bootstrap didn't run!")
      return

    with open(PROCESS_PID_FILE) as f:
      try:
        pid = int(f.read())
      except ValueError, e:
        raise ValueError("%r is empty or doesn't contain a valid pid number: %s" % (
          PROCESS_PID_FILE, str(e)))

    try:
      process = psutil.Process(pid)
      command_string = ' '.join(process.cmdline())
      if "monitor.bootstrap" in command_string and \
          self.getPartitionFolder() in command_string:
        for i in range(0, 15):
          if process.is_running():
            time.sleep(1)
          else:
            break
        else:
          self.logger.error("Monitor bootstrap is running for more than 15 seconds!")
          return
    except psutil.NoSuchProcess:
      # process exited
      pass

    if os.path.exists(STATUS_FILE) and not os.stat(STATUS_FILE).st_size:
      self.logger.info("Bootstrap OK")
      return

    message = "Monitor bootstrap exited with error."
    log_file = os.path.join(self.getPartitionFolder(), ".%s_%s.log" % (
      self.getConfig('partition-id'),
      PROCESS_NAME))
    if os.path.exists(log_file):
      with open(log_file) as f:
        message += "\n ---- Latest monitor-boostrap.log ----\n"
        message += tail(f, 4)

    self.logger.error(message)

  def test(self):
    return self._test(result_count=1, failure_amount=1)

  def anomaly(self):
    # bang if we have 3 error successively
    return self._anomaly(result_count=3, failure_amount=3)
