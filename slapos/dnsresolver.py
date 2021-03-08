# coding: utf-8
# Copyright (C) 2021  Nexedi SA and Contributors.
#                     Łukasz Nowak <luke@nexedi.com>
#
# This program is free software: you can Use, Study, Modify and Redistribute
# it under the terms of the GNU General Public License version 3, or (at your
# option) any later version, as published by the Free Software Foundation.
#
# You can also Link and Combine this program with other software covered by
# the terms of any of the Free Software licenses or any of the Open Source
# Initiative approved licenses and Convey the resulting work. Corresponding
# source of such a combination shall include the source code for all other
# software used.
#
# This program is distributed WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See COPYING file for full licensing terms.
# See https://www.nexedi.com/licensing for rationale and options.
from __future__ import print_function

import click
import dns.exception
import dns.resolver
import ipaddress
import json
import os

TIMEOUT = 5


@click.command(short_help="Resolves domains and IPs to IPs")
@click.option(
  "--style",
  "-s",
  help="Output style of the JSON.",
  type=click.Choice(["list", "full"]),
  default="list",
  show_default=True
)
@click.option(
  "--output",
  "-o",
  help="Output file.",
  type=click.File('wb')
)
@click.argument(
  'input_list',
  nargs=-1,
  type=click.Path(),  # can't use click.File, as existence is required and
                      # that increases usage complexity
)
def main(
  style,
  output,
  input_list
):
  address_dict = {}
  # use default resolver of the machine, as this is expected approach
  resolver = dns.resolver.Resolver(configure=True)
  resolver.timeout = TIMEOUT
  resolver.lifetime = TIMEOUT
  resolver.edns = -1
  for filename in input_list:
    if not os.path.exists(filename):
      continue
    with open(filename, 'rb') as fh:
      for line in fh.readlines():
        line = line.strip()
        if line.startswith('#'):
          continue
        for entry in line.split():
          entry = entry.decode('utf-8')
          try:
            address_dict[entry] = [
              str(ipaddress.ip_address(entry).exploded)]
          except Exception:
            try:
              address_dict[entry] = [
                answer.address for answer in resolver.query(entry)]
            except (
                dns.resolver.NXDOMAIN,
                dns.resolver.NoAnswer,
                dns.exception.Timeout,
                dns.resolver.NoNameservers,
            ):
              address_dict[entry] = []
  if style == 'list':
    merged_list = []
    for q in address_dict.values():
      merged_list.extend(q)
    dumps = json.dumps(sorted(set(merged_list)), indent=2)
  else:
    dumps = json.dumps(address_dict, indent=2)

  if output is None:
    print(dumps)
  else:
    output.write(dumps.encode())


if __name__ == '__main__':
  main()
