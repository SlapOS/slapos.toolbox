#!/usr/bin/env python

from __future__ import print_function

import sys
import os
import errno
import glob
import json
from six.moves import configparser
import time
from datetime import datetime
import base64
import hashlib
import PyRSS2Gen

from slapos.util import bytes2str, str2bytes

def getKey(item):
  return item.source.name

class MonitorFeed(object):

  def __init__(self, instance_name, hosting_name,
      public_url, private_url, feed_url):
    self.rss_item_list = []
    self.report_date = datetime.utcnow()
    self.instance_name = instance_name
    self.hosting_name = hosting_name
    self.public_url = public_url
    self.private_url = private_url
    self.feed_url = feed_url

  def appendItem(self, item_dict, has_string=""):
    event_date = item_dict['result']['change-date']
    report_date = item_dict['result']['date']
    description = item_dict['result'].get('message', '')
    guid = base64.b64encode(str2bytes("%s, %s, %s, %s" % (self.hosting_name,
      item_dict['title'], has_string, event_date)))
    rss_item = PyRSS2Gen.RSSItem(
      categories = [item_dict['status']],
      source = PyRSS2Gen.Source(item_dict['title'], self.public_url),
      title = '[%s] %s' % (item_dict['status'], item_dict['title']),
      description = "\n%s" % (description,),
      link = self.private_url,
      pubDate = event_date,
      guid = PyRSS2Gen.Guid(bytes2str(guid), isPermaLink=False)
    )
    self.rss_item_list.append(rss_item)

  def generateRSS(self, output_file):
    ### Build the rss feed
    # try to keep the list in the same order
    sorted(self.rss_item_list, key=getKey)
    rss_feed = PyRSS2Gen.RSS2 (
      title = self.instance_name,
      link = self.feed_url,
      description = self.hosting_name,
      lastBuildDate = self.report_date,
      items = self.rss_item_list
    )

    with open(output_file, 'w') as frss:
      frss.write(rss_feed.to_xml())

class MonitorStateBuilder(object):

  def __init__(self, config):
    self.monitor_title = config.get('monitor', 'title'),
    self.monitor_root_title = config.get('monitor', 'root-title')

    self.partition_folder = config.get('promises', 'partition-folder')
    self.private_folder = config.get('monitor', 'private-folder')
    self.public_folder = config.get('monitor', 'public-folder')
    self.monitor_url = config.get('monitor', 'base-url')
    self.related_monitor_list = config.get("monitor", "monitor-url-list").split()

    self.documents_folder = os.path.join(self.partition_folder, 'documents')

    self.computer_id = config.get('promises', 'computer-id')
    self.partition_ipv4 = config.get('promises', 'ipv4')
    self.partition_ipv6 = config.get('promises', 'ipv6')
    self.software_release_url = config.get('promises', 'software-release')
    self.software_type = config.get('promises', 'software-type')
    self.partition_id = config.get('promises', 'partition-id')

    self.public_url = "%s/share/public/" % self.monitor_url
    self.private_url = "%s/share/private/" % self.monitor_url
    self.feed_url = "%s/public/feed" % self.monitor_url

    self.global_state_file = os.path.join(
      self.private_folder,
      'monitor.global.json'
    )
    self.public_state_file = os.path.join(
      self.public_folder,
      'monitor.global.json'
    )

    tmp_dir = os.path.join(config.get('promises', 'partition-folder'), 'tmp')
    if not os.path.isdir(tmp_dir):
      os.mkdir(tmp_dir)

  def writeDocumentList(self, folder_path):
    # Save document list in a file called _document_list
    document_list = [os.path.splitext(file)[0]
                  for file in os.listdir(folder_path) if file.endswith('.json')]

    with open(os.path.join(folder_path, '_document_list'), 'w') as f:
      f.write('\n'.join(document_list))

  def savePromiseHistory(self, promise_name, state_dict, previous_state_list):

    history_file = os.path.join(
      self.public_folder,
      '%s.history.json' % promise_name
    )
    tmp_history_file = os.path.join(
      self.tmp_folder,
      '%s.history.json' % promise_name
    )
    history_dict = {
      "date": time.time(),
      "data": [state_dict]
    }

    # Remove useless informations
    result = state_dict.pop('result')
    state_dict.update(result)
    state_dict.pop('path', '')
    state_dict.pop('type', '')

    try:
      with open(history_file) as f:
        history_dict = json.load(f)
    except (IOError, OSError) as e:
      if e.errno != errno.ENOENT:
        raise
    except ValueError:
      # Broken json, use default history_dict
      pass
    else:
      if previous_state_list is not None:
        _, change_date, checksum = previous_state_list
        current_sum = hashlib.md5(str2bytes(state_dict.get('message', ''))).hexdigest()
        if state_dict['change-date'] == change_date and \
            current_sum == checksum:
          # Only save the changes and not the same info
          return

      state_dict.pop('title', '')
      state_dict.pop('name', '')
      history_dict['data'].append(state_dict)

    with open(tmp_history_file, mode="w") as f:
      json.dump(history_dict, f)
    os.rename(tmp_history_file, history_file)

  def saveStatisticsData(self, stat_file_path, content):
    # csv document for success/error statictics
    data_dict = {
      "date": time.time(),
      "data": ["Date, Success, Error, Warning"]
    }

    try:
      with open(stat_file_path) as f:
        data_dict = json.load(f)
    except (IOError, OSError) as e:
      if e.errno != errno.ENOENT:
        raise
    except ValueError:
      # Broken json, we use default
      pass

    if not 'state' in content:
      return
    current_state = '%s, %s, %s, %s' % (
      content['date'],
      content['state']['success'],
      content['state']['error'],
      '')
    data_dict['data'].append(current_state)
    tmp_path = '%s.tmp' % stat_file_path

    with open(tmp_path, mode="w") as f:
      json.dump(data_dict, f)
    os.rename(tmp_path, stat_file_path)

  def generateMonitoringData(self):
    feed_output = os.path.join(self.public_folder, 'feed')
    # search for all status files
    file_list = list(filter(
      os.path.isfile,
      glob.glob("%s/promise/*.status.json" % self.public_folder)
    ))

    promises_status_file = os.path.join(self.private_folder, '_promise_status')
    previous_state_dict = {}
    new_state_dict = {}
    error = success = 0
    monitor_feed = MonitorFeed(
      self.monitor_title,
      self.monitor_root_title,
      self.public_url,
      self.private_url,
      self.feed_url)

    if os.path.exists(promises_status_file):
      with open(promises_status_file) as f:
        try:
          previous_state_dict = json.loads(f.read())
        except ValueError:
          pass

    # clean up stale history files
    expected_history_json_name_list = [
      os.path.basename(q).replace('status.json', 'history.json') for q in file_list]
    cleanup_history_json_path_list = []
    for history_json_name in [q for q in os.listdir(self.public_folder)
                              if q.endswith('history.json')]:
      if history_json_name not in expected_history_json_name_list:
        cleanup_history_json_path_list.append(
          os.path.join(self.public_folder, history_json_name)
        )
    for cleanup_path in cleanup_history_json_path_list:
      try:
        os.unlink(cleanup_path)
      except Exception:
        print('ERROR: Failed to remove stale %s' % (cleanup_path,))
      else:
        print('OK: Removed stale %s' % (cleanup_path,))

    for file in file_list:
      try:
        with open(file, 'r') as temp_file:
          tmp_json = json.load(temp_file)

        if tmp_json['result']['failed']:
          promise_status = "ERROR"
          error += 1
        else:
          promise_status = "OK"
          success += 1
        tmp_json['result']['change-date'] = tmp_json['result']['date']
        if tmp_json['name'] in previous_state_dict:
          status, change_date, _ = previous_state_dict[tmp_json['name']]
          if promise_status == status:
            tmp_json['result']['change-date'] = change_date

        tmp_json['status'] = promise_status
        message_hash = hashlib.md5(
          str2bytes(tmp_json['result'].get('message', ''))).hexdigest()
        new_state_dict[tmp_json['name']] = [
          promise_status,
          tmp_json['result']['change-date'],
          message_hash
        ]
        monitor_feed.appendItem(tmp_json, message_hash)
        self.savePromiseHistory(
          tmp_json['title'],
          tmp_json,
          previous_state_dict.get(tmp_json['name'])
        )
      except ValueError as e:
        # bad json file
        print("ERROR: Bad json file at: %s\n%s" % (file, e))
        continue

    with open(promises_status_file, "w") as f:
      json.dump(new_state_dict, f)

    monitor_feed.generateRSS(feed_output)
    return error, success

  def buildMonitorState(self):
    status = 'OK'
    report_date = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S+0000')
    error, success = self.generateMonitoringData()
    parameter_file = os.path.join(
      self.private_folder, 'config', '.jio_documents', 'config.json')
    if error:
      status = 'ERROR'

    global_state_dict = dict(
      status=status,
      state={
        'error': error,
        'success': success
      },
      type='global', # bwd compatibility
      portal_type='Software Instance',
      date=report_date,
      _links={"rss_url": {"href": self.feed_url},
              "public_url": {"href": self.public_url},
              "private_url": {"href": self.private_url},
              "related_monitor": []
            },
      data={'state': 'monitor_state.data',
            'process_state': 'monitor_process_resource.status',
            'process_resource': 'monitor_resource_process.data',
            'memory_resource': 'monitor_resource_memory.data',
            'io_resource': 'monitor_resource_io.data',
            'monitor_process_state': 'monitor_resource.status'},
      title=self.monitor_title,
      specialise_title=self.monitor_root_title,
      aggregate_reference=self.computer_id,
      ipv4=self.partition_ipv4,
      ipv6=self.partition_ipv6,
      software_release=self.software_release_url,
      software_type=self.software_type,
      partition_id=self.partition_id,
    )

    if not global_state_dict['title']:
      global_state_dict['title'] = 'Instance Monitoring'

    if related_monitor_list:
      global_state_dict['_links']['related_monitor'] = [
        {'href': "%s/share/public" % url} for url in self.related_monitor_list]

    if os.path.exists(parameter_file):
      with open(parameter_file) as f:
        global_state_dict['parameters'] = json.load(f)

    # Public information with the link to private folder
    public_state_dict = dict(
      status=status,
      date=report_date,
      _links={'monitor': {'href': '%s/share/private/' % self.monitor_url}},
      title=global_state_dict['title'],
      specialise_title=global_state_dict.get('specialise_title', ''),
    )
    public_state_dict['_links']['related_monitor'] = global_state_dict['_links'] \
      .get('related_monitor', [])

    with open(global_state_file, 'w') as fg:
      fg.write(json.dumps(global_state_dict))

    with open(public_state_file, 'w') as fpg:
      fpg.write(json.dumps(public_state_dict))

    # write list of files
    self.writeDocumentList(self.public_folder)
    self.writeDocumentList(self.private_folder)
    self.writeDocumentList(documents_folder)

    self.saveStatisticsData(
      os.path.join(documents_folder, 'monitor_state.data.json'),
      global_state_dict
    )

    return 0

def main():
  if len(sys.argv) < 2:
    print("Usage: %s <monitor_conf_path>" % sys.argv[0])
    sys.exit(2)
  builder = MonitorStateBuilder(sys.argv[1])
  sys.exit(builder.buildMonitorState())
