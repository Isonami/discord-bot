# -*- coding: utf-8 -*-
command = r"h(?:elp)?"
helpd = "h(elp) - show help"
description = "{cmd_start}%s" % helpd


def main(self, message, *args, **kwargs):
    help_msg = self.ifnfo_line + "\nAvailable commands:\n"
    for mod_name, cmd in self.cmds.iteritems():
        desc = cmd["Description"]
        if desc.find(helpd) != -1:
            help_msg += "    %s\n" % desc
    for mod_name, cmd in self.cmds.iteritems():
        desc = cmd["Description"]
        if desc.find(helpd) == -1:
            if cmd["Admin"] and not self.is_admin(message.author):
                continue
            if cmd["Private"] and not message.channel.is_private:
                continue
            help_msg += "    %s\n" % desc
    self.send(message.channel, help_msg)
