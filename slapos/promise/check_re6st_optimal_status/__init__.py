import argparse
import re
import time
import sys
from slapos.networkbench.ping import ping, ping6

def test(ipv6, ipv4, count):

  result_ipv4 = ping(ipv4, count=count)
  print "%s host=%s code=%s, result=%s, packet_lost_ratio=%s msg=%s" % result_ipv4

  result_ipv6 = ping6(ipv6, count=count)
  print "%s host=%s code=%s, result=%s, packet_lost_ratio=%s msg=%s" % result_ipv6

  if result_ipv4[3] == "failed" and result_ipv6[3] != "failed":
    # IPv4 is unreacheable
    return "OK"

  if result_ipv6[3] == "failed":
    # IPv6 is unreacheable
    return "FAILED"

  if float(result_ipv4[3]) < float(result_ipv6[3]):
    return "FAIL"

  # Compare if both has Same working rate
  return "OK"  

def main():
  parser = argparse.ArgumentParser()
  # promise ipv6 and ipv4 address to compare.
  parser.add_argument("-4", "--ipv4", required=1 )
  parser.add_argument("-6", "--ipv6", required=1)

  parser.add_argument("-c", "--count", default=10 )
  args = parser.parse_args()

  result = test(args.ipv6, args.ipv4, args.count)

  print result
  if result != "OK":
    # re6st is not on an optimal state.
    sys.exit(1)

