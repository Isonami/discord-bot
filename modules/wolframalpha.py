import logging
from time import time
import json
from tornado.httpclient import HTTPError
from os import path, mkdir
import sqlite3
from xml.dom import minidom
import re
import uuid
from urllib import quote
from threading import Thread
from Queue import Queue, Empty
from time import sleep


walpha_url = None
walpha_delay = 600
walpha_appid = None
walpha_static_url = None
delay = {"last": 0}
bot_dir = ""
admins = []
insql = Queue()
outsql = {}
sql_timeout = 30

msg_template_q = """Question: {question}{qimg}"""

msg_template_a = """Answer: {answer}{img}"""

logger = logging.getLogger(__name__)


def check_xml_pod(pod):
    if pod.hasAttribute('primary') and pod.getAttribute('primary') == 'true':
        return True
    if pod.hasAttribute('title') and (pod.getAttribute('title') == 'Plot' or pod.getAttribute('title') == 'Plots'):
        return True
    if pod.hasAttribute('title') and pod.hasAttribute('id') and pod.getAttribute('title').startswith("Basic")\
            and pod.getAttribute('id').startswith("Basic"):
        return True
    return False


def init_db():
    try:
        logger.debug("Init DB connection")
        con = sqlite3.connect(path.join(bot_dir, "db", "cache.db"))
        cur = con.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS Cache(Question TEXT, Answer TEXT);
            """)
        con.commit()
        return con, cur
    except Exception, exc:
        logger.error("%s: %s" % (exc.__class__.__name__, exc))


def sql_db(bot):
    con, cur = init_db()
    while not bot.disconnect:
        try:
            item = insql.get()
        except Empty:
            sleep(0.1)
            continue
        if item and "uuid" in item and "SQL" in item and "Type" in item and "Args" in item:
            cur.execute(item["SQL"], item["Args"])
            if item["Type"] == 1:
                row = cur.fetchone()
                outsql[item["uuid"]] = row
            else:
                con.commit()
                outsql[item["uuid"]] = True


def insert_db(question, answer):
    cuuid = str(uuid.uuid1())
    ans = {"uuid": cuuid, "SQL": "INSERT INTO Cache VALUES(?, ?);", "Type": 0, "Args": (question, answer)}
    insql.put(ans)
    n = 0
    while n < sql_timeout * 10:
        if cuuid in outsql:
            return outsql[cuuid]
        sleep(0.1)
    return False


def select_db(question):
    cuuid = str(uuid.uuid1())
    ans = {"uuid": cuuid, "SQL": "SELECT * FROM Cache WHERE Question = ?;", "Type": 1, "Args": (question,)}
    insql.put(ans)
    n = 0
    while n < sql_timeout * 10:
        if cuuid in outsql:
            return outsql[cuuid]
        sleep(0.1)
    return None


def delete_db(question):
    cuuid = str(uuid.uuid1())
    ans = {"uuid": cuuid, "SQL": "DELETE FROM Cache WHERE Question = ?;", "Type": 1, "Args": (question,)}
    insql.put(ans)
    n = 0
    while n < sql_timeout * 10:
        if cuuid in outsql:
            return outsql[cuuid]
        sleep(0.1)
    return False


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
    global admins
    admins = bot.config.get("discord.admins")
    global imgre
    imgre = re.compile(r".+Type=image/([a-zA-z]{3,4})&.+")
    global unire
    unire = re.compile(r"\\:([a-z0-9]{4})")
    sql_th = Thread(name="WAlphaSQL", target=sql_db, args=(bot,))
    sql_th.start()


def getanswer(client, qinput):
    try:
        logger.debug("Get answers")
        if not walpha_url:
            logger.debug("Can not get rates, no url specified!")
            return
        response = client.fetch(walpha_url.format(appid=walpha_appid, input=quote(qinput)), method="GET")
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
        # filename = str(uuid.uuid4()).replace("-", "")[10:] + "." + m.group(1)
        # used png, because discor insert ugly "gif" watermark
        filename = str(uuid.uuid4()).replace("-", "")[10:] + "." + "png"
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
            question = kwargs["question"].encode('utf-8')
        else:
            logger.error("Can not parse question!")
            return
        if "clear" in kwargs and kwargs["clear"]:
            if message.author.id in admins:
                delete_db(question.lower())
                self.send(message.channel, "Question %s removed from cache" % question)
                return
            else:
                self.send(message.channel, "You are not an admin")
                return
        self.typing(message.channel)
        row = select_db(question.lower())
        if row:
            logger.debug("Found cache: %s", row[1])
            ans = json.loads(row[1])
        else:
            if now < delay["last"]:
                self.send(message.channel, "Allowed one question per minute")
                return
            out = getanswer(self.http_client, question)
            if not out:
                self.send(message.channel, "Some times error happends, i can not control it =(")
                logger.error("Can not get response from wolframalpha")
                return
            mdom = minidom.parseString(out)
            itemlist = [p for p in mdom.getElementsByTagName('pod') if check_xml_pod(p)]
            if len(itemlist) < 1:
                didyoumeans = [p.childNodes[0].data for p in mdom.getElementsByTagName('didyoumean') if p and
                               p.childNodes > 0]
                if len(didyoumeans) < 1:
                    self.send(message.channel, "Can not understand question.")
                    return
                self.send(message.channel, "Did you mean: %s?" % ", ".join(didyoumeans))
                return
            delay["last"] = now + walpha_delay
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
                    img_node = oneitem.getElementsByTagName('img')
                    img_src = ""
                    if len(text_node.childNodes) == 0 and len(img_node) == 0:
                        continue
                    text = ""
                    if len(text_node.childNodes) > 0:
                        text = text_node.childNodes[0].data.encode('utf-8')
                        text = unire.sub(lambda match: "{0}".format(unichr(int(match.group(1), 16)).encode('utf-8')),
                                         text)
                    if len(img_node) > 0:
                        img_src = img_node[0].getAttribute('src')
                    if len(img_src) > 0:
                        img_src = "\n" + getimage(self.http_client, img_src.replace("&amp;", "&"))
                    ans.append(msg_template_q.format(question=question, qimg=qimg))
                    ans.append(msg_template_a.format(answer=text, img=img_src))
            insert_db(question.lower(), json.dumps(ans))
        for oneans in ans:
            self.send(message.channel, oneans)
    except Exception, exc:
        logger.error("%s: %s" % (exc.__class__.__name__, exc))
