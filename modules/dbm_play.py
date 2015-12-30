import logging
from time import time, sleep
from discord.game import Game
from threading import Thread

command = r"play (?P<playdelay>[0-9]+)(?P<playgame>( [\S]+){1,5})"
description = "{cmd_start}play game_name time - play game for time in seconds (admin command)"
admin = True

logger = logging.getLogger(__name__)
dmin = 10
dmax = 3600


def wait(bot, twait):
    sleep(twait - time())
    if bot.config.get("botcanplay.play_game") and bot.config.get("botcanplay.play_game") == twait:
        logger.debug("End game")
        bot.client.change_status()


def main(self, message, *args, **kwargs):
    try:
        game = kwargs.get("playgame", None)
        delay = int(kwargs.get("playdelay", 0))
        if game and (dmin <= delay <= dmax):
            twait = time() + delay
            game = game.strip()
            self.config.set("botcanplay.play_game", twait)
            logger.debug("Set game to: %s", game)
            self.client.change_status(game=Game(name=game))
            self.send(message.channel, "Set game to: %s" % game)
            th = Thread(target=wait, args=(self, twait))
            th.daemon = True
            th.start()
    except Exception, exc:
        logger.error("%s: %s" % (exc.__class__.__name__, exc))
