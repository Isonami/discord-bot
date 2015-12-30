from time import sleep
import logging
import threading
from tornado.httpclient import HTTPError
import re
from random import randint
import discord.endpoints as endpoints
import json
from discord.game import Game

logger = logging.getLogger(__name__)
url_base = endpoints.BASE + "/{url}"
init_url = url_base.format(url="channels/@me")
games = {"list": None, "id": 0}
play_delay = 420
play_chance = 10
bot_play_th_started = False


def get_game_list(bot):
    try:
        response = bot.http_client.fetch(init_url, method="GET")
        # print response.body
        r = re.compile('<script src=\"([a-z0-9\./]+)\"></script>')
        m = r.findall(response.body)
        if len(m) > 0:
            response = bot.http_client.fetch(url_base.format(url=m[-1]), method="GET")
            r = re.compile('executables:(\{(?:(?:[a-z0-9]+:\[[^\]]+\])?\}?,)+)id:([0-9]+),name:\"([^\"]+)\"')
            return r.findall(response.body)
        return []

    except HTTPError as e:
        # HTTPError is raised for non-200 responses; the response
        # can be found in e.response.
        logger.error("HTTPError: " + str(e))


jsonformat = re.compile(r"([\[\{\]\}:,])([a-z0-9]+)([\[\{\]\}:,])")


def dump(exe):
    try:
        return json.loads(jsonformat.sub(lambda x: '{}"{}"{}'.format(x.group(1), x.group(2), x.group(3)), exe))
    except ValueError as e:
        return {}
# games["list"] = [{"executables": dump(exe[:-1]), "id": gid, "name": name} for exe, gid, name in get_game_list(bot)]


def botplayth(bot):
    global bot_play_th_started
    bot_play_th_started = True
    while not games["list"]:
        games["list"] = [Game(name=name) for exe, gid, name in get_game_list(bot)]
        games["len"] = len(games["list"])
        if not games["list"]:
            sleep(60)
    if len(games["list"]) < 1:
        logger.error("Can not parse games list!")
        return
    while not bot.disconnect:
        if randint(1, play_chance) == 1:
            games["id"] = games["list"][randint(0, games["len"]-1)]
            logger.debug("Set game to: %s", games["id"].name)
            bot.client.change_status(game=games["id"])
        elif games["id"]:
            logger.debug("End game")
            games["id"] = None
            bot.client.change_status()
        sleep(play_delay)


def bot_can_play_th(bot):
    if not bot_play_th_started:
        bot_play_th = threading.Thread(name="BotPlay", target=botplayth, args=(bot,))
        bot_play_th.daemon = True
        bot_play_th.start()


def init(bot):
    global play_delay
    play_delay = bot.config.get("botcanplay.delay", play_delay)
    global play_chance
    play_chance = bot.config.get("botcanplay.chance", play_chance)
    bot.on_ready.append(bot_can_play_th)
