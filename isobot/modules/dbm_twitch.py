# -*- coding: utf-8 -*-
import logging
import re
import asyncio
from datetime import datetime


logger = logging.getLogger(__name__)

base_url = 'https://api.twitch.tv/helix'


class ApiUrl(object):
    def __init__(self, twitch_url):
        self.twitch_url = twitch_url

    def __getattr__(self, item):
        return '{}{}'.format(self.twitch_url, item)


def setup(bot):
    """
    :type bot: isobot.Bot
    """
    config = bot.config('twitch')
    clientid = config.get('clientid')
    twitch_url = config.get('base', base_url)
    if not twitch_url.endswith('/'):
        twitch_url += '/'
    api_url = ApiUrl(twitch_url)
    online_color = bot.Colour.green()
    url_parser = re.compile(r'(?:(?:https?://)?(?:www\.)?twitch\.tv/)?(?P<twitchname>[a-z0-9_]+)/?', re.IGNORECASE)

    if not clientid:
        logger.error('Can not load twitch module ({}), twitch client id must be provided!'.format(__name__))
        bot.unload_extension(__name__)
        return

    headers = {
        'Client-ID': clientid
    }

    @bot.model()
    class Twitch_Streams(bot.BaseModel):
        login = bot.m.CharField()
        display_name = bot.m.CharField()
        user_id = bot.m.CharField(unique=True)
        state = bot.m.IntegerField()
        enabled = bot.m.BooleanField(null=True, default=False)

    @bot.model()
    class Twitch_Streams_Enabled(bot.BaseModel):
        stream = bot.m.ForeignKeyField(Twitch_Streams, related_name='channels')
        channel_id = bot.m.BigIntegerField()

    async def get_stream_status(user_ids, session):
        if not isinstance(user_ids, list):
            user_ids = [user_ids]
        params = [('user_id', user_id) for user_id in user_ids]
        async with session.get(api_url.streams, headers=headers, params=params) as resp:
            if resp.status != 200:
                return
            data = await resp.json()
            return data['data']

    games = {}

    async def get_game(game_id, session):
        if game_id in games:
            return games[game_id]
        async with session.get(api_url.games, headers=headers, params=[('id', game_id)]) as resp:
            if resp.status != 200:
                logger.error('Remote API error!')
            else:
                data = await resp.json()
                if len(data['data']):
                    games[game_id] = data['data'][0]
                    return games[game_id]
            return {}

    async def update_stresm(stream, data):
        if stream.login != data['login']:
            stream.login = data['login']
        if stream.display_name != data['display_name']:
            stream.display_name = data['display_name']
        if stream.dirty_fields:
            await bot.db.update(stream, only=stream.dirty_fields)

    @bot.group(invoke_without_command=True)
    @bot.commands.guild_only()
    async def twitch(ctx: bot.Context):
        """Twitch stream announcer"""
        await bot.show_help(ctx, 'twitch')

    twitch.error(bot.default_error)

    @twitch.command()
    @bot.commands.guild_only()
    @bot.is_admin()
    async def add(ctx: bot.Context, url: str):
        """Add Twitch stream annoncer"""
        if url.startswith('<') and url.endswith('>'):
            url = url[1:-1]
        match = url_parser.match(url)
        if not match:
            await ctx.send('{} is not a valid channel name or twitch channel url, '
                           'try `https://www.twitch.tv/channel_name`'.format(url))
            return
        login = match.groupdict()['twitchname']
        async with bot.ClientSession() as session:
            async with session.get(api_url.users, headers=headers, params=[('login', login)]) as resp:
                if resp.status != 200:
                    await ctx.send('Remote API error!')
                    return
                data = await resp.json()
                data = data['data']
                if len(data) == 0:
                    await ctx.send('Stream with name `{}` not found.'.format(login))
                    return
                elif len(data) > 1:
                    logins = [user['login'] for user in data]
                    await ctx.send('More than one user found: '.format(', '.join(logins)))
                    return
                data = data[0]
                try:
                    stream = await bot.db.get(Twitch_Streams, user_id=data['id'])
                    await update_stresm(stream, data)
                except Twitch_Streams.DoesNotExist:
                    state = await get_stream_status(data['id'], session)
                    if state is None:
                        await ctx.send('Remote API error!')
                        return
                    stream = await bot.db.create(Twitch_Streams, user_id=data['id'], login=data['login'],
                                                 state=1 if state else 0, display_name=data['display_name'])
                try:
                    await bot.db.get(Twitch_Streams_Enabled, stream=stream, channel_id=ctx.channel.id)
                    await ctx.send('Announcer for <https://www.twitch.tv/{}> '
                                   'has already been enabled here.'.format(stream.login))
                except Twitch_Streams_Enabled.DoesNotExist:
                    await bot.db.create(Twitch_Streams_Enabled, stream=stream, channel_id=ctx.channel.id)
                    if not stream.enabled:
                        stream.enabled = True
                        state = await get_stream_status(stream.user_id, session)
                        if state is None:
                            await ctx.send('Remote API error!')
                            return
                        stream.state = 1 if state else 0
                        await bot.db.update(stream, only=stream.dirty_fields)
                    await ctx.send('It will be announced here '
                                   'when <https://www.twitch.tv/{}> goes live.'.format(stream.login))

    add.error(bot.default_error)

    @twitch.command(name='del')
    @bot.commands.guild_only()
    @bot.is_admin()
    async def delete(ctx: bot.Context, url: str):
        """Delete Twitch stream annoncer"""
        if url.startswith('<') and url.endswith('>'):
            url = url[1:-1]
        match = url_parser.match(url)
        if not match:
            await ctx.send('{} is not a valid channel name or twitch channel url, '
                           'try `https://www.twitch.tv/channel_name`'.format(url))
            return
        login = match.groupdict()['twitchname']
        async with bot.ClientSession() as session:
            async with session.get(api_url.users, headers=headers, params=[('login', login)]) as resp:
                if resp.status != 200:
                    await ctx.send('Remote API error!')
                    return
                data = await resp.json()
                data = data['data']
                if len(data) == 0:
                    await ctx.send('Stream with name `{}` not found.'.format(login))
                    return
                elif len(data) > 1:
                    logins = [user['login'] for user in data]
                    await ctx.send('More than one user found: '.format(', '.join(logins)))
                    return
                data = data[0]
                try:
                    stream = await bot.db.get(Twitch_Streams, user_id=data['id'])
                    await update_stresm(stream, data)
                except Twitch_Streams.DoesNotExist:
                    await ctx.send('Stream annoncer for '
                                   '<https://www.twitch.tv/{}> is not enabled here.'.format(data['login']))
                    return
                try:
                    channel = await bot.db.get(Twitch_Streams_Enabled, stream=stream, channel_id=ctx.channel.id)
                    await bot.db.delete(channel)
                    count = await bot.db.count(stream.channels)
                    if count == 0:
                        stream.enabled = False
                        await bot.db.update(stream, only=stream.dirty_fields)
                    await ctx.send('Announcer for <https://www.twitch.tv/{}> has been deleted.'.format(stream.login))
                except Twitch_Streams_Enabled.DoesNotExist:
                    await ctx.send('Stream annoncer for '
                                   '<https://www.twitch.tv/{}> is not enabled here.'.format(stream.login))

    delete.error(bot.default_error)

    @twitch.command(name='list')
    @bot.commands.guild_only()
    async def list_annoncer(ctx: bot.Context):
        """List Twitch stream annoncers"""
        streams = await bot.db.execute(Twitch_Streams.select().join(Twitch_Streams_Enabled)
                                       .where(Twitch_Streams_Enabled.channel_id == ctx.channel.id))
        stream_list = ['\t - <https://www.twitch.tv/{}>'.format(stream.login) for stream in streams]
        if stream_list:
            await ctx.send('Annoncers enabled here:\n{}'.format('\n'.join(stream_list)))
        else:
            await ctx.send('No annoncers on this channel.')

    list_annoncer.error(bot.default_error)

    async def stream_process(stream, dict_data, session):
        if stream.user_id in dict_data:
            state = 1
            data = dict_data[stream.user_id]
        else:
            state = 0
            data = {}
        if stream.state != state:
            stream.state = state
            await bot.db.update(stream, only=stream.dirty_fields)
            if state == 1:
                channels = await bot.db.execute(stream.channels)
                user_data = {}
                if not len(channels):
                    stream.enabled = False
                    await bot.db.update(stream)
                    return
                async with session.get(api_url.users, headers=headers, params=[('id', stream.user_id)]) as resp:
                    if resp.status != 200:
                        print(await resp.text())
                        logger.error('Remote API error!')
                    else:
                        resp_data = await resp.json()
                        resp_data = resp_data['data']
                        if len(resp_data):
                            user_data = resp_data[0]
                            await update_stresm(stream, user_data)
                url = 'https://www.twitch.tv/{}'.format(stream.login)
                game = await get_game(data['game_id'], session)
                embed = bot.Embed(title=url, description=data.get('title', 'No title'))
                embed.set_thumbnail(
                    url='{}?{}'.format(data.get('thumbnail_url', '').format(width=80, height=45),
                                       int(datetime.utcnow().timestamp())))
                if user_data.get('profile_image_url', None):
                    embed.set_author(name='Stream online: {}'.format(stream.display_name), url=url,
                                     icon_url=user_data['profile_image_url'])
                else:
                    embed.set_author(name='Stream online: {}'.format(stream.display_name))
                embed.color = online_color
                if game.get('name', None):
                    embed.set_footer(text=game['name'], icon_url=game['box_art_url'].format(width=57, height=76))
                senders = []
                for channel in channels:
                    text_channel = bot.get_channel(channel.channel_id)
                    if not text_channel:
                        logger.error('Channel with id {} not found.'.format(channel.channel_id))
                        continue
                    senders.append(asyncio.ensure_future(text_channel.send(embed=embed)))
                await asyncio.gather(*senders)
                for sender in senders:
                    if sender.exception():
                        raise sender.exception()

    @bot.crontab('*/2 * * * *')
    async def update_streams():
        streams = await bot.db.execute(Twitch_Streams.select().where(Twitch_Streams.enabled))
        user_ids = []
        stream_list = []
        for stream in streams:
            stream_list.append(stream)
            user_ids.append(stream.user_id)
        if not stream_list:
            return
        async with bot.ClientSession() as session:
            live_data = await get_stream_status(user_ids, session)
            if live_data is None:
                logger.error('Remote API error!')
            dict_data = {}
            for live in live_data:
                dict_data[live['user_id']] = live
            for stream in stream_list:
                await stream_process(stream, dict_data, session)

