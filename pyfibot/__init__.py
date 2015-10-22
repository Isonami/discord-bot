# -*- coding: utf-8 -*-
from pbot import Pbot
import modules


def init(bot):
    pibot = Pbot(bot)
    commands = []
    modules.init(pibot, commands)
    return commands
