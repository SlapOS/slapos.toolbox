#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import stat
import json
import ConfigParser
import traceback
import argparse
import urllib2
import ssl
import glob
from datetime import datetime

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
  parser.add_argument('--config_file',
                      default='monitor.cfg',
                      help='Monitor Configuration file')

  return parser.parse_args()


def mkdirAll(path):
  try:
    os.makedirs(path)
  except OSError, e:
    if e.errno == os.errno.EEXIST and os.path.isdir(path):
      pass
    else: raise

def softConfigGet(config, *args, **kwargs):
  try:
    return config.get(*args, **kwargs)
  except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
    return None

def createSymlink(source, destination):
  try:
    os.symlink(source, destination)
  except OSError, e:
    if e.errno != os.errno.EEXIST:
      raise

class Monitoring(object):

  def __init__(self, configuration_file):
    config = self.loadConfig([configuration_file])

    # Set Monitor variables
    self.title = config.get("monitor", "title")
    self.root_title = config.get("monitor", "root-title")
    self.service_pid_folder = config.get("monitor", "service-pid-folder")
    self.crond_folder = config.get("monitor", "crond-folder")
    self.logrotate_d = config.get("monitor", "logrotate-folder")
    self.promise_runner = config.get("monitor", "promise-runner")
    self.promise_folder = config.get("monitor", "promise-folder")
    self.public_folder = config.get("monitor", "public-folder")
    self.private_folder = config.get("monitor", "private-folder")
    self.collector_db  = config.get("monitor", "collector-db")
    self.collect_script = config.get("monitor", "collect-script")
    self.statistic_script = config.get("monitor", "statistic-script")
    self.webdav_folder = config.get("monitor", "webdav-folder")
    self.report_script_folder = config.get("monitor", "report-folder")
    self.webdav_url = '%s/share' % config.get("monitor", "base-url")
    self.public_url = '%s/public' % config.get("monitor", "base-url")
    self.python = config.get("monitor", "python") or "python"
    self.public_path_list = config.get("monitor", "public-path-list").split()
    self.private_path_list = config.get("monitor", "private-path-list").split()
    self.monitor_url_list = config.get("monitor", "monitor-url-list").split()
    self.parameter_list = [param.strip() for param in config.get("monitor", "parameter-list").split('\n') if param]
    # Use this file to write knowledge0_cfg required by webrunner
    self.parameter_cfg_file = config.get("monitor", "parameter-file-path").strip()
    self.pid_file = config.get("monitor", "pid-file")
    self.monitor_promise_folder = softConfigGet(config, "monitor",
                                                "monitor-promise-folder")
    self.promise_timeout_file = softConfigGet(config, "monitor",
                                                "promises-timeout-file")
    self.nice_command = softConfigGet(config, "monitor",
                                                "nice-cmd")

    self.config_folder = os.path.join(self.private_folder, 'config')
    self.report_folder = self.private_folder

    self.promise_output_file = config.get("monitor", "promise-output-file")
    self.bootstrap_is_ok = True

    if self.nice_command:
      # run monitor promises script with low priority
      self.promise_runner = '%s %s' % (self.nice_command, self.promise_runner)

  def loadConfig(self, pathes, config=None):
    if config is None:
      config = ConfigParser.ConfigParser()
    try:
      config.read(pathes)
    except ConfigParser.MissingSectionHeaderError:
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
        elif (config_list[0] == 'file' or config_list[0] == 'htpasswd')  and \
            os.path.exists(config_list[2]) and os.path.isfile(config_list[2]):
          try:
            with open(config_list[2]) as cfile:
              parameter = dict(
                key=config_list[1],
                title=config_list[1],
                value=cfile.read(),
                description={
                  "type": config_list[0],
                  "file": config_list[2]
                }
              )
              if config_list[0] == 'htpasswd':
                if len(config_list) != 5 or not os.path.exists(config_list[4]):
                  print 'htpasswd file is not specified: %s' % str(config_list)
                  continue
                parameter['description']['user'] = config_list[3]
                parameter['description']['htpasswd'] = config_list[4]
              configuration_list.append(parameter)
          except OSError, e:
            print 'Cannot read file %s, Error is: %s' % (config_list[2], str(e))
            pass
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
          except OSError, e:
            print 'Cannot read file at %s, Error is: %s' % (old_cors_file, str(e))
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
          except OSError, e:
            if e.errno != os.errno.EEXIST:
              raise

  def getMonitorTitleFromUrl(self, monitor_url):
    # This file should be generated
    if not monitor_url.startswith('https://') and not monitor_url.startswith('http://'):
      return 'Unknown Instance'
    if not monitor_url.endswith('/'):
      monitor_url = monitor_url + '/'

    url  = monitor_url + '/.jio_documents/monitor.global.json' # XXX Hard Coded path
    try:
      # XXX - working here with public url
      if hasattr(ssl, '_create_unverified_context'):
        context = ssl._create_unverified_context()
        response = urllib2.urlopen(url, context=context)
      else:
        response = urllib2.urlopen(url)
    except urllib2.HTTPError:
      self.bootstrap_is_ok = False
      print "Error: Failed to get Monitor configuration at %s " % monitor_url
      return 'Unknown Instance'
    else:
      try:
        monitor_dict = json.loads(response.read())
        return monitor_dict.get('title', 'Unknown Instance')
      except ValueError, e:
        print "Bad Json file at %s" % url
        self.bootstrap_is_ok = False
    return 'Unknown Instance'

  def getReportInfoFromFilename(self, filename):
    splited_filename = filename.split('_every_')
    possible_time_list = ['hour', 'minute']
    if len(splited_filename) == 1:
      return (filename, "* * * * *")

    run_time = splited_filename[1].split('_')
    report_name = splited_filename[0]
    if len(run_time) != 2 or not run_time[1] in possible_time_list:
      return (report_name, "* * * * *")

    try:
      value = int(run_time[0])
    except ValueError:
      print "Warning: Bad report filename: %s" % filename
      return (report_name, "* * * * *")

    if run_time[1] == 'hour':
      return (report_name, "11 */%s * * *" % value)
    if run_time[1] == 'minute':
      return (report_name, "*/%s * * * *" % value)

  def configureFolders(self):
    # configure public and private folder
    self.createSymlinksFromConfig(self.webdav_folder, [self.public_folder])
    self.createSymlinksFromConfig(self.webdav_folder, [self.private_folder])

    #configure jio_documents folder
    jio_public = os.path.join(self.webdav_folder, 'jio_public')
    jio_private = os.path.join(self.webdav_folder, 'jio_private')
    mkdirAll(jio_public)
    mkdirAll(jio_private)

    createSymlink(self.public_folder,
                  os.path.join(jio_public, '.jio_documents'))
    createSymlink(self.private_folder,
                  os.path.join(jio_private, '.jio_documents'))

    self.data_folder = os.path.join(self.private_folder, 'data', '.jio_documents')
    self.document_folder = os.path.join(self.private_folder, 'documents')
    config_folder = os.path.join(self.config_folder, '.jio_documents')

    mkdirAll(self.data_folder)
    mkdirAll(config_folder)

    createSymlink(os.path.join(self.private_folder, 'data'),
                  os.path.join(jio_private, 'data'))
    createSymlink(self.config_folder, os.path.join(jio_private, 'config'))
    createSymlink(self.data_folder, self.document_folder)

    # Cleanup private folder
    for file in glob.glob("%s/*.history.json" % self.private_folder):
      try:
        os.unlink(file)
      except OSError:
        print "failed to remove file %s. Ignoring..." % file

  def makeConfigurationFiles(self):
    config_folder = os.path.join(self.config_folder, '.jio_documents')
    parameter_config_file = os.path.join(config_folder, 'config.parameters.json')
    parameter_file = os.path.join(config_folder, 'config.json')
    #mkdirAll(config_folder)

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
    except OSError, e:
      print "Error failed to create file %s" % self.parameter_cfg_file
      pass
      

  def generateOpmlFile(self, feed_url_list, output_file):

    if os.path.exists(output_file):
      creation_date = datetime.fromtimestamp(os.path.getctime(output_file)).utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")
      modification_date = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")
    else:
      creation_date = modification_date = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")

    opml_content = OPML_START % {'creation_date': creation_date,
                                  'modification_date': modification_date,
                                  'outline_title': 'Monitoring RSS Feed list',
                                  'root_title': self.root_title}

    opml_content += OPML_OUTLINE_FEED % {'title': self.title,
        'html_url': self.public_url + '/feed',
        'xml_url': self.public_url + '/feed',
        'global_url': "%s/jio_private/" % self.webdav_url}
    for feed_url in feed_url_list:
      opml_content += OPML_OUTLINE_FEED % {'title': self.getMonitorTitleFromUrl(feed_url + "/share/jio_public/"),
        'html_url': feed_url + '/public/feed',
        'xml_url': feed_url + '/public/feed',
        'global_url': "%s/share/jio_private/" % feed_url}

    opml_content += OPML_END

    with open(output_file, 'w') as wfile:
      wfile.write(opml_content)

  def generateLogrotateEntry(self, name, file_list, option_list):
    """
      Will add a new entry in logrotate.d folder. This can help to rotate data file daily
    """
    content = "%(logfiles)s {\n%(options)s\n}\n" % {
                'logfiles': ' '.join(file_list),
                'options': '\n'.join(option_list)
              }
    file_path = os.path.join(self.logrotate_d, name)
    with open(file_path, 'w') as flog:
      flog.write(content)

  def generateReportCronEntries(self):
    cron_line_list = []

    report_name_list = [name.replace('.report.json', '')
      for name in os.listdir(self.report_folder) if name.endswith('.report.json')]

    for filename in os.listdir(self.report_script_folder):
      report_script = os.path.join(self.report_script_folder, filename)
      if os.path.isfile(report_script) and os.access(report_script, os.X_OK):
        report_name, frequency = self.getReportInfoFromFilename(filename)
        # report_name = os.path.splitext(filename)[0]
        report_json_path = "%s.report.json" % report_name

        report_cmd_line = [
          frequency,
          self.promise_runner,
          '--pid_path "%s"' % os.path.join(self.service_pid_folder,
            "%s.pid" % filename),
          '--output "%s"' % os.path.join(self.report_folder,report_json_path),
          '--promise_script "%s"' % report_script,
          '--promise_name "%s"' % report_name,
          '--monitor_url "%s/jio_private/"' % self.webdav_url, # XXX hardcoded,
          '--history_folder "%s"' % self.data_folder,
          '--instance_name "%s"' % self.title,
          '--hosting_name "%s"' % self.root_title,
          '--promise_type "report"']

        cron_line_list.append(' '.join(report_cmd_line))

      if report_name in report_name_list:
        report_name_list.pop(report_name_list.index(report_name))

    # cleanup removed report json result
    if report_name_list != []:
      for report_name in report_name_list:
        result_path = os.path.join(self.report_folder, '%s.report.json' % report_name)
        if os.path.exists(result_path):
          try:
            os.unlink(result_path)
          except OSError, e:
            print "Error: Failed to delete %s" % result_path, str(e)
            pass

    with open(self.crond_folder + "/monitor-reports", "w") as freport:
      freport.write("\n".join(cron_line_list))

  def generateServiceCronEntries(self):
    # XXX only if at least one configuration file is modified, then write in the cron

    service_name_list = [name.replace('.status.json', '')
      for name in os.listdir(self.public_folder) if name.endswith('.status.json')]

    promise_cmd_line = [
      "* * * * *",
      "sleep $((1 + RANDOM % 20)) &&", # Sleep between 1 to 20 seconds
      self.promise_runner,
      '--pid_path "%s"' % os.path.join(self.service_pid_folder,
        "monitor-promises.pid"),
      '--output "%s"' % self.public_folder,
      '--promise_folder "%s"' % self.promise_folder,
      '--timeout_file "%s"' % self.promise_timeout_file,
      '--monitor_promise_folder "%s"' % self.monitor_promise_folder,
      '--monitor_url "%s/jio_private/"' % self.webdav_url, # XXX hardcoded,
      '--history_folder "%s"' % self.public_folder,
      '--instance_name "%s"' % self.title,
      '--hosting_name "%s"' % self.root_title]

    registered_promise_list = os.listdir(self.promise_folder)
    registered_promise_list.extend(os.listdir(self.monitor_promise_folder))
    delete_promise_list = []
    for service_name in service_name_list:
      if not service_name in registered_promise_list:
        delete_promise_list.append(service_name)

    if delete_promise_list != []:
      # XXX Some service was removed, delete his status file so monitor will not consider the status anymore
      for service_name in delete_promise_list:
        status_path = os.path.join(self.public_folder, '%s.status.json' % service_name)
        if os.path.exists(status_path):
          try:
            os.unlink(status_path)
          except OSError, e:
            print "Error: Failed to delete %s" % status_path, str(e)
            pass

    with open(self.crond_folder + "/monitor-promises", "w") as fp:
      fp.write(' '.join(promise_cmd_line))

  def addCronEntry(self, name, frequency, command):
    entry_line = '%s %s' % (frequency, command)
    cron_entry_file = os.path.join(self.crond_folder, name)
    with open(cron_entry_file, "w") as cronf:
      cronf.write(entry_line)

  def bootstrapMonitor(self):

    if os.path.exists(self.promise_output_file):
      os.unlink(self.promise_output_file)

    # save pid of current process into file
    with open(self.pid_file, 'w') as pid_file:
      pid_file.write(str(os.getpid()))

    # create symlinks from monitor.conf
    self.createSymlinksFromConfig(self.public_folder, self.public_path_list)
    self.createSymlinksFromConfig(self.private_folder, self.private_path_list)

    self.configureFolders()

    # Generate OPML file
    self.generateOpmlFile(self.monitor_url_list,
      os.path.join(self.public_folder, 'feeds'))

    # put promises to a cron file
    self.generateServiceCronEntries()

    # put report script to cron
    self.generateReportCronEntries()

    # Generate parameters files and scripts
    self.makeConfigurationFiles()

    # Rotate monitor data files
    option_list = [
      'daily', 'nocreate', 'olddir %s' % self.data_folder, 'rotate 5',
      'nocompress', 'missingok', 'extension .json', 'dateext',
      'dateformat -%Y-%m-%d', 'notifempty'
    ]
    file_list = [
      "%s/*.data.json" % self.private_folder,
      "%s/*.data.json" % self.data_folder]
    self.generateLogrotateEntry('monitor.data', file_list, option_list)

    # Rotate public history status file, delete data of previous days
    option_list = [
      'daily', 'nocreate', 'rotate 0',
      'nocompress', 'notifempty', 'prerotate',
      '   %s --history_folder %s' % (self.statistic_script, self.public_folder), 
      'endscript'
    ]
    file_list = ["%s/*.history.json" % self.public_folder]
    self.generateLogrotateEntry('monitor.service.status', file_list, option_list)

    # Add cron entry for SlapOS Collect
    command = "sleep $((1 + RANDOM % 60)) && " # Random sleep between 1 to 60 seconds
    if self.nice_command:
      # run monitor collect with low priority
      command += '%s ' % self.nice_command
    command += "%s --output_folder %s --collector_db %s" % (
      self.collect_script, self.data_folder, self.collector_db)
    self.addCronEntry('monitor_collect', '* * * * *', command)

    # Write an empty file when monitor bootstrap went until the end
    if self.bootstrap_is_ok:
      with open(self.promise_output_file, 'w') as promise_file:
        promise_file.write("")

    return 0


def main():
  parser = parseArguments()

  monitor = Monitoring(parser.config_file)
  
  sys.exit(monitor.bootstrapMonitor())
