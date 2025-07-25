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
        self.config_log = self.getConfig('config-log')
        self.testing = self.getConfig('testing') == "True"

    def sense(self):

        if self.testing:
            self.logger.info("skipping promise")
            return

        latest_log = tail_file(self.config_log)
        latest_log.split("\n")

        if "Sending edit-config RPC request..." not in latest_log:
            self.logger.info("No edit-config RPC request")
        else:
            last_segment = latest_log.split("Sending edit-config RPC request...")[-1].strip()

            if "Error" in last_segment:
                self.logger.error("Error sending edit-config RPC request")
            elif "Got exception" in last_segment:
                self.logger.error("Connection lost")
            else:
                self.logger.info("Edit-config RPC request sent successfully")
          
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
