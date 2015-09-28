import logging
from time import time
import json
from tornado.httpclient import HTTPError

rates_url = None
rates_delay = 600
rates = {
    "rates": {},
    "next": 0
}
rates_def = "RUB"
rates_any_list = ["USD", "EUR", "UAH"]
rates_history = {}
ARROW_UP = unichr(8593)
ARROW_DOWN = unichr(8595)

logger = logging.getLogger(__name__)


def init(bot):
    global rates_url
    rates_url = bot.config.get("exchangerates.url").format(appid=bot.config.get("exchangerates.appid"))
    global rates_def
    rates_def = bot.config.get("exchangerates.start_currency", rates_def)
    global rates_any_list
    rates_any_list = bot.config.get("exchangerates.rates_any_list", rates_any_list)
    global rates_delay
    rates_delay = bot.config.get("exchangerates.delay", rates_delay)


def getrates(client):
    try:
        logger.debug("Get new rates")
        if not rates_url:
            logger.debug("Can not get rates, no url specified!")
            return
        response = client.fetch(rates_url, method="GET")
        # print response.body
        rvars = json.loads(response.body)
        if rvars:
            now = time()
            if "rates" in rvars:
                logger.debug("Rates updated")
                rates["rates"] = rvars["rates"]
                rates["next"] = now + rates_delay
        else:
            logger.error("Can not get rates")
        return None
    except HTTPError as e:
        # HTTPError is raised for non-200 responses; the response
        # can be found in e.response.
        logger.error("HTTPError: " + str(e))


def main(self, message, *args, **kwargs):
    try:
        now = time()
        if now > rates["next"]:
            getrates(self.http_client)
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
        self.send(message.channel, "Exchange rates: %s" % u", ".join(cur_out))
    except Exception, exc:
        logger.error("%s: %s" % (exc.__class__.__name__, exc))
