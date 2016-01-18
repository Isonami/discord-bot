#!/usr/bin/env python3.5
# -*- coding: utf-8 -*-
import sys
import threading
from time import sleep
import signal
import pip

from botlib.daemon import Daemon
try:
    import bot
except ImportError:
    bot = None

packages = ['discord.py', 'tornado', 'aioodbc', 'aiofiles']


def check_packages():
    not_found = []
    for package in packages:
        out = pip.main(['-q', 'show', package])
        if out == 1:
            not_found.append(package)
    print(not_found)
    if len(not_found) > 0:
        print('Please install this packages: {}'.format(', '.join(not_found)))
        sys.exit(1)


class MyDaemon(Daemon):
    def run(self):
        sctl_daemon = threading.Thread(name='BotProccess', target=bot.main)
        sctl_daemon.start()
        signal.signal(signal.SIGTERM, bot.sigterm_handler)
        sleep(5)
        self.flush_err()
        while sctl_daemon.isAlive():
            sleep(1)


if __name__ == '__main__':
    check_packages()
    daemon = MyDaemon(bot.PID)
    if len(sys.argv) == 2 or len(sys.argv) == 3:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        elif 'check' == sys.argv[1]:
            bot.main(notrealy=True)
        else:
            print('Unknown command')
            sys.exit(2)
        sys.exit(0)
    else:
        print('usage: %s start|stop|restart' % sys.argv[0])
        sys.exit(2)
