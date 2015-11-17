# -*- coding: utf-8 -*-
import sqlite3
import logging
from Queue import Queue, Empty
from time import sleep
from os import path
from threading import Thread, Event

logger = logging.getLogger(__name__)
insql = Queue()
open_dbs = {}

sql_timeout = 30


class Result(object):
    _result = None
    _sql = None
    _args = None
    _sql_type = None
    _con = None
    _cur = None
    _timeout = True

    def __init__(self):
        self._event = Event()

    @property
    def result(self):
        return self._result

    @result.setter
    def result(self, value):
        self._result = value
        self._timeout = False
        self._event.set()

    @property
    def con(self):
        return self._con

    @con.setter
    def con(self, value):
        self._con = value

    @property
    def cur(self):
        return self._cur

    @cur.setter
    def cur(self, value):
        self._cur = value

    @property
    def sql(self):
        return self._sql

    @property
    def args(self):
        return self._args

    @property
    def sql_type(self):
        return self._sql_type

    def get(self, sql_type, sql, args, timeout):
        self._sql_type = sql_type
        self._sql = sql
        self._args = args
        insql.put(self)
        self._event.wait(timeout=timeout)
        if self._timeout:
            logger.error("Timeout on SQL operation: %s", self.sql)
        return self.result

    def clear(self):
        self._sql = None
        self._args = None
        self._sql_type = None
        self._result = None
        self._timeout = True
        self._event.clear()


class SQLCon(object):
    def __init__(self, init_script, db_name):
        self._result = Result()
        logger.debug("Init DB connection: %s", db_name)
        res = self.get(-1, init_script, (db_name,))
        if res:
            self._result.con, self._result.cur = res
        if not self._result.cur:
            raise sqlite3.DatabaseError("Can not init database: %s" % db_name)

    def request(self, sql_str, *args, **kwargs):
        res = self.get(1, sql_str, args)
        one = kwargs.get("one", None)
        if one and res and len(res) > 0:
            return res[0]
        return res

    def commit(self, sql_str, *args):
        return self.get(0, sql_str, args)

    def get(self, sql_type, sql, args, timeout=sql_timeout):
        res = self._result.get(sql_type, sql, args, timeout)
        self._result.clear()
        return res


def sql_db(bot):
    while not bot.disconnect:
        try:
            item = insql.get()
        except Empty:
            sleep(1)
            continue
        if isinstance(item, Result):
            try:
                logger.debug("New SQL Query: %s, args: %s", item.sql, unicode(item.args))
                if item.sql_type == -1:
                    con = sqlite3.connect(path.join(bot_dir, "db", item.args[0]))
                    cur = con.cursor()
                    cur.executescript(item.sql)
                    item.result = (con, cur)
                else:
                    item.cur.execute(item.sql, item.args)
                    if item.sql_type == 1:
                        row = item.cur.fetchall()
                        item.result = row
                    else:
                        item.con.commit()
                        item.result = True
            except Exception, exc:
                logger.error("%s: %s" % (exc.__class__.__name__, exc))
                item.result = None


def sqlcon(sql_init, db_name):
    if db_name in open_dbs:
        con = open_dbs[db_name]
    else:
        con = SQLCon(sql_init, db_name)
        open_dbs[db_name] = con
    return con


def init(bot):
    global bot_dir
    bot_dir = bot.config.get("main.dir")
    sql_th = Thread(name="SQLTh", target=sql_db, args=(bot,))
    sql_th.daemon = True
    sql_th.start()
    return sqlcon
