import logging
from datetime import datetime, time

logger = logging.getLogger(__name__)
datefmt = "%Y-%m-%d %H:%M"

ans_template = """Started at: {starttime}
Uptime: {uptime}
"""


def init(bot):
    global start_time
    start_time = bot.config.get("main.start_time")


def main(self, message, *args, **kwargs):
    try:
        if self.is_admin(message.author) and message.channel.is_private and start_time:
            delta = datetime.now() - start_time
            msg = ans_template.format(starttime=start_time.strftime(datefmt), uptime=str(delta).split(".")[0])
            self.send(message.channel, msg)
    except Exception, exc:
        logger.error("%s: %s" % (exc.__class__.__name__, exc))
