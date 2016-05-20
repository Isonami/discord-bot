# -*- coding: utf-8 -*-
import logging
command = r'debug(?P<off> off)?'
description = '{cmd_start}debug( off) - enable/disable debug log'
admin = True
private = True

logger = logging.getLogger(__name__)

CRITICAL = 50
FATAL = CRITICAL
ERROR = 40
WARNING = 30
WARN = WARNING
INFO = 20
DEBUG = 10
NOTSET = 0

levels = {
    50: 'CRITICAL',
    40: 'ERROR',
    30: 'WARNING',
    20: 'INFO',
    10: 'DEBUG',
}

old_level = {}
root_level = None
debug_enable = False


async def main(self, message, *args, **kwargs):
    global root_level
    global debug_enable
    await self.typing(message.channel)
    if 'off' in kwargs:
        if root_level:
            level = root_level
            for name, logg in logger.manager.loggerDict.items():
                if isinstance(logg, logging.Logger):
                    if logg.level != 0:
                        logg.setLevel(old_level[name])
                        level = old_level[name]
            logger.manager.root.setLevel(root_level)
            root_level = None
            debug_enable = False
            await self.send(message.channel, 'Set log level to: {}'.format(level))
    elif not debug_enable:
        for name, logg in logger.manager.loggerDict.items():
            if isinstance(logg, logging.Logger):
                if logg.level != 0:
                    old_level[name] = levels[logg.level]
                    logg.setLevel('DEBUG')
        root_level = levels[logger.manager.root.level]
        logger.manager.root.setLevel('DEBUG')
        debug_enable = True
        await self.send(message.channel, 'Set log level to: DEBUG')


