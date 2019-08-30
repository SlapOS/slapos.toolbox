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

  def sense(self):
    """
      Check result of the executed command
    """

    command = self.getConfig('command')

    try:
      process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT)
      out, _ = process.communicate()
      status = process.returncode
    except Exception as e:
      self.logger.error(
        "ERROR %r during running command %r" % (e, command))
      return

    if status != 0:
      self.logger.error(
        'ERROR %r run with failure, output: %s' % (command, out))
    else:
      self.logger.info("OK %r run with success" % (command,))

  def anomaly(self):
    return self._anomaly(result_count=3, failure_amount=3)
