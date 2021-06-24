from zope.interface import implementer
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise

import requests

@implementer(interface.IPromise)
class RunPromise(GenericPromise):
    def __init__(self, config):
        super(RunPromise, self).__init__(config)
        self.setPeriodicity(float(self.getConfig('frequency', 2)))

    def sense(self):
        """
        Check basic HTTP authentication for a service. You should
        probably run check_url_available.py first.
        """
        url = self.getConfig('url')
        username = self.getConfig('username')
        password = self.getConfig('password')

        try:
            result = requests.get(url, auth=(username, password))
        except requests.ConnectionError as _:
            self.logger.error(
                'ERROR connection not possible while accessing %r' % url)
            return
        except Exception as e:
            self.logger.error('ERROR %r' % e)
            return

        credentials = '(%r, %r)' % (username, password)
        if result.ok:
            self.logger.info('%r authenticated with %s' % (url, credentials))
        else:
            self.logger.error('ERROR could not authenticate %r with %s' % \
                              (url, credentials))

    def anomaly(self):
        return self._test(result_count=3, failure_amount=3)
