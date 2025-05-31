import json
import subprocess
import six
from zope.interface import implementer
from slapos.grid.promise import interface
from slapos.grid.promise.generic import \
  AnomalyResult, GenericPromise, TestResult


@implementer(interface.IPromise)
class RunPromise(GenericPromise):

  def __init__(self, config):
    config.setdefault('periodicity', 10)
    super(RunPromise, self).__init__(config)
    self.setTestLess()

  def sense(self):
    try:
      summary = subprocess.check_output(
        (self.getConfig('neoctl'), 'print', 'summary'),
        universal_newlines=True,
        ).splitlines()
      severities = json.loads(summary[0][1:])
      if severities:
        cluster_list = sum(six.itervalues(severities), [])
        try:
          cluster_list.remove(None)
        except ValueError:
          summary = []
        else:
          summary = ['main']
        if cluster_list:
          cluster_list.sort()
          summary.append('backup: ' + ', '.join(cluster_list))
        (self.logger.error if 'problem' in severities else
         self.logger.warning)('; '.join(summary))
      else:
        expected_state = self.getConfig('expected-state')
        status = summary[1]
        if expected_state and not status.startswith(expected_state + ';'):
          self.logger.error('%s; expected %s', status, expected_state)
        else:
          self.logger.info(status)
    except Exception as e:
      self.logger.critical(str(e))

  def anomaly(self):
    latest_result_list = self.getLastPromiseResultList()
    if latest_result_list:
      for result in latest_result_list[0]:
        status = result['status']
        message = result['message']
        if status == 'CRITICAL':
          return AnomalyResult(True, message)
      if status != 'INFO':
        result_class = TestResult
        if status == 'ERROR':
          status = 'PROBLEM'
          # XXX: Allow the user not to bang in this case, because this is
          #      counter-productive as long as we haven't implemented the
          #      ability to ignore the state (started or stopped) of services.
          if self.getConfig('bang-on-problem', True):
            result_class = AnomalyResult
        return result_class(True, '%s (%s)' % (status, message))
    else:
      message = "No result found!"
    return AnomalyResult(False, message)
