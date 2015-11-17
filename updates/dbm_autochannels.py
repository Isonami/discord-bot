import logging
import string

logger = logging.getLogger(__name__)

local_db = {}
channels_db = {}
role_pattern = "@{name}_text"


def update_all_permisions(bot, server, db, localdb):
    all_roles = []
    for cid, channel_perm in db.iteritems():
        all_roles.append(channel_perm["role"])
    for member in server.members:
        for role in all_roles:
            if role in member.roles:
                bot.client.remove_roles(member, role)
    for cid, channel_perm in db.iteritems():
        for member in channel_perm["voice"].voice_members:
            localdb[member.id] = channel_perm["voice"].id
            bot.client.add_roles(member, channel_perm["role"])


def update_channels_db(server, db):
    voice_channels = {}
    for channel in server.channels:
        name = filter(lambda x: x in string.printable, channel.name.lower()).strip()
        if channel.type == 'voice':
            voice_channels[name] = channel
    for channel in server.channels:
        name = filter(lambda x: x in string.printable, channel.name.lower()).strip()
        if channel.type == 'text' and name in voice_channels:
            for role in server.roles:
                role_name = role_pattern.format(name=name)
                if role.name == role_name:
                    db[voice_channels[name].id] = {
                        "channel": channel,
                        "voice": voice_channels[name],
                        "role": role
                    }
                    break


def update_text_perm(bot, member):
    voice = member.voice_channel
    server_name = member.server.name
    if not voice:
        if member.id in local_db[server_name]:
            channel_perm = channels_db[server_name][local_db[server_name][member.id]]
            bot.client.remove_roles(member, channel_perm["role"])
            local_db[server_name].pop(member.id)
            logger.debug("Delete role %s for user %s", channel_perm["role"].name, member.name)
    else:
        if member.id in local_db[server_name] and voice.id == local_db[server_name][member.id]:
            return
        elif member.id in local_db[server_name]:
            channel_perm = channels_db[server_name][local_db[server_name][member.id]]
            bot.client.remove_roles(member, channel_perm["role"])
        if voice.id in channels_db[server_name]:
            bot.client.add_roles(member, channels_db[server_name][voice.id]["role"])
            local_db[server_name][member.id] = voice.id
            logger.debug("Set role %s for user %s", channels_db[server_name][voice.id]["role"].name, member.name)


def main(bot):
    for server in bot.client.servers:
        local_db[server.name] = {}
        channels_db[server.name] = {}
        update_channels_db(server, channels_db[server.name])
        update_all_permisions(bot, server, channels_db[server.name], local_db[server.name])

    @bot.client.event
    def on_voice_state_update(arg):
        update_text_perm(bot, arg)


def init(bot):
    bot.on_ready.append(main)

