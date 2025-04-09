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
import itertools
import warnings
import pkgutil

from slapos.collect.db import Database
from contextlib import closing

# install pandas, numpy and statsmodels for ARIMA prediction
try:
  import pandas as pd
  import numpy as np
  from statsmodels.tsa.arima.model import ARIMA
except ImportError:
  pass

@implementer(interface.IPromise)
class RunPromise(GenericPromise):

  def __init__(self, config):
    super(RunPromise, self).__init__(config)
    # check disk space at least every hours (heavy in computation)
    self.setPeriodicity(float(self.getConfig('frequency', 60)))

  def getDiskSize(self, disk_partition, database):
    database = Database(database, create=False, timeout=10)
    # by using contextlib.closing, we don't need to close the database explicitly
    with closing(database):
      try:
        # fetch disk size
        database.connect()
        where_query = "partition='%s'" % (disk_partition)
        order = "datetime(date || ' ' || time) DESC"
        query_result = database.select("disk", columns="free+used", where=where_query, order=order, limit=1)
        result = query_result.fetchone()
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

  def getFreeSpace(self, disk_partition, database, date, time):
    database = Database(database, create=False, timeout=10)
    with closing(database):
      try:
        # fetch free disk space
        database.connect()
        where_query = "time between '%s:00' and '%s:30' and partition='%s'" % (time, time, disk_partition)
        query_result = database.select("disk", date, "free", where=where_query)
        result = query_result.fetchone()
        if not result or not result[0]:
          self.logger.info("No result from collector database: disk check skipped")
          return -1
        disk_free = result[0]
      except sqlite3.OperationalError as e:
        # if database is still locked after timeout expiration (another process is using it)
        # we print warning message and try the promise at next run until max warn count
        locked_message = "database is locked"
        if locked_message in str(e) and \
            not self.raiseOnDatabaseLocked(locked_message):
          return -1
        raise
    return int(disk_free)

  def getBiggestPartitions(self, database, date, time):
    # displays the 3 biggest partitions thanks to disk usage
    limit = 3
    database = Database(database, create=False, timeout=10)
    with closing(database):
      try:
        database.connect()
        date_time = date + ' ' + time
        # gets the data recorded between the current date (date_time) and 24 hours earlier
        where_query = "datetime(date || ' ' || time) >= datetime('%s', '-1 days') AND datetime(date || ' ' || time) <= datetime('%s')"
        # gets only the most recent data for each partition
        result = database.select(
          "folder",
          columns = "partition, disk_used*1024, max(datetime(date || ' ' || time))",
          where =  where_query % (date_time, date_time),
          group = "partition",
          order = "disk_used DESC",
          limit = limit).fetchall()
        if not result or not result[0]:
          self.logger.info("No result from collector database in table folder: skipped")
          return None
      except sqlite3.OperationalError as e:
        # if database is still locked after timeout expiration (another process is using it)
        # we print warning message and try the promise at next run until max warn count
        locked_message = "database is locked"
        if locked_message in str(e) and \
            not self.raiseOnDatabaseLocked(locked_message):
          return None
        raise
    return result

  def diskSpacePrediction(self, disk_partition, database, date, time, day_range):
    """
    Returns an estimation of free disk space left depending on
    the day_range parameter.

    It uses Arima in order to predict data thanks to the 15 days before.
    """
    database = Database(database, create=False, timeout=10)
    with closing(database):
      try:
        database.connect()
        # get one data per day, where each data is at the same time
        where_query = "time between '%s:00' and '%s:30' and partition='%s'" % (
          time, time, disk_partition)
        result = database.select(
          "disk",
          columns = "free, datetime(date || ' ' || time)",
          where = where_query,
          order = "datetime(date || ' ' || time) ASC").fetchall()
        # checks that there are at least 14 days of data
        if (not result) or (len(result) < 14):
          self.logger.info("No or not enough results from collector database in table disk: no prediction")
          return None
        # put the list in pandas dataframe format and set the right types
        data = np.array(result,
                dtype=[('free', 'float'), ('date', 'datetime64[s]')])
        df = pd.DataFrame.from_records(data)
        df.loc[:,'date'] = pd.to_datetime(df.date)
        df = df.set_index('date')
        df.index = pd.DatetimeIndex(df.index).to_period('D')
        # find the best configuration by trying different combinations
        p_values = d_values = q_values = range(0, 3)
        # We were using a function called evaluateModels() to select the
        # best ARIMA (p, d, q) order, but it evaluates 27 combinations,
        # each taking about 1–2 seconds, which exceeds the 20s limit for a promise.
        # And also in statsmodels 0.11.1, _check_estimable would skip combinations
        # with insufficient degrees of freedom.
        # but in 0.14.4, all 27 combinations are evaluated, resulting in excessive runtime.
        # To save time, we simply use the order (1, 1, 0).
        # XXX: Now we are using the hardcoded order, need to find a better way in future.
        best_cfg = (1, 1, 0)
        # set the days to be predicted
        max_date_predicted = day_range+1
        try:
          # disabling warnings during the ARIMA calculation
          model_arima = ARIMA(df, order=best_cfg, trend="t")
          model_arima_fit = model_arima.fit()
          # save ARIMA predictions
          fcast_result  = model_arima_fit.get_forecast(steps=max_date_predicted)
          fcast = fcast_result.predicted_mean
          conf = fcast_result.conf_int(alpha=0.05).to_numpy()
          if fcast.empty:
            self.logger.info("Arima prediction: none. Skipped prediction")
            return None
        except Exception:
          self.logger.info("Arima prediction error: skipped prediction")
          return None
        # get results with 95% confidence
        lower_series = conf[:, 0]
        upper_series = conf[:, 1]
        return fcast, lower_series, upper_series
      except sqlite3.OperationalError as e:
        # if database is still locked after timeout expiration (another process is using it)
        # we print warning message and try the promise at next run until max warn count
        locked_message = "database is locked"
        if locked_message in str(e) and \
            not self.raiseOnDatabaseLocked(locked_message):
          return None
        raise

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
      currenttime = self.getConfig('test-check-time', '09:17')
      disk_partition = self.getConfig('test-disk-partition', '/dev/sda1')
    else:
      # get last minute
      now = datetime.datetime.utcnow()
      currentdate = now.strftime('%Y-%m-%d')
      currenttime = now - datetime.timedelta(minutes=1)
      currenttime = currenttime.time().strftime('%H:%M')

    disk_size = self.getDiskSize(disk_partition, db_path)
    # threshold is in GB
    default_threshold = 100.0
    if disk_size is not None:
      # if we know the disk size, default threshold is 5%
      default_threshold = round(disk_size/(1024*1024*1024) * 0.05, 2)
    threshold = float(self.getConfig('threshold', default_threshold))

    display_partition = bool(self.getConfig('display-partition', 0))
    if display_partition:
      # Always display the 3 partitions that have the most storage capacity on the disk
      big_partitions = self.getBiggestPartitions(db_path, currentdate, currenttime)
      if big_partitions is not None:
        for partition in big_partitions:
          user_name, size_partition, date_checked = partition
          partition_id = self.getConfig('partition-id', 'slappart')
          # get the name of each partition by adding the user's number to the general name of the partition
          partition_name = ''.join(x for x in partition_id if not x.isdigit()) + ''.join(filter(str.isdigit, user_name))
          self.logger.info("The partition %s uses %.2f G (date checked: %s).",
            partition_name, size_partition/(1024*1024*1024), date_checked)

    inode_usage = self.getInodeUsage(self.getPartitionFolder())
    if inode_usage:
      self.logger.error(inode_usage)

    free_space = self.getFreeSpace(disk_partition, db_path, currentdate,
                                   currenttime)
    if free_space == -1:
      # we couldn't connect to the database, simply ignore this occurence of sense
      return
    elif free_space > threshold*1024*1024*1024:
      self.logger.info("Current disk usage: OK")
      # if the option is enabled and the current disk size is OK,
      # we check the predicted remaining disk space
      display_prediction = bool(int(self.getConfig('display-prediction', 0) or 0))
      if display_prediction:
        # check that the libraries are installed from the slapos.toolbox extra requires
        pandas_found = pkgutil.find_loader("pandas")
        numpy_found = pkgutil.find_loader("numpy")
        statsmodels_found = pkgutil.find_loader("statsmodels")
        if pandas_found is None or numpy_found is None or statsmodels_found is None:
          self.logger.warning("Trying to use statsmodels and pandas " \
            "but at least one module is not installed. Prediction skipped.")
          return
        nb_days_predicted = int(self.getConfig('nb-days-predicted', 10) or 10)
        disk_space_prediction_tuple = self.diskSpacePrediction(
          disk_partition, db_path, currentdate, currenttime, nb_days_predicted)
        if disk_space_prediction_tuple is not None:
          fcast, lower_series, upper_series = disk_space_prediction_tuple
          space_left_predicted = fcast.iloc[-1]
          last_date_predicted = datetime.datetime.strptime(str(fcast.index[-1]),
                                                          "%Y-%m-%d")
          delta_days = (last_date_predicted.date() - \
            datetime.datetime.strptime(currentdate, "%Y-%m-%d").date()).days
          self.logger.info("Prediction: there will be %.2f G left on %s (%s days).",
            space_left_predicted/(1024*1024*1024), last_date_predicted, delta_days)
          if space_left_predicted <= threshold*1024*1024*1024:
            self.logger.error("The free disk space will be too low. " \
                              "(disk size: %.2f G, threshold: %s G)",
                                disk_size/(1024*1024*1024), threshold)
    else:
      self.logger.error("Free disk space low: remaining %.2f G (disk size: %.0f G, threshold: %.0f G).",
        free_space/(1024*1024*1024), disk_size/(1024*1024*1024), threshold)

  def test(self):
    return self._test(result_count=1, failure_amount=1)

  def anomaly(self):
    """
      Anomaly returns a TestResult instead of AnomalyResult because we don't
      want to call bang when there is a problem. Usually the problem won't be
      in the deployment of this instance but rather in one of the partition
      taking too much space.  This will need a human intervention.
    """
    return self._test(result_count=3, failure_amount=3)
