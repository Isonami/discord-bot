# -*- coding: utf-8 -*-
import discord
import logging
import logging.config
import tornado.httpclient as httpclient
import json
from time import sleep
import os
import re
import modules
import updates
import pyfibot
import config
from commands import commands
from threading import Thread
import discord.endpoints as endpoints
import signal
import sys

os.environ['NO_PROXY'] = 'discordapp.com, openexchangerates.org, srhpyqt94yxb.statuspage.io'

PID = config.PID
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
    }
}
logging_file_name = "logging.json"
ifnfo_line = """Nedo bot version %s
by Isonami (github.com/Isonami/discord-bot)"""
cmd_start = "."
status_url = "https://srhpyqt94yxb.statuspage.io/api/v2/summary.json"


def sigterm_handler(_signo, _stack_frame):
    try:
        logger.info("Stopping...")
        if "bot" in globals() and not bot.disconnect:
            bot.disconnect = True
            bot.client.logout()
        sys.exit(0)
    except Exception, exc:
        logger.error("%s: %s" % (exc.__class__.__name__, exc))
        return None, None


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
    def __init__(self):
        self.config = config.Config()
        self.on_ready = []
        self.disconnect = False
        modules.init(self)
        updates.init(self)
        self.login = self.config.get("discord.login")
        self.password = self.config.get("discord.password")
        self.client = discord.Client()
        self.client.login(self.login, self.password)
        self.cmds = {}
        self.desc = []
        self.ifnfo_line = ifnfo_line % self.config.get("version")
        self.http_client = http_client
        pcommands = pyfibot.init(self)
        all_reg = r""
        for reg, cmd_name, desk in commands:
            if hasattr(modules, cmd_name):
                module = getattr(modules, cmd_name)
                if hasattr(module, "main"):
                    self.cmds[cmd_name] = getattr(module, "main")
                    if len(desk) > 0:
                        self.desc.append(desk.format(cmd_start=cmd_start))
                    all_reg += r"(?P<%s>^%s$)|" % (cmd_name, reg)
        for reg, cmd, cmd_name, desk in pcommands:
            self.cmds[cmd_name] = cmd
            if len(desk) > 0:
                self.desc.append(desk.format(cmd_start=cmd_start))
            all_reg += r"(?P<%s>^%s$)|" % (cmd_name, reg)
        logger.debug("Regex: %s", all_reg[:-1])
        self.reg = re.compile(all_reg[:-1])

        @self.client.event
        def on_message(message):
            logger.debug("New message %s", message)
            self.msg_proc(message)

        @self.client.event
        def on_ready():
            logger.debug('Logged in as %s (%s)', self.client.user.name, self.client.user.id)
            for function in self.on_ready:
                try:
                    readyth = Thread(name="readyth_" + function.__name__, target=function, args=(self,))
                    readyth.daemon = True
                    readyth.start()
                except Exception, exc:
                    logger.error("%s: %s" % (exc.__class__.__name__, exc))

        @self.client.event
        def on_disconnect():
            pass
            # if not self.disconnect:
            #    logger.debug('Reconnecting')
            #    self.reconnect()

    def reconnect(self):
        self.client.logout()
        while not self.disconnect:
            try:
                if server_status(self.http_client):
                    logger.info('Reconnect attempt...')
                    self.client.login(self.login, self.password)
                    if self.client.is_logged_in:
                        return
                    sleep(20)
                else:
                    sleep(300)
            except Exception, exc:
                logger.error("%s: %s" % (exc.__class__.__name__, exc))
                sleep(60)

    def send(self, channel, message):
        if type(message) is unicode:
            message = message.encode('utf-8')
        self.client.send_message(channel, message)

    def msg_proc(self, message):
        try:
            if message.content.startswith(cmd_start):
                msg = ' '.join(message.content[len(cmd_start):].split()).lower()
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

    def typing(self, channel):
        if channel:
            if hasattr(channel, 'id'):
                url = "{0}/{1}/typing".format(endpoints.CHANNELS, channel.id)
                try:
                    logger.debug("Send 'typing' status to server")
                    self.http_client.fetch(url, method="POST", headers=self.client.headers, body="")
                    return True
                except httpclient.HTTPError as e:
                    logger.error("HTTPError: " + str(e))
        return False


def main():
    main_dir = os.path.dirname(os.path.realpath(__file__))
    json_file = os.path.join(main_dir, logging_file_name)
    if os.path.exists(json_file):
        with open(json_file) as json_config:
            global LOGGING
            LOGGING = json.load(json_config)
    logging.config.dictConfig(LOGGING)
    global logger
    logger = logging.getLogger(__name__)
    global http_client
    http_client = httpclient.HTTPClient()
    global bot
    bot = Bot()
    th = Thread(name="Bot", target=bot.client.run)
    th.daemon = True
    th.start()
    while not bot.disconnect:
        sleep(60)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, sigterm_handler)
    signal.signal(signal.SIGTERM, sigterm_handler)
    main()

