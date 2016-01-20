# -*- coding: utf-8 -*-
import logging
import string
import asyncio

logger = logging.getLogger(__name__)

local_db = {}
channels_db = {}
role_pattern = '@{name}_text'
perm_th_started = False


async def update_all_permisions(bot, server, db, localdb):
    all_roles = []
    for cid, channel_perm in db.items():
        all_roles.append(channel_perm['role'])
    for member in server.members:
        for role in all_roles:
            if role in member.roles:
                await delete_perm(bot, member, role)
    for cid, channel_perm in db.items():
        for member in channel_perm['voice'].voice_members:
            localdb[member.id] = channel_perm['voice'].id
            await add_perm(bot, member, channel_perm['role'])


def update_channels_db(server, db):
    voice_channels = {}
    for channel in server.channels:
        name = ''.join(filter(lambda x: x in string.printable, channel.name.lower())).strip()
        if str(channel.type) == 'voice':
            voice_channels[name] = channel
    for channel in server.channels:
        name = ''.join(filter(lambda x: x in string.printable, channel.name.lower())).strip()
        if str(channel.type) == 'text' and name in voice_channels:
            for role in server.roles:
                role_name = role_pattern.format(name=name)
                if role.name == role_name:
                    db[voice_channels[name].id] = {
                        'channel': channel,
                        'voice': voice_channels[name],
                        'role': role
                    }
                    break


async def delete_perm(bot, member, role):
    wait_ok.clear()
    await bot.remove_roles(member, *tuple(filter(lambda x: x.id == role.id, member.roles)))
    await asyncio.wait_for(wait_ok.wait(), 30)


async def add_perm(bot, member, role):
    wait_ok.clear()
    await bot.add_roles(member, role)
    await asyncio.wait_for(wait_ok.wait(), 30)


async def update_text_perm(bot, member_before, member):
    try:
        voice = member.voice_channel
        server_name = member.server.name
        if not voice and not member_before.voice_channel or voice == member_before.voice_channel:
            return
        if not voice:
            if member.id in local_db[server_name]:
                channel_perm = channels_db[server_name][local_db[server_name][member.id]]
                await delete_perm(bot, member, channel_perm['role'])
                local_db[server_name].pop(member.id)
                logger.debug('Delete role %s for user %s', channel_perm['role'].name, member.name)
        else:
            if member.id in local_db[server_name] and voice.id == local_db[server_name][member.id]:
                return
            elif member.id in local_db[server_name]:
                channel_perm = channels_db[server_name][local_db[server_name][member.id]]
                await delete_perm(bot, member, channel_perm['role'])
                logger.debug('Delete role %s for user %s', channel_perm['role'].name, member.name)
            if voice.id in channels_db[server_name]:
                await add_perm(bot, member, channels_db[server_name][voice.id]['role'])
                local_db[server_name][member.id] = voice.id
                logger.debug('Set role %s for user %s', channels_db[server_name][voice.id]['role'].name, member.name)
                return
            local_db[server_name].pop(member.id, 1)
    except Exception as exc:
        logger.exception('%s: %s' % (exc.__class__.__name__, exc))


async def update_perm_th(bot):
    while not bot.disconnect:
        items = await perm.get()
        await update_text_perm(bot, *items)


async def ready(bot):
    global perm
    perm = asyncio.Queue()
    global wait_ok
    wait_ok = asyncio.Event()
    if not perm_th_started:
        globals()['perm_th_started'] = True

        @bot.event
        async def on_member_update(*args, **kwargs):
            wait_ok.set()

        for server in bot.servers:
            local_db[server.name] = {}
            channels_db[server.name] = {}
            update_channels_db(server, channels_db[server.name])
            await update_all_permisions(bot, server, channels_db[server.name], local_db[server.name])

        bot.async_function(update_perm_th(bot))

        @bot.event
        async def on_voice_state_update(*args, **kwargs):
            await perm.put(args)
