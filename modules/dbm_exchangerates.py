# -*- coding: utf-8 -*-
import logging
import json

command = r'\$(?P<currency>(?: [a-z]{3})+)?'
description = '{cmd_start}$ USD|EUR - show exchange rates'

rates_url = None
rates_delay = 600
rates = {
    'rates': [
        {},
        {}
    ],
    'next': 0,
    'etag': '',
    'date': ''
}
rates_def = 'RUB'
rates_any_list = ['USD', 'EUR', 'UAH']
rates_format = '1 {need_rate} = {value:0.2f}{arrow} {base_rate}'
rates_last = {}
ARROW_UP = chr(8593)
ARROW_DOWN = chr(8595)

logger = logging.getLogger(__name__)


async def init(bot):
    global rates_url
    rates_url = bot.config.get('exchangerates.url').format(appid=bot.config.get('exchangerates.appid'))
    global rates_def
    rates_def = bot.config.get('exchangerates.start_currency', rates_def)
    global rates_any_list
    rates_any_list = bot.config.get('exchangerates.rates_any_list', rates_any_list)
    global rates_delay
    rates_delay = bot.config.get('exchangerates.delay', rates_delay)
    global rates_format
    rates_format = bot.config.get('exchangerates.format', rates_format)
    global job
    job = bot.scheduler.new(getrates, 'Exchangerates', rates_delay, bot.http)
    job.start()
    bot.config.set('exchangerates.getrate', get_onerate)


async def getrates(cuuid, http):
    logger.debug('[%s] Try to get new rates', cuuid)
    if not rates_url:
        logger.debug('[%s] Can not get rates, no url specified!', cuuid)
        return
    response = await http(rates_url, method='GET', etag=rates['etag'], date=rates['date'])
    if response.code == 0:
        rvars = json.loads(str(response))
        if rvars:
            if 'rates' in rvars:
                logger.debug('[%s] Rates updated', cuuid)
                rates['rates'][1] = rates['rates'][0]
                rates['rates'][0] = rvars['rates']
                if 'ETag' in response.headers and 'Date' in response.headers:
                    logger.debug('[%s] Got ETag: %s, Date: %s', cuuid, response.headers['ETag'],
                                 response.headers['Date'])
                    rates['etag'] = response.headers['ETag']
                    rates['date'] = response.headers['Date']
        else:
            logger.error('[%s] Can not get rates', cuuid)
    elif response.code == 1:
        logger.debug('[%s] Rates did not change', cuuid)


def get_onerate(base_rate, need_rate, fmt=None, arrow_up=ARROW_UP, arrow_down=ARROW_DOWN):
    if base_rate not in rates['rates'][0] or need_rate not in rates['rates'][0]:
        if fmt:
            return ''
        else:
            return 0
    def_cur = rates['rates'][0][base_rate]
    arrow = ''
    num = def_cur / rates['rates'][0][need_rate]
    if need_rate in rates['rates'][1] and base_rate in rates['rates'][1]:
        old_def_cur = rates['rates'][1][base_rate]
        old_num = old_def_cur / rates['rates'][1][need_rate]
        if num > old_num:
            arrow = arrow_up
        elif num < old_num:
            arrow = arrow_down
    if fmt:
        return fmt.format(need_rate=need_rate, base_rate=base_rate, value=num, arrow=arrow)
    return num, arrow


async def main(self, message, *args, **kwargs):
    cur_list = []
    if 'currency' in kwargs and kwargs['currency']:
        splt_cur = kwargs['currency'][1:].split()
        for cur in splt_cur:
            if cur.upper() in rates['rates']:
                cur_list .append(cur.upper())
    else:
        cur_list = rates_any_list
    if len(cur_list) <= 0:
        await self.client.send_message(message.channel, 'Wrong currency specified')
        return
    cur_out = []
    for curenc in cur_list:
        cur_out.append(get_onerate(rates_def, curenc, fmt=rates_format))
    await self.send(message.channel, 'Exchange rates: %s' % ', '.join(cur_out))
