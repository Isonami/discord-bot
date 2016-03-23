# -*- coding: utf-8 -*-
command = r'h(?:elp)?'
helpd = 'h(elp) - show help'
description = '{cmd_start}%s' % helpd


async def main(self, message, *args, **kwargs):
    help_msg = self.ifnfo_line + '\nAvailable commands:\n'
    for mod_name, cmd in self.modules.cmds.items():
        desc = cmd.description
        if desc.find(helpd) != -1:
            help_msg += '    %s\n' % desc
    for mod_name, cmd in self.modules.cmds.items():
        desc = cmd.description
        if desc.find(helpd) == -1:
            if cmd.admin and not self.is_admin(message.author):
                continue
            if cmd.private and not message.channel.is_private:
                continue
            help_msg += '    %s\n' % desc
    await self.send(message.channel, help_msg)
