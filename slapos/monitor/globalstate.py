#!/usr/bin/env python

from __future__ import print_function

import sys
import os
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

  def generateMonitoringRSS(self, public_folder, private_folder):
    feed_output = os.path.join(public_folder, 'feed')
    file_list = filter(
      os.path.isfile,
      glob.glob("%s/promise/*.status.json" % public_folder)
    )

    promises_status_file = os.path.join(private_folder, '_promise_status')
    current_state_dict = {}
    if os.path.exists(promises_status_file):
      with open(promises_status_file) as f:
        try:
          current_state_dict = json.load(f)
        except ValueError:
          pass

    for file in file_list:
      try:
        with open(file, 'r') as temp_file:
          tmp_json = json.load(temp_file)

        name = tmp_json['name']
        if name not in current_state_dict:
          continue
        promise_status, change_date, message_hash = current_state_dict[tmp_json['name']] 
        tmp_json['result']['change-date'] = change_date 
        tmp_json['status'] = promise_status
        self.appendItem(tmp_json, message_hash)
      except ValueError as e:
        # bad json file
        print("ERROR: Bad json file at: %s\n%s" % (file, e))
        continue

    self.generateRSS(feed_output)

def writeDocumentList(folder_path):
  # Save document list in a file called _document_list
  public_document_list = [os.path.splitext(file)[0]
                for file in os.listdir(folder_path) if file.endswith('.json')]

  with open(os.path.join(folder_path, '_document_list'), 'w') as lfile:
    lfile.write('\n'.join(public_document_list))

def run(monitor_conf_file):

  config = configparser.ConfigParser()
  config.read(monitor_conf_file)

  partition_folder = config.get('promises', 'partition-folder')
  base_folder = config.get('monitor', 'private-folder')
  status_folder = config.get('monitor', 'public-folder')
  base_url = config.get('monitor', 'base-url')
  related_monitor_list = config.get("monitor", "monitor-url-list").split()
  statistic_folder = os.path.join(base_folder, 'documents')
  # need webdav to update parameters
  parameter_file = os.path.join(base_folder, 'config', '.jio_documents', 'config.json')

  public_url = "%s/share/public/" % base_url
  private_url = "%s/share/private/" % base_url
  feed_url = "%s/public/feed" % base_url

  slapgrid_global_state_file = os.path.join(partition_folder,
          ".slapgrid/promise/global.json")
  slapgrid_public_state_file = os.path.join(partition_folder,
          ".slapgrid/promise/public.json")

  global_state_file = os.path.join(base_folder, 'monitor.global.json')
  public_state_file = os.path.join(status_folder, 'monitor.global.json')
  report_date = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S+0000')

  monitor_feed = MonitorFeed(
    config.get('monitor', 'title'),
    config.get('monitor', 'root-title'),
    public_url,
    private_url,
    feed_url)

  monitor_feed.generateMonitoringRSS(status_folder, base_folder)

  with open(slapgrid_global_state_file) as f:
    global_state_dict = json.load(f)

  with open(slapgrid_public_state_file) as f:
    public_state_dict = json.load(f)


  global_state_dict.update(dict(
    _links={"rss_url": {"href": feed_url},
            "public_url": {"href": public_url},
            "private_url": {"href": private_url},
            "related_monitor": [{'href': "%s/share/public" % url}
                  for url in related_monitor_list]
          },
    title=config.get('monitor', 'title'),
    specialise_title=config.get('monitor', 'root-title'),
    ipv4=config.get('promises', 'ipv4'),
    ipv6=config.get('promises', 'ipv6'),
    software_release=config.get('promises', 'software-release'),
    software_type=config.get('promises', 'software-type'),
  ))

  if not global_state_dict['title']:
    global_state_dict['title'] = 'Instance Monitoring'

  if os.path.exists(parameter_file):
    with open(parameter_file) as cfile:
      global_state_dict['parameters'] = json.load(cfile)

  # Public information with the link to private folder
  public_state_dict.update(dict(
    _links={'monitor': {'href': '%s/share/private/' % base_url},
            'related_monitor': global_state_dict['_links']['related_monitor']},
    title=global_state_dict['title'],
    specialise_title=global_state_dict['specialise_title'],
  ))

  with open(global_state_file, 'w') as fglobal:
    json.dump(global_state_dict, fglobal)

  with open(public_state_file, 'w') as fpglobal:
    json.dump(public_state_dict, fpglobal)

  # Implement backward compatibility with older UI.
  for hfile in glob.glob(os.path.join(status_folder, "history/*.history.json")):
    hfile_name = os.path.basename(hfile)
    hfile_link = os.path.join(status_folder, hfile_name)
    if not os.path.exists(hfile_link):
      os.symlink(hfile, hfile_link)

  # write list of files
  writeDocumentList(status_folder)
  writeDocumentList(base_folder)
  writeDocumentList(statistic_folder)

  return 0

def main():
  if len(sys.argv) < 2:
    print("Usage: %s <monitor_conf_path>" % sys.argv[0])
    sys.exit(2)
  sys.exit(run(sys.argv[1]))
