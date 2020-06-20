# -*- coding: utf-8 -*-
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4 syntax=python
# vi: tabstop=8 expandtab shiftwidth=4 softtabstop=4 syntax=python
import argparse
from discord.ext import commands
from discord.ext.commands.view import StringView
import discord
from collections import namedtuple
from aiohttp import ClientSession, ClientResponse
from aiocron import Cron
from . import log
from . import db
from . import modules
from . import config
from . import web
import asyncio
import logging
from os import path

VersionInfo = namedtuple('VersionInfo', 'major minor micro releaselevel serial')
version_info = VersionInfo(
    major=6,
    minor=0,
    micro=0,
    releaselevel='0',
    serial=0
)

__version__ = '{}.{}.{}'.format(version_info.major, version_info.minor, version_info.micro)

__description__ = '''Nedo bot version {} \nby Isonami (github.com/Isonami/discord-bot)'''

logger = logging.getLogger('main')
help_word = 'help'


def _is_submodule(parent, child):
    return parent == child or child.startswith(parent + ".")


class Var(object):
    __slots__ = ['value']

    def __init__(self):
        self.value = None

    def set(self, value):
        self.value = value

    def __call__(self, *args, **kwargs):
        return self.value

    def get(self, *args, **kwargs):
        return self.value


class BotClientResponse(ClientResponse):
    async def text(self, *args, **kwargs):
        data = await super().text(*args, **kwargs)
        logger.debug('{} {} has received {}'.format(self.method, self.url, data))
        return data

    async def json(self, *args, **kwargs):
        data = await super().json(*args, **kwargs)
        logger.debug('{} {} has received {}'.format(self.method, self.url, data))
        return data


class BotClientSession(ClientSession):
    def __init__(self, *args, **kwargs):
        if not kwargs.get('response_class', None):
            kwargs['response_class'] = BotClientResponse
        super().__init__(*args, **kwargs)

    async def _request(self, *args, **kwargs):
        resp = await super()._request(*args, **kwargs)
        data = kwargs.get('data') or kwargs.get('json')
        data = 'with {} '.format(data) if data else ''
        logger.debug('{} {} {}has returned {}'.format(resp.method, resp.url, data, resp.status))
        return resp


class IsNotAdministrator(commands.CheckFailure):
    def __init__(self, *args):
        message = 'You are not an administrator on this server.'
        super().__init__(message, *args)


class IsNotModerator(commands.CheckFailure):
    def __init__(self, *args):
        message = 'You are not a moderator on this server.'
        super().__init__(message, *args)


class Bot(commands.Bot):
    Context = commands.Context
    Embed = discord.Embed
    Colour = discord.Colour
    utils = discord.utils
    ClientSession = BotClientSession
    config = config.BaseConfig
    m = db.peewee
    BaseModel = db.peewee.Model
    global_config = None  # type: config.Config
    db = None  # type: db.Manager
    models_load = []
    module_loader_event = asyncio.Event()
    inits = []
    init_loader_event = asyncio.Event()
    unloads = []
    var = Var
    custom_processors = []
    crons = []
    roles = None
    web = None  # type: web.Web

    async def on_message_custom(self, message):
        ctx = self.get_context_custom(message)
        for processor, channels in self.custom_processors:
            if channels:
                if ctx.channel in channels:
                    await processor(ctx)
            else:
                await processor(ctx)

    async def process_commands(self, message):
        await super().process_commands(message)

    def get_context_custom(self, message, *, cls=commands.Context):
        view = StringView(message.content)
        ctx = cls(prefix=None, view=view, bot=self, message=message)
        return ctx

    def unload_extension(self, name):
        lib = self.extensions.get(name)
        if lib is not None:
            lib_name = lib.__name__
            custom_processors = self.custom_processors.copy()
            for processor in custom_processors:
                if _is_submodule(lib_name, processor[0].__module__):
                    self.custom_processors.remove(processor)
            crons = self.crons.copy()
            for cron in crons:
                if _is_submodule(lib_name, cron[0].__module__):
                    cron[1].stop()
                    self.crons.remove(cron)
            unloads = self.unloads.copy()
            for unload in unloads:
                if _is_submodule(lib_name, unload.__module__):
                    unload()
                    self.unloads.remove(unload)
        super().unload_extension(name)

    @staticmethod
    def modules_search():
        return modules.search(__name__)

    async def models_loader(self):
        while not self.is_closed():
            await self.module_loader_event.wait()
            if self.is_closed():
                return
            self.module_loader_event.clear()
            while len(self.models_load):
                name, fut = self.models_load.pop(0)
                try:
                    await fut
                except Exception as exc:
                    logger.error('Model `{}` load error: {}: {}'.format(name, exc.__class__.__name__, exc))

    async def init_loader(self):
        while not self.is_closed():
            await self.init_loader_event.wait()
            if self.is_closed():
                return
            self.init_loader_event.clear()
            while len(self.inits):
                name, fut = self.inits.pop(0)
                try:
                    await fut
                except Exception as exc:
                    logger.error('Model `{}` models load error: {}: {}'.format(name, exc.__class__.__name__, exc))

    async def close(self):
        await super().close()
        self.module_loader_event.set()
        self.init_loader_event.set()

    @property
    def database(self):
        return self.db.database

    def model(self):
        def decorator(model):
            if not not isinstance(model, self.BaseModel):
                raise ValueError('Model {} must be instance of BaseModel.'.format(model.__name__))
            self.models_load.append((model.__name__, db.init_model(model)))
            self.module_loader_event.set()
            return model

        return decorator

    def init(self):
        def decorator(func):
            if not asyncio.iscoroutinefunction(func):
                raise ValueError('Init function must be coroutine')
            self.inits.append((func.__module__, func()))
            self.init_loader_event.set()
            return func

        return decorator

    def unload(self):
        def decorator(func):
            self.unloads.append(func)
            return func

        return decorator

    def crontab(self, schedule, start=True):
        def decorator(func):
            async def cron_func(*args, **kwargs):
                logger.debug('Job {}.{} started.'.format(func.__module__, func.__name__))
                try:
                    await func(*args, **kwargs)
                except Exception as exc:
                    logger.error('{}.{} error - {}: {}'.format(func.__module__, func.__name__,
                                                               exc.__class__.__name__, exc))
                finally:
                    logger.debug('Job {}.{} done.'.format(func.__module__, func.__name__))
            cron = Cron(schedule, cron_func, start=False, loop=self.loop)
            self.crons.append((func, cron))
            if start:
                cron.start()
            return cron

        return decorator

    def message(self, channels=None):
        def decorator(func):
            self.custom_processors.append((func, channels))
            return func

        return decorator

    @staticmethod
    async def default_error(ctx, error):
        if isinstance(error, (bot.UserInputError, bot.CheckFailure)):
            await ctx.send(str(error))
        else:
            logger.exception('{}: {}'.format(error.__class__.__name__, error))

    @staticmethod
    def user_is_admin(ctx):
        if ctx.author.guild_permissions.administrator:
            return True

        return False

    def is_admin(self):
        def predicate(ctx):
            if self.user_is_admin(ctx):
                return True
            raise IsNotAdministrator()

        return commands.check(predicate)

    def is_moderator(self):
        def predicate(ctx):
            if self.user_is_admin(ctx):
                return True
            raise IsNotModerator()

        return commands.check(predicate)

    def __getattr__(self, item):
        return getattr(commands, item)


bot = Bot(command_prefix='.', description=__description__.format(__version__), help_attrs={'name': help_word})


def main(debug=False):
    parser = argparse.ArgumentParser(description='Discord bot.')
    parser.add_argument('--config', type=str, default=path.join(path.dirname(path.realpath(__file__)), 'config.yaml'))
    args = parser.parse_args()

    cfg = config.Config(args.config)
    bot.global_config = cfg
    log.initialize(debug)
    db.initialize(bot)

    for module in modules.search(__name__):
        bot.load_extension(module)

    bot.web = web.Web(bot)

    loaders = {
        'models': None,
        'init': None
    }

    async def on_ready():
        loaders['models'] = asyncio.ensure_future(bot.models_loader())
        loaders['init'] = asyncio.ensure_future(bot.init_loader())
        await bot.web.run()

    bot.add_listener(bot.on_message_custom, 'on_message')
    bot.add_listener(on_ready)
    # bot.loop.run_forever()
    bot.run(cfg.get('token'))
    for loader in loaders.values():
        if not loader.cancelled() and loader.done():
            if loader.exception():
                raise loader.exception()


if __name__ == '__main__':
    main()
