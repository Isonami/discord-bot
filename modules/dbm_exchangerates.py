# -*- coding: utf-8 -*-
import logging
import json
from time import time

command = r'\$(?P<currency>(?: [a-z]{3})+)?'
description = '{cmd_start}$ USD|EUR - show exchange rates'

rates_url = None
rates_delay = 3000
rates_def = 'RUB'
rates_any_list = ['USD', 'EUR', 'UAH']
rates_format = '1 {need_rate} = {value:0.2f}{arrow} {base_rate}'
rates_last = {}
without_job = True
ARROW_UP = chr(8593)
ARROW_DOWN = chr(8595)

logger = logging.getLogger(__name__)


async def init(bot):
    global without_job
    without_job = bot.config.get('exchangerates.without_job', without_job)
    global rates
    rates = Rates(bot, without_job)
    if not without_job:
        global job
        job = bot.scheduler.new(getrates, 'Exchangerates', rates_delay, rates)
        job.start()
    bot.config.set('exchangerates.rates', rates)


class ResolveCur(object):
    __slots__ = ['_rates', '_base', '_none', '_arrow']

    def __init__(self, self_rates, base=False, none=False, arrow=False):
        self._rates = self_rates
        self._base = base
        self._none = none
        self._arrow = arrow

    def __getattr__(self, currency):
        if self._none:
            if self._arrow:
                return ''
            return 0
        currency = currency.upper()
        if currency in self._rates:
            if self._base:
                if self._arrow:
                    return self._rates(currency, self._base)[-1]
                return self._rates(currency, self._base)[0]
            else:
                return ResolveCur(self._rates, currency, arrow=self._arrow)
        else:
            return ResolveCur(self._rates, none=True, arrow=self._arrow)


class Rates(object):
    def __init__(self, bot, no_job):
        self._url = bot.config.get('exchangerates.url').format(appid=bot.config.get('exchangerates.appid'))
        self.default = bot.config.get('exchangerates.start_currency', rates_def)
        self.any_list = bot.config.get('exchangerates.rates_any_list', rates_any_list)
        self.delay = bot.config.get('exchangerates.delay', rates_delay)
        self.default_format = bot.config.get('exchangerates.format', rates_format)
        self.auto_update = not no_job
        self._etag = ''
        self._date = ''
        self._current = {}
        self._last = {}
        self._http = bot.http
        self._next_update = 0

    async def update(self, cuuid=None):
        logger_expand = ''
        if cuuid:
            logger_expand = '[{}] '.format(cuuid)
        curent_time = time()
        if curent_time < self._next_update:
            return
        newrates, headers = await self.http_update(logger_expand)
        self._next_update = curent_time + self.delay - 10
        if newrates:
            try:
                rvars = json.loads(newrates)
            except ValueError as exc:
                logger.error('%sCan not pars rates json: %s', logger_expand, exc)
                return
            if rvars:
                if 'rates' in rvars:
                    self._last = self._current
                    self._current = rvars['rates']
                    if 'ETag' in headers and 'Date' in headers:
                        logger.debug('%sGot ETag: %s, Date: %s', logger_expand, headers['ETag'], headers['Date'])
                        self._etag = headers['ETag']
                        self._date = headers['Date']

    async def http_update(self, logger_expand):
        logger.debug('%sTry to get new rates', logger_expand)
        if not self._url:
            logger.debug('%sCan not get rates, no url specified!', logger_expand)
            return None, None
        response = await self._http.get(self._url, etag=self._etag, date=self._date)
        if response.code == 0:
            return str(response), response.headers
        elif response.code == 3:
            logger.debug('%sRates did not change', logger_expand)
            return None, None

    def __contains__(self, item):
        if item in self._current:
            return True
        return False

    def __call__(self, base_rate, need_rate, fmt=None, arrow_up=ARROW_UP, arrow_down=ARROW_DOWN):
        if base_rate not in self._current or need_rate not in self._current:
            if fmt:
                return ''
            else:
                return 0
        def_cur = self._current[base_rate]
        arrow = ''
        num = def_cur / self._current[need_rate]
        if need_rate in self._last and base_rate in self._last:
            old_def_cur = self._last[base_rate]
            old_num = old_def_cur / self._last[need_rate]
            if num > old_num:
                arrow = arrow_up
            elif num < old_num:
                arrow = arrow_down
        if fmt:
            return fmt.format(need_rate=need_rate, base_rate=base_rate, value=num, arrow=arrow)
        return num, arrow

    @property
    def cur(self):
        return ResolveCur(self)

    @property
    def arrow(self):
        return ResolveCur(self, arrow=True)

    def format(self, fmt):
        return fmt.format(cur=self.cur, arrow=self.arrow)


async def getrates(cuuid, crates):
    await crates.update(cuuid=cuuid)


async def main(self, message, *args, **kwargs):
    if not rates.auto_update:
        await rates.update()
    cur_list = []
    if 'currency' in kwargs and kwargs['currency']:
        splt_cur = kwargs['currency'][1:].split()
        for cur in splt_cur:
            if cur.upper() in rates:
                cur_list.append(cur.upper())
    else:
        cur_list = rates.any_list
    if len(cur_list) <= 0:
        await self.send(message.channel, 'Wrong currency specified')
        return
    cur_out = []
    for curenc in cur_list:
        cur_out.append(rates(rates.default, curenc, fmt=rates_format))
    await self.send(message.channel, 'Exchange rates: %s' % ', '.join(cur_out))
