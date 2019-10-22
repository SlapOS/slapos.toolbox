from __future__ import division

from zope.interface import implementer
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise

import os
import sys

import sqlite3
import argparse
import datetime
import psutil

from slapos.collect.db import Database

@implementer(interface.IPromise)
class RunPromise(GenericPromise):

  def __init__(self, config):
    super(RunPromise, self).__init__(config)
    # check disk space at least every 3 minutes
    self.setPeriodicity(minute=3)

  def getDaysUntilFull(self, disk_partition, database, date, time, threshold_days):
    database = Database(database, create=False, timeout=10)
    try:
      # fetch free disk space
      database.connect()
      result_max = database.select(
        "disk",
        date,
        columns="free*1.0/(used+free) AS percent, max(datetime(date || ' ' || time))",
        where="time between '%s:00' and '%s:30' and partition='%s'" % (time, time, disk_partition),
        limit=1,
      ).fetchone()
      if not result_max or not result_max[1]:
        return None
      result_min = database.select(
        "disk",
        columns="free*1.0/(used+free) AS percent, min(datetime(date || ' ' || time))",
        where="datetime(date || ' ' || time) >= datetime('%s', '-%s days')  and partition='%s'" % (result_max[1], threshold_days, disk_partition,),
        limit=1,
      ).fetchone()
      if not result_min or not result_min[1] or result_min == result_max:
        return None
      change = result_max[0] - result_min[0]
      if change > 0.:
        return None
      timep = '%Y-%m-%d %H:%M:%S'
      timespan = datetime.datetime.strptime(
        result_max[1], timep) - datetime.datetime.strptime(
        result_min[1], timep)
      delta_days = timespan.total_seconds() / (3600.*24)
      try:
        return -(1. - result_max[0]) / (change / delta_days)
      except ZeroDivisionError as e:
        # no data
        return None
    except sqlite3.OperationalError as e:
      # if database is still locked after timeout expiration (another process is using it)
      # we print warning message and try the promise at next run until max warn count
      locked_message = "database is locked"
      if locked_message in str(e) and \
          not self.raiseOnDatabaseLocked(locked_message):
        return None
      raise
    finally:
      try:
        database.close()
      except Exception:
        pass

  def getFreeSpace(self, disk_partition, database, date, time):
    database = Database(database, create=False, timeout=10)
    try:
      # fetch free disk space
      database.connect()
      where_query = "time between '%s:00' and '%s:30' and partition='%s'" % (time, time, disk_partition)
      query_result = database.select("disk", date, "free", where=where_query)
      result = query_result.fetchone()
      if not result or not result[0]:
        self.logger.info("No result from collector database: disk check skipped")
        return 0
      disk_free = result[0]
    except sqlite3.OperationalError as e:
      # if database is still locked after timeout expiration (another process is using it)
      # we print warning message and try the promise at next run until max warn count
      locked_message = "database is locked"
      if locked_message in str(e) and \
          not self.raiseOnDatabaseLocked(locked_message):
        return 0
      raise
    finally:
      try:
        database.close()
      except Exception:
        pass
    return int(disk_free)

  def raiseOnDatabaseLocked(self, locked_message):
    max_warn = 10
    latest_result_list = self.getLastPromiseResultList(result_count=max_warn)
    warning_count = 0
    if len(latest_result_list) < max_warn:
      return False

    for result in latest_result_list[0]:
      if result['status'] == "ERROR" and locked_message in result["message"]:
        return True

    for result_list in latest_result_list:
      found = False
      for result in result_list:
        if result['status'] == "WARNING" and locked_message in result["message"]:
          found = True
          warning_count += 1
          break
      if not found:
        break
    if warning_count == max_warn:
      # too many warning on database locked, now fail.
      return True

    self.logger.warn("collector database is locked by another process")
    return False

  def getInodeUsage(self, path):
    max_inode_usage = 97.99 # < 98% usage
    stat = os.statvfs(path)
    usage_output = ""
    total_inode = stat.f_files
    free_inode = stat.f_ffree
    usage = round(((total_inode - free_inode) / total_inode), 4) * 100
    if usage > max_inode_usage:
      return "Disk Inodes usages is really high: %s%%" % usage
    elif os.path.exists('/tmp'):
      # check if /tmp is mounted on another disk than path
      tmp_stat = os.statvfs('/tmp')
      if tmp_stat.f_blocks != stat.f_blocks:
        tmp_usage = round(((tmp_stat.f_files - tmp_stat.f_ffree) / tmp_stat.f_files), 4) * 100
        if tmp_usage > max_inode_usage:
          return "Disk Inodes usage is high: %s%%" % tmp_usage
    return ""


  def sense(self):
    # find if a disk is mounted on the path
    disk_partition = ""
    db_path = self.getConfig('collectordb')
    check_date = self.getConfig('test-check-date')
    path = os.path.join(self.getPartitionFolder(), "") + "extrafolder"
    partitions = psutil.disk_partitions()
    while path is not '/':
      if not disk_partition:
        path = os.path.dirname(path)
      else:
        break
      for p in partitions:
        if p.mountpoint == path:
          disk_partition = p.device
          break
    if not disk_partition:
      self.logger.error("Couldn't find disk partition")
      return

    threshold = float(self.getConfig('threshold', '2'))
    threshold_days = float(self.getConfig('threshold-days', '30'))

    if check_date:
      # testing mode
      currentdate = check_date
      currenttime = self.getConfig('test-check-time', '09:17')
      disk_partition = self.getConfig('test-disk-partition', '/dev/sda1')
    else:
      # get last minute
      now = datetime.datetime.now()
      currentdate = now.strftime('%Y-%m-%d')
      currenttime = now - datetime.timedelta(minutes=1)
      currenttime = currenttime.time().strftime('%H:%M')

    if db_path.endswith("collector.db"):
      db_path=db_path[:-len("collector.db")]

    free_space = self.getFreeSpace(disk_partition, db_path, currentdate,
                                   currenttime)
    days_until_full = self.getDaysUntilFull(disk_partition, db_path, currentdate, currenttime, threshold_days)
    if days_until_full is not None:
      if days_until_full < threshold_days:
        self.logger.error("Disk will become full in %.2f days (threshold: %.2f days)" % (
        days_until_full, threshold_days))

    if free_space == 0:
      return
    elif free_space > threshold*1024*1024*1024:
      inode_usage = self.getInodeUsage(self.getPartitionFolder())
      if inode_usage:
        self.logger.error(inode_usage)
      else:
        self.logger.info("Disk usage: OK")
      return

    free_space = round(free_space/(1024*1024*1024), 2)
    self.logger.error('Free disk space low: remaining %s G (threshold: %s G)' % (
      free_space, threshold))

  def test(self):
    return self._test(result_count=1, failure_amount=1)

  def anomaly(self):
    return self._test(result_count=3, failure_amount=3)
