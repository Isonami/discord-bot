# -*- coding: utf-8 -*-
import logging
from tornado.httpclient import AsyncHTTPClient, HTTPResponse
from tornado.escape import url_escape
from tornado.httputil import url_concat, urlencode
from tornado.platform.asyncio import to_asyncio_future
import asyncio
import json as jsonlib

logger = logging.getLogger(__name__)

def_timeout = 30


class Http(object):
    def __init__(self, bot):
        self.bot = bot
        self.queue = asyncio.Queue(loop=bot.loop)
        self.urlencode = urlencode
        self.url_escape = url_escape
        self.url_concat = url_concat
        self.json = jsonlib

    async def _request(self, url, method='GET', etag=None, date=None, encoding='utf-8', **kwargs):
        try:
            headers = kwargs.get('headers', {})
            kwargs.pop('headers', 0)
            if etag and len(etag) > 0:
                headers['If-None-Match'] = etag
                headers['If-Modified-Since'] = date
            if method == 'POST':
                kwargs['body'] = kwargs.get('body', '')
            request = Result(url, method, headers, **kwargs)
            response = await request.get(self)
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
            return None

    async def __call__(self, *args, **kwargs):
        post = kwargs.get("method", "GET")
        if post == "POST":
            return await self.post(*args, **kwargs)
        return await self.get(*args, **kwargs)

    async def get(self, url, payload=None, etag=None, date=None, encoding='utf-8', **kwargs):
        """|coro|
        Http GET request.
        Parameters
        ----------
        url : str
            The url to get.
        payload : dict or list
            The payload dict or list to append to url ``None``.
        encoding : str
            The encoding used to decode response body ``utf-8``.
        etag : str
            The etag header, will be added to headers ``None``. Must be used with date.
        date : str
            The date header, will be added to headers ``None``. Must be used with etag.
        """
        if payload:
            url = self.url_concat(url, payload)
        return await self._request(url, method='GET', etag=etag, date=date, encoding=encoding, **kwargs)

    async def post(self, url, payload=None, json=None, etag=None, date=None, encoding='utf-8', **kwargs):
        """|coro|
        Http POST request.
        Parameters
        ----------
        url : str
            The url to get.
        payload : dict or list
            The payload dict or list will be send in body ``None``. Can\'t use with json parameters simultaneously.
        json : `dict`
            The json dict will be send in body ``None``. Can\'t use with payload parameters simultaneously.
        encoding : str
            The encoding used to encode json if exists and decode response body ``utf-8``.
        etag : str
            The etag header, will be added to headers ``None``. Must be used with date.
        date : str
            The date header, will be added to headers ``None``. Must be used with etag.
        """
        if payload and json:
            raise ValueError('Can\'t use payload and json parameters simultaneously.')
        if payload:
            kwargs['body'] = self.urlencode(payload)
        elif json:
            kwargs['body'] = self.json.loads(json, encoding=encoding)
            headers = kwargs.get('headers', {})
            headers['Content-Type'] = 'application/json;charset={encoding}'.format(encoding=encoding)
            kwargs['headers'] = headers
        return await self._request(url, method='POST', etag=etag, date=date, encoding=encoding, **kwargs)


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

    async def get(self, http, timeout=def_timeout):
        await http.queue.put(self)
        try:
            await asyncio.wait_for(self._event.wait(), timeout)
        except asyncio.futures.TimeoutError:
            return None
        return self.result


class Response(object):
    __slots__ = ['_response', 'code', 'http_code', 'encoding', 'body', 'headers']

    def __init__(self, code, response, encoding):
        self.code = code
        if code == 2:
            return
        if isinstance(response, HTTPResponse):
            self._response = response
            self.http_code = self._response.code
            self.encoding = encoding
            self.headers = response.headers
            if code != 3:
                self.body = response.body

    def __str__(self):
        if self.code == 0:
            return self.body.decode(self.encoding)
        return 'None'

    @property
    def raw_response(self):
        return self._response


async def http_geter(http):
    while not bot_main.disconnect:
        req = await http.queue.get()
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
        http = Http(bot)
        bot.async_function(http_geter(http))
        return http
    except Exception as exc:
        logger.error('%s: %s' % (exc.__class__.__name__, exc))
