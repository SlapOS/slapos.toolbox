import os, subprocess, time
import distro
from contextlib import contextmanager
from traceback import format_exception_only
from zope.interface import implementer
from slapos.grid.promise import interface
from slapos.grid.promise.generic import ERROR_LEVEL, GenericPromise, TestResult

NOT_UP_TO_DATE = 'not up-to-date:'

@implementer(interface.IPromise)
class RunPromise(GenericPromise):

  def __init__(self, config):
    config.setdefault('periodicity', 86400)
    super().__init__(config)
    self.setTestLess()

  def sense(self):
    os.environ.pop('LANG', None)
    error_list = []
    error = error_list.append
    @contextmanager
    def exc():
      try:
        yield
      except Exception as e:
        e, = format_exception_only(e)
        error(e.lstrip())
    try:
      subprocess.check_call("""set -e
        for x in Update-Package-Lists Unattended-Upgrade; do
          eval `apt-config shell x APT::Periodic::$x`
          [ "$x" = 1 ]
        done""", shell=True)
    except Exception:
      error('not configured to update/upgrade automatically every day')
    # Let's add a margin in case there's an ongoing upgrade that takes a lot
    # of time (one reason may even be that the system is suspended - sleep).
    stamp = time.time() - float(self.getConfig('tolerance-days', 2)) * 86400
    check_stamp = lambda x: os.stat(x + '-stamp', dir_fd=fd).st_mtime < stamp
    with exc():
      fd = os.open('/var/lib/apt/periodic', 0)
      try:
        if check_stamp('update'):
          error('package lists not up-to-date')
        if check_stamp('download-upgradeable') or check_stamp('upgrade'):
          error('unattended-upgrade: no recent successful run')
      finally:
        os.close(fd)
    args = ['apt-cache', 'policy']
    with exc():
      policies = iter(subprocess.check_output(args, text=1).splitlines())
      next(policies)
      x = next(policies).split(None, 1)
      origin = distro.name()
      suite = distro.codename() + '-security'
      security = None
      official = other = -1
      while x[0] != 'Pinned':
        priority = int(x[0])
        for x in policies:
          x = x.split(None, 1)
          if x[0] == 'release':
            x = dict(x.split('=', 1) for x in x[1].split(','))
            if x.get('a') == suite:
              if security is None or security > priority:
                security = priority
            elif x.get('o') == origin:
              if official < priority:
                official = priority
            elif other < priority:
                other = priority
          elif x[0] != 'origin':
            break
      if security is None:
        error('no package source for security updates')
      elif security < official or security <= other:
        error("security updates don't have priority")
    with exc():
      outdated = self.getConfig('check-other', '').split()
      if outdated:
        args += outdated
        del outdated[:]
        policies = iter(subprocess.check_output(args, text=1).splitlines())
        for x in policies:
          if x[0] != ' ':
            installed = next(policies).split(None, 1)[1]
            candidate = next(policies).split(None, 1)[1]
            if '(none)' != installed != candidate:
              outdated.append(x[:-1] + '_' + installed)
    if error_list:
      self.logger.error('; '.join(error_list))
    elif outdated:
      self.logger.error("%s %s", NOT_UP_TO_DATE, ', '.join(outdated))
    else:
      self.logger.info("system looks up-to-date")

  def anomaly(self):
    latest_result_list = self.getLastPromiseResultList(result_count=3)
    if latest_result_list:
      last, = latest_result_list[0]
      status = last['status']
      msg = last['message']
      message = '%s (%s)' % (status, msg)
      if status in ERROR_LEVEL and (
        not msg.startswith(NOT_UP_TO_DATE)
        or len(latest_result_list) == 3
          and (x := latest_result_list[-1][0])['status'] == status
          and x['message'] == msg):
        return TestResult(True, message)
    else:
      message = "No result found!"
    return TestResult(False, message)
