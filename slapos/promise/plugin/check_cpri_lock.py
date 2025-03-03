import re
from .util import JSONPromise, get_json_log_data_interval

from zope.interface import implementer
from slapos.grid.promise import interface

@implementer(interface.IPromise)
class RunPromise(JSONPromise):
  def __init__(self, config):
    super(RunPromise, self).__init__(config)
    self.setPeriodicity(float(self.getConfig('frequency', 1)))
    self.amarisoft_rf_info_log = self.getConfig('amarisoft-rf-info-log')
    self.sdr_devchan = "/dev/sdr%s@%s" % (self.getConfig('sdr_dev'), self.getConfig('sfp_port'))
    self.stats_period = int(self.getConfig('stats-period'))
    self.testing = self.getConfig('testing') == "True"

  def sense(self):
      if self.testing:
          self.logger.info("skipping promise")
          return

      def error(msg): self.logger.error("%s: %s", self.sdr_devchan, msg)
      def info(msg):  self.logger.info ("%s: %s", self.sdr_devchan, msg)

      data_list = get_json_log_data_interval(self.amarisoft_rf_info_log, self.stats_period * 2)
      if len(data_list) < 1:
        error("rf_info: stale data")
        return

      rf_info_text = data_list[0]['rf_info']
      rf_info = self._parse_rf_info(rf_info_text)
      if self.sdr_devchan not in rf_info:
        error("rf_info: no device entry")
        return

      rf_info = rf_info[self.sdr_devchan]
      icpri = rf_info.get('CPRI_option') or rf_info.get('CPRI')
      if icpri is None:
        error("no CPRI feature")
        return

      hw = ("HW" in icpri)
      sw = ("SW" in icpri)
      if not hw:
        error("HW Lock is missing")
      if not sw:
        error("SW Lock is missing")
      if hw and sw:
        info("CPRI locked")

  @staticmethod
  def _parse_rf_info(rf_info_text):  # -> {} /dev/sdrX@Y -> {key: value}
    """_parse_rf_info parses rf_info output into per-SDR-device key->value dictionaries.

       For example:

         TRX SDR driver 2023-09-07, API v15/18
         PCIe CPRI /dev/sdr1@2:
           FPGA vccint: 0.98 V
           FPGA vccaux: 1.77 V
         PCIe CPRI /dev/sdr3@4:
           ABC: 123
           DEF: 4567

       is parsed as {'/dev/sdr1@2': {'FPGA vccint': '0.98 V',  'FPGA vccaux': '1.77 V'},
                     '/dev/sdr3@4': {'ABC': '123',  'DEF': '4567'}}
    """
    rf_info = {}
    cur = None
    for l in rf_info_text.splitlines():
      if not l.startswith(' '):  # possibly start of new /dev entry
        new = True
        if l.startswith('Clock tune:'):
            new = False # 2024-06-15 started to emit 'Clock tune:' without indent
        if new:
            cur = None
            m = re.search(r' (/dev/sdr[^\s]+):\s*$', l)
            if m is None: # not so - ignore the line
              continue

            cur = {}
            sdr_devchan = m.group(1)
            rf_info[sdr_devchan] = cur
            continue

      # indented line - it populates current if it still holds its context
      if cur is None:
        continue

      l = l.lstrip()
      if not l:
          continue  # empty lines are ignore, e.g. empty trailing lines in 2022 format

      if ':' not in l:
          raise ValueError('invalid line %r' % (l,))

      k, v = l.split(':', 1)
      k = k.strip()
      v = v.strip()
      cur[k] = v

    return rf_info

  def test(self):
    """
      Called after sense() if the instance is still converging.
      Returns success or failure based on sense results.

      In this case, fail if the previous sensor result is negative.
    """
    return self._test(result_count=1, failure_amount=1)


  def anomaly(self):
    """
      Called after sense() if the instance has finished converging.
      Returns success or failure based on sense results.
      Failure signals the instance has diverged.

      In this case, fail if two out of the last three results are negative.
    """
    return self._anomaly(result_count=1, failure_amount=1)
