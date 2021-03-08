import click
import dns.exception
import dns.resolver
import ipaddress
import json

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
@click.argument('input_list', nargs=-1, type=click.File('rb'))
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
  for fileio in input_list:
    for line in fileio.readlines():
      for entry in line.split():
        try:
          address_dict[entry] = [
            str(ipaddress.ip_address(unicode(entry)).exploded)]
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
    print dumps
  else:
    output.write(dumps)


if __name__ == '__main__':
  main()
