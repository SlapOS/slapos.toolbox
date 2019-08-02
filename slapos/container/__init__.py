# -*- coding: utf-8 -*-

from __future__ import print_function
from six.moves import configparser
import argparse
from six.moves import dbm_gnu as gdbm

import sys
import os
import logging

from . import process

def main():
    parser = argparse.ArgumentParser(description="Slapcontainer binary")
    parser.add_argument('configuration_file', type=str,
                        help="SlapOS configuration file.")
    parser.add_argument('database', type=str,
                        help='slapcontainer database')
    log_lvls = [lvl for lvl in logging._levelNames.keys()
                if isinstance(lvl, basestring)]
    parser.add_argument('--log', nargs=1, default=['INFO'],
                        choices=log_lvls,
                        metavar='lvl', help='Log level')
    parser.add_argument('--pid', nargs=1, help='pid file path')
    args = parser.parse_args()

    if args.pid is not None:
        pid_filename = args.pid[0]
        if os.path.exists(pid_filename):
            print("Already running", file=sys.stderr)
            return 127
        with open(pid_filename, 'w') as pid_file:
            pid_file.write(str(os.getpid()))

        try:
            run(args)
        finally:
            os.remove(pid_filename)

    else:
        run(args)

def run(args):
    slapos_conf = configparser.ConfigParser()
    slapos_conf.read(args.configuration_file)

    current_binary = os.path.join(os.getcwd(), sys.argv[0])
    binary_directory = os.path.dirname(current_binary)
    sr_directory = os.path.realpath(os.path.join(binary_directory, '..'))

    partition_amount = slapos_conf.getint('slapformat', 'partition_amount')
    partition_base_name = slapos_conf.get('slapformat', 'partition_base_name')
    try:
        bridge_name = slapos_conf.get('slapformat', 'interface_name')
    except configparser.NoOptionError:
        bridge_name = slapos_conf.get('slapformat', 'bridge_name')
    instance_root = slapos_conf.get('slapos', 'instance_root')
    partition_base_path = os.path.join(instance_root, partition_base_name)
    partition_list = ['%s%d' % (partition_base_path, i)
                      for i in range(partition_amount)]

    logging.basicConfig(level=logging.getLevelName(args.log[0]))

    database = gdbm.open(args.database, 'c', 0o600)
    try:
        process.main(sr_directory, partition_list, database, bridge_name)
    finally:
        database.sync()
        database.close()
