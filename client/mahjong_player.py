# -*- coding: utf-8 -*-
from copy import deepcopy

from client.mahjong_meld import Meld
from client.mahjong_tile import Tile

__author__ = "Jianyang Tang"
__copyright__ = "Copyright 2018, Mahjong AI Master Thesis"
__email__ = "jian4yang2.tang1@gmail.com"


class Player:

    def __init__(self, seat, dealer_seat):
        self.game_table = None
        self.seat = seat
        self.dealer_seat = dealer_seat
        self.init_state()
        self.discard136 = []
        self.meld136 = []
        self.reach_status = False
        self.tmp_rank = 0
        self.score = None
        self.uma = 0
        self.name = ''
        self.level = ''
        self.reach_time = -1

    def init_state(self):
        self.discard136 = []
        self.meld136 = []
        self.reach_status = False
        self.tmp_rank = 0
        self.score = None
        self.uma = 0
        self.reach_time = -1

    def __str__(self):
        return "{} - {} - {}".format(self.name, self.level, self.score)

    def __repr__(self):
        return self.__str__()

    def call_meld(self, meld: Meld):
        if meld.type == Meld.CHANKAN:
            tile34 = meld.tiles[0] // 4
            pons = [m for m in self.meld136 if m.type == Meld.PON and (m.tiles[0] // 4) == tile34]
            if pons:
                self.meld136.remove(pons[0])
        self.meld136.append(meld)

    def discard_tile(self, tile136):
        self.discard136.append(tile136)

    def call_reach(self):
        self.reach_status = True
        self.reach_time = len(self.discard34)

    def just_reach(self):
        return self.reach_time == len(self.discard34)

    @property
    def player_wind(self):
        if self.seat >= self.dealer_seat:
            return [Tile.EAST, Tile.SOUTH, Tile.WEST, Tile.NORTH][self.seat - self.dealer_seat]
        else:
            return [Tile.EAST, Tile.SOUTH, Tile.WEST, Tile.NORTH][self.seat + 4 - self.dealer_seat]

    @property
    def round_wind(self):
        return self.game_table.round_wind

    @property
    def bonus_honors(self):
        return Tile.THREES + [self.game_table.round_wind, self.player_wind]

    @property
    def is_open_hand(self):
        return len([x for x in self.meld136 if x.open]) > 0

    @property
    def is_dealer(self):
        return self.seat == self.dealer_seat

    @property
    def discard34(self):
        return [t // 4 for t in self.discard136]

    @property
    def meld34(self):
        return [[t // 4 for t in m.tiles] for m in self.meld136 if m.type == Meld.PON or m.type == Meld.CHI]

    @property
    def pon34(self):
        return [[t // 4 for t in m.tiles] for m in self.meld136 if m.type == Meld.PON]

    @property
    def chow34(self):
        return [[t // 4 for t in m.tiles] for m in self.meld136 if m.type == Meld.CHI]

    @property
    def minkan34(self):
        return [[t // 4 for t in m.tiles] for m in self.meld136 if
                (m.type == Meld.KAN or m.type == Meld.CHANKAN) and m.open]

    @property
    def ankan34(self):
        return [[t // 4 for t in m.tiles] for m in self.meld136 if
                (m.type == Meld.KAN or m.type == Meld.CHANKAN) and not m.open]

    @property
    def total_melds34(self):
        return [[t // 4 for t in m.tiles] for m in self.meld136]

    @property
    def open_state_f_lst(self):
        res = [min(self.discard34.count(tile) / 3, 1) for tile in range(34)]
        res += [[pon]*3 in self.meld34 or [pon]*4 in (self.minkan34 + self.ankan34) for pon in range(34)]
        res += [Tile.index_to_chow[chow] in self.meld34 for chow in range(21)]
        return res

    @property
    def open_state_f_richii(self):
        res = [min(self.discard34.count(tile) / 3, 1) for tile in range(34)]
        res += [[pon] * 4 in (self.minkan34 + self.ankan34) for pon in range(34)]
        return res

    @property
    def turn_num(self):
        dis_nums = [len(self.game_table.get_player(i).discard34) for i in range(0, 4)]
        return sum(dis_nums) // 4

    @property
    def discard_metric(self):
        metric = [0] * 4
        for tile in self.discard34:
            metric[tile // 9] += 1
        return metric

    @property
    def meld_metric(self):
        metric = [0] * 4
        for meld in self.meld34:
            metric[meld[0] // 9] += 1
        return metric


class MainPlayer(Player):

    def __init__(self):
        super().__init__(0, None)
        self.tiles136 = []
        self.last_draw = None
        self.thclient = None
        self.called_reach = False
        self.to_discard_after_reach = -1

    def init_state(self):
        super().init_state()
        self.tiles136 = []
        self.last_draw = None
        self.called_reach = False
        self.to_discard_after_reach = -1

    def init_hand(self, tiles136):
        self.tiles136 = tiles136

    def draw_tile(self, tile136):
        self.last_draw = tile136
        self.tiles136.append(tile136)
        self.tiles136 = sorted(self.tiles136)

    def discard_tile(self, tile136):
        super().discard_tile(tile136)

    def call_meld(self, meld: Meld):
        if (meld.type == Meld.KAN and meld.open) or meld.type == Meld.CHI or meld.type == Meld.PON:
            for t136 in meld.tiles:
                if t136 != meld.called_tile:
                    if t136 in self.tiles136:
                        self.tiles136.remove(t136)
                    self.game_table.revealed_tiles[t136 // 4] += 1
            self.meld136.append(meld)

        if meld.type == Meld.KAN and not meld.open:
            for t136 in meld.tiles:
                if t136 in self.tiles136:
                    self.tiles136.remove(t136)
                self.game_table.revealed_tiles[t136 // 4] += 1
            self.meld136.append(meld)

        if meld.type == Meld.CHANKAN:
            pon = [m for m in self.meld136 if m.type == Meld.PON and m.tiles[0] // 4 == meld.tiles[0] // 4]
            if pon:
                self.meld136.remove(pon[0])
            self.meld136.append(meld)
            self.tiles136.remove(meld.called_tile)
            self.game_table.revealed_tiles[meld.tiles[0] // 4] += 1

    def format_hand(self, extra_tile):
        hand = '{} + {}'.format(Tile.t136_to_g(self.tiles136),
                                Tile.t136_to_g([extra_tile]))
        if self.is_open_hand:
            melds = []
            for meld in self.meld136:
                melds.append('{}'.format(meld.tiles_graph))
            hand += ' + [{}]'.format(','.join(melds))
        return hand

    def str_hand_tiles(self):
        hand = Tile.t136_to_g(self.tiles136)
        if self.is_open_hand:
            melds = []
            for meld in self.meld136:
                melds.append('{}'.format(meld.tiles_graph))
            hand += ' + [{}]'.format(','.join(melds))
        return hand

    def tile_34_to_136(self, tile34):
        return [t136 for t136 in self.tiles136 if tile34 == (t136 // 4)][-1]

    @property
    def hand34(self):
        return [t // 4 for t in self.tiles136]

    # @property
    # def has_dori(self):
    #     for meld in self.meld34:
    #         if meld[0] > 26 and meld[0] in self.bonus_honors:
    #             return True
    #     for tile in self.bonus_honors:
    #         if self.hand34.count(tile) >= 3:
    #             return True
    #     return False
    #
    # @property
    # def opponents(self):
    #     return [self.game_table.get_player(i) for i in range(1, 4)]
    #
    # @property
    # def total_tiles34(self):
    #     return [t // 4 for t in self.total_tiles136]
    #
    # @property
    # def total_tiles136(self):
    #     return self.tiles136 + [t for meld in self.meld136 for t in meld.tiles]
    #
    # @property
    # def cnt_total_bonus_tiles(self):
    #     cnt = len([t136 for t136 in self.total_tiles136 if t136 in Tile.RED_BONUS])
    #     cnt += sum([self.game_table.bonus_tiles.count(t) for t in self.total_tiles34])
    #     return cnt
    #
    # @property
    # def hand_feature(self):
    #     hand_feature = np.zeros(177)
    #     hand_feature[0:88] = self.hand_vector(self.hand34)
    #     total_melds = self.total_melds34
    #     hand_feature[88:109] = [Tile.index_to_chow[chow] in total_melds for chow in range(21)]
    #     hand_feature[109:143] = [[pon] * 3 in total_melds or [pon] * 4 in total_melds for pon in range(34)]
    #     hand_feature[143:177] = [min(t / 4, 1) for t in self.game_table.revealed_tiles]
    #     return hand_feature
    #
    # @property
    # def hand_vector(self):
    #     h34 = self.hand34
    #     hand_vec = []
    #     for tile in range(0, 27):
    #         tmp_vec = [0] * 3
    #         if tile not in h34:
    #             hand_vec += tmp_vec
    #             continue
    #         tmp_vec[1] = h34.count(tile) / 4
    #         left_cursor = tile - 1
    #         if left_cursor in h34 and left_cursor // 9 == tile // 9:
    #             while left_cursor in h34 and left_cursor // 9 == tile // 9:
    #                 tmp_vec[0] += 1
    #                 left_cursor -= 1
    #         elif left_cursor - 1 in h34 and (left_cursor - 1) // 9 == tile // 9:
    #             tmp_vec[0] = 0.5
    #         tmp_vec[0] = min(tmp_vec[0] / 6, 1)
    #         right_cursor = tile + 1
    #         if right_cursor in h34 and right_cursor // 9 == tile // 9:
    #             while right_cursor in h34 and right_cursor // 9 == tile // 9:
    #                 tmp_vec[2] += 1
    #                 right_cursor += 1
    #         elif right_cursor - 1 in h34 and (right_cursor - 1) // 9 == tile // 9:
    #             tmp_vec[2] = 0.5
    #         tmp_vec[2] = min(tmp_vec[2] / 6, 1)
    #         hand_vec += tmp_vec
    #     for tile in range(27, 34):
    #         hand_vec.append(min(h34.count(tile) / 3, 1))
    #     return hand_vec
    #
    # @property
    # def form_feature_long_np(self):
    #     res = self.hand_vector
    #     res += self.open_state_f_lst
    #     res += self.game_table.revealed_feature
    #     res += self.game_table.get_player(1).open_state_f_lst
    #     res += self.game_table.get_player(2).open_state_f_lst
    #     res += self.game_table.get_player(3).open_state_f_lst
    #     return np.array(res)
    #
    # @property
    # def form_feature_short_np(self):
    #     res = self.hand_vector
    #     res += self.open_state_f_lst
    #     res += self.game_table.revealed_feature
    #     return res


class OpponentPlayer(Player):

    def __init__(self, seat, dealer_seat):
        super().__init__(seat, dealer_seat)
        self.safe_tiles = []
        self.discard_types = []

    def init_state(self):
        super().init_state()
        self.safe_tiles = []
        self.discard_types = []

    def add_safe_tile(self, tile34):
        self.safe_tiles.append(tile34)

    def add_discard_type(self, was_direct):
        self.discard_types.append(1 if was_direct else 0)

    @property
    def is_valid(self):
        return 0 in self.discard_types