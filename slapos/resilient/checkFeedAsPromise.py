# Command line script to test a RSS feed in a promise
# Checks that a given pattern can be found (or not) in the title or the
# description of the latest feed item.
# A time buffer option can be given, so the promise really gets true, or false,
# only if the last item is older or younger than the allowed time buffer.
import argparse
import datetime
import feedparser
import sys

def parseArguments():
  parser = argparse.ArgumentParser()
  parser.add_argument('--feed-path', dest='feed_path',
                      help='Path or Url of the feed to search')
  parser.add_argument('--title', dest='title', action='store_true',
                      help='Patterns should be looked for in feed item\'s title')
  parser.add_argument('--description', dest='description', action='store_true',
                      help='Patterns should be looked for in feed item\'s description')
  parser.add_argument('--ok-pattern', dest='ok_pattern_list', action='append',
                      default=[],
                      help='If this pattern is found, then promise succeeds')
  parser.add_argument('--ko-pattern', dest='ko_pattern_list', action='append',
                      default=[],
                      help='If this pattern is found, then promise fails')
  parser.add_argument('--time-buffer', dest='time_buffer', type=int,
                      help='Time delta in seconds before the promise really succeeds or fails')
  return parser.parse_args()

def containsPattern(string, pattern_list):
  for pattern in pattern_list:
    if string.find(pattern) >= 0:
      return True
  return False

def main():
  option = parseArguments()
  feed = feedparser.parse(option.feed_path)

  if feed.bozo:
    sys.exit('Feed malformed')

  last_item = feed.entries[-1]
  if option.title:
    candidate_string = last_item.title
  elif option.description:
    candidate_string = last_item.description
  else:
    sys.exit('At least one in [--title|--description] should be provided')

  publication_date = datetime.datetime(*last_item.published_parsed[:7])
  publication_age = datetime.datetime.now() - publication_date
  time_buffer = datetime.timedelta(seconds=option.time_buffer)

  ok_pattern_found = containsPattern(candidate_string, option.ok_pattern_list)
  ko_pattern_found = containsPattern(candidate_string, option.ko_pattern_list)

  if ok_pattern_found and ko_pattern_found:
    sys.exit('Both OK and KO patterns found: please check arguments')

  # Expectations fulfilled
  if ok_pattern_found:
      sys.exit(0)

  if ko_pattern_found:
    sys.exit('KO pattern found')

  if not ok_pattern_found:
    if publication_age < time_buffer:
      # We have to wait for buffer to expire
      sys.exit(0)
    else:
      # If time-buffer is out, we are in stalled state
      sys.exit('Stalled situation')

  # If not ok, and not stalled, what can have possibly happen ?
  sys.exit(1)

if __name__ == '__main__':
  main()