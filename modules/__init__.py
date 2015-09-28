""" Import modules """
import help
import exchangerates
import wolframalpha


from types import ModuleType
from sys import modules
import logging

logger = logging.getLogger(__name__)


def init(bot):
    try:
        for key, obj in modules[__name__].__dict__.iteritems():
            if isinstance(obj, ModuleType):
                if hasattr(obj, "init"):
                    obj.init(bot)
    except Exception, exc:
        logger.error("%s: %s" % (exc.__class__.__name__, exc))
        raise
