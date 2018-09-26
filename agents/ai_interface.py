# -*- coding: utf-8 -*-
from client.mahjong_player import MainPlayer

__author__ = "Jianyang Tang"
__email__ = "jian4yang2.tang1@gmail.com"


class AIInterface(MainPlayer):

    def to_discard_tile(self):
        raise NotImplementedError

    def should_call_kan(self, tile136, from_opponent):
        raise NotImplementedError

    def try_to_call_meld(self, tile136, might_call_chi):
        raise NotImplementedError

    def can_call_reach(self):
        raise NotImplementedError

