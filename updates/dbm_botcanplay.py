# -*- coding: utf-8 -*-
import logging
import re
from random import randint
import discord.endpoints as endpoints
import json
from discord.game import Game

logger = logging.getLogger(__name__)
url_base = endpoints.BASE + '/{url}'
init_url = url_base.format(url='channels/@me')
games = {'list': None, 'id': 0}
play_delay = 420
play_chance = 1
bot_play_th_started = False


async def get_game_list(bot):
    response = await bot.http.get(init_url)
    if response.code == 0:
        r = re.compile('<script src=\"([a-z0-9\./]+)\"></script>')
        m = r.findall(str(response))
        if len(m) > 0:
            response = await bot.http.get(url_base.format(url=m[-1]))
            if response.code == 0:
                r = re.compile('executables:(\{(?:(?:[a-z0-9]+:\[[^\]]+\])?\}?,)+)id:([0-9]+),name:\"([^\"]+)\"')
                return r.findall(str(response))
    return []


jsonformat = re.compile(r'([\[\{\]\}:,])([a-z0-9]+)([\[\{\]\}:,])')


def dump(exe):
    try:
        return json.loads(jsonformat.sub(lambda x: '{}"{}"{}'.format(x.group(1), x.group(2), x.group(3)), exe))
    except ValueError as e:
        return {}
# games['list'] = [{'executables': dump(exe[:-1]), 'id': gid, 'name': name} for exe, gid, name in get_game_list(bot)]


async def botplayth(cuuid, bot):
    if not games['list']:
        games['list'] = [Game(name=name) for exe, gid, name in await get_game_list(bot)]
        games['len'] = len(games['list'])
        if not games['list']:
            return
        logger.debug('[%s] Game list loaded', cuuid)
    if len(games['list']) < 1:
        logger.error('[%s] Can not parse games list!', cuuid)
        return
    if not bot.disconnect:
        if bot.config.get('botcanplay.play_game'):
            return
        if randint(1, play_chance) == 1:
            games['id'] = games['list'][randint(0, games['len']-1)]
            logger.debug('Set game to: %s', games['id'].name)
            await bot.change_status(game=games['id'])
        elif games['id']:
            logger.debug('End game')
            games['id'] = None
            await bot.change_status()


async def ready(bot):
    if 'job' not in globals():
        global job
        job = bot.scheduler.new(botplayth, 'BotPlay', play_delay, bot)
        job.start()


async def init(bot):
    global play_delay
    play_delay = bot.config.get('botcanplay.delay', play_delay)
    global play_chance
    play_chance = bot.config.get('botcanplay.chance', play_chance)
    if not isinstance(play_delay, int) or not isinstance(play_chance, int) or play_chance < 1:
        raise ValueError('botcanplay.delay or botcanplay.chance not an intenger or botcanplay.chance < 1')
