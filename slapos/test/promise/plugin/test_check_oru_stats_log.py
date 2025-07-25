import mock
import os
import time
from datetime import datetime
from datetime import timedelta
from slapos.grid.promise import PromiseError
from slapos.promise.plugin.check_oru_stats_log import RunPromise
from . import TestPromisePluginMixin


class TestCheckOruConfigLog(TestPromisePluginMixin):

    promise_name = "check-oru-stats-log.py"

    def setUp(self):
        super(TestCheckOruConfigLog, self).setUp()

    def writePromise(self, **kw):
        super(TestCheckOruConfigLog, self).writePromise(self.promise_name,
            "from %s import %s\nextra_config_dict = %r\n"
            % (RunPromise.__module__, RunPromise.__name__, kw))

    def test_promise_success(self):
        self.stats_log = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'stats.log')
        if os.path.exists(self.stats_log):
            os.remove(self.stats_log)
        with open(self.stats_log, 'w+') as f:
            f.write("""2023-05-23 04:32:46,350 [INFO] Connecting to ('2a11:9ac1:6:800a::1', 830), user oranuser...
2023-05-23 04:32:48,830 [INFO] Connection to ('2a11:9ac1:6:800a::1', 830) successful
2023-05-23 04:32:49,692 [INFO] Subscription to ('2a11:9ac1:6:800a::1', 830) successful
2023-05-23 04:32:49,692 [DEBUG] Waiting for notification from ('2a11:9ac1:6:800a::1', 830)...
2023-05-23 04:33:09,787 [DEBUG] Got new notification from ('2a11:9ac1:6:800a::1', 830)...
2023-05-23 04:33:09,788 [DEBUG] Waiting for notification from ('2a11:9ac1:6:800a::1', 830)...
2023-05-23 04:33:41,318 [DEBUG] Got new notification from ('2a11:9ac1:6:800a::1', 830)...
2023-05-23 04:33:41,319 [DEBUG] Waiting for notification from ('2a11:9ac1:6:800a::1', 830)...
"""
            )
        self.writePromise(**{
            'stats-log': self.stats_log,
        })
        self.configureLauncher()
        self.launcher.run()

    def test_promise_fail(self):
        self.stats_log = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'stats.log')
        if os.path.exists(self.stats_log):
            os.remove(self.stats_log)
        with open(self.stats_log, 'w') as f:
            f.write("""
2023-05-23 04:32:33,230 [INFO] Connecting to ('2a11:9ac1:6:800a::1', 830), user oranuser...
2023-05-23 04:32:36,339 [DEBUG] Got exception, waiting 10 seconds before reconnecting...
2023-05-23 04:32:36,340 [DEBUG] Could not open socket to 2a11:9ac1:6:800a::1:830
"""
            )
        self.writePromise(**{
            'stats-log': self.stats_log,
        })
        self.configureLauncher()
        with self.assertRaises(PromiseError):
            self.launcher.run()


if __name__ == '__main__':
    unittest.main()