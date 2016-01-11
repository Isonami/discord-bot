# -*- coding: utf-8 -*-
import logging
from tornado.escape import url_escape
import json

command = r"twitch (?P<twitchcmd>(?:add)|(?:del)) " \
          r"(?:(?:https?://)?(?:www\.)?twitch\.tv/)?(?P<twitchname>[a-z0-9_]+)/?"
description = "{cmd_start}twitch add|del stream_name|stream_url - add/delete twitch on this channel to watch list " \
              "(admin command)"
admin = True

logger = logging.getLogger(__name__)

sql_init = """
  CREATE TABLE IF NOT EXISTS Streams(ID INTEGER PRIMARY KEY, Name TEXT, State INTEGER, Channels TEXT, Options TEXT);
"""
db_name = "twitch.db"

STRINGS = [
    "Can not add/delete stream on private channels.",
    "Can not get commad or stream name.",
    "Stream {stream} in watch list already.",
    "Stream {stream} does not exist.",
    "Stream {stream} added to watch list.",
    "Internal error occured while adding stream {stream}.",
    "Stream {stream} removed from watch list.",
    "Internal error occured while removing stream {stream}.",
    "Stream {stream} is not in watch list for this channel."
]


def init(bot):
    global sqlcon
    sqlcon = bot.sqlcon(sql_init, db_name)
    enable = bot.config.get("twitch.enable", False)
    if not enable:
        raise EnvironmentError("Can not start control module without scheduler module!")
    global streams_url
    streams_url = bot.config.get("twitch.baseurl")
    global headers
    headers = bot.config.get("twitch.headers")


def sd_select_stream(steam):
    row = sqlcon.request("SELECT * FROM Streams WHERE Name = ?;", steam, one=True)
    if not row or len(row) == 0:
        return {"Name": steam, "State": 1, "Options": None, "Channels": []}
    return {"Name": row[1], "State": row[2], "Options": row[4],
            "Channels": row[3].split(",") if len(row[3]) > 0 else []}


def sd_update_channels(stream, state, channels, options):
    return sqlcon.commit("INSERT OR REPLACE INTO Streams VALUES ((SELECT ID FROM Streams WHERE Name = ?), ?, ?, ?, ?);",
                         stream, stream, state, ",".join(channels), options)


def check_stream(http, stream):
    url = "/".join([streams_url, url_escape(stream)])
    code, response = http(url, headers=headers)
    if code == 0:
        logger.debug("Twitch response: %s", response.body)
        try:
            ret_obj = json.loads(response.body)
        except ValueError as e:
            logger.error("Can not parse json out: %s", unicode(e))
            return False
        if "error" not in ret_obj:
            return True
    return False


def main(self, message, *args, **kwargs):
    try:
        self.typing(message.channel)
        if message.channel.is_private:
            self.send(message.channel, STRINGS[0])
        else:
            cmd = kwargs.get("twitchcmd", None)
            name = kwargs.get("twitchname", None)
            if not cmd or not name:
                self.send(message.channel, STRINGS[1])
                return
            cmd = cmd.lower()
            name = name.lower()
            stream = sd_select_stream(name)
            if cmd == "add":
                if message.channel.id in stream["Channels"]:
                    self.send(message.channel, STRINGS[2].format(stream=stream["Name"], channel=message.channel.name))
                else:
                    if not check_stream(self.http, stream["Name"]):
                        self.send(message.channel, STRINGS[3].format(stream=stream["Name"]))
                        return
                    stream["Channels"].append(message.channel.id)
                    ret = sd_update_channels(stream["Name"], stream["State"], stream["Channels"], stream["Options"])
                    if ret:
                        self.send(message.channel, STRINGS[4].format(stream=stream["Name"],
                                                                     channel=message.channel.name))
                    else:
                        self.send(message.channel, STRINGS[5].format(stream=stream["Name"]))
            elif cmd == "del":
                if message.channel.id in stream["Channels"]:
                    stream["Channels"].remove(message.channel.id)
                    ret = sd_update_channels(stream["Name"], stream["State"], stream["Channels"], stream["Options"])
                    if ret:
                        self.send(message.channel, STRINGS[6].format(stream=stream["Name"],
                                                                     channel=message.channel.name))
                    else:
                        self.send(message.channel, STRINGS[7].format(stream=stream["Name"]))
                else:
                    self.send(message.channel, STRINGS[8].format(stream=stream["Name"], channel=message.channel.name))
    except Exception, exc:
        logger.error("%s: %s" % (exc.__class__.__name__, exc))
