#!/usr/bin/env python
# coding: utf-8
"""
config for route_health_check.py
"""
#
LOG_FILENAME = '/var/log/route_health.log'

# ping setting
INTERFACE = 'stm1.100'
SOURCE_IP = '192.168.10.95'
DEST_IP = '8.8.8.8'
NEXT_HOP = '192.168.10.1'
COUNT = '5'

# cmd setting
STM_DOMAIN = 'localhost'
STM_USER = 'admin'
STM_PWD = 'admin'
STM_SCRIPT_PATH = r'/opt/stm/target/pcli/stm_cli.py'

CMD = []
#CMD = echo 'ping 8.8.8.8 count 3 int stm2 source_address 10.10.3.100 next_hop 10.10.3.254' | ./stm_cli.py admin:admin@localhost
CMD.append(r"echo 'ping {} count {} int {} source_address {} next_hop {}' |sudo {} {}:{}@{}"
           .format(DEST_IP, COUNT, INTERFACE, SOURCE_IP, NEXT_HOP, STM_SCRIPT_PATH,
                   STM_USER, STM_PWD, STM_DOMAIN))


# mail setting
SERVER_HOST = 'smtp.gmail.com'
SERVER_PORT = 587
SERVER_ID = ''
SERVER_PWD = ''

MAIL_FROM = 'admin@gmail.com'
MAIL_TO = 'to@customer.com'
MAIL_SUBJECT = '[ROUTE_HEALTH_ALERT] WARNING'
