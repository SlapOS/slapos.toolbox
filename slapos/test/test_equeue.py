import json
import multiprocessing
import os
import socket
import time
import unittest

from slapos.equeue import EqueueServer


class Options:
  def __init__(self, logfile, loglevel, database, takeover_triggered_file_path, lockfile, timeout):
    self.logfile = logfile
    self.loglevel = loglevel
    self.database = database
    self.takeover_triggered_file_path = takeover_triggered_file_path
    self.lockfile = lockfile
    self.timeout = timeout


class TestEqueue(unittest.TestCase):
  def setUp(self):
    cwd = os.getcwd()
    (
      self.database,
      self.takeover_triggered_file_path,
      self.lockfile,
      self.socket,
      self.testfile,
    ) = self.file_list = [
      'equeue.db',
      'takeover.txt',
      'equeue.lock',
      'equeue.sock',
      'testfile.txt',
    ]
    # Do not delete log files, as it may contain interesting information for debugging
    self.logfile = 'equeue.log'
    self.options = Options(
      logfile=self.logfile,
      loglevel='INFO',
      database=self.database,
      takeover_triggered_file_path=self.takeover_triggered_file_path,
      lockfile=self.lockfile,
      timeout=3,
    )
    self.equeue_server = None


  def tearDown(self):
    self.equeue_server.server_close()
    for filename in self.file_list:
      if os.path.exists(filename):
        os.unlink(filename)


  def test_onlyOneCommandRunAtTheTime(self):
    self.equeue_server = EqueueServer(self.socket, equeue_options=self.options)
    server_process = multiprocessing.Process(target=self.equeue_server.serve_forever)
    server_process.start()
    self.addCleanup(server_process.terminate)

    self.assertTrue(os.path.exists(self.options.database))
    self.assertTrue(os.path.exists(self.socket))

    # Prepare 2 requests, the first one including a delay.
    # If more than one request can be run at a time, then
    # the second would execute first, and the content of the
    # test file would be overwriten by command 1.
    request_1 = {
      'timestamp': 1,
      'command': "bash\0-c\0sleep 3 && echo 1 > %s" % self.testfile,
    }
    request_2 = {
      'timestamp': 2,
      'command': "bash\0-c\0echo 2 > %s" % self.testfile,
    }
    for request in (request_1, request_2):
      equeue_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
      equeue_socket.connect(self.socket)
      equeue_socket.send(json.dumps(request).encode())
      result = equeue_socket.recv(len(request['command']))
      self.assertEqual(result.decode(), request['command'])
      equeue_socket.close()

    # Wait for the 1st command to finish
    time.sleep(5)

    with open(self.testfile, 'r') as fd:
      self.assertEqual(fd.read(), '2\n')


  def test_doNotRunACommandIfItHasAlreadyRun(self):
    self.equeue_server = EqueueServer(self.socket, equeue_options=self.options)
    server_process = multiprocessing.Process(target=self.equeue_server.serve_forever)
    server_process.start()
    self.addCleanup(server_process.terminate)

    self.assertTrue(os.path.exists(self.options.database))
    self.assertTrue(os.path.exists(self.socket))

    # Run 2 times the same command (bash), but with different
    # parameters (equeue doesn't care about parameters). As the
    # timestamp is the same, the second command shouldn't be run
    request_1 = {
      'timestamp': 1,
      'command': "bash\0-c\0echo 1 > %s" % self.testfile,
    }
    request_2 = {
      'timestamp': 1,
      'command': "bash\0-c\0echo 2 > %s" % self.testfile,
    }
    for request in (request_1, request_2):
      equeue_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
      equeue_socket.connect(self.socket)
      equeue_socket.send(json.dumps(request).encode())
      result = equeue_socket.recv(len(request['command']))
      self.assertEqual(result.decode(), request['command'])
      equeue_socket.close()

    # Give a bit of time for command to run
    time.sleep(2)

    with open(self.testfile, 'r') as fd:
      self.assertEqual(fd.read(), '1\n')


  def test_doNothingIfTakeoverHasBeenTriggered(self):
    self.equeue_server = EqueueServer(self.socket, equeue_options=self.options)
    server_process = multiprocessing.Process(target=self.equeue_server.serve_forever)
    server_process.start()
    self.addCleanup(server_process.terminate)

    self.assertTrue(os.path.exists(self.options.database))
    self.assertTrue(os.path.exists(self.socket))

    # Create takeover file
    with open(self.takeover_triggered_file_path, 'w') as f:
      f.write('\0')

    request = {
      'timestamp': 1,
      'command': "bash\0-c\0echo 1 > %s" % self.testfile,
    }
    equeue_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    equeue_socket.connect(self.socket)
    equeue_socket.send(json.dumps(request).encode())
    result = equeue_socket.recv(len(request['command']))
    self.assertEqual(result.decode(), request['command'])
    equeue_socket.close()

    # Give a bit of time for command to run
    time.sleep(2)

    self.assertFalse(os.path.exists(self.testfile))
