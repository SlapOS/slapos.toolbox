from __future__ import division

from zope.interface import implementer
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise

import os
import sys
import pandas as pd
import numpy as np

import sqlite3
import argparse
import datetime
import psutil
import itertools
import warnings

from slapos.collect.db import Database

from statsmodels.tsa.arima_model import ARIMA

@implementer(interface.IPromise)
class RunPromise(GenericPromise):

  def __init__(self, config):
    super(RunPromise, self).__init__(config)
    # check disk space at least every 3 minutes
    self.setPeriodicity(minute=3)

  def getDiskSize(self, disk_partition, database):
    database = Database(database, create=False, timeout=10)
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
    finally:
      try:
        database.close()
      except Exception:
        pass
    return disk_size

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

  def getBiggestPartitions(self, database, date, time):
    # displays the 3 biggest partitions thanks to disk usage
    limit = 3
    database = Database(database, create=False, timeout=10)
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
    finally:
      try:
        database.close()
      except Exception:
        pass
    return result

  def diskSpacePrediction(self, disk_partition, database, date, time, day_range):
    """
    Returns an estimation of free disk space left depending on
    the day_range parameter.

    It uses Arima in order to predict data thanks to the 15 days before.
    """
    database = Database(database, create=False, timeout=10)
    try:
      database.connect()
      # get one data per day, where each data is at the same time
      where_query = "time between '%s:00' and '%s:30' and partition='%s'" % (
        time, time, disk_partition)
      result = database.select(
        "disk",
        columns = "free, datetime(date || ' ' || time)",
        where = where_query,
        order = "datetime(date || ' ' || time) ASC"
        ).fetchall()
      # checks that there are 15 days of data
      if not result or len(result) < 15:
        self.logger.info("No or not enough results from collector database in table disk: no predection")
        return None
      # put the list in pandas dataframe format and set the right types
      df = pd.DataFrame(data=result, columns=['free', 'date'])
      df.loc[:,'date'] = pd.to_datetime(df.date)
      df = df.astype({'free': np.float})
      df = df.set_index('date')
      # find the best configuration by trying different combinations
      p = d = q = range(0,5)
      pdq = list(itertools.product(p,d,q))
      best_score = float("inf")
      best_cfg = None
      for param in pdq:
        try:
          # ignore the warnings during the ARIMA calculation
          warnings.filterwarnings("ignore")
          model_arima = ARIMA(df, order=param)
          model_arima_fit = model_arima.fit(disp=False)
          if model_arima_fit.aic < best_score:
            best_cfg = param
            best_score = model_arima_fit.aic
          # reset warnings 
          warnings.filterwarnings("ignore")
        except:
          continue
      # set the days to be predicted
      max_date_predicted = day_range+1
      future_index_date = pd.date_range(df.index[-1], freq='24H', periods=max_date_predicted)
      try:
        model_arima = ARIMA(df, order=best_cfg)
        # disp < 0 means no output about convergence information
        model_arima_fit = model_arima.fit(disp=-1)
        # save ARIMA predictions
        fcast, se, conf = model_arima_fit.forecast(max_date_predicted, alpha=0.05)
        # pass the same index as the others
        fcast = pd.Series(fcast, index=future_index_date)
        if fcast.empty:
          self.logger.info("Arima prediction: none. Skipped prediction")
          return None
      except:
        self.logger.info("Arima prediction error: skipped prediction")
        return None
      # get results with 95% confidence
      lower_series = pd.Series(conf[:, 0], index=future_index_date)
      upper_series = pd.Series(conf[:, 1], index=future_index_date)
      return fcast, lower_series, upper_series
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
    default_threshold = None
    if disk_size is not None:
      default_threshold = round(disk_size/(1024*1024*1024) * 0.05, 2)
    threshold = float(self.getConfig('threshold', default_threshold) or default_threshold)
    threshold_days = float(self.getConfig('threshold-days', '30') or '30')

    free_space = self.getFreeSpace(disk_partition, db_path, currentdate,
                                   currenttime)
    if free_space == 0:
      return
    elif free_space > threshold*1024*1024*1024:
      inode_usage = self.getInodeUsage(self.getPartitionFolder())
      if inode_usage:
        self.logger.error(inode_usage)
      else:
        self.logger.info("Current disk usage: OK")
        # if the option is enabled and the current disk size is large enough,
        # we check the predicted remaining disk space
        display_prediction = bool(int(self.getConfig('display-prediction'), False))
        self.logger.info("Enable to display disk space predictions: %s" % display_prediction)
        if display_prediction:
          nb_days_predicted = int(self.getConfig('nb-days-predicted', 10) or 10)
          fcast, lower_series, upper_series = self.diskSpacePrediction(
            disk_partition, db_path, currentdate, currenttime, nb_days_predicted)
          space_left_predicted = fcast.iloc[-1]
          last_date_predicted = datetime.datetime.strptime(str(fcast.index[-1]), 
                                                          "%Y-%m-%d %H:%M:%S").date()
          delta_days = (last_date_predicted - \
            datetime.datetime.strptime(currentdate, "%Y-%m-%d").date()).days
          self.logger.info("Prediction: there will be %.2f G left on %s, in %s days." % (
            space_left_predicted/(1024*1024*1024), last_date_predicted, delta_days))
          if space_left_predicted <= threshold*1024*1024*1024:
            self.logger.warning("The free disk space will be too low. " \
                              "(disk size: %.2f G, threshold: %s G)" % (
                                disk_size/(1024*1024*1024), threshold))
          return
        else:
          return

    message = "Free disk space low: remaining %.2f G (disk size: %.2f G, threshold: %s G)." % (
      free_space/(1024*1024*1024), disk_size/(1024*1024*1024), threshold)

    display_partition = bool(int(self.getConfig('display-partition'), False))
    self.logger.info("Enable to display the 3 biggest partitions: %s" % display_partition)
    if display_partition:
      # display the 3 partitions that have the most storage capacity on the disk
      big_partitions = self.getBiggestPartitions(db_path, currentdate, currenttime)
      if big_partitions is not None:
        for partition in big_partitions:
          user_name, size_partition, date_checked = partition
          message += " The partition %s use %s G (date checked: %s)." % (
            user_name, round(size_partition/(1024*1024*1024), 2), date_checked)
    # display the final error message
    self.logger.error(message)

  def test(self):
    return self._test(result_count=1, failure_amount=1)

  def anomaly(self):
    return self._test(result_count=3, failure_amount=3)