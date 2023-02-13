import argparse
import sys
from . import ping

def main():
  parser = argparse.ArgumentParser(
        description="Run network benchmarch.",
        )
  _ = parser.add_argument
  _('-p', '--protocol', default="4", type=str)
  _('-t', '--timeout', default=10, type=int)
  _('-c', '--count', default=10, type=int)
  _('host', type=str)
  config = parser.parse_args()
  result = ping(config.host, config.timeout, config.protocol, config.count)
  print(result)
  if result[3] == "failed":
    sys.exit(1)
