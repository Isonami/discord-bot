# -*- coding: utf-8 -*-
import logging
import json
import re
from datetime import datetime

command = r'w[rz](?P<weather_cities>(?: [a-z0-9]+(?:(?:\([a-z]{2,3}\))|(?:,[a-z]{1,3}))?)+)?'
description = '{cmd_start}wr|wz city|city(country short name)|city id - show weather for one city or more'

weather_format = '{city} {country} - {main[temp]:.1f}°C {weather[main]} {cached:cached at %d.%M %H:%m}'
weather_url = 'http://api.openweathermap.org/data/2.5/'
nocache = False

countryre = re.compile(r'\(([a-z]{1,3})\)')
cachedre = re.compile(r' \{cached(:?:[^}]+)?}')

logger = logging.getLogger(__name__)

sql_init = '''
   CREATE TABLE IF NOT EXISTS Cities(ID INTEGER PRIMARY KEY, Name TEXT, Country TEXT, Code TEXT);
   CREATE TABLE IF NOT EXISTS Useroptions(ID INTEGER PRIMARY KEY, Name TEXT, Option TEXT);
'''
db_name = 'cities.db'

async def init(bot):
    global weather_url
    weather_url = bot.config.get('openweather.url', weather_url)
    appid = bot.config.get('openweather.appid', None)
    if not appid:
        raise ValueError('\'appid\' required!')
    global weather_format
    weather_format = bot.config.get('openweather.format', weather_format)
    global nocache
    nocache = bot.config.get('openweather.nocache', nocache)
    global sqlcon
    sqlcon = await bot.sqlcon(sql_init, db_name)
    global weather
    weather = Weather(bot, appid)
    bot.config.set('openweather.weather', weather)


async def db_get_id(city):
    splitted = city.split(',')
    if len(splitted) > 1:
        ret = await sqlcon.request('SELECT Code FROM Cities WHERE Name = ? AND Country = ?;', splitted[0], splitted[1])
    else:
        ret = await sqlcon.request('SELECT Code FROM Cities WHERE Name = ?;', splitted[0])
    ans = []
    if ret:
        for row in ret:
            ans.append(row[0])
    return ans


async def db_update_id(name, country, code):
    name = name.lower()
    country = country.lower()
    code = str(code)
    return await sqlcon.commit('INSERT OR REPLACE INTO Cities VALUES ((SELECT ID FROM Cities WHERE Name = ?'
                               ' AND Country = ?), ?, ?, ?)', name, country, name, country, code)

async def db_get_user_option(userid):
    userid = str(userid)
    row = await sqlcon.request('SELECT Option FROM Useroptions WHERE Name = ?;', userid, one=True)
    if row:
        print(row)
        return row[0].split(',')


async def db_set_user_option(userid, option):
    userid = str(userid)
    option = ','.join(option)
    return await sqlcon.commit('INSERT OR REPLACE INTO Useroptions VALUES ((SELECT ID FROM Useroptions WHERE Name = ?),'
                               ' ?, ?)', userid, userid, option)


class Result(object):
    __slots__ = ['_cities', '_countryre']

    def __init__(self):
        self._cities = {}
        self._countryre = countryre

    def add(self, weath):
        for one_weather in weath:
            self._cities[one_weather['id']] = one_weather

    def get(self, city_id=None, city_name=None):
        if not city_id and not city_name:
            raise ValueError('neither city_id nor city_name specified')
        ret = []
        if city_id:
            city_id = int(city_id)
            if city_id in self._cities:
                ret = [self._cities[int(city_id)]]
        elif city_name:
            city_name = city_name.lower()
            self._countryre.sub(lambda m: m.group(1), city_name)
            splited = city_name.split(',')
            city_name = splited[0]
            if len(splited) > 1:
                country = splited[1]
            else:
                country = None
            for code, one_weather in self._cities.items():
                if one_weather['name'].lower() == city_name and \
                        (not country or one_weather['country'].lower() == country):
                    ret.append(one_weather)
        return ret

    def __call__(self):
        ret = []
        for code, one_weather in self._cities.items():
            ret.append(one_weather)
        return ret


class Weather(object):
    def __init__(self, bot, appid):
        self._url_one = '{}weather'.format(bot.config.get('openweather.url', weather_url))
        self._url_group = '{}group'.format(bot.config.get('openweather.url', weather_url))
        self._default = bot.config.get('openweather.default')
        self._appid = appid
        self._cache = {}
        self._http = bot.http
        self._idre = re.compile(r'[0-9]+')
        self._namere = re.compile(r'[a-z0-9]+(?:(?:\([a-z]{1,3}\))|(?:,[a-z]{1,3}))?')
        self._countryre = countryre

    @staticmethod
    def _parse(to_parse):
        results = json.loads(to_parse)
        ret = []
        if 'cod' in results and results['cod'] != 200:
            return ret
        if 'cnt' in results:
            weath = results['list']
        else:
            weath = [results]
        for one_weather in weath:
            ret.append({
                'name': one_weather['name'],
                'city': one_weather['name'],
                'id': one_weather['id'],
                'country': one_weather['sys']['country'],
                'weather': one_weather['weather'][0],
                'main': one_weather['main'],
                'wind': one_weather['wind']
            })
        return ret

    def _append_cache(self, weath):
        for one_weather in weath:
            to_cache = one_weather.copy()
            to_cache['cached'] = datetime.now()
            self._cache[one_weather['id']] = to_cache

    def _get_cache(self, ids):
        ret = []
        for one_id in ids:
            one_id = int(one_id)
            if one_id in self._cache:
                ret.append(self._cache[one_id])
        return ret

    async def _get_by_name(self, city):
        ret = []
        res = await self._http.get(self._url_one, payload={'q': city, 'appid': self._appid, 'units': 'metric'})
        if res.code == 0:
            parsed = self._parse(str(res))
            if len(parsed) > 0:
                ret.extend(parsed)
                self._append_cache(parsed)
                for one in parsed:
                    await db_update_id(one['name'], one['country'], one['id'])
        return ret

    async def _get_by_ids(self, ids):
        ret = []
        if len(ids) == 0:
            return ret
        res = await self._http.get('{}?{}'.format(self._url_group, self._http.urlencode({'id': ','.join(ids),
                                                                                         'appid': self._appid,
                                                                                         'units': 'metric'}, safe=',')))
        if res.code == 0:
            parsed = self._parse(str(res))
            if len(parsed) > 0:
                ret.extend(parsed)
                self._append_cache(parsed)
                for one in parsed:
                    await db_update_id(one['name'], one['country'], one['id'])
        else:
            ret.extend(self._get_cache(ids))
        return ret

    async def _get_weather(self, cities):
        ids = []
        ret = []
        for city in cities:
            if city['id']:
                ids.append(city['id'])
            else:
                have_id = await db_get_id(city['name'])
                if len(have_id) > 0:
                    for one_id in have_id:
                        ids.append(one_id)
                else:
                    ret.extend(await self._get_by_name(city['name']))
        ret.extend(await self._get_by_ids(ids))
        return ret

    async def __call__(self, *args):
        cities_strings = []
        cities = []
        for arg in args:
            if isinstance(arg, list):
                for string in arg:
                    if isinstance(string, str):
                        cities_strings.append(string)
            elif isinstance(arg, str):
                cities_strings.append(arg)
        if len(cities_strings) < 1:
            return None
        for string in cities_strings:
            for city in string.split():
                city = city.lower()
                if self._idre.match(city):
                    cities.append({'id': city, 'name': None})
                elif self._namere.match(city):
                    city = self._countryre.sub(lambda m: m.group(1), city)
                    cities.append({'id': None, 'name': city})
        if len(cities) < 1:
            return None
        result = Result()
        result.add(await self._get_weather(cities))
        return result

    async def default(self):
        if self._default:
            return self.__call__(self._default)


async def main(self, message, *args, **kwargs):
    auto = False
    if 'weather_cities' not in kwargs:
        options = await db_get_user_option(message.author.id)
        if options:
            res = await weather(options)
        else:
            res = await weather.default()
            auto = True
    else:
        res = await weather(kwargs['weather_cities'])
    if not res:
        await self.send(message.channel, 'Cities not found or not set.')
        return
    if not auto:
        await db_set_user_option(message.author.id, [str(weth['id']) for weth in res()])
    ans = []
    for one_weather in res():
        fmt = weather_format
        if 'cached' not in one_weather or nocache:
            fmt = cachedre.sub('', fmt)
        ans.append(fmt.format(**one_weather))
    await self.send(message.channel, ', '.join(ans))
