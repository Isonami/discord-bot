import logging

command = r"twitch (?P<twitchcmd>(?:add)|(?:del)) " \
          r"(?:(?:https?://)?(?:www\.)?twitch\.tv/)?(?P<twitchname>[a-z0-9_]+)/?"
description = "{cmd_start}twitch add|del stream_name|stream_url - add/delete twitch on this channel for announce " \
              "(admin command)"
admin = True

logger = logging.getLogger(__name__)

sql_init = """
            CREATE TABLE IF NOT EXISTS Streams(Name TEXT, State INTEGER, Channels TEXT, Options TEXT);
"""
db_name = "twitch.db"


def init(bot):
    global sqlcon
    sqlcon = bot.sqlcon(sql_init, db_name)


def sd_select_stream(steam):
    row = sqlcon.request("SELECT * FROM Streams WHERE Name = ?;", steam, one=True)
    if not row or len(row) == 0:
        return {"Name": steam, "State": 1, "Options": None, "Channels": []}
    return {"Name": row[0], "State": row[1], "Options": row[3],
            "Channels": row[2].split(",") if len(row[2]) > 0 else []}


def sd_update_channels(stream, state, channels, options):
    return sqlcon.commit("INSERT OR REPLACE INTO Streams VALUES (?, ?, ?, ?);", stream, state,
                         ",".join(channels), options)


def main(self, message, *args, **kwargs):
    try:
        self.typing(message.channel)
        if message.channel.is_private:
            self.send(message.channel, "Can not add/delete stream on private channels.")
        else:
            cmd = kwargs.get("twitchcmd", None)
            name = kwargs.get("twitchname", None)
            if not cmd or not name:
                self.send(message.channel, "Can not get commad or stream name.")
                return
            stream = sd_select_stream(name)
            if cmd == "add":
                if message.channel.id in stream["Channels"]:
                    self.send(message.channel,
                              "Stream %s already add for announce on channel %s." % (stream["Name"],
                                                                                     message.channel.name))
                else:
                    stream["Channels"].append(message.channel.id)
                    ret = sd_update_channels(stream["Name"], stream["State"], stream["Channels"], stream["Options"])
                    if ret:
                        self.send(message.channel,
                                  "Stream %s added for announce on channel %s." % (stream["Name"],
                                                                                   message.channel.name))
                    else:
                        self.send(message.channel,
                                  "Internel error while editing stream %s. See the logs." % stream["Name"])
            elif cmd == "del":
                if message.channel.id in stream["Channels"]:
                    stream["Channels"].pop(message.channel.id, 1)
                    ret = sd_update_channels(stream["Name"], stream["State"], stream["Channels"], stream["Options"])
                    if ret:
                        self.send(message.channel,
                                  "Stream %s deleted from announce on channel %s." % (stream["Name"],
                                                                                      message.channel.name))
                    else:
                        self.send(message.channel,
                                  "Internel error while editing stream %s. See the logs." % stream["Name"])
                else:
                    self.send(message.channel,
                              "Stream %s is not announcing on channel %s." % (stream["Name"], message.channel.name))
    except Exception, exc:
        logger.error("%s: %s" % (exc.__class__.__name__, exc))
