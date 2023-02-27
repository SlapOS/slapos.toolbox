"""
Some notable parameters:

  url:
    The URL of the websocket to test
  promise-timeout:
    Optional timeout (in seconds) for promise.
  timeout:
    Optional timeout (in seconds) for websocket request.
  frequency:
    Optional frequency (in minutes) for running this promise.
  content_to_send:
    Optional bytes to send to the websocket
  content_to_receive:
    Optional bytes to compare the first message sent by websocket with (must be used with content to send)
"""

from zope.interface import implementer
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise

import websocket

@implementer(interface.IPromise)
class RunPromise(GenericPromise):
  def __init__(self, config):
    super(RunPromise, self).__init__(config)
    # SR can set custom periodicity
    self.setPeriodicity(float(self.getConfig('frequency', 2)))

  def sense(self):
    """
      Check if frontend URL is available.
    """

    url = self.getConfig('url')
    # make default time a max of 5 seconds, a bit smaller than promise-timeout
    # and in the same time at least 1 second
    default_timeout = max(
      1, min(5, int(self.getConfig('promise-timeout', 20)) - 1))
    content_to_send = self.getConfig('content_to_send')
    content_to_receive = self.getConfig('content_to_receive')

    try:
      ws = websocket.create_connection(url, timeout=int(self.getConfig('timeout', default_timeout)))
    except websocket._exceptions.WebSocketBadStatusException:
      self.logger.error(
        "ERROR connection not possible while accessing %r", url)
    except Exception as e:
      self.logger.error("ERROR: %s", e)
    else:
      if content_to_send and content_to_receive:
        ws.send(content_to_send)
        response = ws.recv()
        if response != content_to_receive:
          self.logger.error("ERROR received %r instead of %r", response, content_to_receive)
        else:
          self.logger.info("Correctly received %r from %r", content_to_receive, url)
      else:
        self.logger.info("Correctly connected to %r", url)

  def anomaly(self):
    return self._test(result_count=3, failure_amount=3)
