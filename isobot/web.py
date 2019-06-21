# -*- coding: utf-8 -*-
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4 syntax=python
# vi: tabstop=8 expandtab shiftwidth=4 softtabstop=4 syntax=python
import socket
from ssl import SSLContext
from typing import Optional, Callable, Type, cast, List
from collections.abc import Iterable

from aiohttp import web
import asyncio
import logging

from aiohttp.abc import AbstractAccessLogger, Application
from aiohttp.log import access_logger
from aiohttp.web_log import AccessLogger
from aiohttp.web_runner import AppRunner, BaseSite, TCPSite, UnixSite, SockSite

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

    async def run(self, *,
                  host: Optional[str] = None,
                  port: Optional[int] = None,
                  path: Optional[str] = '127.0.0.1',
                  sock: Optional[socket.socket] = None,
                  shutdown_timeout: float = 60.0,
                  ssl_context: Optional[SSLContext] = None,
                  print: Callable[..., None] = print,
                  backlog: int = 128,
                  access_log_class: Type[AbstractAccessLogger] = AccessLogger,
                  access_log_format: str = AccessLogger.LOG_FORMAT,
                  access_log: Optional[logging.Logger] = access_logger,
                  handle_signals: bool = True,
                  reuse_address: Optional[bool] = None,
                  reuse_port: Optional[bool] = None) -> None:

        app = cast(Application, self)

        runner = AppRunner(app, handle_signals=handle_signals,
                           access_log_class=access_log_class,
                           access_log_format=access_log_format,
                           access_log=access_log)

        await runner.setup()

        sites = []  # type: List[BaseSite]

        try:
            if host is not None:
                if isinstance(host, (str, bytes, bytearray, memoryview)):
                    sites.append(TCPSite(runner, host, port,
                                         shutdown_timeout=shutdown_timeout,
                                         ssl_context=ssl_context,
                                         backlog=backlog,
                                         reuse_address=reuse_address,
                                         reuse_port=reuse_port))
                else:
                    for h in host:
                        sites.append(TCPSite(runner, h, port,
                                             shutdown_timeout=shutdown_timeout,
                                             ssl_context=ssl_context,
                                             backlog=backlog,
                                             reuse_address=reuse_address,
                                             reuse_port=reuse_port))
            elif path is None and sock is None or port is not None:
                sites.append(TCPSite(runner, port=port,
                                     shutdown_timeout=shutdown_timeout,
                                     ssl_context=ssl_context, backlog=backlog,
                                     reuse_address=reuse_address,
                                     reuse_port=reuse_port))

            if path is not None:
                if isinstance(path, (str, bytes, bytearray, memoryview)):
                    sites.append(UnixSite(runner, path,
                                          shutdown_timeout=shutdown_timeout,
                                          ssl_context=ssl_context,
                                          backlog=backlog))
                else:
                    for p in path:
                        sites.append(UnixSite(runner, p,
                                              shutdown_timeout=shutdown_timeout,
                                              ssl_context=ssl_context,
                                              backlog=backlog))

            if sock is not None:
                if not isinstance(sock, Iterable):
                    sites.append(SockSite(runner, sock,
                                          shutdown_timeout=shutdown_timeout,
                                          ssl_context=ssl_context,
                                          backlog=backlog))
                else:
                    for s in sock:
                        sites.append(SockSite(runner, s,
                                              shutdown_timeout=shutdown_timeout,
                                              ssl_context=ssl_context,
                                              backlog=backlog))
            for site in sites:
                await site.start()

            if print:  # pragma: no branch
                names = sorted(str(s.name) for s in runner.sites)
                print("======== Running on {} ========\n"
                      "(Press CTRL+C to quit)".format(', '.join(names)))
            while True:
                await asyncio.sleep(3600)  # sleep forever by 1 hour intervals
        finally:
            await runner.cleanup()


