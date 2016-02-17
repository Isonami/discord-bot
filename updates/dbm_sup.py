# -*- coding: utf-8 -*-
import logging
import asyncio
import re
from datetime import datetime


logger = logging.getLogger(__name__)
cities = '524901 498817 551487 700051 554234'
delay = 3600
one_weather_format = '{city}: :{weather[emoji]}: {main[temp]:.1f}°C'
one_currency_format = '[USD: {cur.usd.rub:0.2f}{arrow.usd.rub} RUB, {cur.usd.uah:0.2f}{arrow.usd.uah} UAH] ' \
                      '[GBP: {cur.gbp.rub:0.2f}{arrow.gbp.rub} RUB, {cur.gbp.uah:0.2f}{arrow.gbp.uah} UAH]'
one_date_format = '{date:%d.%m %H:%M (UTC)}:'
max_len = 24
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


def sortfn(item):
    return item.timestamp


async def get_messages(bot, lim, chan_id):
    msgs = []
    async for mes in bot.logs_from(bot.get_channel(str(chan_id)), limit=lim):
        msgs.append(mes)
    sort_msgs = sorted(msgs, key=sortfn, reverse=True)
    msgs = []
    for mes in sort_msgs:
        if mes.author == bot.user:
            msgs.append(mes)
        else:
            break
    return [msg for msg in reversed(msgs)]


async def update(cuuid, bot, chan_id):
    sort_msgs = await get_messages(bot, max_len, chan_id)
    message = await generate_message(bot)
    if not message:
        return
    sort_content = [msg.content for msg in sort_msgs]
    sort_content.pop(0)
    # for key, msg in enumerate(stort_msgs):
    #     print(key, msg.content, msg.timestamp)
    # return
    if len(sort_msgs) < max_len:
        def generator(items):
            for item in items:
                yield item.content
        gen = generator(sort_msgs)
        for msg in sort_msgs:
            await bot.delete_message(msg)
        for i in range(0, max_len - 1):
            content = ' '
            if max_len - (i + 1) <= len(sort_msgs):
                content = next(gen)
            await bot.send(bot.get_channel(str(chan_id)), content)
        await bot.send(bot.get_channel(str(chan_id)), '\n'.join(message))
    else:
        for i in range(0, len(sort_msgs) - 1):
            await bot.edit_message(sort_msgs[i], sort_content[i])
            await asyncio.sleep(1)
        await bot.edit_message(sort_msgs[-1], '\n'.join(message))


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
    rates_result = rates.format(one_currency_format)
    return ['', one_date_format.format(date=datetime.utcnow()), weather_result, rates_result]



