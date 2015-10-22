from time import sleep, time
import json
import logging
import threading
from tornado.httpclient import HTTPError
import re
from random import randint
import discord.endpoints as endpoints

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
            r = re.compile('executables:\{(?:(?:[a-z0-9]+:\[[^\]]+\])?\}?,)+id:([0-9]+),name:\"([^\"]+)\"')
            return r.findall(response.body)
        return []

    except HTTPError as e:
        # HTTPError is raised for non-200 responses; the response
        # can be found in e.response.
        logger.error("HTTPError: " + str(e))


class KeepAliveHandler(threading.Thread):
    def __init__(self, seconds, socket, **kwargs):
        threading.Thread.__init__(self, **kwargs)
        self.botcanplay = True
        self.seconds = seconds
        self.socket = socket
        self.stop = threading.Event()
        self.payload = {"op": 3, "d": {"idle_since": None, "game_id": None}}

    def run(self):
        while not self.stop.wait(self.seconds):
            self.set_payload()

            msg = 'Keeping websocket alive with timestamp {0}'
            logger.debug(msg.format(self.payload['d']))
            self.socket.send(json.dumps(self.payload))

    def set_payload(self):
        if self.payload['op'] == 1:
            self.payload['d'] = int(time())
        elif self.payload['op'] == 3:
            self.payload['d'] = {"idle_since": None, "game_id": games['id']}


def botplayth(bot):
    global bot_play_th_started
    bot_play_th_started = True
    while not games["list"]:
        games["list"] = get_game_list(bot)
        games["len"] = len(games["list"])
        if not games["list"]:
            sleep(60)
    if len(games["list"]) < 1:
        logger.error("Can not parse games list!")
        return
    while not bot.disconnect:
        if randint(1, play_chance) == 1:
            games["id"], name = games["list"][randint(0, games["len"]-1)]
            logger.debug("Set game to: %s", name)
            bot.client.ws.keep_alive.payload['op'] = 3
        elif games["id"]:
            logger.debug("End game")
            games["id"] = None
            bot.client.ws.keep_alive.payload['op'] = 1
        sleep(play_delay)


def bot_can_play_th(bot):
    if not hasattr(bot.client.ws, "keep_alive"):
        sleep(5)
    if hasattr(bot.client.ws.keep_alive, "botcanplay"):
        return
    seconds = bot.client.ws.keep_alive.seconds
    bot.client.ws.keep_alive.stop.set()
    logger.debug("Stop old keepalive handler")
    bot.client.ws.keep_alive = KeepAliveHandler(1, bot.client.ws)
    bot.client.ws.keep_alive.start()
    sleep(1)
    bot.client.ws.keep_alive.seconds = seconds
    logger.debug("Start our keepalive handler")
    payload = {"op": 3, "d": {"idle_since": None, "game_id": None}}
    bot.client.ws.keep_alive.socket.send(json.dumps(payload))
    if not bot_play_th_started:
        cleaner_th = threading.Thread(name="BotPlay", target=botplayth, args=(bot,))
        cleaner_th.start()


def init(bot):
    global play_delay
    play_delay = bot.config.get("botcanplay.delay", play_delay)
    global play_chance
    play_chance = bot.config.get("botcanplay.chance", play_chance)
    bot.on_ready.append(bot_can_play_th)
