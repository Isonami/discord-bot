import logging
from time import time
import json
from tornado.httpclient import HTTPError

command = r"\$(?P<currency>(?: [a-z]{3})+)?"
description = "{cmd_start}$ USD|EUR - show exchange rates"

rates_url = None
rates_delay = 600
rates = {
    "rates": {},
    "next": 0
}
rates_def = "RUB"
rates_any_list = ["USD", "EUR", "UAH"]
rates_history = [
    {},
    {}
    ]
rates_format = "1 {base_rate} = {value:0.2f} {need_rate}"
rates_last = {}
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
    global rates_format
    rates_format = bot.config.get("exchangerates.format", rates_format)


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


def get_onerate(base_rate, need_rate, fmt=None, arrow_up=ARROW_UP, arrow_down=ARROW_DOWN):
    def_cur = rates["rates"][base_rate]
    arrow = ""
    num = def_cur / rates["rates"][need_rate]
    if need_rate in rates_history[0]:
        if num > rates_history[0][need_rate]:
            arrow = arrow_up
        elif num < rates_history[0][need_rate]:
            arrow = arrow_down
        if need_rate in rates_history[1]:
            if rates_history[1][need_rate] != num:
                rates_history[0][need_rate] = rates_history[1][need_rate]
                rates_history[1][need_rate] = num
        else:
            rates_history[1][need_rate] = num
    else:
        rates_history[0][need_rate] = num
    if fmt:
        return fmt.format(need_rate=need_rate, base_rate=base_rate, value=num, arrow=arrow)
    return num, arrow


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
        cur_out = []
        for curenc in cur_list:
            cur_out.append(get_onerate(rates_def, curenc, fmt=rates_format))
        self.send(message.channel, "Exchange rates: %s" % u", ".join(cur_out))
    except Exception, exc:
        logger.error("%s: %s" % (exc.__class__.__name__, exc))
