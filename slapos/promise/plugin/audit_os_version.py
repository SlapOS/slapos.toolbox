import distro
from zope.interface import implementer
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise


@implementer(interface.IPromise)
class RunPromise(GenericPromise):

  def __init__(self, config):
    config.setdefault('periodicity', 86400)
    super().__init__(config)
    self.setTestLess()

  anomaly = GenericPromise._test

  def sense(self):
    expected_name = self.getConfig("dist")
    versions = self.getConfig("versions").split()
    name = distro.name()
    version = distro.version()
    if name == expected_name and version in versions:
      self.logger.info("%s %s", name, version)
    else:
      self.logger.error("%s %s (expected: %s %s)",
        name, version, expected_name, versions[0])
