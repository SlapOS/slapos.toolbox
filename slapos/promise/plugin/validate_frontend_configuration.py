from zope.interface import implementer
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise
try:
  import subprocess32 as subprocess
except ImportError:
  import subprocess

@implementer(interface.IPromise)
class RunPromise(GenericPromise):
  def __init__(self, config):
    super(RunPromise, self).__init__(config)
    # check configuration every 5 minutes (only for anomaly)
    self.setPeriodicity(minute=float(self.getConfig('frequency', 5)))

  def sense(self):
    """
      Run frontend validatation script
    """

    validate_script = self.getConfig('verification-script')
    if not validate_script:
      raise ValueError("'verification-script' was not set in promise parameters.")
    try:
      subprocess.check_output(validate_script, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
      message = e.output
      self.logger.error(message if str is bytes else
                        message.decode('utf-8', 'replace'))
    else:
      self.logger.info("OK")

  def anomaly(self):
    return self._anomaly(result_count=1, failure_amount=1)
