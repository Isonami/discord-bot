# -*- coding: utf-8 -*-
import logging
import json
from os import path, mkdir
from xml.dom import minidom
import re
import uuid
from time import time
from tornado.escape import url_escape
import aiofiles

command = r'w(?:a|alpha) (?P<clear>forgot )?(?P<question>[ a-z0-9\+\?\^\-\*,\.\'\'=:;\(\)/%]{1,255})'
description = '{cmd_start}wa(lpha) - question (1-255 symbols)'

walpha_url = None
walpha_delay = 60
walpha_appid = None
walpha_static_url = None
delay = {'last': 0}
bot_dir = ''


msg_template_q = '''Question: {question}{qimg}'''

msg_template_a = '''Answer: {answer}{img}'''

logger = logging.getLogger(__name__)


str_num = [
    'zero',
    'one',
    'two',
    'free',
    'four',
    'five',
    'six',
    'seven',
    'eigth',
    'nine',
    'ten'
]

sql_init = '''
            CREATE TABLE IF NOT EXISTS Cache(Question TEXT, Answer TEXT);
'''
db_name = 'cache.db'


def delay_txt(sdelay):
    if sdelay < 60:
        if sdelay == 1:
            str_out = 'per second'
        else:
            if len(str_num) > sdelay:
                sdelay = str_num[sdelay]
            str_out = 'every %s seconds' % sdelay
    else:
        mdelay, sdelay = divmod(sdelay, 60)
        if mdelay == 1:
            str_out = 'per minute{}'
        else:
            if len(str_num) > mdelay:
                mdelay = str_num[mdelay]
            str_out = 'every %s{} minutes' % mdelay
        if sdelay > 30:
            str_out = str_out.format(' and a half')
        else:
            str_out = str_out.format('')
    return str_out


def check_xml_pod(pod):
    if pod.hasAttribute('primary') and pod.getAttribute('primary') == 'true':
        return True
    if pod.hasAttribute('title') and (pod.getAttribute('title') == 'Plot' or pod.getAttribute('title') == 'Plots'):
        return True
    if pod.hasAttribute('title') and pod.hasAttribute('id') and pod.getAttribute('title').startswith('Basic')\
            and pod.getAttribute('id').startswith('Basic'):
        return True
    return False


async def insert_db(question, answer):
    return await sqlcon.commit('INSERT INTO Cache VALUES(?, ?);', question, answer)


async def select_db(question):
    return await sqlcon.request('SELECT * FROM Cache WHERE Question = ?;', question, one=True)


async def delete_db(question):
    return await sqlcon.commit('DELETE FROM Cache WHERE Question = ?;', question, one=True)


async def init(bot):
    global walpha_url
    walpha_url = bot.config.get('wolframalpha.url')
    global walpha_appid
    walpha_appid = bot.config.get('wolframalpha.appid')
    global walpha_static_url
    walpha_static_url = bot.config.get('wolframalpha.static_url')
    global walpha_delay
    walpha_delay = bot.config.get('wolframalpha.delay', walpha_delay)
    global bot_dir
    bot_dir = bot.config.get('main.dir')
    global imgre
    imgre = re.compile(r'.+Type=image/([a-zA-z]{3,4})&.+')
    global unire
    unire = re.compile(r'\\:([a-z0-9]{4})')
    global sqlcon
    sqlcon = await bot.sqlcon(sql_init, db_name)


async def getanswer(http, qinput):
    logger.debug('Get answers')
    if not walpha_url:
        logger.debug('Can not get rates, no url specified!')
        return
    response = await http(walpha_url.format(appid=walpha_appid, input=url_escape(qinput)), method='GET')
    if response.code == 0:
        return str(response)


async def getimage(http, src):
    logger.debug('Get img')
    if not walpha_static_url:
        return src
    response = http(src, method='GET', raw=True)
    if response.code == 0:
        if not response.raw_response:
            return src
        m = imgre.match(src)
        if not m:
            return src
        filename = str(uuid.uuid4()).replace('-', '')[10:] + '.' + 'png'
        file_dir = path.join(bot_dir, 'static', 'wolframalpha')
        if not path.exists(file_dir):
            mkdir(file_dir, 0o750)
        f = await aiofiles.open(path.join(file_dir, filename), 'wb')
        try:
            await f.write(response.raw_response)
        finally:
            await f.close()
        return walpha_static_url.format(file=filename)
    return src


async def main(self, message, *args, **kwargs):
    now = time()
    if 'question' in kwargs and kwargs['question']:
        question = kwargs['question']
    else:
        logger.error('Can not parse question!')
        return
    if 'clear' in kwargs and kwargs['clear']:
        if self.is_admin(message.author):
            await delete_db(question.lower())
            await self.send(message.channel, 'Question %s removed from cache' % question)
            return
        else:
            await self.send(message.channel, 'You are not an admin')
            return
    await self.typing(message.channel)
    row = await select_db(question.lower())
    if row:
        logger.debug('Found cache: %s', row[1])
        ans = json.loads(row[1])
    else:
        if now < delay['last']:
            await self.send(message.channel, 'Allowed one question %s' % delay_txt(walpha_delay))
            return
        out = await getanswer(self.http, question)
        if not out:
            await self.send(message.channel, 'Some times error happends, i can not control it =(')
            logger.error('Can not get response from wolframalpha')
            return
        mdom = minidom.parseString(out)
        itemlist = [p for p in mdom.getElementsByTagName('pod') if check_xml_pod(p)]
        if len(itemlist) < 1:
            didyoumeans = [p.childNodes[0].data for p in mdom.getElementsByTagName('didyoumean') if p and
                           p.childNodes > 0]
            if len(didyoumeans) < 1:
                await self.send(message.channel, 'Can not understand question.')
                return
            await self.send(message.channel, 'Did you mean: %s?' % ', '.join(didyoumeans))
            return
        delay['last'] = now + walpha_delay
        ans = []
        qimg = ''
        qlist = [p for p in mdom.getElementsByTagName('pod') if p.hasAttribute('id') and
                 p.getAttribute('id') == 'Input']
        if len(qlist) > 0:
            img_node = qlist[0].getElementsByTagName('img')
            if len(img_node) > 0:
                qimg = img_node[0].getAttribute('src')
            if len(qimg) > 0:
                qimg = '\n' + await getimage(self.http, qimg.replace('&amp;', '&'))
        for oneitem in itemlist:
            for text_node in oneitem.getElementsByTagName('plaintext'):
                img_node = oneitem.getElementsByTagName('img')
                img_src = ''
                if len(text_node.childNodes) == 0 and len(img_node) == 0:
                    continue
                text = ''
                if len(text_node.childNodes) > 0:
                    text = text_node.childNodes[0].data.encode('utf-8')
                    text = unire.sub(lambda match: '{0}'.format(chr(int(match.group(1), 16)).encode('utf-8')),
                                     text)
                if len(img_node) > 0:
                    img_src = img_node[0].getAttribute('src')
                if len(img_src) > 0:
                    img_src = '\n' + await getimage(self.http, img_src.replace('&amp;', '&'))
                ans.append(msg_template_q.format(question=question, qimg=qimg))
                ans.append(msg_template_a.format(answer=text, img=img_src))
        await insert_db(question.lower(), json.dumps(ans))
    for oneans in ans:
        await self.send(message.channel, oneans)
