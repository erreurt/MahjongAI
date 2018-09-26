# -*- coding: utf-8 -*-
from client.mahjong_tile import Tile

__author__ = "Jianyang Tang"
__email__ = "jian4yang2.tang1@gmail.com"

class Meld:
    CHI = 'chi'
    PON = 'pon'
    KAN = 'kan'
    CHANKAN = 'chankan'
    NUKI = 'nuki'

    def __init__(self, type=None, tiles=None, open=True, called=None, from_whom=None, by_whom=None):
        self.type = type
        self.tiles = tiles
        self.open = open
        self.called_tile = called
        self.from_whom = from_whom
        self.by_whom = by_whom

    def __str__(self):
        return '{}, {}'.format(
            self.type, Tile.t136_to_g(self.tiles), self.tiles
        )

    def __repr__(self):
        return self.__str__()

    @property
    def tiles_34(self):
        return [x//4 for x in self.tiles]

    @property
    def tiles_graph(self):
        return Tile.t136_to_g(self.tiles)

    @property
    def tiles_string(self):
        return Tile.tile136_to_string(self.tiles)