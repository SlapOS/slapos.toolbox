import subprocess
from zope.interface import implementer
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise


@implementer(interface.IPromise)
class RunPromise(GenericPromise):

  def __init__(self, config):
    config.setdefault('periodicity', 1440)
    super().__init__(config)
    self.setTestLess()

  anomaly = GenericPromise._test

  def sense(self):
    # Developed at https://lab.nexedi.com/nexedi/slapos.package/-/tree/master/obs/notepod
    args = ['/usr/sbin/audit_encryption']
    if self.getConfig("fido2-required"):
      args.append("--fido2-required")
    with subprocess.Popen(args, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                text=True) as p:
      output = p.communicate()[0]
    (self.logger.error if p.returncode else self.logger.info)(output)
