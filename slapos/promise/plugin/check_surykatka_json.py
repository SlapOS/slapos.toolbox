from zope.interface import implementer
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise

import datetime
import email.utils
import json
import os
import time
from six.moves.urllib.parse import urlparse


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
    self.failure_amount = int(
      self.getConfig('failure-amount', self.getConfig('failure_amount', 1)))
    self.result_count = self.failure_amount
    self.error_list = []
    self.info_list = []
    # Make promise test-less, as it's result is not important for instantiation
    self.setTestLess()

  def appendErrorMessage(self, message):
    self.error_list.append(message)

  def appendInfoMessage(self, message):
    self.info_list.append(message)

  def emitLog(self):
   if len(self.error_list) > 0:
     emit = self.logger.error
   else:
     emit = self.logger.info

   message_list = self.error_list + self.info_list
   url = self.getConfig('url')
   if url:
     message_list.insert(0, '%s :' % (url,))
   emit(' '.join(message_list))

  def senseBotStatus(self):
    key = 'bot_status'

    def appendError(msg, *args):
      self.appendErrorMessage(key + ': ERROR ' + msg % args)

    if key not in self.surykatka_json:
      appendError("%r not in %r", key, self.json_file)
      return
    bot_status_list = self.surykatka_json[key]
    if len(bot_status_list) == 0:
      appendError("%r empty in %r", key, self.json_file)
      return
    bot_status = bot_status_list[0]
    if bot_status.get('text') != 'loop':
      appendError(
        "bot_status is %r instead of 'loop' in %r",
        str(bot_status.get('text')), self.json_file)
      return
    timetuple = email.utils.parsedate(bot_status['date'])
    last_bot_datetime = datetime.datetime.fromtimestamp(time.mktime(timetuple))
    last_bot_datetime_string = email.utils.formatdate(time.mktime(timetuple))
    delta = self.utcnow - last_bot_datetime
    # sanity check
    if delta < datetime.timedelta(minutes=0):
      appendError('Last bot datetime %s is in future',
                  last_bot_datetime_string,)
      return
    if delta > datetime.timedelta(minutes=15):
      appendError(
        'Last bot datetime %s is more than 15 minutes old',
        last_bot_datetime_string,)
      return

    self.appendInfoMessage(
      '%s: OK Last bot status from %s' %
      (key, last_bot_datetime_string,))

  def senseSslCertificate(self):
    key = 'ssl_certificate'

    def appendError(msg, *args):
      self.appendErrorMessage(key + ': ERROR ' + msg % args)

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
    if not ssl_check:
      return
    if certificate_expiration_days is None:
      appendError(
        'certificate-expiration-days %r is incorrect',
        self.getConfig('certificate-expiration-days'))
      return
    if not hostname:
      appendError('url is incorrect')
      return
    if key not in self.surykatka_json:
      appendError(
        'No key %r. If the error persist, please update surykatka.' % (key,))
      return
    entry_list = [
      q for q in self.surykatka_json[key] if q['hostname'] == hostname]
    if len(entry_list) == 0:
      appendError('No data')
      return
    for entry in entry_list:
      timetuple = email.utils.parsedate(entry['not_after'])
      if timetuple is None:
        appendError('No certificate information for %s' % (entry['ip']))
      else:
        certificate_expiration_time = datetime.datetime.fromtimestamp(
          time.mktime(timetuple))
        if certificate_expiration_time - datetime.timedelta(
          days=certificate_expiration_days) < self.utcnow:
          appendError(
            'Certificate on %s will expire on %s, which is less than %s days',
            entry['ip'], entry['not_after'], certificate_expiration_days)
          return
        else:
          self.appendInfoMessage(
            '%s: OK Certificate on %s will expire on %s, which is more than '
            '%s days' % (
              key, entry['ip'], entry['not_after'],
              certificate_expiration_days))
          return

  def senseHttpQuery(self):
    key = 'http_query'
    error = False

    def appendError(msg, *args):
      self.appendErrorMessage(key + ': ERROR ' + msg % args)

    if key not in self.surykatka_json:
      appendError("%r not in %r", key, self.json_file)
      return

    url = self.getConfig('url')
    status_code = self.getConfig('status-code')
    ip_list = self.getConfig('ip-list', '').split()
    http_header_dict = json.loads(self.getConfig('http-header-dict', '{}'))

    entry_list = [q for q in self.surykatka_json[key] if q['url'] == url]
    if len(entry_list) == 0:
      appendError('No data')
      return
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
        appendError(
          'IP %s got status code %s instead of %s' % (
            entry['ip'], status_code_explanation, status_code))
        error = True
      if http_header_dict and http_header_dict != entry['http_header_dict']:
        appendError(
          'HTTP Header dict was %s instead of %s' % (
            json.dumps(entry['http_header_dict'], sort_keys=True),
            json.dumps(http_header_dict, sort_keys=True),
        ))
        error = True
    db_ip_list = [q['ip'] for q in entry_list]
    if len(ip_list):
      if set(ip_list) != set(db_ip_list):
        appendError(
          'expected IPs %s differes from got %s' % (
            ' '.join(ip_list), ' '.join(db_ip_list)))
        error = True
    if error:
      return
    info_message = '%s: OK with status code %s' % (key, status_code)
    if http_header_dict:
      info_message += ' and HTTP Header dict %s' % (
        json.dumps(http_header_dict, sort_keys=True),
      )
    if len(ip_list) > 0:
      info_message += ' on IPs %s' % (' '.join(ip_list))
    self.appendInfoMessage(info_message)

  def senseElapsedTime(self):
    key = 'elapsed_time'
    surykatka_key = 'http_query'

    def appendError(msg, *args):
      self.appendErrorMessage(key + ': ERROR ' + msg % args)

    if surykatka_key not in self.surykatka_json:
      appendError(
        'No key %r. If the error persist, please update surykatka.' % (
          surykatka_key,))
      return

    url = self.getConfig('url')
    maximum_elapsed_time = self.getConfig('maximum-elapsed-time')

    entry_list = [
      q for q in self.surykatka_json[surykatka_key] if q['url'] == url]
    if len(entry_list) == 0:
      appendError('No data')
      return
    for entry in entry_list:
      if maximum_elapsed_time:
        if 'total_seconds' in entry:
          maximum_elapsed_time = float(maximum_elapsed_time)
          if entry['total_seconds'] == 0.:
            appendError('IP %s failed to reply' % (entry['ip']))
          elif entry['total_seconds'] > maximum_elapsed_time:
            appendError(
              'IP %s replied in %.2fs which is longer than '
              'maximum %.2fs' %
              (entry['ip'], entry['total_seconds'], maximum_elapsed_time))
          else:
            self.appendInfoMessage(
              '%s: OK IP %s replied in %.2fs which is shorter than '
              'maximum %.2fs' % (key, entry['ip'],
                                 entry['total_seconds'], maximum_elapsed_time))

  def sense(self):
    """
      Check if frontend URL is available
    """
    test_utcnow = self.getConfig('test-utcnow')
    if test_utcnow:
      self.utcnow = datetime.datetime.fromtimestamp(
        time.mktime(email.utils.parsedate(test_utcnow)))
    else:
      self.utcnow = datetime.datetime.utcnow()

    self.json_file = self.getConfig('json-file', '')
    if not os.path.exists(self.json_file):
      self.appendErrorMessage('ERROR File %r does not exists' % self.json_file)
    else:
      with open(self.json_file) as fh:
        try:
          self.surykatka_json = json.load(fh)
        except Exception:
          self.appendErrorMessage(
            "ERROR loading JSON from %r" % self.json_file)
        else:
          report = self.getConfig('report')
          if report == 'bot_status':
            self.senseBotStatus()
          elif report == 'http_query':
            self.senseHttpQuery()
            self.senseSslCertificate()
            self.senseElapsedTime()
          else:
            self.appendErrorMessage(
              "ERROR Report %r is not supported" % report)
    self.emitLog()

  def anomaly(self):
    return self._test(
      result_count=self.result_count, failure_amount=self.failure_amount)
