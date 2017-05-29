import requests
import re
import signal
import os
import psutil
import json
import time

search_pid_regex = r"</td><td.*?>(.+?)</td><td>yes \(old gen\)</td>"

def main(url, user, password, db_path, timeout=600):
  if os.path.exists(db_path):
    with open(db_path) as json_file:
       try:
         pid_dict = json.load(json_file)
       except ValueError:
         pid_dict = {}
  else:
    pid_dict = {}

  r = requests.get(url, auth=(user, password))
  for i in re.findall(search_pid_regex, r.text):
    try:
      process = psutil.Process(int(i))
    except psutil.NoSuchProcess:
      continue

    # Ensure the process is actually an apache
    if process.cmdline()[0].endswith("/httpd"):
      pid_dict.setdefault(i, time.time() + timeout)
      if pid_dict[i] < time.time():
        print "Sending signal -%s to %s" % (signal.SIGKILL, i)
        os.kill(int(i), signal.SIGKILL)

  for i in pid_dict.copy():
    try:
      process = psutil.Process(int(i))
    except psutil.NoSuchProcess:
      del pid_dict[i]

  with open(db_path, "w") as f:
    f.write(json.dumps(pid_dict))

