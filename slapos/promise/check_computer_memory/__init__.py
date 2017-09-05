#!/usr/bin/env python

"""
Check if memory usage is greater than given threshold.

Uses:
- /proc/meminfo
"""

import sys

def getFreeMemory(memFile):

  with open(memFile, 'r') as mem:
    ret = {}
    tmp = 0
    for i in mem:
      sline = i.split()
      if str(sline[0]) == 'MemTotal:':
        ret['total'] = int(sline[1])
      elif str(sline[0]) in ('MemFree:', 'Buffers:', 'Cached:'):
        tmp += int(sline[1])
    ret['free'] = tmp
    ret['used'] = int(ret['total']) - int(ret['free'])
  return ret

def main():
  memory = getFreeMemory('/proc/meminfo')
  if len(sys.argv) > 1:
    threshold = sys.argv[1] 
  else:
    threshold = float(memory['total']) * 0.2

  if memory['free'] > threshold:
    print "All Good. total: "+ str(memory['total']) + " and used: "+ str(memory['used'])
    return 0
  print "Ops! Memory is low, total: "+ str(memory['total']) + " and used: "+ str(memory['used'])
  return 1

if __name__ == "__main__":
  sys.exit(main())
