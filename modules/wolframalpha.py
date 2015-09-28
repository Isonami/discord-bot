import logging
from time import time
import json
from tornado.httpclient import HTTPError
from os import path, mkdir
import sqlite3
from xml.dom import minidom
import re
import uuid
import binascii


walpha_url = None
walpha_delay = 600
walpha_appid = None
walpha_static_url = None
delay = {"last": 0}
bot_dir = ""

msg_template = """Question: {question}{qimg}

Answer: {answer}{img}"""

logger = logging.getLogger(__name__)


def init(bot):
    global walpha_url
    walpha_url = bot.config.get("wolframalpha.url")
    global walpha_appid
    walpha_appid = bot.config.get("wolframalpha.appid")
    global walpha_static_url
    walpha_static_url = bot.config.get("wolframalpha.static_url")
    global walpha_delay
    walpha_delay = bot.config.get("wolframalpha.delay", walpha_delay)
    global bot_dir
    bot_dir = bot.config.get("main.dir")
    global imgre
    imgre = re.compile(r".+Type=image/([a-zA-z]{3,4})&.+")


def getanswer(client, qinput):
    try:
        logger.debug("Get answers")
        if not walpha_url:
            logger.debug("Can not get rates, no url specified!")
            return
        response = client.fetch(walpha_url.format(appid=walpha_appid, input=qinput), method="GET")
        # print response.body
        if response.body:
            return response.body
    except HTTPError as e:
        # HTTPError is raised for non-200 responses; the response
        # can be found in e.response.
        logger.error("HTTPError: " + str(e))


def getimage(client, src):
    try:
        logger.debug("Get img")
        if not walpha_static_url:
            return src
        response = client.fetch(src, method="GET")
        # print response.body
        if not response.body:
            return src
        m = imgre.match(src)
        if not m:
            return src
        filename = str(uuid.uuid4()).replace("-", "")[10:] + "." + m.group(1)
        file_dir = path.join(bot_dir, "static", "wolframalpha")
        if not path.exists(file_dir):
            mkdir(file_dir, 0o750)
        with open(path.join(file_dir, filename), "wb") as f:
            f.write(response.body)
        return walpha_static_url.format(file=filename)
    except HTTPError as e:
        # HTTPError is raised for non-200 responses; the response
        # can be found in e.response.
        logger.error("HTTPError: " + str(e))
        return src


def main(self, message, *args, **kwargs):
    try:
        now = time()
        if "question" in kwargs and kwargs["question"]:
            question = kwargs["question"]
            pass
        else:
            logger.error("Can not parse question!")
            return
            # getanswer(self.http_client, kwargs["question"].encode('utf-8'))
        out = getanswer(self.http_client, kwargs["question"].encode('utf-8'))
        if not out:
            logger.error("Can not get response from wolframalpha")
        mdom = minidom.parseString(out)
        itemlist = [p for p in mdom.getElementsByTagName('pod') if p.hasAttribute('primary') and
                    p.getAttribute('primary') == 'true']
        if len(itemlist) < 1:
            self.send(message.channel, "no answer")
            return
        ans = []
        qimg = ""
        qlist = [p for p in mdom.getElementsByTagName('pod') if p.hasAttribute('id') and
                 p.getAttribute('id') == 'Input']
        if len(qlist) > 0:
            img_node = qlist[0].getElementsByTagName('img')
            if len(img_node) > 0:
                qimg = img_node[0].getAttribute('src')
            if len(qimg) > 0:
                qimg = "\n" + getimage(self.http_client, qimg.replace("&amp;", "&"))
        for oneitem in itemlist:
            for text_node in oneitem.getElementsByTagName('plaintext'):
                if len(text_node.childNodes) == 0:
                    continue
                text = text_node.childNodes[0].data
                img_node = oneitem.getElementsByTagName('img')
                img_src = ""
                if len(img_node) > 0:
                    img_src = img_node[0].getAttribute('src')
                if len(img_src) > 0:
                    img_src = "\n" + getimage(self.http_client, img_src.replace("&amp;", "&"))
                ans.append(msg_template.format(question=question, answer=text, img=img_src, qimg=qimg))
        self.send(message.channel, "\n\n".join(ans))
    except Exception, exc:
        logger.error("%s: %s" % (exc.__class__.__name__, exc))
