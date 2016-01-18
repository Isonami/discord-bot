# -*- coding: utf-8 -*-
import logging
from tornado.httpclient import AsyncHTTPClient, HTTPResponse
from tornado.platform.asyncio import to_asyncio_future
import asyncio

logger = logging.getLogger(__name__)

def_timeout = 30


class Result(object):
    __slots__ = ['_event', '_result', 'url', 'headers', 'kwargs', 'method']

    def __init__(self, url, method, headers, **kwargs):
        self._event = asyncio.Event()
        self._result = None
        self.url = url
        self.headers = headers
        self.kwargs = kwargs
        self.method = method

    @property
    def result(self):
        return self._result

    @result.setter
    def result(self, value):
        self._result = value
        self._event.set()

    async def get(self, timeout=def_timeout):
        await htqueue.put(self)
        try:
            await asyncio.wait_for(self._event.wait(), timeout)
        except asyncio.futures.TimeoutError:
            return None
        return self.result


class Response(object):
    __slots__ = ['_response', 'code', 'http_code', 'encoding', 'body']

    def __init__(self, code, response, encoding):
        self.code = code
        if code == 2:
            return
        if isinstance(response, HTTPResponse):
            self._response = response
            self.http_code = self._response.code
            self.encoding = encoding
            self.body = response.body

    def __str__(self):
        return self.body.decode(self.encoding)

    @property
    def raw_response(self):
        return self._response


async def http_geter():
    while not bot_main.disconnect:
        req = await htqueue.get()
        if isinstance(req, Result):
            logger.debug('New http request: %s', req.url)
            result = await to_asyncio_future(httpclient.fetch(req.url, raise_error=False, method=req.method,
                                                              headers=req.headers, **req.kwargs))
            req.result = result


def init(bot):
    try:
        global httpclient
        httpclient = AsyncHTTPClient(max_buffer_size=1024*1024*3, max_body_size=1024*1024*3, io_loop=bot.tornado_loop)
        global htqueue
        htqueue = asyncio.Queue()
        global bot_main
        bot_main = bot
        bot.async_function(http_geter())
        return http
    except Exception as exc:
        logger.error('%s: %s' % (exc.__class__.__name__, exc))


async def http(url, method='GET', etag=None, date=None, encoding='utf-8', **kwargs):
    try:
        headers = kwargs.get('headers', {})
        kwargs.pop('headers', 0)
        if etag and len(etag) > 0:
            headers['If-None-Match'] = etag
            headers['If-Modified-Since'] = date
        if method == 'POST':
            kwargs['body'] = kwargs.get('body', '')
        request = Result(url, method, headers, **kwargs)
        response = await request.get()
        if isinstance(response, HTTPResponse):
            if response.error:
                if etag and response.code == 304:
                    return Response(3, response, encoding)
                logger.error('HTTPError: ' + str(response.error))
                return Response(1, response, encoding)
            else:
                return Response(0, response, encoding)
        else:
            logger.error('HTTP Request timeout')
            return Response(2, response, encoding)
    except Exception as exc:
        logger.error('%s: %s' % (exc.__class__.__name__, exc))
        return 2, None









