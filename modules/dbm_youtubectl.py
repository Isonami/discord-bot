import logging

command = r"youtube (?P<youtubecmd>(?:add)|(?:del)) " \
          r"(?:https?://)?(?:www\.)?youtube\.com/(?P<youtubetype>(?:user)|(?:channel))/(?P<youtubename>[a-z0-9_]+)/?"
description = "{cmd_start}youtube add|del youtube_channel_url - add/delete youtube channel on this discord channel " \
              "to watch list (admin command)"
admin = True

logger = logging.getLogger(__name__)

types = {
    "user": "user",
    "channel": "channel_id"
}


STRINGS = [
    "Can not add/delete youtube channel on private discord channels.",
    "Can not get commad or youtube channel name.",
    "Youtube channel {ychannel} in watch list already.",
    "Youtube channel {ychannel} does not exist.",
    "Youtube channel {ychannel} added to watch list.",
    "Internal error occured while adding youtube channel {ychannel}.",
    "Youtube channel {ychannel} removed from watch list.",
    "Internal error occured while removing youtube channel {ychannel}.",
    "Youtube channel {ychannel} is not in watch list for this discord channel."
]


def init(bot):
    enable = bot.config.get("youtube.enable", False)
    if not enable:
        raise EnvironmentError("Can not start control module without scheduler module!")
    global youtube_module
    youtube_module = bot.config.get("youtube.module")


def main(self, message, *args, **kwargs):
    try:
        self.typing(message.channel)
        if message.channel.is_private:
            self.send(message.channel, STRINGS[0])
        else:
            cmd = kwargs.get("youtubecmd", None)
            youtype = kwargs.get("youtubetype", None)
            name = kwargs.get("youtubename", None)
            if not cmd or not name or not youtype and youtype not in types:
                self.send(message.channel, STRINGS[1])
                return
            you_chann = youtube_module["sd_select_channel"](types[str(youtype)], name)
            if cmd == "add":
                if message.channel.id in you_chann["Channels"]:
                    self.send(message.channel, STRINGS[2].format(ychannel=you_chann["Name"],
                                                                 channel=message.channel.name))
                else:
                    video = youtube_module["get_last_video"](self.http, you_chann["Name"], you_chann["Type"])
                    if not video:
                        self.send(message.channel, STRINGS[3].format(ychannel=you_chann["Name"]))
                        return
                    you_chann["Channels"].append(message.channel.id)
                    you_chann["Lastid"] = you_chann["Lastid"] if you_chann["Lastid"] else video["id"]
                    you_chann["Lastdate"] = you_chann["Lastdate"] if you_chann["Lastdate"] else video["date"]
                    ret = youtube_module["sd_update_channels"](you_chann["Name"], you_chann["Channels"],
                                                               you_chann["Type"], you_chann["Lastid"],
                                                               you_chann["Lastdate"])
                    if ret:
                        self.send(message.channel, STRINGS[4].format(ychannel=you_chann["Name"],
                                                                     channel=message.channel.name))
                    else:
                        self.send(message.channel, STRINGS[5].format(ychannel=you_chann["Name"]))
            elif cmd == "del":
                if message.channel.id in you_chann["Channels"]:
                    you_chann["Channels"].remove(message.channel.id)
                    ret = youtube_module["sd_update_channels"](you_chann["Name"], you_chann["Channels"],
                                                               you_chann["Type"], you_chann["Lastid"],
                                                               you_chann["Lastdate"])
                    if ret:
                        self.send(message.channel, STRINGS[6].format(ychannel=you_chann["Name"],
                                                                     channel=message.channel.name))
                    else:
                        self.send(message.channel, STRINGS[7].format(ychannel=you_chann["Name"]))
                else:
                    self.send(message.channel, STRINGS[8].format(ychannel=you_chann["Name"],
                                                                 channel=message.channel.name))
    except Exception, exc:
        logger.error("%s: %s" % (exc.__class__.__name__, exc))