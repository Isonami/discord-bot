import importlib
import os
import logging
import types

logger = logging.getLogger(__name__)

mbase = 'dbm_'
dbm_modules = []


class Command(object):
    __slots__ = ['command', 'main', 'name', 'description', 'admin', 'private', 'valid']

    def __init__(self, obj, name):
        self.command = getattr(obj, 'command', None)
        self.main = getattr(obj, 'main', None)
        self.name = name
        self.description = getattr(obj, 'description', None)
        self.admin = getattr(obj, 'admin', False)
        self.private = getattr(obj, 'private', False)
        self.valid = False
        if isinstance(self.command, str) and isinstance(self.main, types.FunctionType):
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
                    dbm_modules.append(importlib.import_module('{}.{}'.format(__name__, mod_name)))
                except Exception as exc:
                    logger.exception('Can not load source: %s: %s', exc.__class__.__name__, exc)


async def init(bot):
    commands = []
    try:
        dis = bot.config.get('disable.modules', [])
        for obj in dbm_modules:
            name = obj.__name__.split('.')[-1]
            if name[len(mbase):] not in dis:
                if hasattr(obj, 'init'):
                    try:
                        await obj.init(bot)
                    except Exception as exc:
                        logger.error('Can not init module %s', name)
                        logger.exception('%s: %s', exc.__class__.__name__, exc)
                        continue
                cmd = Command(obj, name)
                if cmd.valid:
                    commands.append(cmd)
    except Exception as exc:
        logger.exception('%s: %s', exc.__class__.__name__, exc)
        raise
    return commands

main()
