# -*- coding: utf-8 -*-
import logging
from random import randint

logger = logging.getLogger(__name__)

command = r'rand(?:om)?(?: (?P<randcount>[0-9]{1,5}))?'
description = '{cmd_start}rand(om) max - show random number from 1 to max'


async def main(self, message, *args, **kwargs):
    max_rand = 100
    if 'randcount' in kwargs and kwargs['randcount']:
        max_rand = int(kwargs['randcount'])
    await self.send(message.channel, 'Random number is: %d' % randint(1, max_rand))
