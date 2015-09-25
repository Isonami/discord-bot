def main(self, message, *args, **kwargs):
    help_msg = self.ifnfo_line + "\nAvailable commands:\n"
    for desc in self.desc:
        help_msg += "    %s\n" % desc
    self.send(message.channel, help_msg)
