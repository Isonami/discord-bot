command = r"h(?:elp)?"
helpd = "h(elp) - show help"
description = "{cmd_start}%s" % helpd


def main(self, message, *args, **kwargs):
    help_msg = self.ifnfo_line + "\nAvailable commands:\n"
    for desc in self.desc:
        if desc.find(helpd) != -1:
            help_msg += "    %s\n" % desc
    for desc in self.desc:
        if desc.find(helpd) == -1:
            help_msg += "    %s\n" % desc
    self.send(message.channel, help_msg)
