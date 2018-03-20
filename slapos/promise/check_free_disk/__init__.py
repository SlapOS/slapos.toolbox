#!/usr/bin/env python

"""
Check if free disk space is less than given threshold.
"""

import sys
import os

import sqlite3
import argparse
import datetime
import psutil

from slapos.collect.db import Database

def getFreeSpace(disk_partition, database, date, time):

  database = Database(database, create=False, timeout=5)
  try:
    # fetch free disk space
    database.connect()
    where_query = "time between '%s:00' and '%s:30' and partition='%s'" % (time, time, disk_partition)
    query_result = database.select("disk", date, "free", where=where_query)
    result = zip(*query_result)
    if not result or not result[0][0]: 
      print "No result from collector database: disk check skipped"
      return 0
    disk_free = result[0][0]
  finally:
    database.close()
  return int(disk_free)


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
  parser.add_argument("--collectordb", required=True)
  parser.add_argument("--home_path", required=True)
  parser.add_argument("--config", required=True)
  args = parser.parse_args()

  # find if a disk is mounted on the path
  disk_partition = ""
  path = os.path.join(args.home_path, "") +"extrafolder"
  partitions = psutil.disk_partitions()
  while path is not '/':
    if not disk_partition:
      path = os.path.dirname(path)
    else:
      break
    for p in partitions:
      if p.mountpoint is path:
        disk_partition = p.device
        break
  if not disk_partition:
    print "Couldn't find disk partition"
    exit(2)

  min_free_size = 1024*1024*1024*2 # 2G by default
  if os.path.exists(args.config):
    with open(args.config) as f:
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
    with open(args.config, 'w') as f:
      f.write(str(min_free_size/(1024*1024)))

  # get last minute
  now = datetime.datetime.now()
  currentdate = now.strftime('%Y-%m-%d')
  currenttime = now - datetime.timedelta(minutes=1)
  currenttime = currenttime.time().strftime('%H:%M')

  db_path = args.collectordb
  if db_path.endswith("collector.db"):
    db_path=db_path[:-len("collector.db")]

  free_space = getFreeSpace(disk_partition, db_path, currentdate, currenttime)
  if free_space > min_free_size:
    inode_usage = getInodeUsage(args.home_path)
    if inode_usage:
      print inode_usage
      exit(2)
    print "Disk usage: OK"
    exit(0)
  
  free_space = round(free_space/(1024.0*1024*1024), 2)
  min_space = round(min_free_size/(1024.0*1024*1024), 2)
  print 'Free disk space low: remaining %s G (threshold: %s G)' % (
    free_space, min_space)
  print 'Please modify minimum value in your monitor interface.'
  exit(1)

if __name__ == "__main__":
  sys.exit(main())

