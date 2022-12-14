import psutil

from zope.interface import implementer
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise

@implementer(interface.IPromise)
class RunPromise(GenericPromise):

  def __init__(self, config):

    super(RunPromise, self).__init__(config)
    self.setPeriodicity(minute=5)


  def sense(self):

    promise_success = True
    
    # Get reference values
    max_lost_packets = int(self.getConfig('max-lost-packets', 100))
    max_error_messages = int(self.getConfig('max-error-messages', 100))

    # Get current Network statistics
    network_data =  psutil.net_io_counters() # Check for args if useful
    total_dropped = network_data.dropin + network_data.dropout
    total_errors = network_data.errin + network_data.errout

    # Check for network dropped packets
    if total_dropped >= max_lost_packets:
      self.logger.error("Network packets lost reached critical threshold: %s "\
        " (threshold is %s)" % (total_dropped, max_lost_packets))
      promise_success = False

    # Check for network errors
    if total_errors >= max_error_messages:
      self.logger.error("Network errors reached critical threshold: %s "\
        " (threshold is %s)" % (total_errors, max_error_messages))
      promise_success = False

    if promise_success:
      self.logger.info("Network statistics OK")

  def test(self):
    """
    Called after sense() if the instance is still converging.
    Returns success or failure based on sense results.

    In this case, fail if the previous sensor result is negative.
    """
    return self._test(result_count=1, failure_amount=1)


  def anomaly(self):
    """
    Called after sense() if the instance has finished converging.
    Returns success or failure based on sense results.
    Failure signals the instance has diverged.

    In this case, fail if two out of the last three results are negative.
    """
    return self._anomaly(result_count=3, failure_amount=2)
