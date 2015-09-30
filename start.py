#!/usr/bin/env PATH=$PATH:/usr/local/sbin:/usr/local/bin python2.7
import sys
import threading
from time import sleep
from daemon import Daemon
import bot


class MyDaemon(Daemon):
    def run(self):
        sctl_daemon = threading.Thread(name='BotProccess', target=bot.main)
        sctl_daemon.start()
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
        else:
            print "Unknown command"
            sys.exit(2)
        sys.exit(0)
    else:
        print "usage: %s start|stop|restart" % sys.argv[0]
        sys.exit(2)
