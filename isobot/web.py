# -*- coding: utf-8 -*-
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4 syntax=python
# vi: tabstop=8 expandtab shiftwidth=4 softtabstop=4 syntax=python
from aiohttp import web
import asyncio
import logging

logger = logging.getLogger(__name__)


class Web(web.Application):
    def __init__(self, bot, **kwargs):
        self.bot = bot
        if 'loop' not in kwargs:
            kwargs['loop'] = bot.loop
        super().__init__(**kwargs)
        self.router_init()
        self.servers = []
        self.started = False
        self.handler = None

    def router_init(self):
        self.router.add_get('/', self.handle_main)
        resource = self.router.add_resource('/api/reload/{name}')
        resource.add_route('GET', self.handle_reload)

    def handle_main(self, request):
        strings = []
        for name in self.bot.extensions:
            strings.append('<span>{} </span><a href="/api/reload/{}">reload</a>'.format(name, name))
        return web.Response(text='<br>'.join(strings), content_type='text/html')

    def handle_reload(self, request):
        name = request.match_info['name']
        if name not in self.bot.extensions:
            return web.Response(text='Module `{}` not loaded.'.format(name))
        self.bot.unload_extension(name)
        self.bot.load_extension(name)
        return web.Response(text='Module reloaded.')

    async def run(self, *, host=None, port=8088, path=None, sock=None,
                  ssl_context=None, backlog=128, access_log_format=None,
                  access_log=web.access_logger):
        """Run app"""

        await self.startup()

        try:
            make_handler_kwargs = dict()
            if access_log_format is not None:
                make_handler_kwargs['access_log_format'] = access_log_format
            self.handler = self.make_handler(loop=self.loop, access_log=access_log,
                                             **make_handler_kwargs)

            server_creations, uris = web._make_server_creators(
                self.handler,
                loop=self.loop, ssl_context=ssl_context,
                host=host, port=port, path=path, sock=sock,
                backlog=backlog)
            self.servers = await asyncio.gather(*server_creations, loop=self.loop)

            self.started = True

        except Exception as exc:
            logger.error('{}: {}'.format(exc.__class__.__name__, exc))
            await self.cleanup()
            raise

    async def shutdown(self, shutdown_timeout=60.0):
        if self.started:
            server_closures = []
            for srv in self.servers:
                srv.close()
            await asyncio.gather(*server_closures, loop=self.loop)
            await super().shutdown()
            await self.handler.shutdown(shutdown_timeout)
            await self.cleanup()
