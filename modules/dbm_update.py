# -*- coding: utf-8 -*-
import logging
import asyncio
import sys
if sys.platform == 'win32':
    import subprocess

command = r'update(?P<update_lib> lib)?'
description = '{cmd_start}update - update bot from git'
admin = True
private = True

logger = logging.getLogger(__name__)
update_command = 'git -C {maindir} pull origin master 2>&1'
pip_command = 'pip3.5 install --upgrade git+https://github.com/Rapptz/discord.py@async'


async def init(bot):
    global update_command
    update_command = bot.config.get('update.command', update_command)
    update_command = update_command.format(maindir=bot.config.get('main.dir'))


async def update():
    try:
        if sys.platform == 'win32':
            try:
                out = subprocess.check_output(update_command, shell=True)
                if out.find(b'Updating') != -1:
                    return 0
                elif out.find(b'up-to-date') != -1:
                    return -1
                else:
                    return -2
            except subprocess.CalledProcessError as e:
                logger.error('Git process return: %s', vars(e))
                return 1
        else:
            proc = await asyncio.create_subprocess_shell(update_command, stdout=asyncio.subprocess.PIPE)
            try:
                exit_code = await asyncio.wait_for(proc.wait(), 45)
            except asyncio.futures.TimeoutError:
                proc.kill()
                return -3
            out = await proc.stdout.read()
            if exit_code == 0:
                if out.find(b'Updating') != -1:
                    return 0
                elif out.find(b'up-to-date') != -1:
                    return -1
                else:
                    return -2
            logger.error('Git process return: %s', str(out))
            return 1
    except Exception as exc:
        logger.exception('%s: %s' % (exc.__class__.__name__, exc))
        return 2


async def pip_update():
    try:
        if sys.platform == 'win32':
            try:
                out = subprocess.check_output(pip_command, shell=True)
                return out.decode()
            except subprocess.CalledProcessError as e:
                return vars(e)
        else:
            proc = await asyncio.create_subprocess_shell(pip_command, stdout=asyncio.subprocess.PIPE)
            try:
                await asyncio.wait_for(proc.wait(), 45)
            except asyncio.futures.TimeoutError:
                proc.kill()
                return 'Timeout error'
            out = await proc.stdout.read()
            return out.decode()
    except Exception as exc:
        logger.exception('%s: %s' % (exc.__class__.__name__, exc))
        return 'Command error, see logs.'


async def main(self, message, *args, **kwargs):
    await self.typing(message.channel)
    if 'update_lib' in kwargs:
        await self.send(message.channel, await pip_update())
        # 'install git+https://github.com/Rapptz/discord.py@async'
        return
    code = await update()
    if code == 0:
        await self.send(message.channel, 'Update OK.')
    elif code == -1:
        await self.send(message.channel, 'No update found.')
    elif code == -2:
        await self.send(message.channel, 'Unknown git return.')
    elif code == 1:
        await self.send(message.channel, 'Git error. Check logs.')
    elif code == 1:
        await self.send(message.channel, 'Command timeout.')
    else:
        await self.send(message.channel, 'Unknown error.')
