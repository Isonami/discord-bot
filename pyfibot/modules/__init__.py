# -*- coding: utf-8 -*-
import imp
import os
import logging

logger = logging.getLogger(__name__)
base = "command_"
mbase = "module_"
pymods = []


def main():
    fpath = os.path.dirname(os.path.realpath(__file__))
    for mfile in os.listdir(fpath):
        mod_name, file_ext = os.path.splitext(mfile)
        if mod_name.startswith(mbase):
            if file_ext.lower() == '.py':
                pymods.append(imp.load_source(mod_name, os.path.join(fpath, mfile)))


def makefunck(bot, obj, var):
    func = getattr(obj, var)

    def f(self, message, *args, **kwargs):
        ar = None
        if kwargs and var in kwargs:
            ar = kwargs[var]
        func(bot, message.author, message.channel, ar)
    return f


def init(bot, commands, cmd_opt, ban_cmd):
    try:
        for obj in pymods:
            for gl in bot.globals:
                if hasattr(bot, gl):
                    setattr(obj, gl, getattr(bot, gl))
            if hasattr(obj, "init"):
                obj.init(bot)
                all_vars = vars(obj)
                for var in all_vars:
                    if var.startswith(base):
                        cmd_name = var[len(base):]
                        if cmd_name in ban_cmd:
                            continue
                        fnk = makefunck(bot, obj, var)
                        if cmd_name in cmd_opt:
                            cmd = r"%s(?: (?P<%s>.+))?" % (cmd_opt[cmd_name][0], var)
                            desk = "{cmd_start}%s" % cmd_opt[cmd_name][1]
                        else:
                            cmd = r"%s(?: (?P<%s>.+))?" % (cmd_name, var)
                            desk = "{cmd_start}%s - pyfibot command " % cmd_name
                        commands.append((cmd, fnk, cmd_name, desk))
    except Exception, exc:
        logger.error("%s: %s" % (exc.__class__.__name__, exc))
        raise

main()
