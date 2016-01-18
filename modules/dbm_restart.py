# -*- coding: utf-8 -*-
import logging
import os
import sys
from threading import Thread
import asyncio


command = r'restart'
description = '{cmd_start}restart - restart bot'
admin = True
private = True

logger = logging.getLogger(__name__)
restart_command = '%s {maindir}/start.py restart' % sys.executable
syntax_command = '%s {maindir}/start.py check' % sys.executable


async def init(bot):
    global restart_command
    restart_command = bot.config.get('restart.command', restart_command)
    restart_command = restart_command.format(maindir=bot.config.get('main.dir'))
    global syntax_command
    syntax_command = bot.config.get('restart.syntax_command', syntax_command)
    syntax_command = syntax_command.format(maindir=bot.config.get('main.dir'))


def restart():
    pid = os.fork()
    if pid == 0:
        try:
            os.system('nohup %s >/dev/null 2>&1 &' % restart_command)
            exit()
        except Exception as exc:
            logger.error('%s: %s', exc.__class__.__name__, exc)


async def check_syntax():
    try:
        if sys.platform == 'win32':
            code = os.system("%s >/dev/null 2>&1" % syntax_command)
            if code == 0:
                return True
            else:
                return False
        else:
            proc = await asyncio.create_subprocess_shell('%s >/dev/null 2>&1' % syntax_command)
            try:
                exit_code = await asyncio.wait_for(proc.wait(), 45)
            except asyncio.futures.TimeoutError:
                proc.kill()
                return False
            if exit_code == 0:
                return True
            else:
                return False
    except Exception as exc:
        logger.error('%s: %s', exc.__class__.__name__, exc)


async def main(self, message, *args, **kwargs):
    await self.typing(message.channel)
    if await check_syntax():
        await self.send(message.channel, 'Syntax OK. Restarting...')
        th = Thread(target=restart)
        th.start()
    else:
        await self.send(message.channel, 'Syntax errors detected.')


def modrestart(config):
    global restart_command
    restart_command = config.get('restart.command', restart_command)
    restart_command = restart_command.format(maindir=bot.config.get('main.dir'))
    global syntax_command
    syntax_command = config.get('restart.syntax_command', syntax_command)
    syntax_command = syntax_command.format(maindir=config.get('main.dir'))
    th = Thread(target=restart)
    th.start()
