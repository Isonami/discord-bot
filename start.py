#!/usr/bin/env python2.7
import sys
import threading
from time import sleep
import signal

from botlib.daemon import Daemon
import bot


class MyDaemon(Daemon):
    def run(self):
        sctl_daemon = threading.Thread(name='BotProccess', target=bot.main)
        sctl_daemon.start()
        signal.signal(signal.SIGTERM, bot.sigterm_handler)
        sleep(5)
        self.flush_err()
        while True:
            sleep(1)


if __name__ == "__main__":
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
            print "Unknown command"
            sys.exit(2)
        sys.exit(0)
    else:
        print "usage: %s start|stop|restart" % sys.argv[0]
        sys.exit(2)
