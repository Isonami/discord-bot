import importlib
import os
import logging

logger = logging.getLogger(__name__)

mbase = 'dbm_'


def search(name='isobot'):
    base = __name__
    if not base.startswith('{}.'.format(name)):
        base = '{}.{}'.format(name, base)
    dbm_modules = []
    fpath = os.path.dirname(os.path.realpath(__file__))
    for mfile in os.listdir(fpath):
        mod_name, file_ext = os.path.splitext(mfile)
        if mod_name.startswith(mbase):
            if file_ext.lower() == '.py':
                try:
                    dbm_modules.append('{}.{}'.format(base, mod_name))
                except Exception as exc:
                    logger.exception('Can not load source: %s: %s', exc.__class__.__name__, exc)
    return dbm_modules
