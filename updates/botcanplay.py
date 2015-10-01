from time import sleep, time
import json
import logging
import threading
from tornado.httpclient import HTTPError
import re
from random import randint

logger = logging.getLogger(__name__)
url_base = "https://discordapp.com/{url}"
init_url = url_base.format(url="channels/@me")
games = {"list": None, "id": 0}
play_delay = 420
play_chance = 10


def get_game_list(bot):
    try:
        response = bot.http_client.fetch(init_url, method="GET")
        # print response.body
        r = re.compile('<script src=\"([a-z0-9\./]+)\"></script>')
        m = r.findall(response.body)
        response = bot.http_client.fetch(url_base.format(url=m[-1]), method="GET")
        r = re.compile('executables:\{(?:(?:[a-z0-9]+:\[[^\]]+\])?\}?,)+id:([0-9]+),name:\"([^\"]+)\"')
        return r.findall(response.body)

    except HTTPError as e:
        # HTTPError is raised for non-200 responses; the response
        # can be found in e.response.
        logger.error("HTTPError: " + str(e))


class KeepAliveHandler(threading.Thread):
    def __init__(self, seconds, socket, **kwargs):
        threading.Thread.__init__(self, **kwargs)
        self.seconds = seconds
        self.socket = socket
        self.stop = threading.Event()
        self.payload = {
                'op': 1,
                'd': int(time())
            }

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
    if not hasattr(bot.client, "keep_alive"):
        sleep(5)
    seconds = bot.client.keep_alive.seconds
    bot.client.keep_alive.stop.set()
    logger.debug("Stop old keepalive handler")
    bot.client.keep_alive = KeepAliveHandler(1, bot.client.ws)
    bot.client.keep_alive.start()
    sleep(2)
    bot.client.keep_alive.seconds = seconds
    logger.debug("Start our keepalive handler")
    while not games["list"]:
        games["list"] = get_game_list(bot)
        games["len"] = len(games["list"])
        sleep(60)
    while not bot.disconect:
        if randint(1, play_chance) == 1:
            games["id"], name = games["list"][randint(0, games["len"]-1)]
            logger.debug("Set game to: %s", name)
            bot.client.keep_alive.payload['op'] = 3
        else:
            bot.client.keep_alive.payload['op'] = 1
        sleep(play_delay)


def init(bot):
    global play_delay
    play_delay = bot.config.get("botcanplay.delay", play_delay)
    global play_chance
    play_chance = bot.config.get("botcanplay.chance", play_chance)
    cleaner_th = threading.Thread(name="BotPlay", target=botplayth, args=(bot,))
    cleaner_th.start()
