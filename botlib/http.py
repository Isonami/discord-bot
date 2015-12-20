# -*- coding: utf-8 -*-
import logging
from Queue import Queue, Empty
from tornado.httpclient import AsyncHTTPClient
from tornado.gen import coroutine
from tornado.ioloop import IOLoop
from threading import Thread, Event
from time import sleep

logger = logging.getLogger(__name__)

def_timeout = 30


class Result(object):
    def __init__(self, url, method, headers, **kwargs):
        self._event = Event()
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

    def get(self, timeout=def_timeout):
        htqueue.put(self)
        self._event.wait(timeout=timeout)
        return self.result


@coroutine
def http_geter():
    while not bot_main.disconnect:
        try:
            req = htqueue.get()
        except Empty:
            sleep(1)
            continue
        if isinstance(req, Result):
            logger.debug("New http request: %s", req.url)
            result = yield httpclient.fetch(req.url, raise_error=False, method=req.method, headers=req.headers, **req.kwargs)
            req.result = result


def run():
    io_loop = IOLoop.instance()
    io_loop.run_sync(http_geter)


def init(bot):
    try:
        global httpclient
        httpclient = AsyncHTTPClient(max_buffer_size=1024*1024*3, max_body_size=1024*1024*3)
        global htqueue
        htqueue = Queue()
        global bot_main
        bot_main = bot
        http_th = Thread(target=run, name="HTTPRequests")
        http_th.daemon = True
        http_th.start()
        return http
    except Exception, exc:
        logger.error("%s: %s" % (exc.__class__.__name__, exc))


def http(url, method="GET", etag=None, date=None, **kwargs):
    try:
        headers = kwargs.get("headers", {})
        kwargs.pop("headers", 1)
        if etag and len(etag) > 0:
            headers["If-None-Match"] = etag
            headers["If-Modified-Since"] = date
        if method == "POST":
            kwargs["body"] = kwargs.get("body", "")
        request = Result(url, method, headers, **kwargs)
        response = request.get()
        if response:
            if response.error:
                if etag and response.code == 304:
                    return 2, response
                logger.error("HTTPError: " + str(response.error))
                return 1, response
            else:
                return 0, response
        else:
            logger.error("HTTP Request timeout")
            return 2, None
    except Exception, exc:
        logger.error("%s: %s" % (exc.__class__.__name__, exc))
        return 2, None









