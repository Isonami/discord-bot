# -*- coding: utf-8 -*-
import logging
import logging.config
import json
from time import time
import os
import re
import signal
import sys
import discord
from discord import endpoints
import tornado.httpclient as httpclient
import modules
import updates
import asyncio
from botlib import config, sql, scheduler, http, web, unflip
from tornado.platform.asyncio import AsyncIOMainLoop
import functools


os.environ['NO_PROXY'] = 'discordapp.com, openexchangerates.org, srhpyqt94yxb.statuspage.io'

PID = config.PID
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] (%(threadName)-10s) %(message)s',
            'datefmt': '%d/%b/%Y %H:%M:%S'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
        },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'bot.log',
            'formatter': 'verbose',
            'maxBytes': 1024 * 1024 * 5,
            'backupCount': 3,
        },
        },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'DEBUG',
            },
    }
}
logging_file_name = 'logging.json'
ifnfo_line = '''Nedo bot version %s
by Isonami (github.com/Isonami/discord-bot)'''
cmd_start = '.'
status_url = 'https://srhpyqt94yxb.statuspage.io/api/v2/summary.json'
restart_wait_time = 300


def sigterm_handler(_signo, _stack_frame):
    logger.error('Get signal: %s', signame)
    try:
        if 'bot' in globals() and not bot.disconnect:
            logger.info('Stopping...')
            bot.disconnect = True
            loop.run_until_complete(bot.logout())
            sys.exit(0)
        if 'bot' in globals() and bot.disconnect:
            return
        sys.exit(0)
    except Exception as exc:
        logger.error('%s: %s' % (exc.__class__.__name__, exc))
        return None, None


def server_status(client):
    try:
        logger.debug('Get server status')
        response = client.fetch(status_url, method='GET')
        # print response.body
        rvars = json.loads(response.body)
        if 'components' in rvars:
            for item in rvars['components']:
                if item['name'] == 'API':
                    if item['status'] == 'operational':
                        logger.debug('Server status is: operational')
                        return True
                    logger.debug('Server status is: %s' % item['status'])
                    break
        return None
    except httpclient.HTTPError as e:
        # HTTPError is raised for non-200 responses; the response
        # can be found in e.response.
        logger.error('HTTPError: ' + str(e))


class BotModules(object):
    def __init__(self, dbot):
        self.bot = dbot
        self.commands = []
        self.updates = []
        self.cmds = {}
        self.reg = None

    def imp(self):
        self.updates = self.bot.loop.run_until_complete(updates.init(self.bot))
        self.commands = self.bot.loop.run_until_complete(modules.init(self.bot))
        self.compile()

    def compile(self):
        all_reg = r''
        for cmd in self.commands:
            if isinstance(cmd, modules.Command):
                if cmd.description:
                    desk = self.bot.config.get('.'.join([str(cmd), 'description']), cmd.description)
                    cmd.description = desk.format(cmd_start=cmd_start)
                reg = self.bot.config.get('.'.join([str(cmd), 'regex']), cmd.command)
                all_reg += r'(?P<%s>^%s$)|' % (str(cmd), reg)
                self.cmds[str(cmd)] = cmd
        logger.debug('Regex: %s', all_reg[:-1])
        self.reg = re.compile(all_reg[:-1], re.IGNORECASE)


class Bot(object):
    def __init__(self, main_loop, notrealy=False):
        self.loop = main_loop
        ioloop = AsyncIOMainLoop()
        ioloop.asyncio_loop = self.loop
        ioloop.install()
        self.tornado_loop = ioloop
        self.config = config.Config()
        self.admins = self.config.get('discord.admins', [])
        self._next_restart = 0
        self.disconnect = False
        self.tasks = []
        self.http = http.init(self)
        if not self.http:
            raise EnvironmentError('Can not start without http lib.')
        self.scheduler = scheduler.Scheduler(self)
        self.sqlcon = sql.init(self)
        self.modules = BotModules(self)
        self.modules.imp()
        self.login = self.config.get('discord.login')
        self.password = self.config.get('discord.password')
        self.unflip = self.config.get('discord.unflip', False)
        if not notrealy:
            self.client = discord.Client(loop=self.loop)
            self.ifnfo_line = ifnfo_line % self.config.get('version')

        @self.client.event
        async def on_message(message):
            logger.debug('New message %s', message)
            await self.msg_proc(message)

        @self.client.event
        async def on_message_edit(old_message, message):
            logger.debug('Message edited ftom %s to %s', old_message, message)
            await self.msg_proc(message)

        @self.client.event
        async def on_ready():
            logger.debug('Logged in as %s (%s)', self.client.user.name, self.client.user.id)
            waiters = []
            for function in self.modules.updates:
                waiters.append(function(self))
            for one_wait in waiters:
                await one_wait

    async def restart_wait(self):
        cur_time = int(time())
        if cur_time > self._next_restart:
            self._next_restart = cur_time + restart_wait_time
        else:
            await asyncio.sleep(self._next_restart - cur_time)
            self._next_restart = cur_time + restart_wait_time

    async def run(self):
        await self.client.login(self.login, self.password)
        while not self.disconnect:
            try:
                await self.client.connect()
            except (discord.ClientException, discord.GatewayNotFound) as exc:
                logger.error('Bot stop working: %s: %s', exc.__class__.__name__, exc)
                if self.disconnect:
                    break
                if isinstance(exc, discord.GatewayNotFound):
                    resp = await self.http(endpoints.GATEWAY, headers=self.client.headers)
                    if resp.code == 1 and resp.http_code == 401:
                        logger.error('Got 401 UNAUTHORIZED, relogin...')
                        await self.restart_wait()
                        if self.client.ws:
                            await self.client.logout()
                        await self.client.login(self.login, self.password)
                        continue
                await self.restart_wait()
            except Exception as exc:
                logger.error('Bot stopping: %s: %s', exc.__class__.__name__, exc)
                await self.client.logout()

    async def send(self, channel, message, **kwargs):
        await self.client.send_message(channel, message, **kwargs)

    async def msg_proc(self, message):
        try:
            if message.content.startswith(cmd_start):
                msg = ' '.join(message.content[len(cmd_start):].split())
                m = self.modules.reg.match(msg)
                if m:
                    rkwargs = m.groupdict()
                    kwargs = {}
                    command = None
                    mod_name = None
                    for item, value in rkwargs.items():
                        if value:
                            if item in self.modules.cmds:
                                command = self.modules.cmds[item].main
                                mod_name = item
                            else:
                                kwargs[item] = value
                    args = m.groups()[len(rkwargs):]
                    if command and mod_name:
                        if self.modules.cmds[mod_name].admin and not self.is_admin(message.author):
                            return
                        if self.modules.cmds[mod_name].private and not message.channel.is_private:
                            return
                        try:
                            await command(self, message, *args, **kwargs)
                        except Exception as exc:
                            logger.exception("%s: %s", exc.__class__.__name__, exc)
            elif self.unflip and message.content.startswith(unflip.flip_str):
                await unflip.unflip(self, message.channel)
        except Exception as exc:
            logger.exception('%s: %s', exc.__class__.__name__, exc)

    async def typing(self, channel):
        self.client.send_typing(channel)

    def async_function(self, future):
        self.tasks.append(asyncio.ensure_future(future))

    async def logout(self):
        try:
            logger.debug('Logout from server')
            await self.client.logout()
        except Exception as exc:
            logger.error('%s: %s', exc.__class__.__name__, exc)

    def is_admin(self, user):
        return user.id in self.admins


def main(notrealy=False):
    main_dir = os.path.dirname(os.path.realpath(__file__))
    json_file = os.path.join(main_dir, logging_file_name)
    try:
        with open(json_file) as json_config:
            global LOGGING
            LOGGING = json.load(json_config)
    except IOError as e:
        message = 'Can not open logging.json file: %s \n' % str(e)
        sys.stderr.write(message)
        sys.exit(1)
    except ValueError as e:
        message = 'Can not open load json logging file: %s \n ' % str(e)
        sys.stderr.write(message)
        sys.exit(1)
    logging.config.dictConfig(LOGGING)
    global logger
    logger = logging.getLogger(__name__)
    # we may use subrocess in modules
    global loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    global bot
    if notrealy:
        bot = Bot(loop, notrealy=True)
        sys.exit(0)
    try:
        bot = Bot(loop)
    except Exception as exc:
        logger.exception('Can no init Bot, exiting: %s: %s' % (exc.__class__.__name__, exc))
        sys.exit(0)
    if bot.config.get('web.enable'):
        web.start_web(bot)
    loop.run_until_complete(bot.run())
    loop.close()

if __name__ == '__main__':
    signal.signal(signal.SIGINT, sigterm_handler)
    signal.signal(signal.SIGTERM, sigterm_handler)
    main()
