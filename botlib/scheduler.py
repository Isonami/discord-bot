# -*- coding: utf-8 -*-
import asyncio
import uuid
import logging
import types
from random import random

logger = logging.getLogger(__name__)
stardelay = (5, 30)


class Job(object):
    __slots__ = ['name', 'target', 'delay', 'args', 'loop', '_runned', '_handler', 'stardelay']

    def __init__(self, loop, target, name, delay, stdelay, args):
        self.name = name
        self.target = target
        self.delay = delay
        self.args = args
        self.loop = loop
        self._runned = False
        self._handler = None
        self.stardelay = stdelay

    def start(self):
        self._runned = True
        self._handler = self.loop.call_at(random(*self.stardelay), self._wrapper)

    async def _wrapper(self):
        if self._runned:
            self._handler = self.loop.call_at(self.delay, self._wrapper)
            cuuid = str(uuid.uuid4())
            logger.debug('Start Job: %s UUID(%s)', self.name, cuuid)
            try:
                await self.target(*self.args, cuuid=cuuid)
            except Exception as exc:
                logger.error("Job [%s] %s: %s", cuuid, exc.__class__.__name__, exc)
            finally:
                logger.debug('End Job: %s UUID(%s)', self.name, cuuid)

    def destroy(self):
        self._runned = False
        if isinstance(self._handler, asyncio.Handle):
            self._handler.cancel()


class Scheduler(object):
    __slots__ = ['bot', 'jobs', 'stardelay']

    def __init__(self, bot):
        self.bot = bot
        self.jobs = []
        stdelay = bot.config.get('scheduler.startdelay', list(stardelay))
        if isinstance(stdelay, list) and len(stdelay) == 2:
            self.stardelay = tuple(stdelay)
        else:
            self.stardelay = stardelay

    def new(self, job, name, delay, *args):
        if isinstance(job, types.FunctionType) and isinstance(delay, int):
            job = Job(self.bot.loop, job, name, delay, self.stardelay, args)
            self.jobs.append(job)
            return job
        else:
            logger.error("Can not add job: job is not a function or delay not integer")
