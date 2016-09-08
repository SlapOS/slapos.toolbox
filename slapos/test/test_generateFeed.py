import collections
import datetime
import json
import os
import shutil
import tempfile
import unittest

from slapos.generateFeed import generateFeed

class Option(dict):
    def __init__(self, **entries): 
        self.__dict__.update(entries)
    def __setitem__(i, y):
        self.__dict__[i] = y

class TestRunnerBackEnd(unittest.TestCase):
  def setUp(self):
    self.item_directory = tempfile.mkdtemp()
    self.feed_path = os.path.join(self.item_directory, 'path')

  def tearDown(self):
    shutil.rmtree(self.item_directory)

  def getFeedOption(self, **kw):
    """
    Returns a sample of channel elements with values
    """
    option = {
      'title': 'Feed title',
      'link': 'http://example.com',
      'description': 'Feed description',
      'output': self.feed_path,
    }
    option.update(kw)
    return Option(option)

  def saveAsStatusItem(self, filename, content)
    """
    Save a JSON at filename in self.item_directory as a status item
    """
    with open(filename, 'w') as status_file:
      filename.write(json.dumps(content))

  def createItemSample(self):
    """
    Populate item_directory with a few sample items
    """
    item = [
      # Last in alphabet, first in pubDate
      ('zzz.item' :
        {'description': 'description is OK too',
         'link': "http://example.com",
         'pubDate': datetime.datetime(2000, 1, 1),
         'title': 'everything is OK',
        }),
      # First in pubDate, last in alphabet 
      ('aaa.item' :
        {'description': 'what went wrong ?',
         'link': "http://example.com",
         'pubDate': datetime.datetime(2000, 12, 31),
         'title': 'I guess we have an ERROR',
        }),
    ]
    for filename, content in item:
      saveAsStatusItem(filename, content)

  def test_feedItemsAreSortedByDate(self):
    self.createItemSample()
    option = self.getFeedOption()
    content_feed = generateFeed(option)
    feed = feedparser.parse(content_feed)

    self.assertFalse(feed.bozo)

    start_date = None
    for item in feed:
      if start_date is None:
        start_date = item.published_parsed
      assert start_date <= item.published_parsed


if __name__ == '__main__':
  unittest.main()