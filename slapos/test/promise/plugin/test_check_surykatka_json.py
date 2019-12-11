from slapos.grid.promise import PromiseError
from slapos.test.promise.plugin import TestPromisePluginMixin

import os
import shutil
import tempfile


class CheckSurykatkaJSONMixin(TestPromisePluginMixin):
  promise_name = 'check-surykatka-json.py'

  def setUp(self):
    self.working_directory = tempfile.mkdtemp()
    self.json_file = os.path.join(self.working_directory, 'surykatka.json')
    self.addCleanup(shutil.rmtree, self.working_directory)
    TestPromisePluginMixin.setUp(self)

  def writeSurykatkaPromise(self, d=None):
    if d is None:
      d = {}
    content_list = [
      "from slapos.promise.plugin.check_surykatka_json import RunPromise"]
    content_list.append('extra_config_dict = {')
    for k, v in d.items():
      content_list.append("  '%s': '%s'," % (k, v))
    content_list.append('}')
    self.writePromise(self.promise_name, '\n'.join(content_list))

  def writeSurykatkaJson(self, content):
    with open(self.json_file, 'w') as fh:
      fh.write(content)


class TestCheckSurykatkaJSON(CheckSurykatkaJSONMixin):
  def test_no_config(self):
    self.writeSurykatkaPromise()
    self.configureLauncher()
    with self.assertRaises(PromiseError):
      self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], True)
    self.assertEqual(
      result['result']['message'],
      "File '' does not exists")

  def test_not_existing_file(self):
    self.writeSurykatkaPromise({'json-file': self.json_file})
    self.configureLauncher()
    with self.assertRaises(PromiseError):
      self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], True)
    self.assertEqual(
      result['result']['message'],
      "File '%s' does not exists" % (self.json_file,))

  def test_empty_file(self):
    self.writeSurykatkaPromise({'json-file': self.json_file})
    self.writeSurykatkaJson('')
    self.configureLauncher()
    with self.assertRaises(PromiseError):
      self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], True)
    self.assertEqual(
      result['result']['message'],
      "Problem loading JSON from '%s'" % (self.json_file,))


class TestCheckSurykatkaJSONUnknownReport(CheckSurykatkaJSONMixin):
  def test(self):
    self.writeSurykatkaPromise(
      {
        'report': 'NOT_EXISTING_ENTRY',
        'json-file': self.json_file,
      }
    )
    self.writeSurykatkaJson("""{
}
""")
    self.configureLauncher()
    with self.assertRaises(PromiseError):
      self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], True)
    self.assertEqual(
      result['result']['message'],
      "Report 'NOT_EXISTING_ENTRY' is not supported")


class TestCheckSurykatkaJSONBotStatus(CheckSurykatkaJSONMixin):
  def test(self):
    self.writeSurykatkaPromise(
      {
        'report': 'bot_status',
        'json-file': self.json_file,
        'test-utcnow': 'Wed, 13 Dec 2222 09:11:12 -0000'
      }
    )
    self.writeSurykatkaJson("""{
    "bot_status": [
        {
            "date": "Wed, 13 Dec 2222 09:10:11 -0000",
            "text": "loop"
        }
    ]
}
""")
    self.configureLauncher()
    self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], False)
    self.assertEqual(
      result['result']['message'],
      "bot_status: Last bot status from 2222-12-13 09:10:11 ok, "
      "UTC now is 2222-12-13 09:11:12"
    )

  def test_bot_status_future(self):
    self.writeSurykatkaPromise(
      {
        'report': 'bot_status',
        'json-file': self.json_file,
        'test-utcnow': 'Wed, 13 Dec 2222 09:11:12 -0000'
      }
    )
    self.writeSurykatkaJson("""{
    "bot_status": [
        {
            "date": "Wed, 13 Dec 2223 09:10:11 -0000",
            "text": "loop"
        }
    ]
}
""")
    self.configureLauncher()
    with self.assertRaises(PromiseError):
      self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], True)
    self.assertEqual(
      result['result']['message'],
      "bot_status: Last bot datetime 2223-12-13 09:10:11 is in "
      "future, UTC now 2222-12-13 09:11:12"
    )

  def test_bot_status_old(self):
    self.writeSurykatkaPromise(
      {
        'report': 'bot_status',
        'json-file': self.json_file,
        'test-utcnow': 'Wed, 13 Dec 2223 09:26:12 -0000'
      }
    )
    self.writeSurykatkaJson("""{
    "bot_status": [
        {
            "date": "Wed, 13 Dec 2223 09:10:11 -0000",
            "text": "loop"
        }
    ]
}
""")
    self.configureLauncher()
    with self.assertRaises(PromiseError):
      self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], True)
    self.assertEqual(
      result['result']['message'],
      "bot_status: Last bot datetime 2223-12-13 09:10:11 is "
      "more than 15 minutes old, UTC now 2223-12-13 09:26:12"
    )

  def test_not_bot_status(self):
    self.writeSurykatkaPromise(
      {
        'report': 'bot_status',
        'json-file': self.json_file,
      }
    )
    self.writeSurykatkaJson("""{
}
""")
    self.configureLauncher()
    with self.assertRaises(PromiseError):
      self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], True)
    self.assertEqual(
      result['result']['message'],
      "bot_status: 'bot_status' not in '%s'" % (self.json_file,))

  def test_empty_bot_status(self):
    self.writeSurykatkaPromise(
      {
        'report': 'bot_status',
        'json-file': self.json_file,
      }
    )
    self.writeSurykatkaJson("""{
  "bot_status": []
}
""")
    self.configureLauncher()
    with self.assertRaises(PromiseError):
      self.launcher.run()
    result = self.getPromiseResult(self.promise_name)
    self.assertEqual(result['result']['failed'], True)
    self.assertEqual(
      result['result']['message'],
      "bot_status: 'bot_status' empty in '%s'" % (self.json_file,))
