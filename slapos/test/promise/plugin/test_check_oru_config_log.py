import mock
import os
import time
from datetime import datetime
from datetime import timedelta
from slapos.grid.promise import PromiseError
from slapos.promise.plugin.check_oru_config_log import RunPromise
from . import TestPromisePluginMixin


class TestCheckOruConfigLog(TestPromisePluginMixin):

    promise_name = "check-oru-config-log.py"

    def setUp(self):
        super(TestCheckOruConfigLog, self).setUp()

    def writePromise(self, **kw):
        super(TestCheckOruConfigLog, self).writePromise(self.promise_name,
            "from %s import %s\nextra_config_dict = %r\n"
            % (RunPromise.__module__, RunPromise.__name__, kw))

    def test_promise_success(self):
        self.config_log = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.log')
        if os.path.exists(self.config_log):
            os.remove(self.config_log)
        with open(self.config_log, 'w+') as f:
            f.write("""2023-05-23 04:32:48,867 [INFO] Sending edit-config RPC request...
2023-05-23 04:32:49,111 [INFO] Edit-config RPC request sent successfully
"""
            )
        self.writePromise(**{
            'config-log': self.config_log,
        })
        self.configureLauncher()
        self.launcher.run()

    def test_promise_fail(self):
        self.config_log = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.log')
        if os.path.exists(self.config_log):
            os.remove(self.config_log)
        with open(self.config_log, 'w') as f:
            f.write("""2023-05-23 04:32:20,110 [INFO] Connecting to ('2a11:9ac1:6:800a::1', 830), user oranuser...
2023-05-23 04:32:48,863 [INFO] Connection to ('2a11:9ac1:6:800a::1', 830) successful
2023-05-23 04:32:48,867 [INFO] Sending edit-config RPC request...
2023-05-23 04:32:49,111 [ERROR] Error sending edit-config RPC request: Operation failed
"""
            )
        self.writePromise(**{
            'config-log': self.config_log,
        })
        self.configureLauncher()
        with self.assertRaises(PromiseError):
            self.launcher.run()


if __name__ == '__main__':
    unittest.main()