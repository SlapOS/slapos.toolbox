##############################################################################
#
# Copyright (c) 2017 Vifib SARL and Contributors. All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import unittest
import os.path
import socket
import time
from slapos.promise.check_error_on_apache_log import test

from slapos.test.promise import data

class TestCheckErrorOnApacheLog(unittest.TestCase):

  def get_time(self, sec):
    return time.strftime("%a %b %d %H:%M:%S %Y", time.localtime(time.time()-sec))

  def _update_logs(self):
    log_file_list = [
       "apache_error_log",
       "infoonly_error_log",
       "timeout_error_log",
       "unreachable_error_log"]
    i = 600
    for log_file in log_file_list:
      new = ""
      old = ""
      with open(self.base_path + "/" + log_file) as f:
        for line in f:
          new += line.replace("DATETIME", self.get_time(i))
          old += line.replace("DATETIME", self.get_time(i+3600))
          i -= 1

      with open(self.base_path + "/SOFTINST-0_" + log_file, "w") as f:
        f.write(old)
        f.write(new)

  def setUp(self):
    self.base_path = "/".join(data.__file__.split("/")[:-1])
    self._update_logs()

  def test_no_error(self):
    self.assertEquals("OK",
      test(self.base_path + "/SOFTINST-0_infoonly_error_log", 0))

    self.assertEquals("OK",
      test(self.base_path + "/SOFTINST-0_infoonly_error_log", 3600))

  def test_error(self):
    self.assertEquals("ERROR=2 (NOTROUTE=2, UNREACHEABLENET=0, TIMEOUT=0)",
      test(self.base_path + "/SOFTINST-0_apache_error_log", 0))

    self.assertEquals("ERROR=1 (NOTROUTE=1, UNREACHEABLENET=0, TIMEOUT=0)",
      test(self.base_path + "/SOFTINST-0_apache_error_log", 3600))

  def test_error_timeout(self):
    self.assertEquals("ERROR=4 (NOTROUTE=0, UNREACHEABLENET=0, TIMEOUT=4)",
      test(self.base_path + "/SOFTINST-0_timeout_error_log", 0))

    self.assertEquals("ERROR=2 (NOTROUTE=0, UNREACHEABLENET=0, TIMEOUT=2)",
      test(self.base_path + "/SOFTINST-0_timeout_error_log", 3600))

  def test_error_unreacheabler(self):
    self.assertEquals("ERROR=11 (NOTROUTE=0, UNREACHEABLENET=11, TIMEOUT=0)",
      test(self.base_path + "/SOFTINST-0_unreachable_error_log", 0))

    self.assertEquals("ERROR=11 (NOTROUTE=0, UNREACHEABLENET=11, TIMEOUT=0)",
      test(self.base_path + "/SOFTINST-0_unreachable_error_log", 3600))   
  
if __name__ == '__main__':
  unittest.main()

