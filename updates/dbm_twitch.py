import logging
import json
from tornado.escape import url_escape

logger = logging.getLogger(__name__)

base_url = "https://api.twitch.tv/kraken"
streams_url = None
dealy = 600
api_version = "v3"

sql_init = """
   CREATE TABLE IF NOT EXISTS Streams(ID INTEGER PRIMARY KEY, Name TEXT, State INTEGER, Channels TEXT, Options TEXT);
"""
db_name = "twitch.db"

online_msg = "Stream online: {name} | {title} | {game} | {url}"

channels = {}


def init(bot):
    global online_msg
    online_msg = bot.config.get("twitch.message", online_msg)
    global dealy
    dealy = bot.config.get("twitch.dealy", dealy)
    global api_version
    api_version = bot.config.get("twitch.apiversion", api_version)
    ret_url = get_stream_url(bot.http)
    if ret_url:
        global streams_url
        streams_url = ret_url
        global sqlcon
        sqlcon = bot.sqlcon(sql_init, db_name)
        bot.scheduler.append(update, "Twitch", bot.config.get("twitch.dealy", dealy), bot)
        global headers
        headers = {
            "Accept": "application/vnd.twitchtv.{version}+json".format(version=api_version)
        }
        bot.config.set("twitch.enable", True)
        bot.config.set("twitch.baseurl", streams_url)
        bot.config.set("twitch.headers", headers)


def sd_select_state(steam):
    row = sqlcon.request("SELECT State FROM Streams WHERE Name = ?;", steam, one=True)
    if not row or len(row) == 0:
        return -1
    return row[0]


def sd_select_channels():
    rows = sqlcon.request("SELECT * FROM Streams;")
    ret = []
    for row in rows:
        if len(row) == 4:
            ret.append({"Name": row[1], "State": row[2], "Options": row[4],
                        "Channels": row[3].split(",") if len(row[3]) > 0 else []})
    return ret


def sd_set_state(stream, state):
    return sqlcon.commit("UPDATE Streams SET State = ? WHERE Name = ?;", state, stream)


def update(bot):
    if not streams_url:
        return
    streams = sd_select_channels()
    for one_stream in streams:
        if len(one_stream["Channels"]) > 0:
            url = "/".join([streams_url, url_escape(one_stream["Name"])])
            code, response = bot.http(url, headers=headers)
            if code == 0:
                logger.debug("Twitch response: %s", response.body)
                try:
                    ret_obj = json.loads(response.body)
                except ValueError as e:
                    logger.error("Can not parse json out: %s", unicode(e))
                    continue
                if "error" in ret_obj:
                    logger.error("Twitch API error: %s", ret_obj.get("message", ""))
                    continue
                stream = ret_obj.get("stream", None)
                if stream and "channel" in stream:
                    if one_stream["State"] != 0:
                        logger.debug("Stream %s going ONLINE", one_stream["Name"])
                        sd_set_state(one_stream["Name"], 0)
                        msg = online_msg.format(url=stream["channel"].get("url", ""),
                                                name=stream["channel"].get("name", ""),
                                                title=stream["channel"].get("status", ""),
                                                game=stream["channel"].get("game", ""))
                        for channel_id in one_stream["Channels"]:
                            bot.send(str(channel_id), msg)
                else:
                    if one_stream["State"] != 1:
                        logger.debug("Stream %s going OFFLINE", one_stream["Name"])
                        sd_set_state(one_stream["Name"], 1)


def get_stream_url(http):
    code, response = http(base_url)
    if code == 0:
        ret_obj = json.loads(response.body)
        if "_links" in ret_obj and "streams" in ret_obj["_links"]:
            return ret_obj["_links"]["streams"]
