import argparse
import re
import time
import sys
from slapos.networkbench.ping import ping, ping6

def test(address, ipv4, count):

  if ipv4:
    return ping(address, count=count)

  return ping6(address, count=count)

def main():
  parser = argparse.ArgumentParser()
  # Address to ping to
  parser.add_argument("-a", "--address", required=True)
  # Force use ipv4 protocol
  parser.add_argument("-4", "--ipv4", action="store_true" )
  parser.add_argument("-c", "--count", metavar="COUNT", default=10 )
  args = parser.parse_args()

  result = test(args.address, args.ipv4, args.count)

  print "%s host=%s code=%s, result=%s, packet_lost_ratio=%s msg=%s" % result
  if result[4] != "0":
    # Packet lost occurred
    print "FAIL"
    sys.exit(1)
  print "OK"

