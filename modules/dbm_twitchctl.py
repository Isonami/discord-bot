# -*- coding: utf-8 -*-
import logging
import json

command = r'twitch (?:(?:(?P<twitchcmd>(?:add)|(?:del)) ' \
          r'(?:(?:https?://)?(?:www\.)?twitch\.tv/)?(?P<twitchname>[a-z0-9_]+)/?)|' \
          r'(?P<twitchlist>list))'
description = '{cmd_start}twitch add|del|list stream_name|stream_url - add/delete twitch on this channel to watch list ' \
              '(admin command)'
admin = True

logger = logging.getLogger(__name__)

sql_init = '''
  CREATE TABLE IF NOT EXISTS Streams(ID INTEGER PRIMARY KEY, Name TEXT, State INTEGER, Channels TEXT, Options TEXT);
'''
db_name = 'twitch.db'

STRINGS = [
    'Can not add/delete stream on private channels.',
    'Can not get commad or stream name.',
    'Stream {stream} in watch list already.',
    'Stream {stream} does not exist.',
    'Stream {stream} added to watch list.',
    'Internal error occured while adding stream {stream}.',
    'Stream {stream} removed from watch list.',
    'Internal error occured while removing stream {stream}.',
    'Stream {stream} is not in watch list for this channel.',
    'Twitch streams in watch list:'
]


async def init(bot):
    global sqlcon
    sqlcon = await bot.sqlcon(sql_init, db_name)
    enable = bot.config.get('twitch.enable', False)
    if not enable:
        raise EnvironmentError('Can not start control module without scheduler module!')
    global streams_url
    streams_url = bot.config.get('twitch.baseurl')
    global headers
    headers = bot.config.get('twitch.headers')


async def sd_select_stream(steam):
    row = await sqlcon.request('SELECT * FROM Streams WHERE Name = ?;', steam, one=True)
    if not row or len(row) == 0:
        return {'Name': steam, 'State': 1, 'Options': None, 'Channels': []}
    return {'Name': row[1], 'State': row[2], 'Options': row[4],
            'Channels': row[3].split(',') if len(row[3]) > 0 else []}


async def sd_select_streams_for_channel(channel):
    rows = await sqlcon.request('SELECT * FROM Streams;')
    out = []
    for row in rows:
        channels = row[3].split(',') if len(row[3]) > 0 else []
        if channel in channels:
            out.append({'Name': row[1], 'State': row[2], 'Options': row[4], 'Channels': channels})
    return out


async def sd_update_channels(stream, state, channels, options):
    return await sqlcon.commit('INSERT OR REPLACE INTO Streams VALUES ((SELECT ID FROM Streams WHERE Name '
                               '= ?), ?, ?, ?, ?);', stream, stream, state, ','.join(channels), options)


async def check_stream(http, stream):
    url = '/'.join([streams_url, http.url_escape(stream)])
    response = await http.get(url, headers=headers)
    if response.code == 0:
        logger.debug('Twitch response: %s', str(response))
        try:
            ret_obj = json.loads(str(response))
        except ValueError as e:
            logger.error('Can not parse json out: %s', e)
            return False
        if 'error' not in ret_obj:
            return True
    return False


async def main(self, message, *args, **kwargs):
    await self.typing(message.channel)
    if message.channel.is_private:
        await self.send(message.channel, STRINGS[0])
    else:
        if 'twitchlist' in kwargs:
            msg = STRINGS[9]
            for stream in await sd_select_streams_for_channel(message.channel.id):
                msg += '\n{}: {}'.format(stream['Name'], 'online' if stream['State'] == 0 else 'offline')
            await self.send(message.channel, msg)
            return
        cmd = kwargs.get('twitchcmd', None)
        name = kwargs.get('twitchname', None)
        if not cmd or not name:
            await self.send(message.channel, STRINGS[1])
            return
        cmd = cmd.lower()
        name = name.lower()
        stream = await sd_select_stream(name)
        if cmd == 'add':
            if message.channel.id in stream['Channels']:
                await self.send(message.channel, STRINGS[2].format(stream=stream['Name'], channel=message.channel.name))
            else:
                if not check_stream(self.http, stream['Name']):
                    await self.send(message.channel, STRINGS[3].format(stream=stream['Name']))
                    return
                stream['Channels'].append(message.channel.id)
                ret = await sd_update_channels(stream['Name'], stream['State'], stream['Channels'], stream['Options'])
                if ret:
                    await self.send(message.channel, STRINGS[4].format(stream=stream['Name'],
                                                                       channel=message.channel.name))
                else:
                    await self.send(message.channel, STRINGS[5].format(stream=stream['Name']))
        elif cmd == 'del':
            if message.channel.id in stream['Channels']:
                stream['Channels'].remove(message.channel.id)
                ret = await sd_update_channels(stream['Name'], stream['State'], stream['Channels'], stream['Options'])
                if ret:
                    await self.send(message.channel, STRINGS[6].format(stream=stream['Name'],
                                                                       channel=message.channel.name))
                else:
                    await self.send(message.channel, STRINGS[7].format(stream=stream['Name']))
            else:
                await self.send(message.channel, STRINGS[8].format(stream=stream['Name'], channel=message.channel.name))
