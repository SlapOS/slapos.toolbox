from zope import interface as zope_interface
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise
import os
import subprocess

class RunPromise(GenericPromise):

  zope_interface.implements(interface.IPromise)

  def __init__(self, config):
    GenericPromise.__init__(self, config)
    # check configuration every 5 minutes (only for anomaly)
    self.setPeriodicity(minute=5)

  def sense(self):
    """
      RUn frontend validatation script
    """

    validate_script = self.getConfig('verification-script')
    result = float(subprocess.check_output([validate_script]))
    process = subprocess.Popen(
        [validate_script],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    stdout, stderr = process.communicate()
    if process.returncode != 0:
      self.logger.info("OK")
    else:
      if stderr:
        self.logger.error(stderr)
      else:
        self.logger.error(stdout)

  def anomaly(self):
    return self._test(result_count=2, failure_amount=2)
