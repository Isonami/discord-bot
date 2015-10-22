# -*- coding: utf-8 -*-
import module_openweather

from types import ModuleType
from sys import modules
import logging

logger = logging.getLogger(__name__)
base = "command_"


def makefunck(bot, obj, var):
    func = getattr(obj, var)

    def f(self, message, *args, **kwargs):
        ar = None
        if kwargs and var in kwargs:
            ar = kwargs[var]
        func(bot, message.author, message.channel, ar)
    return f


def init(bot, commands, cmd_opt):
    try:
        for key, obj in modules[__name__].__dict__.iteritems():
            if isinstance(obj, ModuleType):
                if hasattr(obj, "init"):
                    obj.init(bot)
                    all_vars = vars(obj)
                    for var in all_vars:
                        if var.startswith(base):
                            cmd_name = var[len(base):]
                            fnk = makefunck(bot, obj, var)
                            if cmd_name in cmd_opt:
                                cmd = r"%s(?: (?P<%s>.+)$)?" % (cmd_opt[cmd_name][0], var)
                                desk = "{cmd_start}%s" % cmd_opt[cmd_name][1]
                            else:
                                cmd = r"%s(?: (?P<%s>.+)$)?" % (cmd_name, var)
                                desk = "{cmd_start}%s - pyfibot command " % cmd_name
                            commands.append((cmd, fnk, cmd_name, desk))
    except Exception, exc:
        logger.error("%s: %s" % (exc.__class__.__name__, exc))
        raise
