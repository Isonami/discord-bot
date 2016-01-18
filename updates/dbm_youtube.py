# -*- coding: utf-8 -*-
import logging
from tornado.escape import url_escape
from xml.dom import minidom
from xml.parsers.expat import ExpatError
from datetime import datetime

logger = logging.getLogger(__name__)

base_url = 'https://www.youtube.com/feeds/videos.xml?{type}={channel}'
streams_url = None
dealy = 900

sql_init = '''
   CREATE TABLE IF NOT EXISTS YouChannels(ID INTEGER PRIMARY KEY, Name TEXT, Channels TEXT, Type TEXT, Lastid TEXT, Lastdate INTEGER);
'''
db_name = 'youtube.db'

new_msg = 'New video: {name} | {title} | {url}'


async def init(bot):
    global new_msg
    new_msg = bot.config.get('youtube.message', new_msg)
    global dealy
    dealy = bot.config.get('youtube.dealy', dealy)
    global sqlcon
    sqlcon = await bot.sqlcon(sql_init, db_name)
    global job
    job = bot.scheduler.new(update, 'Youtube', dealy, bot)
    job.start()
    bot.config.set('youtube.enable', True)
    bot.config.set('youtube.module', globals())


async def sd_select_channels():
    rows = await sqlcon.request('SELECT * FROM YouChannels;')
    ret = []
    for row in rows:
        if len(row) == 6:
            ret.append({'ID': row[0], 'Name': row[1], 'Channels': row[2].split(',') if len(row[2]) > 0 else [],
                        'Type': row[3], 'Lastid': row[4], 'Lastdate': row[5]})
    return ret


async def sd_set_state(cid, lastid, lastdate):
    return await sqlcon.commit('UPDATE YouChannels SET Lastid = ?, Lastdate = ? WHERE ID = ?;', lastid, lastdate, cid)


async def sd_select_channel(ytype, name):
    row = await sqlcon.request('SELECT * FROM YouChannels WHERE Name = ? AND Type = ?;', name, ytype, one=True)
    if not row or len(row) == 0:
        return {'Name': name, 'Channels': [], 'Type': ytype, 'Lastid': None, 'Lastdate': None}
    return {'Name': row[1], 'Channels': row[2].split('','') if len(row[3]) > 0 else [],
            'Type': row[3], 'Lastid': row[4], 'Lastdate': row[5]}


async def sd_update_channels(name, channels, ytype, lastid, lastdate):
    return await sqlcon.commit('INSERT OR REPLACE INTO YouChannels VALUES ((SELECT ID FROM YouChannels WHERE Name = ? '
                               'AND Type = ?), ?, ?, ?, ?, ?);', name, ytype, name, ','.join(channels), ytype, lastid,
                               lastdate)


async def get_last_video(cuuid, http, name, ytype):
    url = base_url.format(channel=url_escape(name), type=url_escape(ytype))
    response = await http(url)
    if response.code == 0:
        try:
            mdom = minidom.parseString(str(response))
        except ExpatError as e:
            logger.error('[%s] Can not parse response xml: %s', cuuid, e)
            return
        ents = mdom.getElementsByTagName('entry')
        if isinstance(ents, list) and len(ents) > 0:
            ent = ents[0]
            video = {}
            try:
                video['title'] = ent.getElementsByTagName('title')[0].childNodes[0].data
                video['id'] = ent.getElementsByTagName('yt:videoId')[0].childNodes[0].data
                vdate = ent.getElementsByTagName('published')[0].childNodes[0].data
                video['author'] = \
                    ent.getElementsByTagName('author')[0].getElementsByTagName('name')[0].childNodes[0].data
                video['url'] = ent.getElementsByTagName('link')[0].getAttribute('href')
            except ValueError as e:
                logger.error('[%s] Can not find element: %s', cuuid, e)
                return
            except IndexError as e:
                logger.error('[%s] Can not find element: %s', cuuid, e)
                return
            dt = datetime.strptime(vdate, '%Y-%m-%dT%H:%M:%S+00:00')
            video['date'] = int((dt - datetime.utcfromtimestamp(0)).total_seconds())
            return video


async def update(cuuid, bot):
    youchannels = await sd_select_channels()
    for you_chann in youchannels:
        if len(you_chann['Channels']) > 0:
            video = await get_last_video(cuuid, bot.http, you_chann['Name'], you_chann['Type'])
            if video:
                logger.debug('[%s] Youtube last video: %s', cuuid, video)
                if video['id'] != you_chann['Lastid'] and video['date'] > you_chann['Lastdate']:
                    await sd_set_state(you_chann['ID'], video['id'], video['date'])
                    msg = new_msg.format(name=video['author'], title=video['title'], url=video['url'])
                    for channel_id in you_chann['Channels']:
                        await bot.send(bot.client.get_channel(str(channel_id)), msg)
