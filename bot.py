import discord
import logging
import logging.config
import tornado.httpclient as httpclient
import json
from time import sleep, time
from settings import login, password, version, rates_url
import os
import re

os.environ['NO_PROXY'] = 'discordapp.com, openexchangerates.org'


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
cmd_start = "!"
commands = [
    (r"h(?:elp)?", "cmd_help", "!help - show help"),
    (r"\$(?P<currency>(?: [a-zA-Z]{3})+)?", "cmd_exchange", "!$ USD|EUR - show exchange rates"),
]
rates_delay = 600
rates = {
    "rates": {},
    "next": 0
}
rates_def = "RUB"
rates_any_list = ["USD", "EUR", "UAH"]
rates_history = {}
status_url = "https://srhpyqt94yxb.statuspage.io/api/v2/summary.json"
ARROW_UP = unichr(8593)
ARROW_DOWN = unichr(8595)


def getrates():
    try:
        logger.debug("Get new rates")
        response = http_client.fetch(rates_url, method="GET")
        # print response.body
        rvars = json.loads(response.body)
        now = time()
        if "rates" in rvars:
            logger.debug("Rates updated")
            rates["rates"] = rvars["rates"]
            rates["next"] = now + rates_delay
        return None
    except httpclient.HTTPError as e:
        # HTTPError is raised for non-200 responses; the response
        # can be found in e.response.
        logger.error("HTTPError: " + str(e))


def server_status():
    try:
        logger.debug("Get server status")
        response = http_client.fetch(status_url, method="GET")
        # print response.body
        rvars = json.loads(response.body)
        if "components" in rvars:
            for item in rvars["components"]:
                if item["name"] == "API":
                    if item["status"] == "operational":
                        return True
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
        all_reg = r""
        for reg, cmd_name, desk in commands:
            if hasattr(self, cmd_name):
                self.cmds[cmd_name] = getattr(self, cmd_name)
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

    def reconnect(self):
        while not self.disconect:
            if server_status():
                self.client.login(self.login, self.password)
                if self.client.is_logged_in:
                    return
                sleep(20)
            else:
                sleep(300)

    def msg_proc(self, message):
        # splt_msg = message.content.split(" ")
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
                        command(message, *args, **kwargs)
        except Exception, exc:
            logger.error("%s: %s" % (exc.__class__.__name__, exc))

    def cmd_help(self, message, *args, **kwargs):
        help_msg = ifnfo_line + "\nAvailable commands:\n"
        for desc in self.desc:
            help_msg += "    %s\n" % desc
        self.client.send_message(message.channel, help_msg)

    def cmd_exchange(self, message, *args, **kwargs):
        try:
            now = time()
            if now > rates["next"]:
                getrates()
            cur_list = []
            if "currency" in kwargs and kwargs["currency"]:
                splt_cur = kwargs["currency"][1:].split()
                for cur in splt_cur:
                    if cur.upper() in rates["rates"]:
                        cur_list .append(cur.upper())
            else:
                cur_list = rates_any_list
            if len(cur_list) <= 0:
                self.client.send_message(message.channel, "Wrong currency specified")
                return
            def_cur = rates["rates"][rates_def]
            cur_out = []
            for curenc in cur_list:
                arrow = ""
                num = def_cur / rates["rates"][curenc]
                if curenc in rates_history:
                    if num > rates_history[curenc]:
                        arrow = ARROW_UP
                    elif num < rates_history[curenc]:
                        arrow = ARROW_DOWN
                cur_out.append("1 %s = %0.2f%s %s" % (curenc, num, arrow, rates_def))
                rates_history[curenc] = num
            self.client.send_message(message.channel, "Exchange rates: %s" % ", ".join(cur_out))
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
        bot.client.run()
        sleep(10)


if __name__ == "__main__":
    main()

