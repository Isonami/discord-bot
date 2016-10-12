# -*- coding: utf-8 -*-
import os.path as path
import logging
import yaml
CONFIG = {
    'token': '',
    'dsn': '',
}


logger = logging.getLogger(__name__)


class BaseConfig(object):
    def __init__(self, prefix):
        if prefix:
            self.prefix = '{}.'.format(prefix)
        else:
            self.prefix = ''

    def get(self, var, value=None):
        var = var
        return self._getset("get", self.prefix + var.lower(), value)

    @staticmethod
    def _getset(action_type, var, value):
        if not var or type(var) is not str or len(var) < 1:
            logger.error("Can not %s config varible, argument must be a string with length > 1", action_type)
            return
        var_path = var.split(".")
        length = len(var_path)
        config_path = CONFIG
        for key, var_name in enumerate(var_path):
            if key + 1 < length:
                if var_name in config_path:
                    if type(config_path[var_name]) is not dict:
                        logger.error("Varible %s must be a dict, but %s found", ".".join(var_path[:key + 1]),
                                     config_path[var_name].__class__.__name__)
                        return
                else:
                    if action_type == "set":
                        config_path[var_name] = {}
                    elif value is not None:
                        return value
                    else:
                        return None
                config_path = config_path[var_name]
            else:
                if action_type == "set":
                    config_path[var_name] = value
                elif var_name not in config_path and action_type == "get":
                    return value
                elif var_name in config_path and action_type == "get" and config_path[var_name] is None:
                    return value
                return config_path[var_name]


class Config(BaseConfig):
    def __init__(self, file_path):
        super().__init__('')
        self.file_path = file_path
        self._load()

    def _load(self):
        if path.exists(self.file_path):
            try:
                with open(self.file_path) as yaml_config:
                    config_data = yaml.load(yaml_config)
            except IOError as e:
                logger.error('Can not open config file: %s', str(e))
            except ValueError as e:
                logger.error('Can not load yaml config file: %s', str(e))
        else:
            logger.warning('Config file {} not found!'.format(self.file_path))

        def split_path(config_var, strpath):
            for key, value in config_var.items():
                if strpath:
                    new_strpath = ".".join([strpath, key])
                else:
                    new_strpath = key
                if type(value) is dict:
                    split_path(value, new_strpath)
                else:
                    self._set(new_strpath, value)
        if "config_data" in locals():
            split_path(locals()["config_data"], None)

    def _set(self, var, value):
        var = var
        return self._getset("set", self.prefix + var.lower(), value)


def default_config():
    return yaml.dump(CONFIG)
