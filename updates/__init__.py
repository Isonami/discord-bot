import importlib
import os
import logging
import types

logger = logging.getLogger(__name__)

mbase = "dbm_"
dbm_updates = []


class Update(object):
    __slots__ = ['ready', 'main', 'name', 'description', 'admin', 'private', 'valid']

    def __init__(self, obj, name):
        self.ready = getattr(obj, 'ready', None)
        self.name = name
        self.description = getattr(obj, 'description', None)
        self.valid = False
        if isinstance(self.ready, types.FunctionType):
            self.valid = True

    def __str__(self):
        return self.name


def main():
    fpath = os.path.dirname(os.path.realpath(__file__))
    for mfile in os.listdir(fpath):
        mod_name, file_ext = os.path.splitext(mfile)
        if mod_name.startswith(mbase):
            if file_ext.lower() == '.py':
                try:
                    dbm_updates.append(importlib.import_module('{}.{}'.format(__name__, mod_name)))
                except Exception as exc:
                    logger.exception('Can not load source: %s: %s', exc.__class__.__name__, exc)


async def init(bot):
    updates = []
    try:
        dis = bot.config.get("disable.updates", [])
        for obj in dbm_updates:
            name = obj.__name__.split('.')[-1]
            real_name = name[len(mbase):]
            if real_name not in dis:
                if hasattr(obj, "init"):
                    try:
                        ret = await obj.init(bot)
                        if ret == 1:
                            continue
                    except Exception as exc:
                        logger.error("Can not init module %s", name)
                        logger.exception("%s: %s", exc.__class__.__name__, exc)
                upd = Update(obj, real_name)
                if upd.valid:
                    updates.append(upd)
                bot.modules.loaded(real_name, obj)
    except Exception as exc:
        logger.exception("%s: %s", exc.__class__.__name__, exc)
        raise
    return updates


main()
