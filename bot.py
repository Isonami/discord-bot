# -*- coding: utf-8 -*-
import logging
import logging.config
import json
from time import sleep
import os
import re
from threading import Thread
import signal
import sys
import types
import discord
import tornado.httpclient as httpclient
import discord.endpoints as endpoints
import modules
import updates
import pyfibot
from pyfibot.pbot import NAME as PBOTNAME
from botlib import config, sql, scheduler, web, http

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
        if "webth" in globals():
            webth.terminate()
        if "bot" in globals() and not bot.disconnect:
            logger.info("Stopping...")
            bot.disconnect = True
            bot.logout()
            sys.exit(0)
        if "bot" in globals() and bot.disconnect:
            return
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


class Bot(object):
    def __init__(self, notrealy=False):
        self.config = config.Config()
        self.admins = self.config.get("discord.admins", [])
        self.on_ready = []
        self.disconnect = False
        self.http_client = http_client
        self.http = http.init(self)
        if not self.http:
            raise EnvironmentError("Can not start without http lib.")
        self.scheduler = scheduler.Scheduler()
        self.sqlcon = sql.init(self)
        updates.init(self)
        commands = modules.init(self)
        self.login = self.config.get("discord.login")
        self.password = self.config.get("discord.password")
        if not notrealy:
            self.client = discord.Client()
            self.client.login(self.login, self.password)
            self.cmds = {}
            self.ifnfo_line = ifnfo_line % self.config.get("version")
        pcommands = pyfibot.init(self)
        if notrealy:
            return
        all_reg = r""
        for reg, cmd, mod_name, desk, admin, private in commands:
            if isinstance(cmd, types.FunctionType):
                if desk:
                    desk = self.config.get(".".join([mod_name, "description"]), desk)
                    desk = desk.format(cmd_start=cmd_start)
                reg = self.config.get(".".join([mod_name, "regex"]), reg)
                all_reg += r"(?P<%s>^%s$)|" % (mod_name, reg)
                self.cmds[mod_name] = {"CMD": cmd, "Description": desk, "Admin": admin, "Private": private}
        for reg, cmd, cmd_name, mod_name, desk in pcommands:
            if desk:
                desk = self.config.get(".".join([PBOTNAME, mod_name, cmd_name, "description"]), desk)
                if desk:
                    desk = desk.format(cmd_start=cmd_start)
            reg = self.config.get(".".join([PBOTNAME, mod_name, cmd_name, "regex"]), reg)
            all_reg += r"(?P<%s>^%s$)|" % (cmd_name, reg)
            self.cmds[cmd_name] = {"CMD": cmd, "Description": desk, "Admin": False, "Private": False}
        logger.debug("Regex: %s", all_reg[:-1])
        self.reg = re.compile(all_reg[:-1])
        self.scheduler.start()

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
                    mod_name = None
                    for item, value in rkwargs.iteritems():
                        if value:
                            if item in self.cmds:
                                command = self.cmds[item]["CMD"]
                                mod_name = item
                            else:
                                kwargs[item] = value
                    args = m.groups()[len(rkwargs):]
                    if command and mod_name:
                        if self.cmds[mod_name]["Admin"] and not self.is_admin(message.author):
                            return
                        if self.cmds[mod_name]["Private"] and not message.channel.is_private:
                            return
                        command(self, message, *args, **kwargs)
        except Exception, exc:
            logger.error("%s: %s" % (exc.__class__.__name__, exc))

    def typing(self, channel):
        if channel:
            if hasattr(channel, 'id'):
                url = "{0}/{1}/typing".format(endpoints.CHANNELS, channel.id)
                logger.debug("Send 'typing' status to server")
                state, resp = self.http(url, method="POST", headers=self.client.headers)
                if state == 0:
                    return True
        return False

    def logout(self):
        try:
            logger.debug("Logout from server")
            self.http_client.fetch(endpoints.LOGOUT, method="POST", headers=self.client.headers, body="",
                                   request_timeout=5, connect_timeout=5)
        except httpclient.HTTPError as e:
            logger.error("HTTPError: " + str(e))
        except Exception, exc:
            logger.error("%s: %s" % (exc.__class__.__name__, exc))
        self.client._close = True
        self.client.ws.close()
        self.client._is_logged_in = False

    def is_admin(self, user):
        return user.id in self.admins


def main(notrealy=False):
    main_dir = os.path.dirname(os.path.realpath(__file__))
    json_file = os.path.join(main_dir, logging_file_name)
    if os.path.exists(json_file):
        try:
            with open(json_file) as json_config:
                global LOGGING
                LOGGING = json.load(json_config)
        except IOError as e:
            print "Can not open logging.json file: %s" % str(e)
            exit()
        except ValueError as e:
            print "Can not open load json logging file: %s" % str(e)
            exit()
    logging.config.dictConfig(LOGGING)
    global logger
    logger = logging.getLogger(__name__)
    global http_client
    http_client = httpclient.HTTPClient()
    global bot
    if notrealy:
        bot = Bot(notrealy=True)
        sys.exit(0)
    try:
        bot = Bot()
    except Exception, exc:
        logger.error("Can no init Bot, exiting: %s: %s" % (exc.__class__.__name__, exc))
        exit()
    th = Thread(name="Bot", target=bot.client.run)
    th.daemon = True
    th.start()
    if bot.config.get("web.enable"):
        global webth
        webth = web.WebProxyThread(name="WebProxy", target=web.start_web, args=(bot,))
        webth.daemon = True
        webth.start()
    while not bot.disconnect:
        sleep(1)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, sigterm_handler)
    signal.signal(signal.SIGTERM, sigterm_handler)
    main()
