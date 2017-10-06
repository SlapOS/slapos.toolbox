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

def checkApachedexResult(apachedex_file, apachedex_report_status_file, desired_threshold, just_deployed):

  result = { 'status' : 1 }

  if not os.path.isfile(apachedex_file):
    open(apachedex_file, 'a').close()

  if just_deployed:
    result['message'] = "Instance has been just deployed. Skipping check.."
    result['status'] = 0
    return result

  with open(apachedex_file, 'r') as content_file:
    content = content_file.read()
 
  if len(content) == 0:
    # File is empty
    # Check if the file from yesterday is empty
    # If yes, check if the today's file creation date is greater than 12 hours

    yesterday = datetime.date.fromordinal(datetime.date.today().toordinal()-1).strftime('%Y-%m-%d')
    apachedex_folder = os.path.dirname(apachedex_file)
    last_file = apachedex_folder + "/ApacheDex-" + yesterday + ".html"
    if not os.path.isfile(last_file):
      # last file do not exist
      result['message'] = "File is empty, Apachedex is yet to run or running"
      result['status'] = 0
      return result
    
    with open(last_file, 'r') as content_file:
      last_content = content_file.read()
     
    date_created = os.path.getmtime(apachedex_file)
    current_date = time.mktime(datetime.datetime.now().timetuple())
    if current_date - date_created > 43200 and len(last_content) is 0:
      with open(apachedex_report_status_file) as f:
        json_content = f.read()

      # Print the message from the monitor report status file and fail
      result['message'] = "No apachedex result since 36 hours"
      if len(json_content) > 0:
        message = json.loads(json_content)["message"]
        result['message'] = message + "\n" + result['message']
      return result
    else:
      result['message'] = "File is empty, Apachedex is yet to run or running" 
      result['status'] = 0
      return result
  else:
    #TODO: check if not a lot of usage by checking number of lines

    regex = r"Overall<\/h2>.*\n<th>apdex<\/th><th>.*?\n<\/tr><tr>\n<td [^<]*>(.*?)%<\/td>"
    m = re.findall(regex, content)
    if len(m) > 0:
      apx_result=int(m[0])
      if apx_result > desired_threshold:
        result['message'] = "Thanks for keeping it all clean, result is " + str(apx_result)
        result['status'] = 0
        return result
      else:
        result['message'] = "Threshold is lower than expected:  Expected was " + \
               str(desired_threshold) +" and current result is " + str(apx_result)
        return result
  
  result['message'] = "No result found in the apdex file or the file is corrupted"
  return result

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("--apachedex_file", required=True)
  parser.add_argument("--status_file", required=True)
  parser.add_argument("--threshold", required=True)
  args = parser.parse_args()

  # check if the folder age is less than 10 mins
  just_deploye = False 
  st=os.stat(args.apachedex_file)
  if st.st_mtime < 600:
    just_deploye = True 

  if apachedex_file:
    apachedex_file = apachedex_file + "/ApacheDex-" +  datetime.date.today().strftime('%Y-%m-%d') + ".html"

  result = checkApachedexResult(args.apachedex_file, args.status_file, args.threshold, just_deployed)
  print result['message']
  sys.exit(result['status'])
