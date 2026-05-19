from zope.interface import implementer
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise

import os
import json


@implementer(interface.IPromise)
class RunPromise(GenericPromise):
  def __init__(self, config):
    super(RunPromise, self).__init__(config)

    self.setPeriodicity(float(self.getConfig('frequency', 2)))
    self.result_count = int(self.getConfig('result-count', 3))
    self.failure_amount = int(self.getConfig('failure-amount', 3))

  def sense(self):
    """
      Check exit code of process in etc/run, promise fail if exit != 0
    """

    process_scripts_dir = self.getConfig(
      'script-directory',
      os.path.join(self.getPartitionFolder(), 'etc/run')
    )
    process_state_dir = self.getConfig(
      'state-directory',
      os.path.join(self.getPartitionFolder(), '.slapgrid/state')
    )

    state_result_list = []
    for process_name in os.listdir(process_scripts_dir):
      state_file = os.path.join(process_state_dir, '%s.json' % process_name)
      if os.path.exists(state_file):
        with open(state_file) as f:
          try:
            state_dict = json.load(f)
            # 'expected' will be 0 if the exit code was unexpected,
            # or 1 if the exit code was expected.
            if state_dict.get("expected", "1") != "1":
              state_result_list.append("Process '%s' script exited with unexpected exit code" % process_name)
          except ValueError as e:
            self.logger.error("ERROR %r", e, exc_info=True)
            break
    if len(state_result_list) > 0:
      self.logger.error('\n'.join(state_result_list))
    else:
      self.logger.info('Processes exit code are OK')

  def anomaly(self):
    return self._anomaly(result_count=self.result_count, failure_amount=self.failure_amount)
