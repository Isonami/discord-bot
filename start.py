#!/usr/bin/env python3.5
# -*- coding: utf-8 -*-
import sys
import signal
import pip
import asyncio
import functools

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
    if len(not_found) > 0:
        print('Please install this packages: {}'.format(', '.join(not_found)))
        sys.exit(1)


class MyDaemon(Daemon):
    def run(self):
        loop = asyncio.get_event_loop()
        if sys.platform == 'win32':
            signal.signal(signal.SIGTERM, bot.sigterm_handler)
        else:
            for signame in ('SIGINT', 'SIGTERM'):
                loop.add_signal_handler(getattr(signal, signame),
                                        functools.partial(bot.sigterm_handler, signame))
        loop.call_later(3, self.flush_err)
        loop.run_until_complete(bot.main(loop))
        loop.close()


if __name__ == '__main__':
    def usage():
        print('usage: %s [-p PID] start|stop|restart' % sys.argv[0])
        sys.exit(2)
    check_packages()
    args = sys.argv
    if '-p' in args:
        if len(args) < 4:
            usage()
        index = args.index('-p')
        PID = args[index + 1]
        args.pop(index + 1)
        args.pop(index)
    else:
        PID = bot.PID
    daemon = MyDaemon(PID)
    if len(args) == 2 or len(args) == 3:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        elif 'check' == sys.argv[1]:
            cloop = asyncio.get_event_loop()
            cloop.run_until_complete(bot.main(cloop, notrealy=True))
            cloop.close()
        else:
            print('Unknown command')
            sys.exit(2)
        sys.exit(0)
    else:
        usage()
