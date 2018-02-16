#!/usr/bin/env python

"""
Check if memory usage is lower than 80% of total memory.

Uses:
- /proc/meminfo
"""

import sys
import sqlite3
import argparse
import datetime

from slapos.collect.db import Database

def getFreeMemory(database, time, date):

  mem = {}
  database = Database(database)
  try:
    database.connect()
    query_result = database.select("computer", date, "memory_size", limit=1) 
    result = zip(*query_result)
    if not result or not result[0][0]:
      print "couldn't fetch total memory, collectordb is empty?"
      return 0
    mem['total'] = result[0][0]

    # fetch free and used memory 
    where_query = "time between '%s:00' and '%s:30' " % (time, time)
    query_result = database.select("system", date, "memory_free, memory_used", where=where_query)
    result = zip(*query_result)
    if not result or not result[0][0]: 
      print "couldn't fetch free memory"
      return 0
    mem['free'] = result[0][0]
    if not result or not result[1][0]: 
      print "couldn't fetch used memory"
      return 0
    mem['used'] = result[1][0]
  finally:
    database.close()

  return mem

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("-db", "--collectordb", required=True)
  args = parser.parse_args()

  # get last minute
  now = datetime.datetime.now()
  currentdate = now.strftime('%Y-%m-%d')
  delta = datetime.timedelta(minutes=1)
  currenttime = now - delta
  currenttime = currenttime.time().strftime('%H:%M')
  db_path = args.collectordb

  if db_path.endswith("collector.db"):db_path=db_path[:-len("collector.db")]
  memory = getFreeMemory(db_path, currenttime, currentdate)
  threshold = float(memory['total']) * 0.2

  if memory is 0:
    return 0
  if memory['free'] > threshold:
    print "OK - memory used: {:d}% ({}B of {}B)".format(memory["used"] * 100 / memory["total"], memory["used"], memory["total"])
    return 0
  print "Low memory - usage: {:d}% ({}B of {}B)".format(memory["used"] * 100 / memory["total"], memory["used"], memory["total"])
  return 1

if __name__ == "__main__":
  sys.exit(main())
