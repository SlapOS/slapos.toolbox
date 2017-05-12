import re
import time
import sys
import gzip
import argparse
import os

r = re.compile("^(\[[^\]]+\]) (\[[^\]]+\]) (.*)$")

def test(log_file, maximum_delay):
  error_amount = 0
  no_route_error = 0
  network_is_unreacheable = 0
  timeout = 0
  parsing_failure = 0
  if not os.path.exists(log_file):
    # file don't exist, nothing to check
    return "OK"

  with open(log_file) as f:

    f.seek(0, 2)
    block_end_byte = f.tell()
    f.seek(-min(block_end_byte, 4096), 1)

    data = f.read()
    for line in reversed(data.splitlines()):
      m = r.match(line)
      if m is None:
        continue
      dt, level, msg = m.groups()
      try:
        try:
          t = time.strptime(dt[1:-1], "%a %b %d %H:%M:%S %Y")
        except ValueError:
          # Fail to parser for the first time, try a different output.
          t = time.strptime(dt[1:-1], "%a %b %d %H:%M:%S.%f %Y")
      except ValueError:
          # Probably it fail to parse
          if parsing_failure < 3:
            # Accept failure 2 times, as the line can be actually
            # cut on the middle.
            parsing_failure += 1
            continue
          raise

      if maximum_delay and (time.time()-time.mktime(t)) > maximum_delay:
        # no result in the latest hour
        break

      if level != "[error]":
        continue

      # Classify the types of errors
      if "(113)No route to host" in msg:
        no_route_error += 1
      elif "(101)Network is unreachable" in msg:
        network_is_unreacheable += 1
      elif "(110)Connection timed out" in msg:
        timeout += 1

      error_amount += 1

  if error_amount:
    return "ERROR=%s (NOTROUTE=%s, UNREACHEABLENET=%s, TIMEOUT=%s)" % (error_amount, no_route_error, network_is_unreacheable, timeout)

  return "OK"

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("-l", "--log-file", required=True)
  parser.add_argument("-d", "--maximum-delay", default=0)
  args = parser.parse_args()

  log_file = args.log_file

  result = test(args.log_file, args.maximum_delay)

  print result
  if result != "OK":
    sys.exit(1)

