# -*- coding: utf-8 -*-
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4 syntax=python
# vi: tabstop=8 expandtab shiftwidth=4 softtabstop=4 syntax=python
import peewee
from peewee_async import Manager, PooledPostgresqlDatabase, PooledMySQLDatabase, _run_sql
import logging
import dsnparse

db = None
manager = None
db_sqls = None
logger = logging.getLogger(__name__)


class UglyHook(object):
    schema_replace = 'DB_SCHEMA'
    sequence_replace = 'SEQUENCE_NAME'

    def __init__(self, cls):
        self.sequences = cls.sequences
        self.cls = cls
        self.get_tables_sql = None
        self.sequence_exists_sql = None
        self.mode = 'get_tables'

    def load(self):
        try:
            self.cls.get_tables(self, schema=self.schema_replace)
        except Exception as exc:
            if not self.get_tables_sql:
                logger.error('Can not get create_table sql from peewee ({})!'.format(exc))
                raise
        if self.sequences:
            self.mode = 'sequence_exists'
            try:
                self.cls.sequence_exists(self, self.sequence_replace)
            except Exception as exc:
                if not self.sequence_exists_sql:
                    logger.error('Can not get sequence_exists sql from peewee ({})!'.format(exc))
                    raise

    def set_value(self, value):
        if self.mode == 'get_tables':
            self.get_tables_sql = value
        elif self.mode == 'sequence_exists':
            self.sequence_exists_sql = value

    def execute_sql(self, *args):
        if len(args) == 2:
            self.set_value(args[0] % args[1])
        else:
            self.set_value(args[0])


async def _fetch_sql(database, operation, *args, **kwargs):
    cursor = await _run_sql(database, operation, *args, **kwargs)
    result = []
    while True:
        row = await cursor.fetchone()
        if not row:
            await cursor.release
            return result
        result.append(row)


def initialize(bot):
    """
    :type bot: isobot.Bot
    """
    config = bot.global_config
    global db, manager, db_sqls
    dsn = dsnparse.parse(config.get('dsn'))

    params = dsn.query
    for value in [('username', 'user'), 'password', 'host', 'port']:
        if isinstance(value, tuple):
            search_value, set_value = value
        else:
            search_value = set_value = value
        if getattr(dsn, search_value):
            params[set_value] = getattr(dsn, search_value)

    if dsn.scheme.lower() == 'postgresql':
        if dsn.paths:
            database_name = dsn.paths[0]
        else:
            database_name = 'postgresql'
        db = PooledPostgresqlDatabase(database_name, **params)
        db_sqls = UglyHook(PooledPostgresqlDatabase)
        db_sqls.load()
    elif dsn.scheme.lower() == 'mysql':
        if dsn.paths:
            database_name = dsn.paths[0]
        else:
            database_name = 'mysql'
        db = PooledMySQLDatabase(database_name, **params)
        db_sqls = UglyHook(PooledMySQLDatabase)
        db_sqls.load()
    else:
        raise ValueError('db must be one of (postgresql, mysql)')

    class BaseModel(peewee.Model):
        class Meta:
            database = db

        @classmethod
        async def table_exists(cls):
            if cls._meta.schema:
                query = db_sqls.get_tables_sql.replace(db_sqls.schema_replace, '\'{}\''.format(cls._meta.schema))
            else:
                query = db_sqls.get_tables_sql.replace(db_sqls.schema_replace, '\'{}\''.format('public'))
            for r in await _fetch_sql(db, query):
                if isinstance(r, tuple):
                    r = r[0]
                if r == cls._meta.db_table:
                    return True
            return False

        @classmethod
        async def sequence_exists(cls, name):
            query = db_sqls.sequence_exists_sql.replace(db_sqls.sequence_replace, '\'{}\''.format(name))
            for r in await _fetch_sql(db, query):
                return True
            return False

        @classmethod
        async def create_index(cls, fields, unique=False):
            db = cls._meta.database
            qc = db.compiler()
            if not isinstance(fields, (list, tuple)):
                raise ValueError('Fields passed to "create_index" must be a list '
                                 'or tuple: "%s"' % fields)
            fobjs = [
                cls._meta.fields[f] if isinstance(f, str) else f
                for f in fields]
            return await _run_sql(db, *qc.create_index(cls, fobjs, unique))

        @classmethod
        async def _create_indexes(cls):
            for field_list, is_unique in cls._index_data():
                await cls.create_index(field_list, is_unique)

        @classmethod
        async def create_table(cls, fail_silently=False):
            if await cls.table_exists():
                return

            db = cls._meta.database
            pk = cls._meta.primary_key
            qc = db.compiler()
            if db.sequences and pk is not False and pk.sequence:
                if not await cls.sequence_exists(pk.sequence):
                    await _run_sql(db, *qc.create_sequence(pk.sequence))

            await _run_sql(db, *qc.create_table(cls, False))
            await cls._create_indexes()

    manager = Manager(db)
    bot.db = manager
    bot.BaseModel = BaseModel


async def init_model(model):
    """
    :type model: peewee.Model
    """
    await model.create_table()
