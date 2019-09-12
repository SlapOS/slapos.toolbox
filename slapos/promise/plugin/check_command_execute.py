from zope.interface import implementer
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise

import subprocess


@implementer(interface.IPromise)
class RunPromise(GenericPromise):
  def __init__(self, config):
    super(RunPromise, self).__init__(config)
    # SR can set custom periodicity
    self.setPeriodicity(float(self.getConfig('frequency', 2)))
    self.result_count = int(self.getConfig('result_count', '1'))
    self.failure_amount = int(self.getConfig('failure_amount', '1'))

  def sense(self):
    """
      Check result of the executed command
    """

    command = self.getConfig('command')

    try:
      out = subprocess.check_output(
        command,
        shell=True,
        stderr=subprocess.STDOUT)
      status = 0
    except subprocess.CalledProcessError as e:
      out = e.output
      status = e.returncode
    except Exception as e:
      self.logger.error(
        "ERROR %r during running command %r" % (e, command))
      return

    if status != 0:
      self.logger.error(
        'ERROR %r run with failure, output: %r' % (command, out))
    else:
      self.logger.info("OK %r run with success" % (command,))

  def anomaly(self):
    return self._anomaly(result_count=self.result_count, failure_amount=self.failure_amount)
