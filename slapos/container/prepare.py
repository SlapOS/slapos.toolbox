# -*- coding: utf-8 -*-

import ConfigParser
import os
import subprocess

import lockfile

class SlapContainerError(Exception):
    """This exception is thrown, if there is
    any failure during slapcontainer preparation,
    starting or stopping process"""



def main(sr_directory, partition_list):

    for partition_path in partition_list:
        slapcontainer_filename = os.path.join(partition_path,
                                              '.slapcontainer')
        if os.path.isfile(slapcontainer_filename):
            lock = lockfile.FileLock(slapcontainer_filename)
            try:
                lock.acquire(timeout=0)
                slapcontainer_conf = ConfigParser.ConfigParser()
                slapcontainer_conf.read(slapcontainer_filename)

                requested_status = slapcontainer_conf.get('requested', 'status')

                if not slapcontainer_conf.has_section('current'):
                    slapcontainer_conf.add_section('current')
                if not slapcontainer_conf.has_option('current', 'created'):
                    slapcontainer_conf.set('current', 'created', 'no')
                if not slapcontainer_conf.has_option('current', 'status'):
                    slapcontainer_conf.set('current', 'status', 'stopped')

                if requested_status == 'started':
                    start(sr_directory, partition_path,
                          slapcontainer_conf)
                else:
                    stop(sr_directory, partition_path,
                         slapcontainer_conf)

                with open(slapcontainer_filename, 'w') as slapcontainer_fp:
                    slapcontainer_conf.write(slapcontainer_fp)
            except lockfile.LockTimeout:
                # Can't do anything, we'll see on the next run
                pass
            finally:
                lock.release()



def start(sr_directory, partition_path, conf):
    if conf.get('current', 'created') == 'no':
        create(sr_directory, partition_path, conf)

    conf.set('current', 'created', 'yes')

    lxc_start = os.path.join(sr_directory,
                             'parts/lxc/bin/lxc-start')
    config_filename = os.path.join(partition_path, 'config')

    call([lxc_start, '-f', config_filename])
    # TODO: Check if container is started,
    #       Start container

    conf.set('current', 'status', 'started')



def stop(sr_directory, partition_path, conf):

    # TODO : Check if container is stopped
    #        Stop container

    if conf.get('current', 'created') == 'yes':
        destroy(partition_path, conf)



def create(sr_directory, partition_path, conf):
    lxc_debian = os.path.join(sr_directory,
                              'parts/lxc/lib/lxc/templates/lxc-debian')
    return call([lxc_debian, '-p', partition_path])


def destroy(partition_path, conf):
    # TODO: Destroy container
    pass


def call(command_line):
    process = subprocess.Popen(command_line, stdin=subprocess.PIPE)
    process.stdin.flush()
    process.stdin.close()

    if process.wait() != 0:
        raise SlapContainerError("Subprocess call failed")
