# -*- coding: utf-8 -*-
import logging
import json
import re

logger = logging.getLogger(__name__)

base_url = 'https://api.twitch.tv/kraken'
github_url = 'https://raw.githubusercontent.com/justintv/Twitch-API/master/README.md'
streams_url = None
dealy = 600
api_version = "v3"

sql_init = '''
   CREATE TABLE IF NOT EXISTS Streams(ID INTEGER PRIMARY KEY, Name TEXT, State INTEGER, Channels TEXT, Options TEXT);
'''
db_name = 'twitch.db'

online_msg = 'Stream online: {name} | {title} | {game} | {url}'

channels = {}


async def init(bot):
    global online_msg
    online_msg = bot.config.get('twitch.message', online_msg)
    global dealy
    dealy = bot.config.get('twitch.dealy', dealy)
    global api_version
    api_version = bot.config.get('twitch.apiversion', api_version)
    ret_url = await get_stream_url(bot.http_client)
    if ret_url:
        global streams_url
        streams_url = ret_url
        global sqlcon
        sqlcon = await bot.sqlcon(sql_init, db_name)
        global job
        job = bot.scheduler.new(update, 'Twitch', bot.config.get('twitch.dealy', dealy), bot)
        job.start()
        global headers
        headers = {
            'Accept': 'application/vnd.twitchtv.{version}+json'.format(version=api_version)
        }
        bot.config.set('twitch.enable', True)
        bot.config.set('twitch.baseurl', streams_url)
        bot.config.set('twitch.headers', headers)


async def sd_select_state(steam):
    row = await sqlcon.request('SELECT State FROM Streams WHERE Name = ?;', steam, one=True)
    if not row or len(row) == 0:
        return -1
    return row[0]


async def sd_select_channels():
    rows = await sqlcon.request('SELECT * FROM Streams;')
    ret = []
    for row in rows:
        if len(row) == 5:
            ret.append({'Name': row[1], 'State': row[2], 'Options': row[4],
                        'Channels': row[3].split(',') if len(row[3]) > 0 else []})
    return ret


async def sd_set_state(stream, state):
    return await sqlcon.commit('UPDATE Streams SET State = ? WHERE Name = ?;', state, stream)


async def update(cuuid, bot):
    if not streams_url:
        return
    streams = await sd_select_channels()
    for one_stream in streams:
        if len(one_stream['Channels']) > 0:
            url = '/'.join([streams_url, bot.http_client.url_escape(one_stream['Name'])])
            response = await bot.http_client.get(url, headers=headers)
            if response.code == 0:
                logger.debug('[%s] Twitch response: %s', cuuid, str(response))
                try:
                    ret_obj = json.loads(str(response))
                except ValueError as e:
                    logger.error('[%s] Can not parse json out: %s', cuuid, e)
                    continue
                if 'error' in ret_obj:
                    logger.error('[%s] Twitch API error: %s', cuuid, ret_obj.get('message', ''))
                    continue
                stream = ret_obj.get('stream', None)
                if stream and 'channel' in stream:
                    if one_stream['State'] != 0:
                        logger.debug('[%s] Stream %s going ONLINE', cuuid, one_stream['Name'])
                        try:
                            await sd_set_state(one_stream['Name'], 0)
                            msg = online_msg.format(url=stream['channel'].get("url", ""),
                                                    name=stream['channel'].get('name', ''),
                                                    title=stream['channel'].get('status', ''),
                                                    game=stream['channel'].get('game', ''))
                        except Exception as exc:
                            logger.error('[%s] %s: %s', cuuid, exc.__class__.__name__, exc)
                            return
                        for channel_id in one_stream['Channels']:
                            logger.debug(channel_id)
                            try:
                                await bot.send(bot.get_channel(str(channel_id)), msg)
                            except Exception as exc:
                                logger.error('[%s] %s: %s', cuuid, exc.__class__.__name__, exc)
                else:
                    if one_stream['State'] != 1:
                        logger.debug('[%s] Stream %s going OFFLINE', cuuid, one_stream['Name'])
                        await sd_set_state(one_stream['Name'], 1)


async def get_stream_url(http):
    #twitch now requires client-id for base request...try to use github readme (sic!)
    #re.match(r'\| \[GET ([/a-zA-Z0-9_\-]+)\]\((?:[/a-zA-Z0-9_\-]+#get-streams\) \| Get stream object \|\)')
    #| [GET /streams](/v3_resources/streams.md#get-streams) | Get stream object |
    response = await http.get(github_url)
    if response.code == 0:
        for line in str(response).split('\n'):
            m = re.match(r'\| \[GET ([/a-zA-Z0-9_\-]+)\]\((?:[/a-zA-Z0-9_\-]+#get-streams\) \| Get stream object \|\)', line)
            if m:
                logger.error(m)
    return
    response = await http.get(base_url)
    if response.code == 0:
        ret_obj = json.loads(str(response))
        if '_links' in ret_obj and 'streams' in ret_obj['_links']:
            return ret_obj['_links']['streams']
