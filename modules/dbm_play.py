# -*- coding: utf-8 -*-
import logging
from time import time
from discord.game import Game
import asyncio

command = r'play (?P<playdelay>[0-9]+)(?P<playgame>(?: [\S]+){1,5})'
description = '{cmd_start}play time game_name - play game for time in seconds (admin command)'
admin = True

logger = logging.getLogger(__name__)
dmin = 10
dmax = 3600


async def wait(bot, twait):
    await asyncio.sleep(twait - time())
    if bot.config.get('botcanplay.play_game') and bot.config.get('botcanplay.play_game') == twait:
        logger.debug('End game')
        await bot.client.change_status()


async def main(self, message, *args, **kwargs):
    game = kwargs.get('playgame', None)
    delay = int(kwargs.get('playdelay', 0))
    if game and (dmin <= delay <= dmax):
        twait = time() + delay
        game = game.strip()
        self.config.set('botcanplay.play_game', twait)
        logger.debug('Set game to: %s', game)
        await self.client.change_status(game=Game(name=game))
        await self.send(message.channel, 'Set game to: %s' % game)
        await wait(self, twait)
