# -*- coding: utf-8 -*-
import logging
from datetime import datetime, time

command = r'uptime'
description = '{cmd_start}uptime - show bot uptime'
admin = True
private = True

logger = logging.getLogger(__name__)
datefmt = '%Y-%m-%d %H:%M'

ans_template = '''Started at: {starttime}
Uptime: {uptime}
'''


async def init(bot):
    global start_time
    start_time = bot.config.get('main.start_time')


async def main(self, message, *args, **kwargs):
    if start_time:
        delta = datetime.now() - start_time
        msg = ans_template.format(starttime=start_time.strftime(datefmt), uptime=str(delta).split('.')[0])
        await self.send(message.channel, msg)
