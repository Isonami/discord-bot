# -*- coding: utf-8 -*-
import logging

command = r'uid (?P<server_name>.+)'
description = '{cmd_start}uid <server_name> - show users ids on server'
admin = True
private = True

logger = logging.getLogger(__name__)
user_ans_template = 'User:{username} ID:{id}'


async def init(bot):
    pass


async def main(self, message, *args, **kwargs):
    server_name = kwargs['server_name']
    for server in self.client.servers:
        if server.name.lower() == server_name:
            ans = []
            for user in server.members:
                ans.append(user_ans_template.format(username=user.name.encode('utf-8'), id=user.id))
            if len(ans) > 0:
                await self.send(message.channel, '`{}`'.format('\n'.join(ans)))
            return
        await self.send(message.channel, 'Can not find server \'%s\' or not logged on it.' % server_name)
