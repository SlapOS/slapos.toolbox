from zope.interface import implementer
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise

import datetime
import email.utils
import json
import os
import time
from six.moves.urllib.parse import urlparse
import operator


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
    self.enabled_sense_list = self.getConfig(
      'enabled-sense-list',
      'dns_query whois tcp_server http_query ssl_certificate'
      ' elapsed_time').split()
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

  def appendError(self, message):
    self.error = True
    self.message_list.extend(['ERROR', message])

  def appendOk(self, message):
    self.message_list.extend(['OK', message])

  def senseBotStatus(self):
    key = 'bot_status'
    self.appendMessage('%s:' % (key, ))

    if key not in self.surykatka_json:
      self.appendError("%r not in %r" % (key, self.json_file))
      return
    bot_status_list = self.surykatka_json[key]
    if len(bot_status_list) == 0:
      self.appendError("%r empty in %r" % (key, self.json_file))
      return
    bot_status = bot_status_list[0]
    if bot_status.get('text') != 'loop':
      self.appendError(
        "bot_status is %r instead of 'loop' in %r" % (str(
          bot_status.get('text')), self.json_file))
      return
    timetuple = email.utils.parsedate(bot_status['date'])
    last_bot_datetime = datetime.datetime.fromtimestamp(time.mktime(timetuple))
    delta = self.utcnow - last_bot_datetime
    # sanity check
    if delta < datetime.timedelta(minutes=0):
      self.appendError('Last bot datetime is in future')
      return
    if delta > datetime.timedelta(minutes=15):
      self.appendError('Last bot datetime is more than 15 minutes old')
      return

    self.appendOk('Last bot status')

  def senseSslCertificate(self):
    key = 'ssl_certificate'
    self.appendMessage('%s:' % (key, ))

    url = self.getConfig('url')
    parsed_url = urlparse(url)
    if parsed_url.scheme == 'https':
      hostname = parsed_url.netloc
      certificate_expiration_days = self.getConfig(
        'certificate-expiration-days', '15')
      try:
        certificate_expiration_days = int(certificate_expiration_days)
      except ValueError:
        self.appendError(
          'certificate-expiration-days %r is incorrect' % (
            self.getConfig('certificate-expiration-days')))
    else:
      self.appendOk('No check needed')
      return
    if not hostname:
      self.appendError('url is incorrect')
      return
    if key not in self.surykatka_json:
      self.appendError("%r not in %r" % (key, self.json_file))
      return

    entry_list = [
      q for q in self.surykatka_json[key] if q['hostname'] == hostname]
    if len(entry_list) == 0:
      self.appendError('No data')
      return

    for entry in sorted(entry_list, key=operator.itemgetter('ip')):
      timetuple = email.utils.parsedate(entry['not_after'])
      if timetuple is None:
        self.appendError('IP %s no information' % (entry['ip'],))
      else:
        certificate_expiration_time = datetime.datetime.fromtimestamp(
          time.mktime(timetuple))
        if certificate_expiration_time - datetime.timedelta(
          days=certificate_expiration_days) < self.utcnow:
          self.appendError(
            'IP %s expires in < %s days' % (
              entry['ip'], certificate_expiration_days))
        else:
          self.appendOk(
            'IP %s expires in > %s days' % (
              entry['ip'], certificate_expiration_days))

  def senseHttpQuery(self):
    key = 'http_query'
    self.appendMessage('%s:' % (key, ))

    if key not in self.surykatka_json:
      self.appendError("%r not in %r" % (key, self.json_file))
      return

    url = self.getConfig('url')
    status_code = self.getConfig('status-code')
    http_header_dict = json.loads(self.getConfig('http-header-dict', '{}'))

    entry_list = [q for q in self.surykatka_json[key] if q['url'] == url]
    if len(entry_list) == 0:
      self.appendError('No data')
      return

    for entry in sorted(entry_list, key=operator.itemgetter('ip')):
      entry_status_code = str(entry['status_code'])
      if entry_status_code != status_code:
        status_code_explanation = self.EXTENDED_STATUS_CODE_MAPPING.get(
          entry_status_code)
        if status_code_explanation:
          status_code_explanation = '%s (%s)' % (
            entry_status_code, status_code_explanation)
        else:
          status_code_explanation = entry_status_code
        self.appendError(
          'IP %s status_code %s != %s' % (
            entry['ip'], status_code_explanation, status_code))
      else:
        self.appendOk(
          'IP %s status_code %s' % (entry['ip'], status_code))
      if http_header_dict:
        if http_header_dict != entry['http_header_dict']:
          self.appendError(
            'IP %s HTTP Header %s != %s' % (
              entry['ip'],
              json.dumps(http_header_dict, sort_keys=True),
              json.dumps(entry['http_header_dict'], sort_keys=True)))
        else:
          self.appendOk(
            'IP %s HTTP Header %s' % (
              entry['ip'], json.dumps(http_header_dict, sort_keys=True)))

  def senseDnsQuery(self):
    key = 'dns_query'
    self.appendMessage('%s:' % (key, ))

    if key not in self.surykatka_json:
      self.appendError("%r not in %r" % (key, self.json_file))
      return

    url = self.getConfig('url')
    hostname = urlparse(url).hostname
    ip_set = set(self.getConfig('ip-list', '').split())

    entry_dict = {}
    for q in self.surykatka_json[key]:
      if q['domain'] == hostname and q['rdtype'] in ('A', 'AAAA'):
        if not q['resolver_ip'] in entry_dict:
          entry_dict[q['resolver_ip']] = {
            'domain': q['domain'],
            'response_ip_set': set()
          }
        entry_dict[q['resolver_ip']]['response_ip_set'].update([r.strip() for r in q['response'].split(",") if r.strip()])

    if len(ip_set):
      if not entry_dict:
        self.appendError('No data')
        return

      for resolver_ip, entry in sorted(entry_dict.items()):
        response_ip_set = entry['response_ip_set']
        if ip_set != response_ip_set:
          self.appendError(
            "resolver's %s: %s != %s" % (
              resolver_ip, ' '.join(sorted(ip_set)),
              ' '.join(sorted(response_ip_set)) or "empty-reply"))
        else:
          self.appendOk(
            "resolver's %s: %s" % (
              resolver_ip, ' '.join(sorted(ip_set)),))
    else:
      self.appendOk('No check configured')

  def senseTcpServer(self):
    key = 'tcp_server'
    self.appendMessage('%s:' % (key, ))

    if key not in self.surykatka_json:
      self.appendError("%r not in %r" % (key, self.json_file))
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
    if len(ip_set) == 0:
      self.appendOk('No check configured')
      return

    entry_list = [
      q for q in self.surykatka_json[key]
      if hostname in [
        r.strip() for r in q['domain'].split(',')] and q['port'] == port]
    if len(entry_list) == 0:
      self.appendError('No data')
      return
    for ip in sorted(ip_set):
      ok = False
      for entry in sorted(entry_list, key=operator.itemgetter('ip')):
        if entry['ip'] == ip:
          if entry['state'] == 'closed':
            ok = False
            break
          if entry['state'] == 'open':
            ok = True
      if ":" in ip:
        ip = "[%s]" % ip
      if ok:
        self.appendOk('IP %s:%s' % (ip, port))
      else:
        self.appendError('IP %s:%s' % (ip, port))

  def senseWhois(self):
    key = 'whois'
    self.appendMessage('%s:' % (key, ))
    url = self.getConfig('url')
    parsed_url = urlparse(url)
    hostname = parsed_url.netloc
    if not hostname:
      self.appendError('url is incorrect')
      return
    domain_expiration_days = self.getConfig(
      'domain-expiration-days', '30')
    try:
      domain_expiration_days = int(domain_expiration_days)
    except ValueError:
      self.appendError(
        'domain-expiration-days %r is incorrect' % (
          self.getConfig('domain-expiration-days')))
      return

    if key not in self.surykatka_json:
      self.appendError("%r not in %r" % (key, self.json_file))
      return

    def checkHostnameDomain(hostname, domain):
      if hostname == domain:
        return True
      elif hostname.endswith('.' + domain):
        return True
      return False

    entry_list = [
      q for q in self.surykatka_json[key]
      if checkHostnameDomain(hostname, q['domain'])]
    if len(entry_list) == 0:
      self.appendError('No data')
      return

    if len(entry_list) > 1:
      self.appendError('Bad data')
      return
    entry = entry_list[0]
    expiration_date = entry['expiration_date']
    if expiration_date is None:
      self.appendError('%s expiration date not avaliable' % (entry['domain'],))
      return
    timetuple = email.utils.parsedate(expiration_date)
    if timetuple is None:
      self.appendError("Can't parse date %s" % (expiration_date,))
    domain_expiration_time = datetime.datetime.fromtimestamp(
      time.mktime(timetuple))
    if domain_expiration_time - datetime.timedelta(
      days=domain_expiration_days) < self.utcnow:
      self.appendError(
        '%s expires in < %s days' % (entry['domain'], domain_expiration_days,))
    else:
      self.appendOk(
        '%s expires in > %s days' % (entry['domain'], domain_expiration_days,))

  def senseElapsedTime(self):
    key = 'elapsed_time'
    self.appendMessage('%s:' % (key, ))
    surykatka_key = 'http_query'

    if surykatka_key not in self.surykatka_json:
      self.appendError("%r not in %r" % (surykatka_key, self.json_file))
      return

    url = self.getConfig('url')
    maximum_elapsed_time = self.getConfig('maximum-elapsed-time')

    entry_list = [
      q for q in self.surykatka_json[surykatka_key] if q['url'] == url]
    if len(entry_list) == 0:
      self.appendError('No data')
      return
    if maximum_elapsed_time:
      found = False
      for entry in sorted(entry_list, key=operator.itemgetter('ip')):
        if 'total_seconds' in entry:
          found = True
          maximum_elapsed_time = float(maximum_elapsed_time)
          if entry['total_seconds'] == 0.:
            self.appendError('IP %s failed to reply' % (entry['ip']))
          elif entry['total_seconds'] > maximum_elapsed_time:
            self.appendError(
              'IP %s replied > %.2fs' %
              (entry['ip'], maximum_elapsed_time))
          else:
            self.appendOk('IP %s replied < %.2fs' % (
              entry['ip'], maximum_elapsed_time))
      if not found:
        self.appendError(
          "No entry with total_seconds found. If the error persist, please "
          "update surykatka")
    else:
      self.appendOk("No check configured")

  def sense(self):
    """
      Sense various information about the given url
    """
    self.utcnow = datetime.datetime.utcnow()

    self.json_file = self.getConfig('json-file', '')
    if not os.path.exists(self.json_file):
      self.appendError('File %r does not exists' % self.json_file)
    else:
      with open(self.json_file) as fh:
        try:
          self.surykatka_json = json.load(fh)
        except Exception:
          self.appendError(
            "loading JSON from %r" % self.json_file)
        else:
          report = self.getConfig('report')
          if report == 'bot_status':
            self.senseBotStatus()
          elif report == 'http_query':
            for check_name, check_method in [
              ('dns_query', self.senseDnsQuery),
              ('whois', self.senseWhois),
              ('tcp_server', self.senseTcpServer),
              ('http_query', self.senseHttpQuery),
              ('ssl_certificate', self.senseSslCertificate),
              ('elapsed_time', self.senseElapsedTime)
            ]:
              if check_name in self.enabled_sense_list:
                check_method()
          else:
            self.appendError(
              "Report %r is not supported" % report)
    self.emitLog()

  def anomaly(self):
    """
      Anomaly returns a TestResult instead of AnomalyResult because we don't
      want to call bang when there is a problem.
      This will need a human intervention.
    """
    return self._test(
      result_count=self.result_count, failure_amount=self.failure_amount)
