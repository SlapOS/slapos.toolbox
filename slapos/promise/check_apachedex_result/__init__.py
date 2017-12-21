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

def checkApachedexResult(apachedex_path, apachedex_report_status_file, desired_threshold):
  message = "No apachedex result for today or yesterday"
  today = datetime.date.today()
  today_or_yesterday = today, today - datetime.timedelta(1)
  try:
    apachedex_file = max(os.listdir(apachedex_path),
      key=lambda x: os.stat(os.path.join(apachedex_path, x)).st_mtime)
  except ValueError:
    if datetime.date.fromtimestamp(os.stat(apachedex_path).st_mtime) in today_or_yesterday: 
      return 0, "Instance has been just deployed. Skipping check.."
  else:
    for date in today_or_yesterday:
      if apachedex_file == date.strftime('ApacheDex-%Y-%m-%d.html'):

        with open(os.path.join(apachedex_path, apachedex_file)) as f:
          content = f.read()
        if content:
          # XXX: if not a lot of usage, skip
          # XXX: too fragile, use lxml.html and use xpath
          regex = r"Overall<\/h2>.*\n<th>apdex<\/th><th>.*?\n<\/tr><tr>\n<td [^<]*>(.*?)%<\/td>"
          m = re.findall(regex, content)
          if m:
            apx_result=int(m[0])
            if apx_result > desired_threshold:
              return 0,  "Thanks for keeping it all clean, result is " + str(apx_result)
            else:
              return 1, "Threshold is lower than expected:  Expected was " + \
                     str(desired_threshold) +" and current result is " + str(apx_result)
        message = "No result found in the apdex file or the file is corrupted"
        break

  with open(apachedex_report_status_file) as f:
    try:
      json_content = json.load(f)
    except ValueError, e:
      json_content = ''
  if json_content:
    message += "\n" + json_content["message"]
  return 1, message

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("--apachedex_path", required=True)
  parser.add_argument("--status_file", required=True)
  parser.add_argument("--threshold", required=True)
  args = parser.parse_args()

  status, message = checkApachedexResult(args.apachedex_path, args.status_file, args.threshold)
  print(message)
  sys.exit(status)