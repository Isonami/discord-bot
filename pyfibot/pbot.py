# -*- coding: utf-8 -*-
from tornado.httpclient import HTTPError
import json
import logging
NAME = "pyfibot"
logger = logging.getLogger(__name__)


class Response:
    def __init__(self, resp):
        for var_name in resp.__dict__:
            if not var_name.startswith("__"):
                setattr(self, var_name, getattr(resp, var_name))
        logger.debug(self.__dict__)
        self.status_code = resp.code
        self.content = resp.body

    def json(self):
        if hasattr(self, "content") and self.content:
            return json.loads(self.content)
        raise ValueError


def geturl(client, url, nocache=False, params=None, headers=None, cookies=None):
    try:
        logger.debug("Get URL: %s", url)
        if params:
            method = "POST"
        else:
            method = "GET"
        if cookies:
            if not headers:
                headers = {}
            headers = {"Cookie": cookies}
        response = client.fetch(url, method=method, headers=headers, body=params)
        logger.debug("Response: %s", response.body)
        return Response(response)
    except HTTPError as e:
        # HTTPError is raised for non-200 responses; the response
        # can be found in e.response.
        logger.error("HTTPError: " + str(e))
        return Response(e.response)


class Config:
    def __init__(self, bot, name=None):
        self.bot = bot
        if name:
            self.name = ".".join([NAME, name])
        else:
            self.name = NAME

    def get(self, var, *args):
        if len(args) > 0 and type(args[0]) is dict and len(args[0]) == 0:
            return Config(self.bot, var)
        else:
            return self.bot.config.get(".".join([self.name, var]), *args)

    def set(self, var, *args):
        return self.bot.config.set(".".join([self.name, var]), *args)


class Pbot:
    http_client = None

    def __init__(self, bot):
        for var_name in self.__class__.__dict__:
            if not var_name.startswith("__"):
                if hasattr(bot, var_name):
                    setattr(self, var_name, getattr(bot, var_name))
        self.parent = bot
        self.say = bot.send
        self.config = Config(bot)
        self.admins = bot.config.get("discord.admins")

    @staticmethod
    def getNick(user):
        return user.name

    def isAdmin(self, user):
        return user.id in self.admins

    def get_url(self, url, nocache=False, params=None, headers=None, cookies=None):
        return geturl(self.http_client, url, nocache, params, headers, cookies)

    def getUrl(self, url, nocache=False, params=None, headers=None, cookies=None):
        return geturl(self.http_client. url, nocache, params, headers, cookies)
