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
        for obj in dbm_updates:
            if hasattr(obj, "init"):
                obj.init(bot)
            if hasattr(obj, "command") and hasattr(obj, "main"):
                commands.append((obj.command, obj.main, obj.__name__[len(mbase):], getattr(obj, "description", "")))
    except Exception, exc:
        logger.error("%s: %s" % (exc.__class__.__name__, exc))
        raise
    return commands

main()
