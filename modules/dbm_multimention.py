# -*- coding: utf-8 -*-
import logging
import re

command = r"@(?:(?:(?P<mentionedit>(?:add)|(?:del)|(?:upd)) " \
          r"(?P<editmentionname>[a-z0-9]+)(?P<mentionlist>(?: [\S]+){0,100}))|(?P<mentionname>[a-z0-9]+))"
description = "{cmd_start}@('mention_name' or 'add|upd|del mention_name name_list_splited_by_space') - send multi " \
              "mention or create it"

sql_init = """
            CREATE TABLE IF NOT EXISTS Mentions(ID INTEGER PRIMARY KEY, Name TEXT, List TEXT);
"""
db_name = "multimention.db"

mention_re = re.compile(r"<@([0-9]+)>")
mention_fmt = "<@{mid}>"
msg_fmt = "{name} mention: {lst}"

logger = logging.getLogger(__name__)


def init(bot):
    global sqlcon
    sqlcon = bot.sqlcon(sql_init, db_name)


def add_or_update_mention_list(name, lst):
    return sqlcon.commit("INSERT OR REPLACE INTO Mentions VALUES ((SELECT ID FROM Mentions WHERE Name = ?), ?, ?)",
                         name, name, ",".join(lst))


def select_mention_list(name):
    row = sqlcon.request("SELECT List FROM Mentions WHERE Name = ?;", name, one=True)
    if row:
        if len(row[0]) > 0:
            return row[0].split(",")
    return []


def get_id_list(in_lst, message):
    lst = []
    for in_one in in_lst:
        m = mention_re.match(in_one)
        if m:
            lst.append(m.group(1))
        else:
            for member in message.server.members:
                if member.name.lower() == in_one.lower():
                    lst.append(member.id)
                    break
    return lst


def main(self, message, *args, **kwargs):
    try:
        if message.channel.is_private:
            self.send(message.channel, "Not work in private chats.")
            return
        if "mentionedit" in kwargs and "editmentionname" in kwargs:
            if self.is_admin(message.author):
                name = kwargs["editmentionname"].lower()
                if (kwargs["mentionedit"].lower() == "add" or kwargs["mentionedit"].lower() == "upd")\
                        and "mentionlist" in kwargs:
                    lst = get_id_list(kwargs["mentionlist"].split(), message)
                    if add_or_update_mention_list(name, lst):
                        self.send(message.channel, "Mention list updated.")
                    else:
                        self.send(message.channel, "Can not update mention list.")
                    return
                elif kwargs["mentionedit"].lower() == "del":
                    if add_or_update_mention_list(name, []):
                        self.send(message.channel, "Mention list deleted.")
                    else:
                        self.send(message.channel, "Can not delete mention list.")
                    return
            else:
                self.send(message.channel, "User must be an bot admin.")
                return
        elif "mentionname" in kwargs:
            name = kwargs["mentionname"].lower()
            lst_id = select_mention_list(name)
            if len(lst_id) > 0:
                lst = []
                for one_id in lst_id:
                    lst.append(mention_fmt.format(mid=one_id))
                self.send(message.channel, msg_fmt.format(name=name, lst=" ".join(lst)), mentions=None)
            return
        self.send(message.channel, "Can not parse command.")
    except Exception as exc:
        logger.error("%s: %s" % (exc.__class__.__name__, exc))
