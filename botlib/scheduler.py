# -*- coding: utf-8 -*-
import asyncio
import uuid
import logging
import types
from random import randint
import functools

logger = logging.getLogger(__name__)
stardelay = (5, 30)


class Job(object):
    __slots__ = ['name', 'paused', 'target', 'delay', 'args', 'loop', '_runned', '_handler', 'stardelay']

    def __init__(self, bot, target, name, delay, stdelay, args):
        self.name = name
        self.target = target
        self.delay = delay
        self.args = args
        self.loop = bot.loop
        self.paused = bot.notrealy
        self._runned = False
        self._handler = None
        self.stardelay = stdelay

    def __str__(self):
        return self.name

    def start(self):
        if self.paused:
            return
        self._runned = True
        self._handler = self.loop.call_later(randint(*self.stardelay), self._wrapper)

    def _wrapper(self):
        if self._runned:
            self._handler = self.loop.call_later(self.delay, self._wrapper)
            self._call()

    def _result(self, cuuid, result):
        result = result.result()[0]
        if isinstance(result, Exception):
            logger.exception("Job [%s] %s: %s", cuuid, result.__class__.__name__, result)
        logger.info('End Job: %s UUID(%s)', str(self), cuuid)

    def _call(self):
        cuuid = str(uuid.uuid4())
        logger.info('Start Job: %s UUID(%s)', str(self), cuuid)
        asyncio.gather(
            self.target(cuuid, *self.args),
            loop=self.loop, return_exceptions=True
            ).add_done_callback(functools.partial(self._result, cuuid))

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
            job = Job(self.bot, job, name, delay, self.stardelay, args)
            self.jobs.append(job)
            return job
        else:
            logger.error("Can not add job: job is not a function or delay not integer")
