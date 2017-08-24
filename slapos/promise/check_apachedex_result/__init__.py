#!/usr/bin/env python

"""
Check if a apachedex result matches the desired threshold or raises an error.
"""

import json
import os
import re
import sys
import time
import datetime
import argparse

def checkApachedexResult(apachedex_file, apachedex_report_status_file, desired_threshold):

  if not os.path.isfile(apachedex_file):
    open(apachedex_file, 'a').close()

  with open(apachedex_file, 'r') as content_file:
    content = content_file.read()
 
  if len(content) == 0:
    # File is empty
    # Check the creation date of the file
    # and if the date is greater than 30 hour throw an error
    date_created = os.path.getmtime(apachedex_file)
    current_date = time.mktime(datetime.datetime.now().timetuple())
    if current_date - date_created > 108000:
      with open(apachedex_report_status_file) as f:
        json_content = f.read()

      # Print the message from the monitor report
      if len(json_content) > 0:
        message = json.loads(json_content)["message"]
        return message + "\nFile modification date is greater than 30 hours"
      return "File modification date is greater than 30 hour"
  else:
    #TODO: this is old regex for bash, improve it
    regex = r"Overall<\/h2>.*\n<th>apdex<\/th><th>.*?\n<\/tr><tr>\n<td [^<]*>(.*?)%<\/td>"
    m = re.findall(regex, content)
    if len(m) > 0:
      result=int(m[0])
      if result > desired_threshold:
        return "Thanks for keeping it all clean, result is " + str(result)
      else:
        return "Threshold is lower than expected:  Expected was " + \
               str(desired_threshold) +" and current result is " + str(result)
  return "No result found in the apdex file or the file is corrupted"

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("--apachedex_file", required=True)
  parser.add_argument("--status_file", required=True)
  parser.add_argument("--threshold", required=True)
  args = parser.parse_args()

  if args.apachedex_file:
    args.apachedex_file = args.apachedex_file + "/ApacheDex-" + datetime.date.today().strftime('%Y-%m-%d') + ".html"

  result = checkApachedexResult(args.apachedex_file, args.status_file, args.threshold)

  print result
  if result != "OK":
    sys.exit(1)
