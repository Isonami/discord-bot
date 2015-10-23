import logging
import os
import sys
logger = logging.getLogger(__name__)
command = "%s {maindir}/start.py restart" % sys.executable


def init(bot):
    global command
    command = bot.config.get("restart.command", command)
    command = command.format(maindir=bot.config.get("main.dir"))


def main(self, message, *args, **kwargs):
    try:
        if self.is_admin(message.author) and message.channel.is_private:
            self.send(message.channel, "Restarting...")
            pid = os.fork()
            if pid == 0:
                os.system("nohup %s &" % sys.executable)
                exit()
    except Exception, exc:
        logger.error("%s: %s" % (exc.__class__.__name__, exc))