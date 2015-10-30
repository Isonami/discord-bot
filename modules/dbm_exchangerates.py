import logging
import json
from tornado.httpclient import HTTPError

command = r"\$(?P<currency>(?: [a-z]{3})+)?"
description = "{cmd_start}$ USD|EUR - show exchange rates"

rates_url = None
rates_delay = 600
rates = {
    "rates": [
        {},
        {}
    ],
    "next": 0,
    "etag": "",
    "date": ""
}
rates_def = "RUB"
rates_any_list = ["USD", "EUR", "UAH"]
rates_history = [
    {},
    {}
    ]
rates_format = "1 {need_rate} = {value:0.2f}{arrow} {base_rate}"
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
    bot.scheduler.append(getrates, "Exchagerates", rates_delay, bot.http_client)


def getrates(client):
    try:
        logger.debug("Try to get new rates")
        if not rates_url:
            logger.debug("Can not get rates, no url specified!")
            return
        headers = {}
        if len(rates["etag"]) > 0:
            headers["If-None-Match"] = rates["etag"]
            headers["If-Modified-Since"] = rates["date"]
        response = client.fetch(rates_url, method="GET", headers=headers)
        logger.debug(response.code)
        # print response.body
        rvars = json.loads(response.body)
        if rvars:
            if "rates" in rvars:
                logger.debug("Rates updated")
                rates["rates"][1] = rates["rates"][0]
                rates["rates"][0] = rvars["rates"]
                if "ETag" in response.headers and "Date" in response.headers:
                    logger.debug("Got ETag: %s, Date: %s", response.headers["ETag"], response.headers["Date"])
                    rates["etag"] = response.headers["ETag"]
                    rates["date"] = response.headers["Date"]
        else:
            logger.error("Can not get rates")
        return None
    except HTTPError as e:
        if e.response.code == 304:
            logger.debug("Rates did not change")
            return
        # HTTPError is raised for non-200 responses; the response
        # can be found in e.response.
        logger.error("HTTPError: " + str(e))
    except Exception, exc:
        logger.error("%s: %s" % (exc.__class__.__name__, exc))


def get_onerate(base_rate, need_rate, fmt=None, arrow_up=ARROW_UP, arrow_down=ARROW_DOWN):
    if base_rate not in rates["rates"][0] or need_rate not in rates["rates"][0]:
        if fmt:
            return ""
        else:
            return 0
    def_cur = rates["rates"][0][base_rate]
    arrow = ""
    num = def_cur / rates["rates"][0][need_rate]
    if need_rate in rates["rates"][1] and base_rate in rates["rates"][1]:
        old_def_cur = rates["rates"][1][base_rate]
        old_num = old_def_cur / rates["rates"][1][need_rate]
        if num > old_num:
            arrow = arrow_up
        elif num < old_num:
            arrow = arrow_down
    if fmt:
        return fmt.format(need_rate=need_rate, base_rate=base_rate, value=num, arrow=arrow)
    return num, arrow


def main(self, message, *args, **kwargs):
    try:
        # now = time()
        # if now > rates["next"]:
        #     getrates(self.http_client)
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
