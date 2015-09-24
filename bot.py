import discord
import logging
import logging.config
import tornado.httpclient as httpclient
import json
from time import sleep, time
from settings import login, password, version, rates_url


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
ifnfo_line = "Nedo bot version %s" % version
commands = {
    "!help": {
        "function": "cmd_help",
        "descriprion": "- show help",
    },
    "!$": {
        "function": "cmd_exchange",
        "descriprion": "USD|EUR - show exchange rates",
    },
}
rates_delay = 600
rates = {
    "rates": {},
    "next": 0
}
rates_def = "RUB"


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


class Bot:
    def __init__(self, log, pswd):
        self.client = discord.Client()
        self.client.login(log, pswd)

        @self.client.event
        def on_message(message):
            self.msg_proc(message)

        @self.client.event
        def on_ready():
            logger.debug('Logged in as %s (%s)', self.client.user.name, self.client.user.id)

    def msg_proc(self, message):
        splt_msg = message.content.split(" ")
        if len(splt_msg) > 0 and splt_msg[0].lower() in commands:
            logger.debug("New message")
            cmd_name = commands[splt_msg[0].lower()]["function"]
            if hasattr(self, cmd_name):
                getattr(self, cmd_name)(splt_msg[1:], message)

    def cmd_help(self, splt_msg, message):
        help_msg = ifnfo_line + "\nAvailable commands:\n"
        for cmd in commands:
            help_msg += "    %s %s\n" % (cmd, commands[cmd]["descriprion"])
        self.client.send_message(message.channel, help_msg)

    def cmd_exchange(self, splt_msg, message):
        try:
            now = time()
            logger.debug(now)
            if now > rates["next"]:
                getrates()
            if len(splt_msg) <= 0:
                self.client.send_message(message.channel, "No currency specified")
                return
            curenc = splt_msg[0].upper()
            if curenc not in rates["rates"]:
                self.client.send_message(message.channel, "Can not find currency!")
                return
            def_cur = rates["rates"][rates_def]
            needed = rates["rates"][curenc]
            ret_cur = def_cur / needed
            self.client.send_message(message.channel, "Exchange rates: 1 %s = %0.2f %s" % (curenc, ret_cur, rates_def))
        except Exception, exc:
            logger.error("%s: %s" % (exc.__class__.__name__, exc))


def main():
    logging.config.dictConfig(LOGGING)
    global logger
    logger = logging.getLogger(__name__)
    global http_client
    http_client = httpclient.HTTPClient()
    bot = Bot(login, password)
    bot.client.run()


if __name__ == "__main__":
    main()
