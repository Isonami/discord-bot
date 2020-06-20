# -*- coding: utf-8 -*-
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4 syntax=python
# vi: tabstop=8 expandtab shiftwidth=4 softtabstop=4 syntax=python


def setup(bot):
    """
    :type bot: isobot.Bot
    """
    @bot.message()
    async def unflip(ctx: bot.Context):
        if ctx.message.content.startswith('(╯°□°）╯︵ ┻━┻'):
            await ctx.send('┬─┬﻿ ノ( ゜-゜ノ)')

