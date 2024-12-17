from __future__ import division

from zope.interface import implementer
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise

import os
import sys
import pwd

import sqlite3
import argparse
import datetime
import psutil
import math
import pkgutil

# try to install pandas and numpy
try:
  import pandas as pd
  import numpy as np
except ImportError:
  pass

from slapos.collect.db import Database
from contextlib import closing

@implementer(interface.IPromise)
class RunPromise(GenericPromise):

  def __init__(self, config):
    super(RunPromise, self).__init__(config)
    # at least every hours (heavy in computation)
    self.setPeriodicity(float(self.getConfig('frequency', 60)))

  def getDiskSize(self, disk_partition, db_path):
    database = Database(db_path, create=False, timeout=10)
    # by using contextlib.closing, we don't need to close the database explicitly
    with closing(database):
      try:
        database.connect()
        where_query = "partition='%s'" % (disk_partition)
        order = "datetime(date || ' ' || time) DESC"
        result = database.select(
          "disk",
          columns="free+used",
          where=where_query,
          order=order,
          limit=1).fetchone()
        if not result or not result[0]:
          return None
        disk_size = result[0]
      except sqlite3.OperationalError as e:
        # if database is still locked after timeout expiration (another process is using it)
        # we print warning message and try the promise at next run until max warn count
        locked_message = "database is locked"
        if locked_message in str(e) and \
            not self.raiseOnDatabaseLocked(locked_message):
          return None
        raise
    return disk_size

  def getPartitionSize(self, disk_partition, db_path):
    database = Database(db_path, create=False, timeout=10)
    with closing(database):
      try:
        database.connect()
        where_query = "partition='%s'" % (disk_partition)
        order = "datetime(date || ' ' || time) DESC"
        result = database.select(
          "folder",
          columns="disk_used*1024",
          where=where_query,
          order=order,
          limit=1).fetchone()
        if not result or not result[0]:
          return None
        partition_size = result[0]
      except sqlite3.OperationalError as e:
        # if database is still locked after timeout expiration (another process is using it)
        # we print warning message and try the promise at next run until max warn count
        locked_message = "database is locked"
        if locked_message in str(e) and \
            not self.raiseOnDatabaseLocked(locked_message):
          return None
        raise
    return partition_size

  def getAnomaly(self, disk_partition, db_path, user, date, time):
    database = Database(db_path, create=False, timeout=10)
    with closing(database):
      try:
        disk_size = self.getDiskSize(disk_partition, db_path)
        if disk_size is None:
          return None
        database.connect()
        result = database.select(
          "folder",
          columns = "%s-disk_used*1024, disk_used*1024, datetime(date || ' ' || time)" % disk_size,
          where =  "partition='%s'" % (user),
          order = "date ASC, time ASC"
        ).fetchall()
        if not result or not result[0]:
          self.logger.info("No result from collector database for the user %s: skipped", user)
          return None
        datetime_now = datetime.datetime.strptime(date + ' ' + time, "%Y-%m-%d %H:%M:%S")
        # check that the last data is less than 24 hours old
        last_date = datetime.datetime.strptime(result[-1][2], "%Y-%m-%d %H:%M:%S")
        if (datetime_now - last_date) > datetime.timedelta(days=1):
          self.logger.info("Not enough recent data to detect anomalies: skipped")
          return None
        # check that the first data is at least 13 days old
        first_date = datetime.datetime.strptime(result[0][2], "%Y-%m-%d %H:%M:%S")
        if (datetime_now - first_date) < datetime.timedelta(days=13):
          self.logger.info("Not enough data to detect anomalies: skipped")
          return None

        df = pd.DataFrame(result, columns=["free", "used", "date"])
        df.loc[:,'date'] = pd.to_datetime(df.date)
        # keep a sample every 5 minutes, set NaN when there is no information
        freq = 5
        df = df.resample(str(freq)+"min", on='date').mean()
        # estimate the missing information
        df['free'] = df.free.astype(float).interpolate(method='linear')
        df['used'] = df.used.astype(float).interpolate(method='linear')
        # calculate the median for the element-wise absolute value
        # of the difference between each x and the median of x
        df = df.reset_index()
        x = df['date']
        y = df['free']
        mad = lambda x: np.median(np.fabs(x - np.median(x)))
        # threshold is set at 8% of the disk size by default
        threshold_ratio = float(self.getConfig('threshold-ratio', 0.08) or 0.08)
        threshold = threshold_ratio*disk_size
        # use a 1-day window
        minutes_per_day = 60*24/freq
        rolling_window = int(minutes_per_day*1)
        rolling_mad = y.rolling(window=rolling_window, center=False).median() + \
          y.rolling(window=rolling_window, center=False).apply(mad)
        rolling_mad_upper = rolling_mad + threshold
        rolling_mad_lower = rolling_mad - threshold
        # create Pandas DataFrame and rename columns
        data = pd.concat([x, y, df['used'], rolling_mad, rolling_mad_upper, rolling_mad_lower], axis=1)
        data.columns = ["date", "free", "used", "mad", "upper_mad", "lower_mad"]
        # drop initial values (outside rolling window)
        data.dropna(subset=["mad"], inplace=True)
        # determine anomalies and display their number
        data["is_anomaly"] = ~(data["free"].between(data["lower_mad"], data["upper_mad"]))
        data = data.set_index("date")
        if (len(data)==0):
          self.logger.info("No result from anomaly detection")
          return None
        self.logger.info("There were %s anomalies in the last 15 days " \
          "(1 data every %s minutes, threshold: %s %% of the disk size)" % (
          len(data[data['is_anomaly'] == True]), freq, threshold_ratio*100))
        return data
      except sqlite3.OperationalError as e:
        # if database is still locked after timeout expiration (another process is using it)
        # we print warning message and try the promise at next run until max warn count
        locked_message = "database is locked"
        if locked_message in str(e) and \
            not self.raiseOnDatabaseLocked(locked_message):
          return None
        raise

  @staticmethod
  def _checkInodeUsage(path):
    stat = os.statvfs(path)
    total_inode = stat.f_files
    if total_inode:
      usage = 100 * (total_inode - stat.f_ffree) / total_inode
      if usage >= 98:
        return "Disk Inodes usage is really high: %.4f%%" % usage

  def getInodeUsage(self, path):
    return (self._checkInodeUsage(path) or
       os.path.ismount('/tmp') and self._checkInodeUsage('/tmp') or
       "")

  def sense(self):
    # check that the libraries are installed from the slapos.toolbox extra requires
    pandas_found = pkgutil.find_loader("pandas")
    numpy_found = pkgutil.find_loader("numpy")
    if pandas_found is None or numpy_found is None:
      self.logger.warning("Trying to use pandas but the module is not installed. Promise skipped.")
      return
    # find if a disk is mounted on the path
    disk_partition = ""
    db_path = self.getConfig('collectordb')
    check_date = self.getConfig('test-check-date')
    path = os.path.join(self.getPartitionFolder(), "") + "extrafolder"
    partitions = psutil.disk_partitions()
    while path != '/':
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

    if db_path.endswith("collector.db"):
      db_path=db_path[:-len("collector.db")]

    if check_date:
      # testing mode
      currentdate = check_date
      currenttime = self.getConfig('test-check-time', '09:30:30')
      user = self.getConfig('test-partition', 'slapuser0')
    else:
      # get the user name of the partition
      user = pwd.getpwuid(os.getuid()).pw_name
      # get last minute
      now = datetime.datetime.utcnow()
      currentdate = now.strftime('%Y-%m-%d')
      currenttime = now - datetime.timedelta(minutes=1)
      currenttime = currenttime.time().strftime('%H:%M:%S')

    partition_size = self.getPartitionSize(user, db_path)
    data = self.getAnomaly(disk_partition, db_path, user, currentdate, currenttime)
    if data is None:
      return
    last_data = data.iloc[-1]
    last_date = data.index[-1]
    if last_data.is_anomaly:
      self.logger.error("Anomaly detected on %s. Space used by %s: %.2f G." % (
        last_date, user, partition_size/(1024*1024*1024)))
    else:
      self.logger.info("No anomaly detected (last date checked: %s)" % (last_date))

  def test(self):
    return self._test(result_count=1, failure_amount=1)

  def anomaly(self):
    """
      Anomaly returns a TestResult instead of AnomalyResult because we don't
      want to call bang when there is a problem. Usually the problem won't be
      in the deployment of this instance but rather in this partition taking
      too much space.  This will need a human intervention.
    """
    return self._test(result_count=3, failure_amount=3)
