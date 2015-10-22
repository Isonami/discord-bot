# -*- coding: utf-8 -*-
from pbot import Pbot
from commands import cmd_opt, ban_cmd
import modules


def init(bot):
    pibot = Pbot(bot)
    commands = []
    modules.init(pibot, commands, cmd_opt, ban_cmd)
    return commands
