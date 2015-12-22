# -*- coding: utf-8 -*-
flip_str = u'(\u256f\xb0\u25a1\xb0\uff09\u256f\ufe35 \u253b\u2501\u253b'
unflip_str = u'\u252c\u2500\u252c\ufeff \u30ce( \u309c-\u309c\u30ce)'


def unflip(self, channel):
    self.send(channel, unflip_str)
