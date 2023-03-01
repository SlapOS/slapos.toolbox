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
    self.error = False
    self.message_list = []
    # Make promise test-less, as it's result is not important for instantiation
    self.setTestLess()

  def appendMessage(self, message):
    self.message_list.append(message)

  def emitLog(self):
   if self.error:
     emit = self.logger.error
   else:
     emit = self.logger.info

   url = self.getConfig('url')
   if url:
     self.message_list.insert(0, '%s :' % (url,))
   emit(' '.join(self.message_list))

  def senseBotStatus(self):
    key = 'bot_status'

    def appendError(msg, *args):
      self.error = True
      self.appendMessage(key + ': ERROR ' + msg % args)

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
    delta = self.utcnow - last_bot_datetime
    # sanity check
    if delta < datetime.timedelta(minutes=0):
      appendError('Last bot datetime is in future')
      return
    if delta > datetime.timedelta(minutes=15):
      appendError('Last bot datetime is more than 15 minutes old')
      return

    self.appendMessage('%s: OK Last bot status' % (key,))

  def senseSslCertificate(self):
    key = 'ssl_certificate'

    def appendError(msg, *args):
      self.error = True
      self.appendMessage(key + ': ERROR ' + msg % args)

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
      self.appendMessage('%s: OK No check needed' % (key,))
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
    if len(entry_list) > 0:
      self.appendMessage('%s:' % (key,))

    def addError(msg, *args):
      self.error = True
      self.appendMessage('ERROR ' + msg % args)
    for entry in entry_list:
      timetuple = email.utils.parsedate(entry['not_after'])
      if timetuple is None:
        addError('IP %s no information' % (entry['ip'],))
      else:
        certificate_expiration_time = datetime.datetime.fromtimestamp(
          time.mktime(timetuple))
        if certificate_expiration_time - datetime.timedelta(
          days=certificate_expiration_days) < self.utcnow:
          addError(
            'IP %s will expire in < %s days',
            entry['ip'], certificate_expiration_days)
        else:
          self.appendMessage(
            'OK IP %s will expire in > %s days' % (
              entry['ip'], certificate_expiration_days))

  def senseHttpQuery(self):
    key = 'http_query'

    def appendError(msg, *args):
      self.error = True
      self.appendMessage(key + ': ERROR ' + msg % args)

    if key not in self.surykatka_json:
      appendError("%r not in %r", key, self.json_file)
      return

    url = self.getConfig('url')
    status_code = self.getConfig('status-code')
    http_header_dict = json.loads(self.getConfig('http-header-dict', '{}'))

    entry_list = [q for q in self.surykatka_json[key] if q['url'] == url]
    if len(entry_list) == 0:
      appendError('No data')
      return

    def addError(msg, *args):
      self.error = True
      self.appendMessage('ERROR ' + msg % args)
    self.appendMessage('%s:' % (key,))
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
        addError(
          'IP %s expected status_code %s != %s' % (
            entry['ip'], status_code_explanation, status_code))
      else:
        self.appendMessage(
          'OK IP %s status_code %s' % (entry['ip'], status_code))
      if http_header_dict:
        if http_header_dict != entry['http_header_dict']:
          addError(
            'IP %s expected HTTP Header %s != of %s' % (
              entry['ip'],
              json.dumps(http_header_dict, sort_keys=True),
              json.dumps(entry['http_header_dict'], sort_keys=True)))
        else:
          self.appendMessage(
            'OK IP %s HTTP Header %s' % (
              entry['ip'], json.dumps(http_header_dict, sort_keys=True)))

  def senseDnsQuery(self):
    key = 'dns_query'

    def appendError(msg, *args):
      self.error = True
      self.appendMessage(key + ': ERROR ' + msg % args)

    if key not in self.surykatka_json:
      appendError("%r not in %r", key, self.json_file)
      return

    url = self.getConfig('url')
    hostname = urlparse(url).hostname
    ip_set = set(self.getConfig('ip-list', '').split())

    entry_list = [
      q for q in self.surykatka_json[key]
      if q['domain'] == hostname and q['rdtype'] == 'A']
    if len(entry_list) == 0:
      appendError('No data')
      return

    self.appendMessage('%s:' % (key,))
    if len(ip_set):
      for entry in entry_list:
        response_ip_set = set([
          q.strip() for q in entry['response'].split(",") if q.strip()])
        if ip_set != response_ip_set:
          self.error = True
          self.appendMessage(
            "ERROR resolver %s expected %s != %s" % (
              entry['resolver_ip'], ' '.join(sorted(ip_set)),
              ' '.join(sorted(response_ip_set)) or "empty-reply"))
        else:
          self.appendMessage(
            "OK resolver %s returned expected set of IPs %s" % (
              entry['resolver_ip'], ' '.join(sorted(ip_set)),))
    else:
      self.appendMessage('OK No check configured')

  def senseTcpServer(self):
    key = 'tcp_server'

    def appendError(msg, *args):
      self.error = True
      self.appendMessage(key + ': ERROR ' + msg % args)

    if key not in self.surykatka_json:
      appendError("%r not in %r", key, self.json_file)
      return

    url = self.getConfig('url')
    parsed_url = urlparse(url)
    hostname = parsed_url.hostname
    if parsed_url.port is not None:
      port = parsed_url.port
    else:
      if parsed_url.scheme == 'https':
        port = 443
      else:
        port = 80
    ip_set = set(self.getConfig('ip-list', '').split())

    entry_list = [
      q for q in self.surykatka_json[key]
      if hostname in [
        r.strip() for r in q['domain'].split(',')] and q['port'] == port]
    if len(entry_list) == 0:
      appendError('No data')
      return
    self.appendMessage('%s:' % (key,))
    if len(ip_set) > 0:
      for ip in sorted(ip_set):
        ok = False
        for entry in entry_list:
          if entry['ip'] == ip:
            if entry['state'] == 'closed':
              ok = False
              break
            if entry['state'] == 'open':
              ok = True
        if ok:
          self.appendMessage('OK IP %s:%s' % (ip, port))
        else:
          self.error = True
          self.appendMessage('ERROR IP %s:%s' % (ip, port))
    else:
      self.appendMessage('OK No check configured')

  def senseElapsedTime(self):
    key = 'elapsed_time'
    surykatka_key = 'http_query'

    def appendError(msg, *args):
      self.error = True
      self.appendMessage('ERROR ' + msg % args)

    if surykatka_key not in self.surykatka_json:
      self.error = True
      self.appendMessage(
        '%s: ERROR No key %r. If the error persist, please update '
        'surykatka.' % (
          key, surykatka_key,))
      return

    url = self.getConfig('url')
    maximum_elapsed_time = self.getConfig('maximum-elapsed-time')

    entry_list = [
      q for q in self.surykatka_json[surykatka_key] if q['url'] == url]
    if len(entry_list) == 0:
      self.error = True
      self.appendMessage('%s: ERROR No data' % (key,))
      return
    self.appendMessage('%s:' % (key,))
    if maximum_elapsed_time:
      found = False
      for entry in entry_list:
        if 'total_seconds' in entry:
          found = True
          maximum_elapsed_time = float(maximum_elapsed_time)
          if entry['total_seconds'] == 0.:
            appendError('IP %s failed to reply' % (entry['ip']))
          elif entry['total_seconds'] > maximum_elapsed_time:
            appendError(
              'IP %s replied > %.2fs' %
              (entry['ip'], maximum_elapsed_time))
          else:
            self.appendMessage(
              'OK IP %s replied < %.2fs' % (
                entry['ip'], maximum_elapsed_time))
      if not found:
        appendError("No matching entry found")
    else:
      self.appendMessage("OK No check configured")

  def sense(self):
    """
      Check if frontend URL is available
    """
    self.utcnow = datetime.datetime.utcnow()

    self.json_file = self.getConfig('json-file', '')
    if not os.path.exists(self.json_file):
      self.error = True
      self.appendMessage('ERROR File %r does not exists' % self.json_file)
    else:
      with open(self.json_file) as fh:
        try:
          self.surykatka_json = json.load(fh)
        except Exception:
          self.error = True
          self.appendMessage(
            "ERROR loading JSON from %r" % self.json_file)
        else:
          report = self.getConfig('report')
          if report == 'bot_status':
            self.senseBotStatus()
          elif report == 'http_query':
            self.senseDnsQuery()
            self.senseTcpServer()
            self.senseHttpQuery()
            self.senseSslCertificate()
            self.senseElapsedTime()
          else:
            self.error = True
            self.appendMessage(
              "ERROR Report %r is not supported" % report)
    self.emitLog()

  def anomaly(self):
    return self._test(
      result_count=self.result_count, failure_amount=self.failure_amount)
