import os
import shutil
import socket
import tempfile
import unittest

import mock

from slapos.pubsub import notifier


class TestNotifier(unittest.TestCase):
  def setUp(self):
    self.working_directory = tempfile.mkdtemp()
    self.logfile = os.path.join(self.working_directory, 'feed.xml')

  def tearDown(self):
    shutil.rmtree(self.working_directory, ignore_errors=True)

  @mock.patch('slapos.pubsub.notifier.httplib.HTTPConnection')
  @mock.patch('slapos.pubsub.notifier.urlopen')
  @mock.patch('slapos.pubsub.notifier.subprocess.check_output')
  def test_connectionErrorDuringNotificationDoesNotRaiseTypeError(
      self, check_output, urlopen, http_connection_class):
    check_output.return_value = 'ok'

    feed = mock.Mock()
    feed.read.return_value = b'<rss></rss>'
    feed.info.return_value.get.return_value = 'application/xml'
    urlopen.return_value = feed

    connection = http_connection_class.return_value
    connection.request.side_effect = socket.error('No route to host')

    argv = [
      'pubsubnotifier',
      '--log', self.logfile,
      '--title', 'test',
      '--feed', 'http://example.com/feed',
      '--executable', '/bin/true',
      '--notification-url', 'http://example.com/notify',
    ]
    with mock.patch('sys.argv', argv):
      with self.assertRaises(SystemExit) as raised:
        notifier.main()

    self.assertEqual(raised.exception.code, 1)


if __name__ == '__main__':
  unittest.main()
