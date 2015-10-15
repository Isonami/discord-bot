import logging
from random import randint

logger = logging.getLogger(__name__)


def main(self, message, *args, **kwargs):
    try:
        max_rand = 100
        if "randcount" in kwargs and kwargs["randcount"]:
            max_rand = int(kwargs["randcount"])
        self.send(message.channel, "Random number is: %d" % randint(1, max_rand))
    except Exception, exc:
        logger.error("%s: %s" % (exc.__class__.__name__, exc))
