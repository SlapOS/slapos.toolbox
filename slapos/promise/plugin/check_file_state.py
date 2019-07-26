from zope.interface import implementer
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise


@implementer(interface.IPromise)
class RunPromise(GenericPromise):
  def __init__(self, config):
    super(RunPromise, self).__init__(config)
    # SR can set custom periodicity
    self.setPeriodicity(float(self.getConfig('frequency', 2)))

  def sense(self):
    """
      Check state of the filename

      state can be empty or not-empty
    """

    filename = self.getConfig('filename')
    state = self.getConfig('state')
    url = self.getConfig('url').strip()

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

  def anomaly(self):
    return self._anomaly(result_count=3, failure_amount=3)
