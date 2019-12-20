from zope.interface import implementer
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise

import datetime
import email.utils
import json
import os
import time
try:
  from urlparse import urlparse
except ImportError:
  from urllib.parse import urlparse


@implementer(interface.IPromise)
class RunPromise(GenericPromise):
  EXTENDED_STATUS_CODE_MAPPING = {
    '520': 'Too many redirects',
    '523': 'Connection error',
    '524': 'Connection timeout',
    '526': 'SSL Error',

  }

  def __init__(self, config):
    super(RunPromise, self).__init__(config)
    # Set frequency compatible to default surykatka interval - 2 minutes
    self.setPeriodicity(float(self.getConfig('frequency', 2)))
    self.error_list = []
    self.info_list = []

  def appendError(self, message):
    self.error_list.append(message)

  def appendInfo(self, message):
    self.info_list.append(message)

  def emitLog(self):
   if len(self.error_list) > 0:
     emit = self.logger.error
   else:
     emit = self.logger.info

   emit(' '.join(self.error_list + self.info_list))

  def senseBotStatus(self):
    key = 'bot_status'

    def logError(msg, *args):
      self.appendError(key + ': ' + msg % args)

    if key not in self.surykatka_json:
      logError("%r not in %r", key, self.json_file)
      return
    bot_status_list = self.surykatka_json[key]
    if len(bot_status_list) == 0:
      logError("%r empty in %r", key, self.json_file)
      return
    bot_status = bot_status_list[0]
    if bot_status.get('text') != 'loop':
      logError("No type loop detected in %r", self.json_file)
      return
    timetuple = email.utils.parsedate(bot_status['date'])
    last_bot_datetime = datetime.datetime.fromtimestamp(time.mktime(timetuple))
    last_bot_datetime_string = email.utils.formatdate(time.mktime(timetuple))
    delta = self.utcnow - last_bot_datetime
    # sanity check
    if delta < datetime.timedelta(minutes=0):
      logError('Last bot datetime %s is in future, UTC now %s',
               last_bot_datetime_string, self.utcnow_string)
      return
    if delta > datetime.timedelta(minutes=15):
      logError('Last bot datetime %s is more than 15 minutes old, UTC now %s',
               last_bot_datetime_string, self.utcnow_string)
      return

    self.appendInfo(
      '%s: Last bot status from %s ok, UTC now is %s' %
      (key, last_bot_datetime_string, self.utcnow_string))

  def senseSslCertificate(self):
    key = 'ssl_certificate'

    def appendError(msg, *args):
      self.appendError(key + ': ' + msg % args)

    url = self.getConfig('url')
    parsed_url = urlparse(url)
    if parsed_url.scheme == 'https':
      hostname = parsed_url.netloc
      ssl_check = True
      certificate_expiration_days = self.getConfig(
        'certificate-expiration-days', '15')
      try:
        certificate_expiration_days = int(certificate_expiration_days)
      except ValueError:
        certificate_expiration_days = None
    else:
      ssl_check = False
      certificate_expiration_days = None
    if ssl_check is None:
      return
    if certificate_expiration_days is None:
      appendError(
        'certificate-expiration-days %r is incorrect',
        self.getConfig('certificate-expiration-days'))
      return
    if not hostname:
      appendError('url %r is incorrect', url)
      return
    if key not in self.surykatka_json:
      appendError(
        'No data for %s . If the error persist, please update surykatka.', url)
      return
    entry_list = [
      q for q in self.surykatka_json[key] if q['hostname'] == hostname]
    if len(entry_list) == 0:
      appendError('No data for %s', url)
      return
    for entry in entry_list:
      timetuple = email.utils.parsedate(entry['not_after'])
      certificate_expiration_time = datetime.datetime.fromtimestamp(
        time.mktime(timetuple))
      if certificate_expiration_time - datetime.timedelta(
        days=certificate_expiration_days) < self.utcnow:
        appendError(
          'Certificate for %s will expire on %s, which is less than %s days, '
          'UTC now is %s',
          url, entry['not_after'], certificate_expiration_days,
          self.utcnow_string)
        return
      else:
        self.appendInfo(
          '%s: Certificate for %s will expire on %s, which is more than %s '
          'days, UTC now is %s' %
          (key, url, entry['not_after'], certificate_expiration_days,
           self.utcnow_string))
        return

  def senseHttpQuery(self):
    key = 'http_query'
    error_list = []

    def logError(msg, *args):
      self.appendError(key + ': ' + msg % args)

    if key not in self.surykatka_json:
      logError("%r not in %r", key, self.json_file)
      return

    url = self.getConfig('url')
    status_code = self.getConfig('status-code')
    ip_list = self.getConfig('ip-list', '').split()

    entry_list = [q for q in self.surykatka_json[key] if q['url'] == url]
    if len(entry_list) == 0:
      logError('No data for %s', url)
      return
    error_list = []
    for entry in entry_list:
      entry_status_code = str(entry['status_code'])
      if entry_status_code != status_code:
        status_code_explanation = self.EXTENDED_STATUS_CODE_MAPPING.get(
          entry_status_code)
        if status_code_explanation:
          status_code_explanation = '%s (%s)' % (
            entry_status_code, status_code_explanation)
        else:
          status_code_explanation = entry_status_code
        error_list.append(
          'IP %s got status code %s instead of %s' % (
            entry['ip'], status_code_explanation, status_code))
    db_ip_list = [q['ip'] for q in entry_list]
    if len(ip_list):
      if set(ip_list) != set(db_ip_list):
        error_list.append(
          'expected IPs %s differes from got %s' % (
            ' '.join(ip_list), ' '.join(db_ip_list)))
    if len(error_list):
      logError('Problem with %s : ' % (url,) + ', '.join(error_list))
      return
    if len(ip_list) > 0:
      self.appendInfo(
        '%s: %s replied correctly with status code %s on ip list %s' %
        (key, url, status_code, ' '.join(ip_list)))
    else:
      self.appendInfo(
        '%s: %s replied correctly with status code %s' %
        (key, url, status_code))

  def sense(self):
    """
      Check if frontend URL is available
    """
    test_utcnow = self.getConfig('test-utcnow')
    if test_utcnow:
      self.utcnow = datetime.datetime.fromtimestamp(
        time.mktime(email.utils.parsedate(test_utcnow)))
      self.utcnow_string = test_utcnow
    else:
      self.utcnow = datetime.datetime.utcnow()
      self.utcnow_string = email.utils.formatdate(time.mktime(
        self.utcnow.timetuple()))

    self.json_file = self.getConfig('json-file', '')
    if not os.path.exists(self.json_file):
      self.appendError('File %r does not exists' % self.json_file)
    else:
      with open(self.json_file) as fh:
        try:
          self.surykatka_json = json.load(fh)
        except Exception:
          self.appendError("Problem loading JSON from %r" % self.json_file)
        else:
          report = self.getConfig('report')
          if report == 'bot_status':
            self.senseBotStatus()
          elif report == 'http_query':
            self.senseHttpQuery()
            self.senseSslCertificate()
          else:
            self.appendError("Report %r is not supported" % report)
    self.emitLog()

  def anomaly(self):
    return self._test(result_count=3, failure_amount=3)
