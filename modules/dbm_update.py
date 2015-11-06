import logging
import subprocess

command = r"update"
description = "{cmd_start}update - update bot from git"
admin = True
private = True

logger = logging.getLogger(__name__)
update_command = "git -C {maindir} pull origin master 2>&1"


def init(bot):
    global update_command
    update_command = bot.config.get("update.command", update_command)
    update_command = update_command.format(maindir=bot.config.get("main.dir"))


def update():
    try:
        out = subprocess.check_output(update_command, shell=True)
        if out.find("Updating") != -1:
            return 0
        elif out.find("up-to-date") != -1:
            return -1
        else:
            return -2
    except subprocess.CalledProcessError as e:
        logger.error("Git process return: %s", vars(e))
        return 1
    except Exception, exc:
        logger.error("%s: %s" % (exc.__class__.__name__, exc))
        return 2


def main(self, message, *args, **kwargs):
    try:
        self.typing(message.channel)
        code = update()
        if code == 0:
            self.send(message.channel, "Update OK.")
        elif code == -1:
            self.send(message.channel, "No update found.")
        elif code == -2:
            self.send(message.channel, "Unknown git return.")
        elif code == 1:
            self.send(message.channel, "Git error. Check logs.")
        else:
            self.send(message.channel, "Unknown error.")
    except Exception, exc:
        logger.error("%s: %s" % (exc.__class__.__name__, exc))
