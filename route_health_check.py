#!/usr/bin/python2.7
# coding: utf-8
"""
Parses the output of the system ping command.
"""

import re
import sys
import imp
import time
import subprocess
from collections import namedtuple
import logging
import logging.handlers
#import route_health_checker_config as config

first = True
count = 0

data_01 = '''
From 8.8.8.8 (8.8.8.8): icmp_seq 1 rtt 45.68 mS
From 8.8.8.8 (8.8.8.8): icmp_seq 2 rtt 35.26 mS
From 8.8.8.8 (8.8.8.8): icmp_seq 3 rtt 28.86 mS
From 8.8.8.8 (8.8.8.8): icmp_seq 4 rtt 29.98 mS
From 8.8.8.8 (8.8.8.8): icmp_seq 5 rtt 28.79 mS
From 8.8.8.8 (8.8.8.8): icmp_seq 6 rtt 29.77 mS
From 8.8.8.8 (8.8.8.8): icmp_seq 7 rtt 35.28 mS
From 8.8.8.8 (8.8.8.8): icmp_seq 8 rtt 28.84 mS
From 8.8.8.8 (8.8.8.8): icmp_seq 9 rtt 30.00 mS
From 8.8.8.8 (8.8.8.8): icmp_seq 10 rtt 28.84 mS
10 packets transmitted, 10 received, 0% packet loss
rtt min/max/avg/mdev = 28.000 / 45.000 / 32.000 / 5.000 ms
'''

data_02 = '''
From 8.8.8.8 (8.8.8.8): icmp_seq 1 rtt 45.68 mS
From 8.8.8.8 (8.8.8.8): icmp_seq 2 rtt 35.26 mS
From 8.8.8.8 (8.8.8.8): icmp_seq 3 rtt 28.86 mS
From 8.8.8.8 (8.8.8.8): icmp_seq 4 rtt 29.98 mS
From 8.8.8.8 (8.8.8.8): icmp_seq 5 rtt 28.79 mS
From 8.8.8.8 (8.8.8.8): icmp_seq 6 rtt 29.77 mS
From 8.8.8.8 (8.8.8.8): icmp_seq 7 rtt 35.28 mS
From 8.8.8.8 (8.8.8.8): icmp_seq 8 rtt 28.84 mS
From 8.8.8.8 (8.8.8.8): icmp_seq 9 rtt 30.00 mS
From 8.8.8.8 (8.8.8.8): icmp_seq 10 rtt 28.84 mS
10 packets transmitted, 10 received, 0% packet loss
rtt min/max/avg/mdev = 28.000 / 65.000 / 32.000 / 5.000 ms
'''

data_03 = '''
From 8.8.8.8 (8.8.8.8): icmp_seq 1 rtt 45.68 mS
From 8.8.8.8 (8.8.8.8): icmp_seq 2 rtt 35.26 mS
From 8.8.8.8 (8.8.8.8): icmp_seq 3 rtt 28.86 mS
From 8.8.8.8 (8.8.8.8): icmp_seq 4 rtt 29.98 mS
From 8.8.8.8 (8.8.8.8): icmp_seq 5 rtt 28.79 mS
From 8.8.8.8 (8.8.8.8): icmp_seq 6 rtt 29.77 mS
From 8.8.8.8 (8.8.8.8): icmp_seq 7 rtt 35.28 mS
From 8.8.8.8 (8.8.8.8): icmp_seq 8 rtt 28.84 mS
From 8.8.8.8 (8.8.8.8): icmp_seq 9 rtt 30.00 mS
From 8.8.8.8 (8.8.8.8): icmp_seq 10 rtt 28.84 mS
10 packets transmitted, 10 received, 0% packet loss
rtt min/max/avg/mdev = 28.000 / 85.000 / 32.000 / 5.000 ms
'''

# Pull out eg. rtt min/max/avg/mdev == minping/maxping/avgping/jitter
# == 49.042/49.042/49.042/0.000 ms
host_matcher = re.compile(r'From ([a-zA-Z0-9.\-]+) *\(')
rslt_matcher = re.compile(r'(\d+) packets transmitted, (\d+) (?:packets )?received, (\d+\.?\d*)% packet loss')
minmax_matcher = re.compile(r'(\d+.\d+) / (\d+.\d+) / (\d+.\d+) / (\d+.\d+)')

# logger setting
# recorder logger setting
LOG_FILENAME = '/var/log/route_health.log'

# Configure logging - rotate every 20MB and keep the last 100MB in total
logger = logging.getLogger('saisei.route_health')
logger.setLevel(logging.INFO)
filter = logging.Filter('saisei.route_health')
fh = logging.handlers.RotatingFileHandler(LOG_FILENAME,
                                          maxBytes=1000 * 1000 * 50,
                                          backupCount=5)
fh.setFormatter(logging.Formatter(
    '%(asctime)s %(name)s %(levelname)s: %(message)s'))
fh.addFilter(filter)

logger.addHandler(fh)
logger.addFilter(fh)
logger.info('***** starting route_health *****')

# Excute command in shell
def subprocess_open(command):
    try:
        popen = subprocess.Popen(command, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, shell=True)
        (stdoutdata, stderrdata) = popen.communicate()
    except Exception as e:
        logger.error("not opened from subprocess, error: {}".format(e))
        sys.exit(1)
    return stdoutdata, stderrdata


def _get_match_groups(ping_output, regex):
    """
    Get groups by matching regex in output from ping command.
    """
    match = regex.search(ping_output)
    if not match:
        raise Exception('Invalid PING output: {} \n'.format(ping_output))
        pass
    return match.groups()


def parse(ping_output):
    """
    Parse `ping_output` string into a dictionary containing the following
    fields:

        `host`: *string*; the target hostname that was pinged
        `sent`: *int*; the number of ping request packets sent
        `received`: *int*; the number of ping reply packets received
        `packet_loss`: *int*; the percentage of  packet loss
        `minping`: *float*; the minimum (fastest) round trip ping request/reply
                    time in milliseconds
        `avgping`: *float*; the average round trip ping time in milliseconds
        `maxping`: *float*; the maximum (slowest) round trip ping time in
                    milliseconds
        `jitter`: *float*; the standard deviation between round trip ping times
                    in milliseconds
    """
    host = _get_match_groups(ping_output, host_matcher)[0]
    sent, received, packet_loss = _get_match_groups(ping_output, rslt_matcher)

    try:
        minping, maxping, avgping, jitter = _get_match_groups(ping_output,
                                                              minmax_matcher)
    except:
        minping = avgping = maxping = jitter = 'NaN'

    return {
            'host': host,
            'sent': sent,
            'received': received,
            'packet_loss': packet_loss,
            'minping': minping,
            'avgping': avgping,
            'maxping': maxping,
            'jitter': jitter
            }

try:
    config = imp.load_module('route_health_check_config',
                             *imp.find_module('route_health_check_config'))
except ImportError:
    pass
except Exception as e:
    sys.exit(1)

try:
    cmd = config.CMD[0]
except Exception as e:
    print(e)
    sys.exit(1)


def main():
    global first, count
    global data_01, data_02, data_03
#    ping_data = []
    Pingstat = namedtuple('Pingstat', ['timestamp', 'host', 'sent', 'received',
                                       'packet_loss', 'minping', 'avgping',
                                       'maxping', 'jitter'])
#    ping_data = [data_01, data_02, data_03]
    while True:
        try:
            try:
                ping_result = subprocess_open(cmd)
                #ping_result = ping_data
            except Exception as e:
                ping_result = None
                logger.error("cannot get data from cmd, error: {}".format(e))
                pass
            else:
                logger.info("ping is done!")

            try:
                if first is True:
                    try:
                        parse_result = parse(ping_result[0])
                        parse_result['timestamp'] = time.strftime("%d %b %Y %H:%M:%S",
                                                              time.localtime())
                    except Exception:
                        pass
                    else:
                        logger.info("first parsing is done.")
                else:
                    try:
                        parse_result = parse(ping_result[0])
                        parse_result['timestamp'] = time.strftime("%d %b %Y %H:%M:%S",
                                                              time.localtime())
                    except Exception:
                        pass
                    else:
                        logger.info("parsing is done")
            except Exception as e:
                logger.error("parsing error: {}".format(e))

            if first is True:
                try:
                    before_ping_stat = Pingstat(**parse_result)
                    first = False
                except Exception as e:
                    logger.error("making first namedtuple error: {}".format(e))
                else:
                    logger.info("first : {}".format(before_ping_stat))
            else:
                logger.info("before : {}".format(before_ping_stat))

                try:
                    current_ping_stat = Pingstat(**parse_result)
                except Exception as e:
                    logger.error("set currnet_ping_stat error: {}".format(e))
                else:
                    logger.info("current : {}".format(current_ping_stat))

                try:
                    diff = float(current_ping_stat.maxping) - float(before_ping_stat.maxping)
                except Exception as e:
                    logger.error("get diff between current and before error : {}".format(e))
                else:
                    logger.info("diff : {}".format(diff))

                try:
                    before_ping_stat = Pingstat(**parse_result)
                except Exception as e:
                    logger.error("set current_ping_stat into before_ping_stat: {}".format(e))
                else:
                    logger.info("before : {}".format(before_ping_stat))

                if diff > 10:
                    # do email
                    logger.info("sending e-mail from {} to {}, contents, {}".format(config.MAIL_FROM, config.MAIL_TO, config.MAIL_SUBJECT))
                else:
                    # do logging it's stable
                    logger.info("diff is ok")

            time.sleep(10)
        except KeyboardInterrupt:
            print('\r\nThe script is terminated.')
            print('Bye!!')
            sys.exit(1)
        except Exception as e:
            print(e)
            sys.exit(1)


if __name__ == "__main__":
    main()
