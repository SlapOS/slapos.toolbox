# -*- coding: utf-8 -*-
# vim: set et sts=2:
# pylint: disable-msg=W0311,C0301,C0103,C0111,R0904,R0903

import ConfigParser
import datetime
import logging
import logging.handlers
import os
from slapos.htpasswd import HtpasswdFile
from slapos.runner.process import setHandler
import sys
from slapos.runner.utils import runInstanceWithLock, updateProxy, startProxy
from slapos.runner.views import *

TRUE_VALUES = (1, '1', True, 'true', 'True')

class Config:
  def __init__(self):
    self.configuration_file_path = None
    self.console = None
    self.log_file = None
    self.logger = None
    self.verbose = None

  def setConfig(self):
    """
    Set options given by parameters.
    """
    self.configuration_file_path = os.path.abspath(os.getenv('RUNNER_CONFIG'))

    # Load configuration file
    configuration_parser = ConfigParser.SafeConfigParser()
    configuration_parser.read(self.configuration_file_path)

    for section in ("slaprunner", "slapos", "slapproxy", "slapformat",
                    "sshkeys_authority", "gitclient", "cloud9_IDE"):
      configuration_dict = dict(configuration_parser.items(section))
      for key in configuration_dict:
        if not getattr(self, key, None):
          setattr(self, key, configuration_dict[key])

    # set up logging
    self.logger = logging.getLogger("slaprunner")
    self.logger.setLevel(logging.INFO)
    if self.console:
      self.logger.addHandler(logging.StreamHandler())

    self.log_file = self.log_dir + '/slaprunner.log'
    if not os.path.isdir(os.path.dirname(self.log_file)):
    # fallback to console only if directory for logs does not exists and
    # continue to run
      raise ValueError('Please create directory %r to store %r log file' % (
      os.path.dirname(self.log_file), self.log_file))
    else:
      file_handler = logging.FileHandler(self.log_file)
      file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
      self.logger.addHandler(file_handler)
      self.logger.info('Configured logging to file %r' % self.log_file)

    self.logger.info("Started.")
    self.logger.info(os.environ['PATH'])
    if self.verbose:
      self.logger.setLevel(logging.DEBUG)
      self.logger.debug("Verbose mode enabled.")


def checkHtpasswd(config):
  """XXX:set for backward compatiblity
  create a htpassword if etc/.users exist"""
  user = os.path.join(config['etc_dir'], '.users')
  htpasswdfile = os.path.join(config['etc_dir'], '.htpasswd')
  if os.path.exists(user) and not os.path.exists(htpasswdfile):
    data = open(user).read().strip().split(';')
    htpasswd = HtpasswdFile(htpasswdfile, create=True)
    htpasswd.update(data[0], data[1])
    htpasswd.save()
  else:
    return

def checkJSONConfig(config):
  """create a default json file with some parameters inside
  if the file has never been created"""
  json_file = os.path.join(config['etc_dir'], 'config.json')
  if not os.path.exists(json_file):
    params = {
      'run_instance' : True,
      'run_software' : True,
      'max_run_instance' : 3,
      'max_run_software' : 2
    }
    open(json_file, "w").write(json.dumps(params))
    

def run():
  "Run default configuration."
  # Parse arguments
  config = Config()
  config.setConfig()

  if os.getuid() == 0:
    # avoid mistakes (mainly in development mode)
    raise Exception('Do not run SlapRunner as root.')

  serve(config)

def serve(config):
  from werkzeug.contrib.fixers import ProxyFix
  workdir = os.path.join(config.runner_workdir, 'project')
  software_link = os.path.join(config.runner_workdir, 'softwareLink')
  app.config.update(**config.__dict__)
  app.config.update(
    software_log=config.software_root.rstrip('/') + '.log',
    instance_log=config.instance_root.rstrip('/') + '.log',
    workspace=workdir,
    software_link=software_link,
    instance_profile='instance.cfg',
    software_profile='software.cfg',
    SECRET_KEY=os.urandom(24),
    PERMANENT_SESSION_LIFETIME=datetime.timedelta(days=31),
  )
  checkHtpasswd(app.config)
  checkJSONConfig(app.config)
  if not os.path.exists(workdir):
    os.mkdir(workdir)
  if not os.path.exists(software_link):
    os.mkdir(software_link)
  setHandler()
  startProxy(app.config)
  updateProxy(app.config)
  config.logger.info('Running slapgrid...')
  if app.config['auto_deploy_instance'] in TRUE_VALUES:
    runInstanceWithLock(app.config)
  config.logger.info('Done.')
  app.wsgi_app = ProxyFix(app.wsgi_app)

run()
