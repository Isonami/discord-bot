import logging
import os
import sys
from threading import Thread
logger = logging.getLogger(__name__)
command = "%s {maindir}/start.py restart" % sys.executable
syntax_command = "%s {maindir}/start.py check" % sys.executable


def init(bot):
    global command
    command = bot.config.get("restart.command", command)
    command = command.format(maindir=bot.config.get("main.dir"))
    global syntax_command
    syntax_command = bot.config.get("restart.syntax_command", syntax_command)
    syntax_command = syntax_command.format(maindir=bot.config.get("main.dir"))


def restart():
    pid = os.fork()
    if pid == 0:
        try:
            os.system("nohup %s >/dev/null 2>&1 &" % command)
            exit()
        except Exception, exc:
            logger.error("%s: %s" % (exc.__class__.__name__, exc))


def check_syntax():
    try:
        code = os.system("%s >/dev/null 2>&1" % syntax_command)
        if code == 0:
            return True
        else:
            return False
    except Exception, exc:
        logger.error("%s: %s" % (exc.__class__.__name__, exc))


def main(self, message, *args, **kwargs):
    try:
        if self.is_admin(message.author) and message.channel.is_private:
            if check_syntax():
                self.send(message.channel, "Syntax OK. Restarting...")
                th = Thread(target=restart)
                th.start()
            else:
                self.send(message.channel, "Syntax errors detected.")
    except Exception, exc:
        logger.error("%s: %s" % (exc.__class__.__name__, exc))
