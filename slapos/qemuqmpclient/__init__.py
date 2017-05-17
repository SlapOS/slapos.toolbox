##############################################################################
#
# Copyright (c) 2013 Vifib SARL and Contributors. All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import argparse
import json
import os
import pprint
import socket
import time

def parseArgument():
  """
  Very basic argument parser. Might blow up for anything else than
  "./executable mysocket.sock stop/resume".
  """
  parser = argparse.ArgumentParser()
  parser.add_argument('--suspend', action='store_const', dest='action', const='suspend')
  parser.add_argument('--resume', action='store_const', dest='action', const='resume')
  parser.add_argument('--create-snapshot', action='store_const', dest='action', const='createSnapshot')
  parser.add_argument('--create-internal-snapshot', action='store_const', dest='action', const='createInternalSnapshot')
  parser.add_argument('--delete-internal-snapshot', action='store_const', dest='action', const='deleteInternalSnapshot')
  parser.add_argument('--drive-backup', action='store_const', dest='action', const='driveBackup') 
  parser.add_argument('--query-commands', action='store_const', dest='action', const='queryCommands')

  parser.add_argument('--socket', dest='unix_socket_location', required=True)
  parser.add_argument('remainding_argument_list', nargs=argparse.REMAINDER)
  args = parser.parse_args()
  return args.unix_socket_location, args.action, args.remainding_argument_list


class QemuQMPWrapper(object):
  """
  Small wrapper around Qemu's QMP to control a qemu VM.
  See http://git.qemu.org/?p=qemu.git;a=blob;f=qmp-commands.hx for
  QMP API definition.
  """
  def __init__(self, unix_socket_location):
    self.socket = self.connectToQemu(unix_socket_location)
    self.capabilities()

  @staticmethod
  def connectToQemu(unix_socket_location):
    """
    Create a socket, connect to qemu, be sure it answers, return socket.
    """
    if not os.path.exists(unix_socket_location):
      raise Exception('unix socket %s does not exist.' % unix_socket_location)

    print 'Connecting to qemu...'
    so = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    connected = False
    while not connected:
      try:
        so.connect(unix_socket_location)
      except socket.error:
        time.sleep(1)
        print 'Could not connect, retrying...'
      else:
        connected = True
    so.recv(1024)

    return so


  def _send(self, message):
    self.socket.send(json.dumps(message))
    data = self.socket.recv(65535)
    try:
      return json.loads(data)
    except ValueError:
      # if error the raise
      if "error" in data:
        raise Exception('ERROR: %s' % data)
      else:
        print 'Wrong data: %s' % data

  def _getVMStatus(self):
    response = self._send({'execute': 'query-status'})
    if response:
      return self._send({'execute': 'query-status'})['return']['status']
    else:
      raise IOError('Empty answer')

  def _waitForVMStatus(self, wanted_status):
    while True:
      try:
        actual_status = self._getVMStatus()
        if actual_status == wanted_status:
          return
        else:
          print 'VM in %s status, wanting it to be %s, retrying...' % (
              actual_status, wanted_status)
          time.sleep(1)
      except IOError:
          print 'VM not ready, retrying...'


  def capabilities(self):
    print 'Asking for capabilities...'
    self._send({'execute': 'qmp_capabilities'})

  def suspend(self):
    print 'Suspending VM...'
    self._send({'execute': 'stop'})
    self._waitForVMStatus('paused')

  def resume(self):
    print 'Resuming VM...'
    self._send({'execute': 'cont'})
    self._waitForVMStatus('running')

  def _queryBlockJobs(self, device):
    return self._send({'execute': 'query-block-jobs'})

  def _getRunningJobList(self, device):
    result = self._queryBlockJobs(device)

    while result is None:
      # If result is None retry to command until if return something.
      time.sleep(3)
      result = self._queryBlockJobs(device)
    if result.get('return'):
      return result['return']
    else:
      return

  def driveBackup(self, backup_target, source_device='virtio0', sync_type='full'):
    print 'Asking Qemu to perform backup to %s' % backup_target
    # XXX: check for error
    self._send({
        'execute': 'drive-backup',
        'arguments': {
            'device': source_device,
            'sync': sync_type,
            'target': backup_target,
         }
    })
    while self._getRunningJobList(backup_target):
      print 'Job is not finished yet.'
      time.sleep(20)

  def createSnapshot(self, snapshot_file, device='virtio0'):
    print self._send({
        'execute': 'blockdev-snapshot-sync',
        'arguments': {
            'device': device,
            'snapshot-file': snapshot_file,
         }
    })

  def createInternalSnapshot(self, name=None, device='virtio0'):
    if name is None:
      name = int(time.time())
    self._send({
        'execute': 'blockdev-snapshot-internal-sync',
        'arguments': {
            'device': device,
            'name': name,
         }
    })

  def deleteInternalSnapshot(self, name, device='virtio0'):
    self._send({
        'execute': 'blockdev-snapshot-delete-internal-sync',
        'arguments': {
            'device': device,
            'name': name,
         }
    })

  def queryCommands(self):
    pprint.pprint(self._send({'execute': 'query-commands'})['return'])

def main():
  unix_socket_location, action, remainding_argument_list = parseArgument()
  qemu_wrapper = QemuQMPWrapper(unix_socket_location)

  if remainding_argument_list:
    getattr(qemu_wrapper, action)(*remainding_argument_list)
  else:
    getattr(qemu_wrapper, action)()

if __name__ == '__main__':
  main()

