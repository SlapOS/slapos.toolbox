from setuptools import setup, find_packages
import glob
import os

version = '0.157'
name = 'slapos.toolbox'
long_description = open("README.rst").read() + "\n"

for f in sorted(glob.glob(os.path.join('slapos', 'README.*.rst'))):
  long_description += '\n' + open(f).read() + '\n'

long_description += open("CHANGES.txt").read() + "\n"

prediction_require = ['statsmodels>=0.14.0', 'scipy', 'pandas']
test_require = [
  'cryptography',
  'jsonschema',
  'mock',
  'websockets',
] + prediction_require

setup(name=name,
      version=version,
      description="SlapOS toolbox.",
      long_description=long_description,
      long_description_content_type='text/markdown',
      classifiers=[
          "Programming Language :: Python",
        ],
      keywords='slapos toolbox',
      license='GPLv3',
      namespace_packages=['slapos'],
      packages=find_packages(),
      include_package_data=True,
      maintainer="Nexedi",
      maintainer_email="info@nexedi.com",
      url="https://lab.nexedi.com/nexedi/slapos.toolbox",
      python_requires='>=3.8',
      install_requires=(
        'Flask', # needed by servers
        'atomize', # needed by pubsub
        'feedparser', # needed by pubsub
        'lockfile', # used by equeue
        'lxml', # needed for xml parsing
        'psutil', # needed for playing with processes in portable way
        'setuptools', # namespaces
        'slapos.core', # as it provides library for slap
        'xml_marshaller', # needed to dump information
        'croniter', # needed to know cron schedule
        'pytz', # needed to manipulate timezone
        'tzlocal', # needed to manipulate timezone
        'netifaces',
        'erp5.util',
        'PyRSS2Gen',
        'dnspython',
        'requests',
        'zc.buildout',
        'six',
        'pyasn1-modules',
        'click',
        'websocket-client',
      ),
      extras_require = {
        'lampconfigure':  ["mysqlclient"], #needed for MySQL Database access
        'zodbpack': ['ZODB3'], # needed to play with ZODB
        'flask_auth' : ["Flask-Auth"],
        'pandas' : ['pandas'], # needed to monitor_partition_space promise
        'prediction' : prediction_require, # needed to use ARIMA in check_free_disk_space
        'test': test_require,
      },
      tests_require=test_require,
      zip_safe=False, # proxy depends on Flask, which has issues with
                      # accessing templates
      entry_points={
        'console_scripts': [
          'agent = slapos.agent.agent:main',
          'apache-mpm-watchdog = slapos.promise.apache_mpm_watchdog:main',
          'check-computer-memory = slapos.promise.check_computer_memory:main',
          'check-feed-as-promise = slapos.checkfeedaspromise:main',
          'check-apachedex-result = slapos.promise.check_apachedex_result:main',
          'check-slow-queries-digest-result = slapos.promise.check_slow_queries_digest_result:main',
          'equeue = slapos.equeue:main',
          'generatefeed = slapos.generatefeed:main',
          'htpasswd = slapos.htpasswd:main',
          'is-local-tcp-port-opened = slapos.promise.is_local_tcp_port_opened:main',
          'is-process-older-than-dependency-set = slapos.promise.is_process_older_than_dependency_set:main',
          'killpidfromfile = slapos.systool:killpidfromfile', # BBB
          'loganalyze = slapos.loganalyze:main',
          'monitor.bootstrap = slapos.monitor.monitor:main',
          'monitor.collect = slapos.monitor.collect:main',
          'monitor.statistic = slapos.monitor.build_statistic:main',
          'monitor.runpromise = slapos.monitor.runpromise:main',
          'monitor.genstatus = slapos.monitor.globalstate:main',
          'monitor.configwrite = slapos.monitor.monitor_config_write:main',
          'runResiliencyUnitTestTestNode = slapos.resiliencytest:runUnitTest',
          'runResiliencyScalabilityTestNode = slapos.resiliencytest:runResiliencyTest',
          'runApacheDex = slapos.apachedex:main',
          'lampconfigure = slapos.lamp:run [lampconfigure]',
          'onetimedownload = slapos.onetimedownload:main',
          'onetimeupload = slapos.onetimeupload:main',
          'pubsubnotifier = slapos.pubsub.notifier:main',
          'pubsubserver = slapos.pubsub:main',
          'qemu-qmp-client = slapos.qemuqmpclient:main',
          'rdiffbackup.genstatrss = slapos.resilient.rdiffBackupStat2RSS:main',
          'runner-exporter = slapos.resilient.runner_exporter:runExport',
          'runner-importer-post-notification-run = slapos.resilient.runner_importer:postNotificationRun',
          'backup-identity-script-excluding-path = slapos.resilient.identity_script_excluding_path:calculateSignature',
          'securedelete = slapos.securedelete:main',
          'slapos-kill = slapos.systool:kill',
          'zodbpack = slapos.zodbpack:run [zodbpack]',
          'cachechecker = slapos.cachechecker:web_checker_utility',
          'dnsresolver = slapos.dnsresolver:cli',
          'backup-signature = slapos.backup_signature:cli',
        ]
      },
      test_suite='slapos.test',
    )
