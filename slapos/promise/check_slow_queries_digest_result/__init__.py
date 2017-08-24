#!/usr/bin/env python

"""
Check if a mariadb result matches the desired threshold or raises an error.
"""

import json
import os
import re
import sys
import time
import datetime
import argparse

def checkMariadbDigestResult(mariadbdex_file, mariadbdex_report_status_file,
                             max_query_threshold, slowest_query_threshold):

  if not os.path.isfile(mariadbdex_file):
    open(mariadbdex_file, 'a').close()

  with open(mariadbdex_file, 'r') as content_file:
    content = content_file.read()
 
  if len(content) == 0:
    # File is empty
    # Check the creation date of the file
    # and if the date is greater than 30 hour throw an error
    date_created = os.path.getmtime(mariadbdex_file)
    current_date = time.mktime(datetime.datetime.now().timetuple())
    if current_date - date_created > 108000:
      with open(mariadbdex_report_status_file) as f:
        json_content = f.read()

      # Print the message from the monitor report
      if len(json_content) > 0:
        message = json.loads(json_content)["message"]
        return message + "\nFile modification date is greater than 30 hours"
      return "File modification date is greater than 30 hour"
  else:
    regex = r"Overall: (.*) total,[\S\s]*# Exec time( *([\d]+)m?s?){4}"
    m = re.findall(regex, content)
    if len(m) > 0:
      total_queries_exec=m[0][0].strip()
      slowest_query_time=int(m[0][2].strip())
      has_k=total_queries_exec[-1:]
      if has_k == "k":
        pre=total_queries_exec[:-1]
        total_queries_exec=float(pre)*1000
      else:
        total_queries_exec=int(total_queries_exec)

      if total_queries_exec < max_query_threshold and slowest_query_time < slowest_query_threshold:
        return "Thanks for keeping it all clean, total queries are : " + str(total_queries_exec) + \
               " slowest query time is : " + str(slowest_query_time)
      else:
        return "Threshold is lower than expected: \nExpected total queries : " + \
               str(max_query_threshold) +" and current is: " + str(total_queries_exec) + "\n"+ \
               "Expected slowest query : " + str(slowest_query_threshold) + " and current is: " + str(slowest_query_time)
  return "No result found in the apdex file or the file is corrupted"

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("--ptdigest_file", required=True)
  parser.add_argument("--status_file", required=True)
  parser.add_argument("--max_queries_threshold", required=True)
  parser.add_argument("--slowest_query_threshold", required=True)
  args = parser.parse_args()

  result = checkMariadbDigestResult(args.ptdigest_file, args.status_file, args.max_queries_threshold, args.slowest_query_threshold)

  print result
  if result != "OK":
    sys.exit(1)
