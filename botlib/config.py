# -*- coding: utf-8 -*-
import os.path as path
import logging
import json
from datetime import datetime
VERSION = '5.0.7'
PID = '/var/run/discord-bot/bot.pid'
CONFIG = {
    'discord': {
        'login': None,
        'password': None,
        'admins': [],
    },
    'exchangerates': {
        'url': 'https://openexchangerates.org/api/latest.json?app_id={appid}',
        'appid': None,
        'start_currency': 'RUB',
        'rates_any_list': ['USD', 'EUR', 'UAH'],
        'delay': 600,
    },
    'wolframalpha': {
        'url': 'http://api.wolframalpha.com/v2/query?input={input}&appid={appid}',
        'appid': None,
        'delay': 60,
        'static_url': None,
    },
    'restart': {
        'command': None
    }
}


logger = logging.getLogger(__name__)
config_file_name = 'settings.json'


class Config(object):
    def __init__(self, conf_file=config_file_name, nullconfig=False):
        if nullconfig:
            return
        main_dir = path.join(path.dirname(path.realpath(__file__)), path.pardir)
        json_file = path.join(main_dir, conf_file)
        if path.exists(json_file):
            try:
                with open(json_file) as json_config:
                    config_data = json.load(json_config)
            except IOError as e:
                logger.error('Can not open config file: %s', str(e))
            except ValueError as e:
                logger.error('Can not load json config file: %s', str(e))

        def split_path(config_var, strpath):
            for key, value in config_var.items():
                if strpath:
                    new_strpath = '.'.join([strpath, key])
                else:
                    new_strpath = key
                if type(value) is dict:
                    split_path(value, new_strpath)
                else:
                    self.set(new_strpath, value)
        if 'config_data' in locals():
            split_path(locals()['config_data'], None)
        self.set('main.dir', main_dir)
        self.set('main.start_time', datetime.now())
        self.set('version', VERSION)

    def set(self, var, value):
        var = str(var)
        return self.__getset('set', var.lower(), value)

    def get(self, var, value=None):
        var = str(var)
        return self.__getset('get', var.lower(), value)

    @staticmethod
    def __getset(action_type, var, value):
        if not var or type(var) is not str or len(var) < 1:
            logger.error('Can not %s config varible, argument must be a string with length > 1', action_type)
            return
        var_path = var.split('.')
        length = len(var_path)
        config_path = CONFIG
        for key, var_name in enumerate(var_path):
            if key + 1 < length:
                if var_name in config_path:
                    if type(config_path[var_name]) is not dict:
                        logger.error('Varible %s must be a dict, but %s found', '.'.join(var_path[:key + 1]),
                                     config_path[var_name].__class__.__name__)
                        return
                else:
                    if action_type == 'set':
                        config_path[var_name] = {}
                    elif action_type == 'get' and value is not None:
                        config_path[var_name] = {}
                    else:
                        return None
                config_path = config_path[var_name]
            else:
                if action_type == 'set':
                    config_path[var_name] = value
                elif var_name not in config_path and action_type == 'get' and value is None:
                    return None
                elif var_name not in config_path and action_type == 'get':
                    config_path[var_name] = value
                elif var_name in config_path and action_type == 'get' and config_path[var_name] is None and value:
                    return value
                return config_path[var_name]
