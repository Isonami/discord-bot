# -*- coding: utf-8 -*-
import logging
import logging.config
import tornado.auth
import tornado.escape
import tornado.ioloop
import tornado.httpserver
import tornado.web
import os
import json
from multiprocessing import Process, Pipe
logger = logging.getLogger(__name__)
port = 8480
address = "127.0.0.1"
debug = False
logging_file_name = "logging-web.json"


class MainHandler(tornado.web.RequestHandler):

    def get(self):
        client_pipe.send(["stats"])
        out = client_pipe.recv()
        if out[0] == 0:
            self.write(out[1])
        elif out[0] == 2:
            self.write('{"error":"Unknown command"}')
        elif out[0] == 1:
            self.write('{"error":"Unknown discord error"}')
        else:
            self.write('{"error":"Unknown error"}')


def get_stats(bot):
    try:
        dict_out = {}
        for server in bot.client.servers:
            dict_out[server.name] = {}
            online = 0
            members_temp = []
            for member in server.members:
                members_temp.append(member)
                if member.status == 'online' or member.status == 'idle':
                    online += 1
            dict_out[server.name]["online"] = online
            dict_out[server.name]["channels"] = {}
            for channel in server.channels:
                if channel.is_default_channel() and channel.type == 'text':
                    dict_out[server.name]["channels"][channel.name] = {
                        "members": {},
                        "messages": []
                    }
                    for member in members_temp:
                        # curently not a simple way to determinate member for specifed channel
                        # try:
                        # if channel.permissions_for(member).can_read_messages:
                        dict_out[server.name]["channels"][channel.name]["members"][member.name] = {
                            "status": member.status,
                            "avatar": member.avatar
                        }
                        # except AttributeError:
                        #     pass
                    for msg in bot.client.logs_from(channel, limit=10):
                        one_msg = {
                            "name": msg.author.name,
                            "msg": msg.content
                        }
                        dict_out[server.name]["channels"][channel.name]["messages"].append(one_msg)
        return dict_out
    except Exception, exc:
        logger.error("%s: %s" % (exc.__class__.__name__, exc))


def start_web(bot):
    parent_pipe, child_pipe = Pipe()
    wp = Process(name="WebServer", target=main, args=(bot.config.get("web"), child_pipe))
    wp.daemon = True
    wp.start()
    i = 1
    while not bot.disconnect:
        in_put = parent_pipe.recv()
        if in_put[0] == "stats":
            ret_dict = get_stats(bot)
            if ret_dict:
                parent_pipe.send([0, json.dumps(ret_dict)])
            else:
                parent_pipe.send([1])
        else:
            parent_pipe.send([2])
    wp.terminate()


def main(config, pipe):
    global client_pipe
    client_pipe = pipe
    global port
    global address
    main_dir = os.path.dirname(os.path.realpath(__file__))
    json_file = os.path.join(main_dir, logging_file_name)
    if os.path.exists(json_file):
        try:
            with open(json_file) as json_config:
                global LOGGING
                LOGGING = json.load(json_config)
        except IOError as e:
            print "Can not open logging-web.json file: %s" % str(e)
            exit()
        except ValueError as e:
            print "Can not open load json logging-web file: %s" % str(e)
            exit()
    logging.config.dictConfig(LOGGING)
    global logger
    logger = logging.getLogger(__name__)
    if config:
        if "port" in config:
            port = config["port"]
            print port
        if "address" in config:
            port = config["address"]
    try:
        global running
        global http_server
        running = True
        app = tornado.web.Application(
            [
                (r"/stats", MainHandler),
                ],
            xsrf_cookies=False,
            debug=debug,
            )
        http_server = tornado.httpserver.HTTPServer(app)
        http_server.bind(port, address=address)
        proc_count = 1
        http_server.start(proc_count)
        logger.debug("Http server started.")
        tornado.ioloop.IOLoop.instance().start()
    except Exception, exc:
        logger.error("%s: %s" % (exc.__class__.__name__, exc))