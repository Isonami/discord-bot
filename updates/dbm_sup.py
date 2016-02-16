# -*- coding: utf-8 -*-
import logging
from discord import Message
import re
from datetime import datetime


logger = logging.getLogger(__name__)
cities = '524901 498817 551487 700051'
delay = 3600
one_weather_format = '{city}: :{weather[emoji]}: {main[temp]:.1f}°C'
one_currency_format = '[USD: {cur.usd.rub:0.2f}{arrow.usd.rub} RUB, {cur.usd.uah:0.2f}{arrow.usd.uah} UAH] ' \
                      '[GBP: {cur.gbp.rub:0.2f}{arrow.gbp.rub} RUB, {cur.gbp.uah:0.2f}{arrow.gbp.uah} UAH]'
one_date_format = '{date:%d.%m %H:%M}:'
max_len = 12 * 4 - 1
separrator = ', '
cachedre = re.compile(r' \{cached(:?:[^}]+)?}')

emoji_weather = {
    '01': 'sunny',
    '02': 'partly_sunny',
    '03': 'cloud',
    '04': 'cloud',
    '09': 'umbrella',
    '10': 'umbrella',
    '11': 'zap',
    '13': 'snowflake',
    '50': 'foggy',
}


class ResolveCur(object):
    __slots__ = ['_rates', '_base', '_none', '_arrow']

    def __init__(self, rates, base=False, none=False, arrow=False):
        self._rates = rates
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


async def init(bot):
    chan_id = bot.config.get('sup.channel_id', None)
    if not chan_id:
        raise ValueError('Channel id (\'channel_id\') required!')
    global cities
    cities = bot.config.get('sup.cities', cities)
    global one_weather_format
    one_weather_format = bot.config.get('sup.weather_format', one_weather_format)
    global one_currency_format
    one_currency_format = bot.config.get('sup.currency_format', one_currency_format)
    global one_date_format
    one_date_format = bot.config.get('sup.date_format', one_date_format)
    global separrator
    separrator = bot.config.get('sup.separrator', separrator)
    global max_len
    max_len = bot.config.get('sup.max_len', max_len)
    global delay
    delay = bot.config.get('sup.delay', delay)
    job = bot.scheduler.new(update, 'Sup', delay, bot, chan_id)
    job.start()


async def update(cuuid, bot, chan_id):
    msg = None
    async for mes in bot.logs_from(bot.get_channel(str(chan_id)), limit=1):
        msg = mes
    message = await generate_message(bot)
    if not message:
        return
    if not isinstance(msg, Message) or msg.author != bot.user:
        message.insert(0, one_date_format.format(date=datetime.now()))
        await bot.send(bot.get_channel(str(chan_id)), '\n'.join(message))
    else:
        messgae_strings = msg.content.split('\n')
        messgae_strings.append('')
        messgae_strings.append(one_date_format.format(date=datetime.now()))
        messgae_strings.extend(message)
        messgae_strings = messgae_strings[-max_len:]
        await bot.edit_message(msg, '\n'.join(messgae_strings))


async def generate_message(bot):
    rates = bot.config.get('exchangerates.rates')
    weather = bot.config.get('openweather.weather')
    if not rates or not weather:
        return
    if not rates.auto_update:
        await rates.update()
    weather_result = []
    for one_weather in (await weather(cities))():
        fmt = one_weather_format
        if 'cached' not in one_weather:
            fmt = cachedre.sub('', fmt)
        one_weather['weather']['emoji'] = emoji_weather.get(one_weather['weather']['icon'][:-1],
                                                            '{}({})'.format(one_weather['weather']['main'],
                                                                            one_weather['weather']['icon'][:-1]))
        weather_result.append(fmt.format(**one_weather))
    weather_result = separrator.join(weather_result)
    rates_result = one_currency_format.format(cur=ResolveCur(rates), arrow=ResolveCur(rates, arrow=True))
    return [weather_result, rates_result]



