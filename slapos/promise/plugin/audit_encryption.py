import json, re, subprocess
from zope.interface import implementer
from slapos.grid.promise import interface
from slapos.grid.promise.generic import GenericPromise


@implementer(interface.IPromise)
class RunPromise(GenericPromise):

  def __init__(self, config):
    config.setdefault('periodicity', 86400)
    super().__init__(config)
    self.setTestLess()

  anomaly = GenericPromise._test

  def sense(self):
    plain = []
    crypted = []
    crypted_all = set()
    root = False
    is_virtual = re.compile(r'(nbd|zram)\d+').fullmatch
    for x in json.loads(subprocess.check_output((
        'lsblk', '--json', '-o', 'PKNAME,KNAME,NAME,TYPE,MOUNTPOINTS',
        '-Q', 'TYPE != "loop" && !RM'), text=1))['blockdevices']:
      if x['type'] == 'crypt':
        crypted_all.add(x['kname'])
        crypted.append("%(name)s (%(pkname)s)" % x)
      else:
        mountpoints = x['mountpoints']
        if x['pkname'] in crypted_all:
          crypted_all.add(x['kname'])
        elif mountpoints and not (is_virtual(x['name']) or
                                  '/boot' in mountpoints or
                                  '/boot/efi' in mountpoints):
          mountpoints.sort()
          plain.append("%s (%s)" % (x['name'], ', '.join(mountpoints)))
        if '/' in mountpoints:
          root = True
    if not root:
      plain.append('? (/)')
    if plain:
      self.logger.error('unencrypted devices: %s', ', '.join(plain))
    else:
      self.logger.info('encrypted devices: %s', ', '.join(crypted))
