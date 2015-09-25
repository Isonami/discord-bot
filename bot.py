# -*- coding: utf-8 -*-
import discord
import logging
import logging.config
import tornado.httpclient as httpclient
import json
from time import sleep, time
from settings import login, password, version, rates_url
import os
import re
import modules

os.environ['NO_PROXY'] = 'discordapp.com, openexchangerates.org, srhpyqt94yxb.statuspage.io'


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] (%(threadName)-10s) %(message)s",
            'datefmt': "%d/%b/%Y %H:%M:%S"
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
        'discord': {
            'handlers': ['console'],
            'level': 'DEBUG',
            },
    }
}
ifnfo_line = "Nedo bot version %s" % version
cmd_start = "."
commands = [
    (r"h(?:elp)?", "help", "%shelp - show help" % cmd_start),
    (r"\$(?P<currency>(?: [a-zA-Z]{3})+)?", "exchangerates", "%s$ USD|EUR - show exchange rates" % cmd_start),
]
status_url = "https://srhpyqt94yxb.statuspage.io/api/v2/summary.json"


def server_status(client):
    try:
        logger.debug("Get server status")
        response = client.fetch(status_url, method="GET")
        # print response.body
        rvars = json.loads(response.body)
        if "components" in rvars:
            for item in rvars["components"]:
                if item["name"] == "API":
                    if item["status"] == "operational":
                        logger.debug("Server status is: operational")
                        return True
                    logger.debug("Server status is: %s" % item["status"])
                    break
        return None
    except httpclient.HTTPError as e:
        # HTTPError is raised for non-200 responses; the response
        # can be found in e.response.
        logger.error("HTTPError: " + str(e))


class Bot:
    def __init__(self, log, pswd):
        self.login = log
        self.password = pswd
        self.client = discord.Client()
        self.client.login(self.login, self.password)
        self.disconect = False
        self.cmds = {}
        self.desc = []
        self.ifnfo_line = ifnfo_line
        self.http_client = http_client
        all_reg = r""
        for reg, cmd_name, desk in commands:
            if hasattr(modules, cmd_name):
                module = getattr(modules, cmd_name)
                if hasattr(module, "main"):
                    self.cmds[cmd_name] = getattr(module, "main")
                    if len(desk) > 0:
                        self.desc.append(desk)
                    all_reg += r"(?P<%s>^%s$)|" % (cmd_name, reg)
        self.reg = re.compile(all_reg[:-1])

        @self.client.event
        def on_message(message):
            logger.debug("New message %s", message)
            self.msg_proc(message)

        @self.client.event
        def on_ready():
            logger.debug('Logged in as %s (%s)', self.client.user.name, self.client.user.id)

        @self.client.event
        def on_disconnect():
            if not self.disconect:
                logger.debug('Reconnecting')
                self.reconnect()

    def reconnect(self):
        self.client.logout()
        while not self.disconect:
            if server_status(self.http_client):
                logger.info('Reconnect attempt...')
                self.client.login(self.login, self.password)
                if self.client.is_logged_in:
                    return
                sleep(20)
            else:
                sleep(300)

    def send(self, channel, message):
        if type(message) is unicode:
            message = message.encode('utf-8')
        self.client.send_message(channel, message)

    def msg_proc(self, message):
        try:
            if message.content.startswith(cmd_start):
                msg = ' '.join(message.content[len(cmd_start):].split())
                m = self.reg.match(msg)
                if m:
                    rkwargs = m.groupdict()
                    kwargs = {}
                    command = None
                    for item, value in rkwargs.iteritems():
                        if value:
                            if item in self.cmds:
                                command = self.cmds[item]
                            else:
                                kwargs[item] = value
                    args = m.groups()[len(rkwargs):]
                    if command:
                        command(self, message, *args, **kwargs)
        except Exception, exc:
            logger.error("%s: %s" % (exc.__class__.__name__, exc))


def main():
    logging.config.dictConfig(LOGGING)
    global logger
    logger = logging.getLogger(__name__)
    global http_client
    http_client = httpclient.HTTPClient()
    bot = Bot(login, password)
    while not bot.disconect:
        sleep(60)

if __name__ == "__main__":
    main()

