# -*- coding: utf-8 -*-
import logging
import logging.config
import tornado.auth
import tornado.escape
import tornado.ioloop
import tornado.httpserver
import tornado.web
import json
from datetime import datetime
import re
from tornado.ioloop import IOLoop

mention = re.compile(r"<@([0-9]+)>")
logger = logging.getLogger(__name__)
port = 8480
address = "127.0.0.1"
debug = False
chat_limit = 10


class MainHandler(tornado.web.RequestHandler):
    def __init__(self, *args, **kwargs):
        bot = kwargs.get('bot', None)
        if not bot:
            raise ValueError('kwarg "bot" must be specified!')
        self.bot = bot
        super(MainHandler, self).__init__(*args)
    async def get(self,):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        ret_dict = await get_stats(self.bot)
        if ret_dict:
            try:
                ret = json.dumps(ret_dict)
                self.write(ret)
                return
            except Exception as exc:
                logger.error("%s: %s" % (exc.__class__.__name__, exc))
                self.write('{"error":"Unknown command"}')
                return
        else:
            self.write('{"error":"Unknown discord error"}')


async def get_stats(bot):
    try:
        dict_out = {}
        for server in bot.client.servers:
            dict_out[server.name] = {}
            online = 0
            members_temp = []
            mention_id = {}
            for member in server.members:
                members_temp.append(member)
                mention_id[member.id] = member.name
                if member.status == 'online' or member.status == 'idle':
                    online += 1
            dict_out[server.name]["online"] = online
            dict_out[server.name]["channels"] = {}
            for channel in server.channels:
                logger.debug('%s - %s', channel.name, channel.is_default)
                if channel.is_default and str(channel.type) == 'text':
                    dict_out[server.name]["channels"][channel.name] = {
                        "members": {},
                        "messages": []
                    }
                    for member in members_temp:
                        # curently not a simple way to determinate member for specifed channel
                        # try:
                        # if channel.permissions_for(member).can_read_messages:
                        dict_out[server.name]["channels"][channel.name]["members"][member.name] = {
                            "status": str(member.status),
                            "avatar": member.avatar,
                            "id": member.id
                        }
                        # except AttributeError:
                        #     pass
                    for msg in await bot.client.logs_from(channel, limit=chat_limit):
                        one_msg = {
                            "timestamp": (msg.timestamp - datetime.utcfromtimestamp(0)).total_seconds(),
                            "name": msg.author.name,
                            "msg": msg.clean_content
                        }
                        dict_out[server.name]["channels"][channel.name]["messages"].append(one_msg)
        return dict_out
    except Exception as exc:
        logger.error("%s: %s" % (exc.__class__.__name__, exc))


def start_web(bot):
    global chat_limit
    chat_limit = bot.config.get("web.limit", chat_limit)
    main(bot)


def main(bot):
    try:
        app = tornado.web.Application(
            [
                (r"/stats", MainHandler, {'bot': bot}),
                ],
            xsrf_cookies=False,
            debug=debug,
            )
        app.listen(bot.config.get("web.port", port), address=bot.config.get("web.address", address),
                   io_loop=bot.tornado_loop)
        logger.debug("Http server started.")
    except Exception as exc:
        logger.error("%s: %s", exc.__class__.__name__, exc)
