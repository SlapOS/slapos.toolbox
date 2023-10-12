#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import sys
try:
  import errno
except ImportError:
  from os import errno
import os
import stat
import json
from six.moves import configparser
import traceback
import argparse
from six.moves.urllib.request import urlopen
from six.moves.urllib.error import HTTPError
import ssl
import glob
import socket
from datetime import datetime
from xml.sax.saxutils import escape

OPML_START = """<?xml version="1.0" encoding="UTF-8"?>
<!-- OPML generated by SlapOS -->
<opml version="1.1">
	<head>
		<title>%(root_title)s</title>
		<dateCreated>%(creation_date)s</dateCreated>
		<dateModified>%(modification_date)s</dateModified>
	</head>
	<body>
	  <outline text="%(outline_title)s">"""
OPML_END = """	  </outline>
  </body>
</opml>"""

OPML_OUTLINE_FEED = '<outline text="%(title)s" title="%(title)s" type="rss" version="RSS" htmlUrl="%(html_url)s" xmlUrl="%(xml_url)s" url="%(global_url)s" />'


def parseArguments():
  """
  Parse arguments for monitor instance.
  """
  parser = argparse.ArgumentParser()
  parser.add_argument('-c', '--config-file', required=True,
                      default='monitor.cfg',
                      help='Monitor Configuration file')

  return parser.parse_args()


def mkdirAll(path):
  try:
    os.makedirs(path)
  except OSError as e:
    if e.errno == errno.EEXIST and os.path.isdir(path):
      pass
    else: raise

def softConfigGet(config, *args, **kwargs):
  try:
    return config.get(*args, **kwargs)
  except (configparser.NoOptionError, configparser.NoSectionError):
    return None

def createSymlink(source, destination):
  try:
    os.symlink(source, destination)
  except OSError as e:
    if e.errno != errno.EEXIST:
      raise

class Monitoring(object):

  def __init__(self, configuration_file):
    self._config_file = configuration_file
    config = self.loadConfig([configuration_file])

    # Set Monitor variables
    self.title = config.get("monitor", "title")
    self.root_title = config.get("monitor", "root-title")
    self.service_pid_folder = config.get("monitor", "service-pid-folder")
    self.crond_folder = config.get("monitor", "crond-folder")
    self.public_folder = config.get("monitor", "public-folder")
    self.private_folder = config.get("monitor", "private-folder")
    self.webdav_folder = config.get("monitor", "webdav-folder")
    self.webdav_url = '%s/share' % config.get("monitor", "base-url")
    self.public_url = '%s/public' % config.get("monitor", "base-url")
    self.public_path_list = config.get("monitor", "public-path-list").split()
    self.private_path_list = config.get("monitor", "private-path-list").split()
    self.monitor_url_list = config.get("monitor", "monitor-url-list").split()
    self.parameter_list = [param.strip() for param in config.get("monitor", "parameter-list").split('\n') if param]
    # Use this file to write knowledge0_cfg required by webrunner
    self.parameter_cfg_file = config.get("monitor", "parameter-file-path").strip()
    self.pid_file = config.get("monitor", "pid-file")
    self.promise_output_file = config.get("monitor", "promise-output-file")
    self.promise_folder = config.get("promises", 'promise-folder')
    if config.has_option("promises", 'legacy-promise-folder'):
      self.legacy_promise_folder = config.get("promises", 'legacy-promise-folder')
    else:
      self.legacy_promise_folder = None
    self.promise_output = config.get("promises", 'output-folder')

    self.config_folder = os.path.join(self.private_folder, 'config')
    self.data_folder = config.get("monitor", "document-folder")
    self.bootstrap_is_ok = True

  def loadConfig(self, pathes, config=None):
    if config is None:
      config = configparser.ConfigParser()
    try:
      config.read(pathes)
    except configparser.MissingSectionHeaderError:
      traceback.print_exc()
    return config

  def readInstanceConfiguration(self):
    type_list = ['raw', 'file', 'htpasswd', 'httpdcors']
    configuration_list = []

    if not self.parameter_list:
      return []
  
    for config in self.parameter_list:
      config_list = config.strip().split(' ')
      # type: config_list[0]
      if len(config_list) >= 3 and config_list[0] in type_list:
        if config_list[0] == 'raw':
          configuration_list.append(dict(
            key='',
            title=config_list[1],
            value=' '.join(config_list[2:])
          ))
        elif (config_list[0] == 'file' or config_list[0] == 'htpasswd'):
          directory = os.path.dirname(config_list[2])
          if not os.path.exists(directory) or not os.access(directory, os.W_OK):
            raise OSError("Directory does not exists or does not have write acess")
          if os.path.exists(config_list[2]) and os.path.isfile(config_list[2]):
            try:
              with open(config_list[2]) as cfile:
                param_value = cfile.read()
            except OSError as e:
              print('Cannot read file %s, Error is: %s' % (config_list[2], e))
              pass
          else:
            param_value = ""
          parameter = dict(
            key=config_list[1],
            title=config_list[1],
            value=param_value,
            description={
              "type": config_list[0],
              "file": config_list[2]
            }
          )
          if config_list[0] == 'htpasswd':
            if len(config_list) != 5 or not os.path.exists(config_list[4]):
              print('htpasswd file is not specified: %s' % config_list)
              continue
            parameter['description']['user'] = config_list[3]
            parameter['description']['htpasswd'] = config_list[4]
          configuration_list.append(parameter)
        elif config_list[0] == 'httpdcors' and os.path.exists(config_list[2]) and \
            os.path.exists(config_list[3]):
          old_cors_file = os.path.join(
            os.path.dirname(config_list[2]),
            'prev_%s' % os.path.basename(config_list[2])
          )
          try:
            cors_content = ""
            if os.path.exists(old_cors_file):
              with open(old_cors_file) as cfile:
                cors_content = cfile.read()
            else:
              # Create empty file
              with open(old_cors_file, 'w') as cfile:
                cfile.write("")
            parameter = dict(
              key=config_list[1],
              title=config_list[1],
              value=cors_content,
              description={
                "type": config_list[0],
                "cors_file": config_list[2],
                "gracefull_bin": config_list[3]
              }
            )
            configuration_list.append(parameter)
          except OSError as e:
            print('Cannot read file at %s, Error is: %s' % (old_cors_file, e))
            pass
    return configuration_list

  def createSymlinksFromConfig(self, destination_folder, source_path_list, name=""):
    if destination_folder:
      if source_path_list:
        for path in source_path_list:
          path = path.rstrip('/')
          dirname = os.path.join(destination_folder, name)
          try:
            mkdirAll(dirname)  # could also raise OSError
            os.symlink(path, os.path.join(dirname, os.path.basename(path)))
          except OSError as e:
            if e.errno != errno.EEXIST:
              raise

  def getMonitorTitleFromUrl(self, monitor_url):
    # This file should be generated
    if not monitor_url.startswith('https://') and not monitor_url.startswith('http://'):
      return 'Unknown Instance'
    if not monitor_url.endswith('/'):
      monitor_url = monitor_url + '/'

    url  = monitor_url + '/monitor.global.json'
    success = False
    monitor_title = 'Unknown Instance'
    try:
      # Timeout after 20 seconds
      timeout = 20
      # XXX - working here with public url
      if hasattr(ssl, '_create_unverified_context'):
        context = ssl._create_unverified_context()
        response = urlopen(url, context=context, timeout=timeout)
      else:
        response = urlopen(url, timeout=timeout)
    except HTTPError:
      print("ERROR: Failed to get Monitor configuration file at %s " % url)
    except (socket.timeout, ssl.SSLError) as e:
      print("ERROR: Timeout with %r while downloading monitor config at %s " % (e, url))
    else:
      try:
        monitor_dict = json.loads(response.read())
        monitor_title = monitor_dict.get('title', 'Unknown Instance')
        success = True
      except ValueError as e:
        print("ERROR: Json file at %s is not valid" % url)

    self.bootstrap_is_ok = success
    return monitor_title

  def configureFolders(self):
    # create symlinks from monitor.conf
    self.createSymlinksFromConfig(self.public_folder, self.public_path_list)
    self.createSymlinksFromConfig(self.private_folder, self.private_path_list)
    # configure public and private folder
    self.createSymlinksFromConfig(self.webdav_folder, [self.public_folder])
    self.createSymlinksFromConfig(self.webdav_folder, [self.private_folder])

    config_jio_folder = os.path.join(self.config_folder, '.jio_documents')
    mkdirAll(config_jio_folder)

  def makeConfigurationFiles(self):
    config_folder = os.path.join(self.config_folder, '.jio_documents')
    parameter_config_file = os.path.join(config_folder, 'config.parameters.json')
    parameter_file = os.path.join(config_folder, 'config.json')

    parameter_list = self.readInstanceConfiguration()
    description_dict = {}

    if parameter_list:
      for i in range(0, len(parameter_list)):
        key = parameter_list[i]['key']
        if key:
          description_dict[key] = parameter_list[i].pop('description')

    with open(parameter_config_file, 'w') as config_file:
      config_file.write(json.dumps(description_dict))

    with open(parameter_file, 'w') as config_file:
      config_file.write(json.dumps(parameter_list))

    try:
      with open(self.parameter_cfg_file, 'w') as pfile:
        pfile.write('[public]\n')
        for parameter in parameter_list:
          if parameter['key']:
            pfile.write('%s = %s\n' % (parameter['key'], parameter['value']))
    except OSError as e:
      print("Error failed to create file %s" % self.parameter_cfg_file)
      pass


  def generateOpmlFile(self, feed_url_list, output_file):

    if os.path.exists(output_file):
      creation_date = datetime.utcfromtimestamp(os.path.getctime(output_file))\
        .strftime("%a, %d %b %Y %H:%M:%S +0000")
      modification_date = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")
    else:
      creation_date = modification_date = datetime.utcnow()\
        .strftime("%a, %d %b %Y %H:%M:%S +0000")

    opml_content = OPML_START % {'creation_date': creation_date,
                                  'modification_date': modification_date,
                                  'outline_title': 'Monitoring RSS Feed list',
                                  'root_title': escape(self.root_title)}

    opml_content += OPML_OUTLINE_FEED % {'title': escape(self.title),
        'html_url': self.public_url + '/feed',
        'xml_url': self.public_url + '/feed',
        'global_url': "%s/private/" % self.webdav_url}
    for feed_url in feed_url_list:
      opml_content += OPML_OUTLINE_FEED % {
        'title': self.getMonitorTitleFromUrl(feed_url + "/public"),
        'html_url': feed_url + '/public/feed',
        'xml_url': feed_url + '/public/feed',
        'global_url': "%s/share/private/" % feed_url}

    opml_content += OPML_END

    with open(output_file, 'w') as wfile:
      wfile.write(opml_content)

  def cleanupMonitorDeprecated(self):
    # Monitor report feature is removed
    cleanup_file_list = glob.glob("%s/*.history.json" % self.private_folder)
    cleanup_file_list.extend(glob.glob("%s/*.report.json" % self.private_folder))
    cleanup_file_list.extend(glob.glob("%s/*.report.json" % self.data_folder))
    cleanup_file_list.extend(glob.glob("%s/*.history.json" % self.data_folder))
    cleanup_file_list.extend(glob.glob("%s/*.status.json" % self.public_folder))
    cleanup_file_list.append(self.crond_folder + "/monitor-reports")
    cleanup_file_list.append(self.crond_folder + "/monitor-promises")

    for file in cleanup_file_list:
      try:
        if os.path.exists(file):
          os.unlink(file)
      except OSError as e:
        print("failed to remove file %s." % file, e)

    # cleanup result of promises that was removed
    if self.legacy_promise_folder is not None:
      promise_list = os.listdir(self.legacy_promise_folder)
    else:
      promise_list = []
    for name in os.listdir(self.promise_folder):
      if name.startswith('__init__'):
        continue
      promise_list.append(os.path.splitext(name)[0])
    for name in os.listdir(self.promise_output):
      if not name.endswith('.status.json'):
        continue
      try:
        position = promise_list.index(name.replace('.status.json', ''))
      except ValueError:
        status_path = os.path.join(self.promise_output, name)
        if os.path.exists(status_path):
          try:
            os.unlink(status_path)
          except OSError as e:
            print("Error: Failed to delete %s" % status_path, e)
      else:
        promise_list.pop(position)

  def bootstrapMonitor(self):

    # save pid of current process into file
    with open(self.pid_file, 'w') as pid_file:
      pid_file.write(str(os.getpid()))

    self.configureFolders()

    # Generate OPML file
    self.generateOpmlFile(self.monitor_url_list,
      os.path.join(self.public_folder, 'feeds'))

    # cleanup deprecated entries
    self.cleanupMonitorDeprecated()

    # Generate parameters files and scripts
    self.makeConfigurationFiles()

    # Write an empty file when monitor bootstrap went until the end
    if self.bootstrap_is_ok:
      with open(self.promise_output_file, 'w') as promise_file:
        promise_file.write("")
      print("SUCCESS: bootstrap is OK")
    elif os.path.exists(self.promise_output_file):
      os.unlink(self.promise_output_file)


    return 0


def main():
  parser = parseArguments()

  monitor = Monitoring(parser.config_file)
  
  sys.exit(monitor.bootstrapMonitor())
