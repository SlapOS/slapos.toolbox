#!/usr/bin/env python

"""
Check if free disk space is less than given threshold.
"""

import sys
import os

import sqlite3
import argparse
import datetime

from slapos.collect.db import Database

def getFreeSpace(path, database, date, time):

  database = Database(database)
  try:
    database.connect()
    # fetch free and used memory 
    where_query = "time between '%s:00' and '%s:30' and mountpoint=%s" % (time, time, path)
    query_result = database.select("disk", date, "free", where=where_query)
    result = zip(*query_result)
    if not result or not result[0][0]: 
      print "couldn't fetch free disk space"
      return 0
    disk_free = result[0][0]
  finally:
    database.close()

  return disk_free


def getInodeUsage(path):
  max_inode_usage = 97.99 # < 98% usage
  stat = os.statvfs(path)
  usage_output = ""
  total_inode = stat.f_files
  free_inode = stat.f_ffree
  usage = round((float(total_inode - free_inode) / total_inode), 4) * 100
  if usage > max_inode_usage:
    return "Disk Inodes usages is really high: %s%%" % usage
  elif os.path.exists('/tmp'):
    # check if /tmp is mounted on another disk than path
    tmp_stat = os.statvfs('/tmp')
    if tmp_stat.f_blocks != stat.f_blocks:
      tmp_usage = round((float(tmp_stat.f_files - tmp_stat.f_ffree) / tmp_stat.f_files), 4) * 100
      if tmp_usage > max_inode_usage:
        return "Disk Inodes usage is high: %s%%" % tmp_usage
  return ""

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("-db", "--collectordb", required=True)
  parser.add_argument("-hp", "--home_path", required=True)
  parser.add_argument("-c", "--config", required=True)
  args = parser.parse_args()

  min_free_size = 1024*1024*1024*2 # 2G by default
  if os.path.exists(args.config_file):
    with open(args.config_file) as f:
      min_size_str = f.read().strip()
      if min_size_str == '0':
        # disable check
        print "Free disk space check is disabled\n set a number up to 0 to enable!"
        exit(0)
      if min_size_str.isdigit():
        value = int(min_size_str)
        if value >= 200:
          # Minimum value is 200Mb, it's already low
          min_free_size = int(min_size_str)*1024*1024
  else:
    with open(args.config_file, 'w') as f:
      f.write(str(min_free_size/(1024*1024)))

  # get last minute
  now = datetime.datetime.now()
  currentdate = now.strftime('%Y-%m-%d')
  delta = datetime.timedelta(minutes=1)
  currenttime = now - delta
  currenttime = currenttime.time().strftime('%H:%M')
  db_path = args.collectordb
  if db_path.endswith("collector.db"):db_path=db_path[:-len("collector.db")]

  free_space = getFreeSpace(args.home_path, db_path, currentdate, currenttime)
  if free_space > min_free_size:
    inode_usage = check_inode_usage(args.home_path)
    if inode_usage:
      print inode_usage
      exit(2)
    print "Disk usage: OK"
    exit(0)

  memory = getFreeMemory(db_path, currenttime, currentdate)
  threshold = float(memory['total']) * 0.2

  if memory is 0:
    return 0
  if memory['free'] > threshold:
    print "All Good. total memory: "+ str(memory['total']) + " and used memory: "+ str(memory['used'])
    return 0
  print "Ops! Memory is low, total memory: "+ str(memory['total']) + " and used memory: "+ str(memory['used'])
  return 1

if __name__ == "__main__":
  sys.exit(main())

