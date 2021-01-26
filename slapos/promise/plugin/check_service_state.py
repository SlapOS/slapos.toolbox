from zope.interface import implementer
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise

from slapos.grid.svcbackend import getSupervisorRPC
from slapos.grid.svcbackend import _getSupervisordSocketPath

import os


@implementer(interface.IPromise)
class RunPromise(GenericPromise):
  def __init__(self, config):
    super(RunPromise, self).__init__(config)
    # SR can set custom periodicity
    self.setPeriodicity(float(self.getConfig('frequency', 2)))

  def sense(self):
    """
      Check if a service is in the expected state
    """

    service = self.getConfig('service')
    expect = self.getConfig('expect', '')

    if expect not in ("running", "stopped"):
      self.logger.info("OK service %r is allowed to be in any state (expect = %r)" % (service, expect))
      return

    if not service:
      self.logger.error("ERROR no service is specified")
      return

    try:
      run_directory = os.path.join(self.getPartitionFolder(), "srv/runner/var/run")
      supervisor_rpc = getSupervisorRPC(_getSupervisordSocketPath(run_directory, self.logger))

      with supervisor_rpc as supervisor:
        state = supervisor.getProcessInfo(service)['statename'].lower()
        if state != expect:
          self.logger.error("ERROR service %r is in state %r (expected %r)" % (service, state, expect))
        else:
          self.logger.info("OK service %r is in expected state %r" % (service, state))

    except Exception as e:
      self.logger.error("ERROR %r" % (e,))

  def anomaly(self):
    return self._anomaly(result_count=3, failure_amount=3)
