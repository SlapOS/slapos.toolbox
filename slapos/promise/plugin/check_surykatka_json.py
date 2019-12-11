from zope.interface import implementer
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise

import datetime
import email.utils
import json
import json
import os
import subprocess
import sys
import time


@implementer(interface.IPromise)
class RunPromise(GenericPromise):
  def __init__(self, config):
    super(RunPromise, self).__init__(config)
    # SR can set custom periodicity
    self.setPeriodicity(float(self.getConfig('frequency', 2)))

  def senseBotStatus(self):
    key = 'bot_status'
    def logError(msg, *args):
      self.logger.error(key + ': ' + msg, *args)

    if key not in self.surykatka_json:
      logError("%r not in %r", key, self.json_file)
      return
    bot_status_list = self.surykatka_json[key]
    if len(bot_status_list) == 0:
      logError("%r empty in %r", key, self.json_file)
      return
    bot_status = bot_status_list[0]
    bot_status_dump = json.dumps(bot_status, indent=2)
    if bot_status.get('text') != 'loop':
      logError("No type loop detected in %r", self.json_file)
      return
    timetuple = email.utils.parsedate(bot_status['date'])
    last_bot_datetime = datetime.datetime.fromtimestamp(time.mktime(timetuple))
    delta = self.utcnow - last_bot_datetime
    # sanity check
    if delta < datetime.timedelta(minutes=0):
      logError('Last bot datetime %s is in future, UTC now %s',
        last_bot_datetime, self.utcnow)
      return
    if delta > datetime.timedelta(minutes=15):
      logError('Last bot datetime %s is more than 15 minutes old, UTC now %s',
        last_bot_datetime, self.utcnow)
      return
    self.logger.info('%s: Last bot status from %s ok, UTC now is %s', key, last_bot_datetime, self.utcnow)

  def sense(self):
    """
      Check if frontend URL is available
    """
    test_utcnow = self.getConfig('test-utcnow')
    if test_utcnow:
      self.utcnow = datetime.datetime.fromtimestamp(time.mktime(email.utils.parsedate(test_utcnow)))
    else:
      self.utcnow = datetime.datetime.utcnow()
    self.json_file = self.getConfig('json-file', '')
    if not os.path.exists(self.json_file):
      self.logger.error('File %r does not exists', self.json_file)
      return
    with open(self.json_file) as fh:
      try:
        self.surykatka_json = json.load(fh)
      except Exception as e:
        self.logger.error("Problem loading JSON from %r", self.json_file)
        return
    report = self.getConfig('report')
    if report == 'bot_status':
      return self.senseBotStatus()
    else:
      self.logger.error("Report %r is not supported", report)
      return
      
    

    key = sys.argv[2]
    status = True
    jsoned = json.load(open(sys.argv[1]))
    if key == 'http_query':
      url = sys.argv[3]
      http_code = sys.argv[4]
      ip_list = sys.argv[5:]
    
      entry_list = [q for q in jsoned[key] if q['url'] == url]
      if len(entry_list) == 0:
        print 'no entries for %s' % (url,)
        status = False
      entry_list_dump = json.dumps(entry_list, indent=2)
      http_code_list = [q['status_code'] for q in entry_list]
      db_ip_list = [q['ip'] for q in entry_list]
      if not all([http_code == str(q) for q in http_code_list]):
        print 'http_code %s does not match at least one entry in:\n%s' % (
          http_code, entry_list_dump)
        status = False
      if len(ip_list):
        if set(ip_list) != set(db_ip_list):
          print 'ip_list %s differes from:\n%s' % (ip_list, entry_list_dump)
          status = False

  def anomaly(self):
    return self._test(result_count=3, failure_amount=3)
