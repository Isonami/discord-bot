import imp
import os
import logging

logger = logging.getLogger(__name__)

mbase = "dbm_"
dbm_updates = []


def main():
    fpath = os.path.dirname(os.path.realpath(__file__))
    for mfile in os.listdir(fpath):
        mod_name, file_ext = os.path.splitext(mfile)
        if mod_name.startswith(mbase):
            if file_ext.lower() == '.py':
                dbm_updates.append(imp.load_source(mod_name, os.path.join(fpath, mfile)))


def init(bot):
    commands = []
    try:
        dis = bot.config.get("disable.modules", [])
        for obj in dbm_updates:
            if obj.__name__[len(mbase):] not in dis:
                if hasattr(obj, "init"):
                    try:
                        obj.init(bot)
                    except Exception, exc:
                        logger.error("Can not init module %s", obj.__name__)
                        logger.error("%s: %s" % (exc.__class__.__name__, exc))
                        continue
                if hasattr(obj, "command") and hasattr(obj, "main"):
                    commands.append((obj.command, obj.main, obj.__name__[len(mbase):],
                                     getattr(obj, "description", None), getattr(obj, "admin", False),
                                     getattr(obj, "private", False)))
    except Exception, exc:
        logger.error("%s: %s" % (exc.__class__.__name__, exc))
        raise
    return commands

main()
