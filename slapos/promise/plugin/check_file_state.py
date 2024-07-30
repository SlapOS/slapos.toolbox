from zope.interface import implementer
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise
import os


@implementer(interface.IPromise)
class RunPromise(GenericPromise):
  def __init__(self, config):
    super(RunPromise, self).__init__(config)
    # SR can set custom periodicity
    self.setPeriodicity(float(self.getConfig('frequency', 2)))
    self.result_count = int(self.getConfig('result-count', '1'))
    self.failure_amount = int(self.getConfig('failure-amount', '1'))
    if self.result_count < self.failure_amount:
      raise ValueError(
        'Bad configuration: result-count %i < failure_amount %i' % (
          self.result_count, self.failure_amount))

    if self.getConfig(
      'perdiodic-only', 'false').lower() in ('true', 'yes', '1'):
      self.setTestLess()

    if self.getConfig(
      'report-anomaly', 'true').lower() in ('false', 'no', '0'):
      self.setAnomalyLess()

  def sense(self):
    """
      Check state of the filename

      state can be one of:
        absent
        empty
        not-empty
    """

    filename = self.getConfig('filename')
    state = self.getConfig('state')
    url = (self.getConfig('url') or '').strip()

    exists = os.path.exists(filename)
    if state == 'absent':
      if exists:
        self.logger.error("ERROR %r not absent", filename)
      else:
        self.logger.info("OK %r state %r" % (filename, state))
      return
    if not exists:
      self.logger.error("ERROR %r not present", filename)
      return

    try:
      with open(filename) as f:
        result = f.read()
    except Exception as e:
      self.logger.error(
        "ERROR %r during opening and reading file %r" % (e, filename))
      return

    if state == 'empty' and result != '':
      message_list = ['ERROR %r not empty' % (filename,)]
      if url:
        message_list.append(', content available at %s' % (url,))
      self.logger.error(''.join(message_list))
    elif state == 'not-empty' and result == '':
      self.logger.error(
          "ERROR %r empty" % (filename,))
    else:
      self.logger.info("OK %r state %r" % (filename, state))

  def test(self):
    return self._test(
      result_count=self.result_count, failure_amount=self.failure_amount)

  def anomaly(self):
    return self._anomaly(
      result_count=self.result_count, failure_amount=self.failure_amount)
