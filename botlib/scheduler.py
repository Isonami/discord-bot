# -*- coding: utf-8 -*-
import threading
import uuid
import logging
import types

logger = logging.getLogger(__name__)


class Job(threading.Thread):
    def __init__(self, target, name, args):
        threading.Thread.__init__(self, target=target, name="job_{}".format(name), args=args)
        self.daemon = True


class Scheduler(threading.Thread):
    """Thread that executes a task every N seconds"""

    def __init__(self, interval=10):
        threading.Thread.__init__(self)
        self._finished = threading.Event()
        self._interval = interval
        self._tasks = {}
        self.daemon = True

    def setInterval(self, interval):
        """Set the number of seconds we sleep between executing our task"""
        self._interval = interval

    def shutdown(self):
        """Stop this thread"""
        self._finished.set()

    def run(self):
        while 1:
            if self._finished.isSet():
                return
            interval = self._interval
            self.task(interval)
            self._finished.wait(interval)

    def task(self, interval):
        for key, one_task in self._tasks.iteritems():
            next_delay = one_task["Next"] - interval
            if next_delay < 0:
                cur_job = Job(one_task["Job"], one_task["Name"], one_task["Args"])
                logger.debug("Starting job: %s", one_task["Name"])
                cur_job.start()
                one_task["Next"] = one_task["Delay"]
            else:
                one_task["Next"] = next_delay

    def append(self, job, name, delay, *args):
        if isinstance(job, types.FunctionType) and isinstance(delay, int):
            cuuid = str(uuid.uuid1())
            self._tasks[cuuid] = {"Name": name, "Job": job, "Delay": delay, "Next": 0, "Args": args}
            return cuuid
        else:
            logger.error("Can not add job: job is not a function or delay not integer")

    def remove(self, cuuid):
        self._tasks.pop(cuuid)
