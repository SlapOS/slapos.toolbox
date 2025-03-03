import errno
import json
import logging
import os

from dateutil import parser
from .util import JSONPromise
from .util import tail_file

from zope.interface import implementer
from slapos.grid.promise import interface

@implementer(interface.IPromise)
class RunPromise(JSONPromise):
    def __init__(self, config):
        super(RunPromise, self).__init__(config)
        self.setPeriodicity(float(self.getConfig('frequency', 1)))
        self.stats_log = self.getConfig('stats-log')
        self.testing = self.getConfig('testing') == "True"

    def sense(self):

        if self.testing:
            self.logger.info("skipping promise")
            return

        latest_log = tail_file(self.stats_log)
        latest_log.split("\n")

        if "Waiting for notification from" not in latest_log:
            self.logger.error("Not subscribed")
        else:
            self.logger.info("Subscribed successful")
          
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
        return self._anomaly(result_count=1, failure_amount=1)
