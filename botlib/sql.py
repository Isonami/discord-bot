# -*- coding: utf-8 -*-
import aioodbc
import pyodbc
import logging
import asyncio
from os import path

logger = logging.getLogger(__name__)
open_dbs = {}

sql_timeout = 30

driver = "SQLite"


class Result(object):
    __slots__ = ['_result', '_sql', '_args', '_sql_type', '_con', '_cur', '_timeout', '_event']

    def __init__(self):
        self._result = None
        self._sql = None
        self._args = None
        self._sql_type = None
        self._con = None
        self._cur = None
        self._timeout = True
        self._event = asyncio.Event()

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
        return self._sql or ""

    @property
    def args(self):
        return self._args

    @property
    def sql_type(self):
        return self._sql_type

    async def get(self, sql_type, sql, args, timeout):
        self._sql_type = sql_type
        self._sql = sql
        self._args = args
        await insql.put(self)
        try:
            await asyncio.wait_for(self._event.wait(), timeout)
        except asyncio.futures.TimeoutError:
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
    __slots__ = ['_result', 'dsn', 'init_script']

    def __init__(self, init_script, db_name):
        self._result = Result()
        logger.debug("Init DB connection: %s", db_name)
        db_path = path.join(sdir, "db", db_name)
        self.dsn = 'Driver={};Database={}'.format(driver, db_path)
        self.init_script = init_script

    async def connection(self):
        res = await self.get(-1, self.init_script, (self.dsn,))
        if res:
            self._result.con, self._result.cur = res
        if not self._result.cur:
            raise pyodbc.DatabaseError("Can not init database: %s" % self.dsn)

    async def request(self, sql_str, *args, **kwargs):
        res = await self.get(1, sql_str, args)
        one = kwargs.get("one", None)
        if isinstance(res, list):
            if one and res and len(res) > 0:
                return res[0]
        return res

    async def commit(self, sql_str, *args):
        return await self.get(0, sql_str, args)

    async def get(self, sql_type, sql, args, timeout=sql_timeout):
        res = await self._result.get(sql_type, sql, args, timeout)
        self._result.clear()
        return res


async def sql_db(bot):
    loop = bot.loop
    while not bot.disconnect:
        item = await insql.get()
        if isinstance(item, Result):
            try:
                logger.debug("New SQL Query: %s, args: %s", item.sql, str(item.args))
                if item.sql_type == -1:
                    con = await aioodbc.connect(dsn=item.args[0], loop=loop)
                    cur = await con.cursor()
                    await cur.execute(item.sql)
                    item.result = (con, cur)
                else:
                    await item.cur.execute(item.sql, item.args)
                    if item.sql_type == 1:
                        row = await item.cur.fetchall()
                        item.result = row
                    else:
                        await item.con.commit()
                        item.result = True
            except Exception as exc:
                logger.exception("%s: %s" % (exc.__class__.__name__, exc))
                item.result = None


async def sqlcon(sql_init, db_name):
    if db_name in open_dbs:
        con = open_dbs[db_name]
    else:
        con = SQLCon(sql_init, db_name)
        await con.connection()
        open_dbs[db_name] = con
    return con


async def close():
    for db_name in open_dbs:
        con = open_dbs[db_name]
        print(db_name)
        await con.cur.close()
        await con.con.close()


def init(bot):
    global sdir
    sdir = bot.config.get("main.dir")
    global driver
    driver = bot.config.get("sql.driver", driver)
    global insql
    insql = asyncio.Queue()
    bot.async_function(sql_db(bot))
    return sqlcon
