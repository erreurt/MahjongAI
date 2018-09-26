# -*- coding: utf-8 -*-
import datetime
import os
import pickle
import random
from copy import deepcopy
from time import sleep

import numpy as np

from agents.ai_interface import AIInterface
from agents.utils.wait_calc import WaitCalc
from agents.utils.win_calc import WinCalc
from client.mahjong_meld import Meld
from client.mahjong_player import OpponentPlayer
from client.mahjong_tile import Tile

__author__ = "Jianyang Tang"
__email__ = "jian4yang2.tang1@gmail.com"


class OppPlayer(OpponentPlayer):

    level_dict = {'新人': 91, '9級': 91, '8級': 91, '7級': 91, '6級': 91, '5級': 91, '4級': 91, '3級': 91, '2級': 92,
                  '1級': 94, '初段': 96, '二段': 97, '三段': 98, '四段': 99,
                  '五段': 100, '六段': 101, '七段': 102, '八段': 103, '九段': 104, '十段': 105, '天鳳位': 106}

    def __init__(self, seat, dealer_seat):
        super().__init__(seat, dealer_seat)
        self.safe_tiles = []
        self.prios_history = []
        self.discard_types = []

    def init_state(self):
        super().init_state()
        self.safe_tiles = []
        self.prios_history = []
        self.discard_types = []

    def add_prediction(self, prios):
        self.prios_history.append(prios)

    def add_safe_tile(self, tile34):
        self.safe_tiles.append(tile34)

    def waiting_feature_212(self, self_index):
        res = self.open_state_f_lst  # 89
        res += self.game_table.revealed_feature  # 34
        opponents_discard = [t for i in range(1, 4) for t in self.game_table.get_player((i + self_index) % 4).discard34]
        res += [min(opponents_discard.count(tile) / 4, 1) for tile in range(34)]  # 34
        opponents_melds = []
        for i in range(1, 4):
            opp = self.game_table.get_player((i + self_index) % 4)
            opponents_melds += opp.meld34 + opp.minkan34 + opp.ankan34
        res += [Tile.index_to_chow[chow] in opponents_melds for chow in range(21)]  # 21
        res += [[pon] * 3 in opponents_melds or [pon] * 4 in opponents_melds for pon in range(34)]  # 34
        return np.array(res)

    def richii_feature_225(self, self_index):
        res = self.open_state_f_richii  # 68
        res += [tile in self.safe_tiles for tile in range(34)]  # 34
        res += self.game_table.revealed_feature  # 34
        opponents_discard = [t for i in range(1, 4) for t in self.game_table.get_player((i + self_index) % 4).discard34]
        res += [min(opponents_discard.count(tile) / 4, 1) for tile in range(34)]  # 34
        opponents_melds = []
        for i in range(1, 4):
            opp = self.game_table.get_player((i + self_index) % 4)
            opponents_melds += opp.meld34 + opp.minkan34 + opp.ankan34
        res += [Tile.index_to_chow[chow] in opponents_melds for chow in range(21)]  # 21
        res += [([pon] * 3) in opponents_melds or ([pon] * 4) in opponents_melds for pon in range(34)]  # 34
        return np.array(res)

    @property
    def is_valid(self):
        return 0 in self.discard_types

    @property
    def waiting_prediction(self):
        prios = {tile: 0 for tile in range(34)}
        safe_tiles = self.abs_safe_tiles
        if len(self.prios_history) == 0:
            return []
        factor = 1
        for p in self.prios_history[-1::-1]:
            v = p[0]
            if factor <= 0:
                break
            for tile in range(34):
                if tile in safe_tiles:
                    continue
                prios[tile] += v[tile] * factor
            factor -= 0.280

        prios = sorted(prios.items(), key=lambda x: -x[1])
        cnt, res = 0, []
        if self.dangerous:
            prios = prios[0:7]
        elif self.meld_len >= 2:
            prios = prios[0:6 if self.turn_num <= 11 else 5]
        elif self.meld_len == 1:
            prios = prios[0:5 if self.turn_num <= 11 else 4]
        elif self.prios_history[-1][1] <= self.level_dict[self.level]:
            prios = prios[0:4 if self.turn_num <= 11 else 3]
        else:
            return []

        for r in prios:
            tile = r[0]
            if tile in safe_tiles or tile in res or r[1] == 0 or self.game_table.revealed_tiles[tile] >= 4:
                continue
            if cnt == 0:
                res.append(tile)
                cnt += 1
            elif cnt == 1:
                for danger in res:
                    if tile < 27 and danger // 9 == tile // 9 and abs(tile - danger) == 3:
                        res.append(tile)
                        break
                else:
                    res.append(tile)
                    cnt += 1
            else:
                for danger in res:
                    if tile < 27 and danger // 9 == tile // 9 and abs(tile - danger) == 3:
                        res.append(tile)
        return res

    @property
    def is_freezing(self):
        return self.reach_status and abs(self.reach_time - len(self.discard34)) <= 2 and self.turn_num < 13

    @property
    def dangerous(self):
        return self.reach_status or (self.cnt_open_bonus_tiles > 2 and self.turn_num > 6)

    @property
    def cnt_open_bonus_tiles(self):
        cnt = 0
        bts = self.game_table.bonus_tiles
        for meld in self.total_melds34:
            for tile in meld:
                if tile in bts:
                    cnt += 1
        for meld in self.meld136:
            if any(rb in meld.tiles for rb in Tile.RED_BONUS):
                cnt += 1
        for meld in self.total_melds34:
            if meld[0] == meld[1] and meld[0] > 26:
                cnt += (meld[0] in Tile.THREES) + (meld[0] == self.round_wind) + (meld[0] == self.player_wind)
        return cnt

    @property
    def enough_fan_to_win(self):
        for meld in self.total_melds34:
            if meld[0] == meld[1] and meld[0] in self.bonus_honors:
                return True
        return False

    @property
    def abs_safe_tiles(self):
        return list(set(self.safe_tiles + self.discard34))

    @property
    def is_reach_dealer(self):
        return self.reach_status and self.is_dealer

    @property
    def gin_safe_tiles(self):
        res = []
        for i in range(0, 9, 18):
            i in self.discard34 and i + 6 in self.discard34 and res.append(i + 3)
            i + 1 in self.discard34 and i + 7 in self.discard34 and res.append(i + 4)
            i + 2 in self.discard34 and i + 8 in self.discard34 and res.append(i + 5)
            i + 3 in self.discard34 and (res.append(i) or res.append(i + 6))
            i + 4 in self.discard34 and (res.append(i + 1) or res.append(i + 7))
            i + 5 in self.discard34 and (res.append(i + 2) or res.append(i + 8))
        return res

    @property
    def relaxed_gin_safe_tiles(self):
        res = []
        abs_safe = self.abs_safe_tiles
        for i in range(0, 9, 18):
            i in abs_safe and i + 6 in abs_safe and res.append(i + 3)
            i + 1 in abs_safe and i + 7 in abs_safe and res.append(i + 4)
            i + 2 in abs_safe and i + 8 in abs_safe and res.append(i + 5)
            i + 3 in abs_safe and (res.append(i) or res.append(i + 6))
            i + 4 in abs_safe and (res.append(i + 1) or res.append(i + 7))
            i + 5 in abs_safe and (res.append(i + 2) or res.append(i + 8))
        return res

    @property
    def meld_len(self):
        return len(self.meld136)

    @property
    def dangerous_type(self):
        if self.meld_len >= 2:
            meld_types = []
            for m in self.total_melds34:
                if m[0] // 9 < 3 and m[0] // 9 not in meld_types:
                    meld_types.append(m[0] // 9)
            if len(meld_types) == 1:
                return meld_types[0]
        if self.meld_len == 1 and len(self.discard34) > 8:
            meld = self.total_melds34[0]
            discard_geos = [0] * 3
            for d in self.discard34:
                if d < 27:
                    discard_geos[d // 9] += 1
            min_num = min(discard_geos)
            if min_num == 0:
                min_type = discard_geos.index(min_num)
                if meld[0] // 9 == min_type or meld[0] // 9 == 3:
                    return min_type
        if len(self.discard34) > 12:
            discard_geos = [0] * 3
            for d in self.discard34:
                if d < 27:
                    discard_geos[d // 9] += 1
            min_num = min(discard_geos)
            if min_num <= 1:
                return discard_geos.index(min_num)
        return -1


class EnsembleCLF:
    root_dir = os.path.dirname(os.path.abspath(__file__)) + "/utils/clfs/"
    RICHII = True
    NORMAL = True

    def __init__(self):
        if self.RICHII:
            self.clfs_richii = []
            clfs = os.listdir(self.root_dir)
            clfs = [f for f in clfs if 'R_(' in f]
            for f in clfs:
                self.clfs_richii.append(pickle.load(open(self.root_dir + f, 'rb')))
            print("{} richii classifiers loaded".format(len(self.clfs_richii)))
        if self.NORMAL:
            self.clfs_normal = []
            clfs = os.listdir(self.root_dir)
            clfs = [f for f in clfs if 'N_(' in f]
            # print(ensembles_normal)
            for f in clfs:
                self.clfs_normal.append(pickle.load(open(self.root_dir + f, 'rb')))
            print("{} normal waiting classifiers loaded".format(len(self.clfs_normal)))

    def predict_normal_single_prio(self, input_f):
        f = np.zeros((1, 212))
        f[0,] = input_f
        times = [0] * 35
        for clf in self.clfs_normal:
            prd = clf.predict(f)
            predict = [tile for tile in range(34) if prd[0, tile] and not f[0, tile]]
            if len(predict) == 0:
                times[34] += 1
            for p in predict:
                times[p] += 1
        return [[time / 120 for time in times[:34]], times[34]]

    def predict_richii_single_prio(self, input_f):
        f = np.zeros((1, 225))
        f[0,] = input_f
        times = [0] * 34
        for clf in self.clfs_richii:
            prd = clf.predict(f)
            predict = [tile for tile in range(34) if prd[0, tile] and not f[0, tile]]
            for p in predict:
                times[p] += 1
        return [[time / 60 for time in times], 0]


class HandParti:
    NORMAL, PINHU, NO19, PPH, SP, QH = 0, 1, 2, 3, 4, 5
    names = ['NM', 'PH', 'NO19', 'PPH', '7P', 'QH']
    total_forms = 6
    prios = [QH, PPH, NO19, PINHU, SP]
    second_prios = [NO19, PINHU]

    def __init__(self, hand34, melds, forms, bonus_winds, revealed, bonus_tiles):
        self.h34 = sorted(hand34)
        self.m34 = melds
        self.bonus_winds = bonus_winds
        self.revealed = revealed
        self.bonus_tiles = bonus_tiles
        self.partitions = []
        self.partitions_geo = []
        self.hand_partition()
        self.shantins = [10] * self.total_forms
        self.best_partitions = [[]] * self.total_forms
        funcs = [
            self.cal_normal_shantin, self.cal_pinhu_shantin, self.cal_no19_shantin,
            self.cal_pph_shantin, self.cal_sp_shantin, self.cal_qh_shantin
        ]
        for i in range(6):
            forms[i] and funcs[i]()

    def __str__(self):
        res = ""
        for i in range(self.total_forms):
            if self.shantins[i] < 10:
                res += "{}: {}  ".format(self.names[i], self.shantins[i])
        return res

    def __repr__(self):
        return self.__str__()

    @property
    def current_shantin(self):
        if self.shantins[self.SP] == 1:
            return 1
        else:
            return self.shantins[self.NORMAL]

    @property
    def all_melds(self):
        res = []
        for partition in self.best_partitions[self.NORMAL]:
            for meld in partition:
                meld not in res and res.append(meld)
        return res

    @staticmethod
    def partition(tiles):
        len_t = len(tiles)

        # no tiles of this type
        if len_t == 0:
            return [[]]
        # one tile, or two tile which can be parsed into an open set
        if len_t == 1 or (len_t == 2 and abs(tiles[0] - tiles[1]) < 3):
            return [[tiles]]
        # two separate tiles
        if len_t == 2:
            return [[tiles[0:1], tiles[1:2]]]

        res = []

        if tiles[0] == tiles[1] == tiles[2]:
            tmp_res = HandParti.partition(tiles[3:])
            if len(tmp_res) > 0:
                for tile_set in tmp_res:
                    res.append([tiles[0:3]] + tile_set)

        if tiles[0] + 1 in tiles and tiles[0] + 2 in tiles:
            rec_tiles = deepcopy(tiles)
            rec_tiles.remove(tiles[0])
            rec_tiles.remove(tiles[0] + 1)
            rec_tiles.remove(tiles[0] + 2)
            tmp_res = HandParti.partition(rec_tiles)
            if len(tmp_res) > 0:
                for tile_set in tmp_res:
                    res.append([[tiles[0], tiles[0] + 1, tiles[0] + 2]] + tile_set)

        if tiles[0] + 1 in tiles:
            rec_tiles = deepcopy(tiles)
            rec_tiles.remove(tiles[0])
            rec_tiles.remove(tiles[0] + 1)
            tmp_res = HandParti.partition(rec_tiles)
            if len(tmp_res) > 0:
                for tile_set in tmp_res:
                    res.append([[tiles[0], tiles[0] + 1]] + tile_set)

        if tiles[0] + 2 in tiles:
            rec_tiles = deepcopy(tiles)
            rec_tiles.remove(tiles[0])
            rec_tiles.remove(tiles[0] + 2)
            tmp_res = HandParti.partition(rec_tiles)
            if len(tmp_res) > 0:
                for tile_set in tmp_res:
                    res.append([[tiles[0], tiles[0] + 2]] + tile_set)

        if tiles[0] == tiles[1]:
            tmp_res = HandParti.partition(tiles[2:])
            if len(tmp_res) > 0:
                for tile_set in tmp_res:
                    res.append([tiles[0:2]] + tile_set)

        tmp_res = HandParti.partition(tiles[1:])
        if len(tmp_res) > 0:
            for tile_set in tmp_res:
                res.append([tiles[0:1]] + tile_set)

        tuned_res = []
        min_len = min([len(p) for p in res])
        for p in res:
            if len(p) <= min_len and p not in tuned_res:
                tuned_res.append(p)

        return tuned_res

    def dy_decided(self, tile136):
        danyao_st = self.shantins[self.NO19]
        return self.current_shantin == danyao_st == 2 and tile136 // 4 not in Tile.ONENINE

    def qh_decided(self, num_turn):
        if self.shantins[self.QH] <= 3 and self.shantins[self.QH] * 4 + num_turn <= 16:
            return True
        chr_pair = len([tile for tile in set(self.h34) if tile > 26 and self.h34.count(tile) >= 2])
        chr_pair += len([m for m in self.m34 if m[0] > 26])
        if chr_pair >= 2 and self.shantins[self.QH] <= self.shantins[self.NORMAL] + 1:
            return True
        return False

    @property
    def pp_decided(self):
        has_dead_pair = any(self.revealed[tile] == 2 for tile in self.pairs)
        has_bonus_pair = any(tile in self.bonus_tiles for tile in self.pairs)
        good_cnt = len([tile for tile in self.pairs if tile in Tile.GOOD_PAIR])

        if len(self.meld_kezi) > 0:
            if self.shantins[self.PPH] <= 2:
                return True
        else:
            if self.shantins[self.PPH] <= 1:
                return True
            else:
                if len(self.pairs) == 5 or (len(self.pairs) == 4 and len(self.hand_kezi) == 1):
                    if has_dead_pair:
                        return False
                    if has_bonus_pair:
                        return True
                    if good_cnt >= len(self.pairs) - 2:
                        return True
                if len(self.pairs) == 4 and len(self.hand_kezi) == 0:
                    if self.shantins[self.PPH] > self.shantins[self.NORMAL] + 1:
                        return False
                    if has_dead_pair:
                        return False
                    if has_bonus_pair and good_cnt >= 2:
                        return True
                    if good_cnt >= 3:
                        return True
        return False

    @property
    def sp_decided(self):
        if len(self.meld_kezi) > 0:
            return False
        if len(self.pairs) == 6 or (len(self.pairs) == 5 and len(self.hand_kezi) == 1):
            return True
        if len(self.pairs) == 5 or (len(self.pairs) == 4 and len(self.hand_kezi) == 1):
            if not self.pp_decided:
                return True
        return False

    @property
    def pairs(self):
        return [tile for tile in set(self.h34) if self.h34.count(tile) == 2]

    @property
    def meld_kezi(self):
        return [m[0] for m in self.m34 if m[0] == m[1]]

    @property
    def hand_kezi(self):
        return [tile for tile in set(self.h34) if self.h34.count(tile) >= 3]

    def hand_partition(self):
        p_man = self.partition([t for t in self.h34 if 0 <= t < 9])
        p_pin = self.partition([t for t in self.h34 if 9 <= t < 18])
        p_suo = self.partition([t for t in self.h34 if 18 <= t < 27])
        h_chr = [t for t in self.h34 if 27 <= t < 34]
        p_chr = [[[chr_tile] * h_chr.count(chr_tile) for chr_tile in set(h_chr)]]

        for pm in p_man:
            for pp in p_pin:
                for ps in p_suo:
                    for pc in p_chr:
                        self.partitions.append(pm + pp + ps + pc)

        for p in self.partitions:
            self.partitions_geo.append(self.geo_vec_normal(p))

    def cal_normal_shantin(self):

        def shantin_n(geo_index):
            geo_vec = self.partitions_geo[geo_index]
            needed_set = (4 - len(self.m34)) - geo_vec[4] - geo_vec[5]
            if geo_vec[3] > 0:
                if geo_vec[1] + geo_vec[2] + geo_vec[3] - 1 >= needed_set:
                    return needed_set - 1
                else:
                    return 2 * needed_set - (geo_vec[1] + geo_vec[2] + geo_vec[3] - 1) - 1
            else:
                if geo_vec[1] + geo_vec[2] >= needed_set:
                    return needed_set
                else:
                    return 2 * needed_set - (geo_vec[1] + geo_vec[2])

        shantin_geo = [[index, shantin_n(index)] for index in range(len(self.partitions))]
        min_shantin = min(shantin_geo, key=lambda x: x[1])[1]
        self.shantins[self.NORMAL] = min_shantin
        self.best_partitions[self.NORMAL] = [self.partitions[g[0]] for g in shantin_geo if g[1] == min_shantin]

    def cal_pinhu_shantin(self):
        if len(self.m34) > 0:
            self.shantins[self.PINHU] = 10
            return

        def shantin_p(geo_index):
            partition = self.partitions[geo_index]
            geo = self.geo_vec_pinhuh(partition)
            need_chow = 4 - geo[4]
            if geo[1] + geo[2] >= need_chow:
                return (geo[3] == 0) + need_chow - 1 + (geo[2] == 0)
            else:
                return (geo[3] == 0) + need_chow - 1 + need_chow - geo[1] - geo[2]

        shantin_geo = [[index, shantin_p(index)] for index in range(len(self.partitions))]
        min_shantin = min(shantin_geo, key=lambda x: x[1])[1]
        self.shantins[self.PINHU] = min_shantin
        self.best_partitions[self.PINHU] = [self.partitions[g[0]] for g in shantin_geo if g[1] == min_shantin]

    def cal_no19_shantin(self):

        for m in self.m34:
            if any(tile in Tile.ONENINE for tile in m):
                self.shantins[self.NO19] = 10
                return

        def shantin_no19(geo_index):
            partition = self.partitions[geo_index]
            geo_vec = self.geo_vec_no19(partition)
            needed_set = (4 - len(self.m34)) - geo_vec[4] - geo_vec[5]
            if geo_vec[3] > 0:
                if geo_vec[1] + geo_vec[2] + geo_vec[3] - 1 >= needed_set:
                    return needed_set - 1
                else:
                    need_single = needed_set - (geo_vec[1] + geo_vec[2] + geo_vec[3] - 1)
                    if geo_vec[0] >= need_single:
                        return 2 * needed_set - (geo_vec[1] + geo_vec[2] + geo_vec[3] - 1) - 1
                    else:
                        return 2 * needed_set - (geo_vec[1] + geo_vec[2] + geo_vec[3] - 1) - 1 + need_single - geo_vec[
                            0]
            else:
                if geo_vec[1] + geo_vec[2] >= needed_set:
                    return needed_set + (geo_vec[0] == 0)
                else:
                    need_single = needed_set - (geo_vec[1] + geo_vec[2]) + 1
                    if geo_vec[0] >= need_single:
                        return 2 * needed_set - (geo_vec[1] + geo_vec[2])
                    else:
                        return 2 * needed_set - (geo_vec[1] + geo_vec[2]) + need_single - geo_vec[0]

        shantin_geo = [[index, shantin_no19(index)] for index in range(len(self.partitions))]
        min_shantin = min(shantin_geo, key=lambda x: x[1])[1]
        self.shantins[self.NO19] = min_shantin
        self.best_partitions[self.NO19] = [self.partitions[g[0]] for g in shantin_geo if g[1] == min_shantin]

    def cal_pph_shantin(self):
        for m in self.m34:
            if m[0] != m[1]:
                return
        num_kezi = len([tile for tile in set(self.h34) if self.h34.count(tile) == 3])
        num_pair = len([tile for tile in set(self.h34) if self.h34.count(tile) == 2])
        need_kezi = 4 - len(self.m34) - num_kezi
        if num_pair >= need_kezi + 1:
            self.shantins[self.PPH] = need_kezi - 1
        else:
            self.shantins[self.PPH] = 2 * need_kezi - num_pair
        self.best_partitions[self.PPH] = [[[tile] * self.h34.count(tile) for tile in set(self.h34)]]

    def cal_sp_shantin(self):
        if len(self.m34) > 0:
            self.shantins[self.SP] = 10
            return
        num_pair = len([tile for tile in set(self.h34) if self.h34.count(tile) >= 2])
        self.shantins[self.SP] = 6 - num_pair
        self.best_partitions[self.SP] = [[[tile] * self.h34.count(tile) for tile in set(self.h34)]]

    def cal_qh_shantin(self):
        q_type = self.qh_type()
        if len(q_type) == 0:
            self.shantins[self.QH] = 10
            return

        def shantin_n(par_index, tp):
            partition = self.partitions[par_index]
            geo_vec = self.geo_vec_qh(partition, tp)
            needed_set = (4 - len(self.m34)) - geo_vec[4] - geo_vec[5]
            if geo_vec[3] > 0:
                if geo_vec[1] + geo_vec[2] + geo_vec[3] - 1 >= needed_set:
                    return needed_set - 1
                else:
                    needed_open = needed_set - (geo_vec[1] + geo_vec[2] + geo_vec[3] - 1)
                    if needed_open > geo_vec[0]:
                        return needed_set - 1 + needed_open + needed_open - geo_vec[0]
                    else:
                        return needed_set - 1 + needed_open
            else:
                if geo_vec[1] + geo_vec[2] >= needed_set:
                    return needed_set + (geo_vec[0] == 0)
                else:
                    needed_open = (needed_set - (geo_vec[1] + geo_vec[2]))
                    if geo_vec[0] > needed_open:
                        return needed_set + needed_open
                    else:
                        return needed_set + needed_open + needed_open - geo_vec[0]

        def shantin_qh(par_index):
            return min([shantin_n(par_index, tp) for tp in q_type])

        shantin_geo = [[index, shantin_qh(index)] for index in range(len(self.partitions))]
        min_shantin = min(shantin_geo, key=lambda x: x[1])[1]
        self.shantins[self.QH] = min_shantin
        self.best_partitions[self.QH] = [self.partitions[g[0]] for g in shantin_geo if g[1] == min_shantin]

    def geo_vec_pinhuh(self, p):
        geo_vec = [0] * 6

        def incre(set_type):
            geo_vec[set_type] += 1

        for m in p:
            len(m) == 1 and incre(0)
            len(m) == 2 and abs(m[0] - m[1]) == 0 and m[0] not in self.bonus_winds and incre(3)
            len(m) == 2 and abs(m[0] - m[1]) == 1 and incre(2 if m[0] % 9 > 0 and m[1] % 9 < 8 else 1)
            len(m) == 2 and abs(m[0] - m[1]) == 2 and incre(1)
            len(m) == 3 and incre(5 if m[0] == m[1] else 4)

        return geo_vec

    def qh_type(self):
        qh_type = []

        if len(self.m34) > 0:
            meld_types = []
            for m in self.m34:
                if m[0] // 9 == 3:
                    continue
                if m[0] // 9 not in meld_types:
                    meld_types.append(m[0] // 9)
            if len(meld_types) > 1:
                self.shantins[self.QH] = 10
                return []
            else:
                qh_type = meld_types

        if (len(qh_type) == 0 and len(self.m34) > 0) or len(self.m34) == 0:
            type_geo = [
                len([t for t in self.h34 if 0 <= t < 9]),
                len([t for t in self.h34 if 9 <= t < 18]),
                len([t for t in self.h34 if 18 <= t < 27])
            ]
            max_num = max(type_geo)
            qh_type = [i for i in range(3) if type_geo[i] == max_num]

        return qh_type

    @staticmethod
    def geo_vec_normal(p):
        geo_vec = [0] * 6

        def incre(set_type):
            geo_vec[set_type] += 1

        for m in p:
            len(m) == 1 and incre(0)
            len(m) == 2 and abs(m[0] - m[1]) == 0 and incre(3)
            len(m) == 2 and abs(m[0] - m[1]) == 1 and incre(2 if m[0] % 9 > 0 and m[1] % 9 < 8 else 1)
            len(m) == 2 and abs(m[0] - m[1]) == 2 and incre(1)
            len(m) == 3 and incre(5 if m[0] == m[1] else 4)

        return geo_vec

    @staticmethod
    def geo_vec_no19(p):
        geo_vec = [0] * 6

        def incre(set_type):
            geo_vec[set_type] += 1

        for m in p:
            if m[0] > 26:
                continue
            len(m) == 1 and 0 < m[0] % 9 < 8 and incre(0)
            len(m) == 2 and abs(m[0] - m[1]) == 0 and 0 < m[0] % 9 < 8 and incre(3)
            len(m) == 2 and abs(m[0] - m[1]) == 1 and m[0] % 9 > 1 and m[1] % 9 < 7 and incre(2)
            len(m) == 2 and abs(m[0] - m[1]) == 1 and (m[0] % 9 == 1 or m[1] % 9 == 7) and incre(1)
            len(m) == 2 and abs(m[0] - m[1]) == 2 and m[0] % 9 > 0 and m[1] % 9 < 8 and incre(1)
            len(m) == 3 and m[0] == m[1] and 0 < m[0] % 9 < 8 and incre(5)
            len(m) == 3 and m[0] != m[1] and incre(4 if m[0] % 9 > 0 and m[2] % 9 < 8 else 1)

        return geo_vec

    @staticmethod
    def geo_vec_qh(p, tp):
        allowed_types = [tp, 3]
        geo_vec = [0] * 6

        def incre(set_type):
            geo_vec[set_type] += 1

        for m in p:
            if m[0] // 9 in allowed_types:
                len(m) == 1 and incre(0)
                len(m) == 2 and abs(m[0] - m[1]) == 0 and incre(3)
                len(m) == 2 and abs(m[0] - m[1]) == 1 and incre(2 if m[0] % 9 > 0 and m[1] % 9 < 8 else 1)
                len(m) == 2 and abs(m[0] - m[1]) == 2 and incre(1)
                len(m) == 3 and incre(5 if m[0] == m[1] else 4)
        return geo_vec


class HandAnalyser(HandParti):

    def norm_eff_vec(self, bot):
        total_revealed = deepcopy(self.revealed)
        for tile in self.h34:
            total_revealed[tile] += 1
        current_shantin = self.current_shantin
        res = []
        for to_discard in set(self.h34):
            tmp_h34 = deepcopy(self.h34)
            tmp_h34.remove(to_discard)
            eff = self._eff_nm_p7p(tmp_h34, total_revealed, current_shantin)
            if to_discard in self.bonus_tiles:
                eff *= 0.9
            if to_discard < 27 and to_discard % 9 == 4 and self.h34.count(to_discard) == 1:
                if bot.tile_34_to_136(to_discard) in Tile.RED_BONUS:
                    eff *= 0.9
            res.append([to_discard, eff])
        res = sorted(res, key=lambda x: 0 if x[0] in Tile.ONENINE else 4 - abs(x[0] % 9 - 4))
        res = sorted(res, key=lambda x: -x[1])
        self.set_19_prior(res)
        return res

    def enforce_eff_vec(self, num_turn, bot):

        decided_pph, decided_dy, decided_qh = bot.decided_pph, bot.decided_dy, bot.decided_qh

        def enforce_eff(index):
            bot.thclient.drawer and bot.thclient.drawer.set_enforce_form(self.names[index])
            return self.spec_eff_vec(index, bot)

        qh_decided = self.qh_decided(num_turn) or decided_qh or self.shantins[self.QH] == self.current_shantin
        pp_decided = self.pp_decided or decided_pph or self.shantins[self.PPH] == self.current_shantin

        if qh_decided and pp_decided:
            if self.shantins[self.PPH] < self.shantins[self.QH]:
                return enforce_eff(self.PPH)
            else:
                return enforce_eff(self.QH)
        elif qh_decided:
            return enforce_eff(self.QH)
        elif pp_decided:
            return enforce_eff(self.PPH)

        if self.sp_decided:
            return enforce_eff(self.SP)
        if decided_dy:
            return enforce_eff(self.NO19)

    def deep_eff_vec(self, bot):
        deep_eff = {}
        normal_eff = {}
        total_revealed = deepcopy(self.revealed)
        for tile in self.h34:
            total_revealed[tile] += 1
        current_shantin = self.current_shantin
        for to_discard in set(self.h34):
            tmp_h34 = deepcopy(self.h34)
            tmp_h34.remove(to_discard)
            drawn_sum = 0
            total_eff = 0
            hand_ana = HandAnalyser(tmp_h34, self.m34, [1, 0, 0, 0, 1, 0], self.bonus_winds, self.revealed, self.bonus_tiles)
            if hand_ana.shantins[self.NORMAL] == current_shantin or hand_ana.shantins[self.SP] == current_shantin:
                for drawn in range(34):
                    if total_revealed[drawn] < 4:
                        tiles_after_drawn = tmp_h34 + [drawn]
                        hand_ana = HandAnalyser(tiles_after_drawn, self.m34, [1, 0, 0, 0, 1, 0], self.bonus_winds, self.revealed, self.bonus_tiles)
                        if hand_ana.shantins[self.NORMAL] < current_shantin or hand_ana.shantins[self.SP] < current_shantin:
                            remain = 4 - total_revealed[drawn]
                            drawn_sum += remain
                            tmp_revealed = deepcopy(total_revealed)
                            tmp_revealed[drawn] += 1
                            eff = hand_ana._eff_nm_p7p(tiles_after_drawn, tmp_revealed, current_shantin - 1)
                            total_eff += eff * remain
            if drawn_sum > 0:
                factor = 1
                if to_discard in self.bonus_tiles:
                    factor *= 0.9
                if to_discard < 27 and to_discard % 9 == 4 and self.h34.count(to_discard) == 1:
                    if bot.tile_34_to_136(to_discard) in Tile.RED_BONUS:
                        factor *= 0.9
                deep_eff[to_discard] = total_eff / drawn_sum
                normal_eff[to_discard] = drawn_sum * factor
            else:
                deep_eff[to_discard] = 0
                normal_eff[to_discard] = 0

        normal_eff = sorted(normal_eff.items(), key=lambda x: 0 if x[0] in Tile.ONENINE else 4 - abs(x[0] % 9 - 4))
        normal_eff = sorted(normal_eff, key=lambda x: - x[1])
        index = 0
        res = []
        while True:
            current_index = index + 1
            while current_index < len(normal_eff) and abs(normal_eff[index][1] - normal_eff[current_index][1]) < 2:
                current_index += 1
            tmp_eff = sorted(normal_eff[index:current_index], key=lambda x: - deep_eff[x[0]])
            for pr in tmp_eff:
                res.append(pr)
            if current_index == len(normal_eff):
                break
            else:
                index = current_index
        return res

    def _eff_nm_p7p(self, tiles, total_revealed, current_shantin):
        eff = 0
        for drawn in range(34):
            if total_revealed[drawn] >= 4 or not self._has_adj(drawn):
                continue
            tiles_after = tiles + [drawn]
            forms = [1, 0, 0, 0, 1, 0]
            hand_analiser = HandAnalyser(tiles_after, self.m34, forms, self.bonus_winds, self.revealed, self.bonus_tiles)
            if hand_analiser.shantins[self.NORMAL] < current_shantin or \
                    hand_analiser.shantins[self.SP] < current_shantin:
                eff += (4 - total_revealed[drawn]) * self._get_factor(drawn)
        return eff

    def spec_eff_vec(self, goal_form, bot):
        total_revealed = deepcopy(self.revealed)
        for tile in self.h34:
            total_revealed[tile] += 1
        current_shantin = self.shantins[goal_form]
        res = []
        for to_discard in set(self.h34):
            tmp_h34 = deepcopy(self.h34)
            tmp_h34.remove(to_discard)
            eff = self._eff_spec(tmp_h34, total_revealed, current_shantin, goal_form)
            if to_discard in self.bonus_tiles:
                eff *= 0.9
            res.append([to_discard, eff])
        norm_res = self.norm_eff_vec(bot)
        norm_eff = {x[0]: x[1] for x in norm_res}
        res = sorted(res, key=lambda x: 0 if x[0] in Tile.ONENINE else 4 - abs(x[0] % 9 - 4))
        res = sorted(res, key=lambda x: - norm_eff[x[0]])
        res = sorted(res, key=lambda x: -x[1])
        self.set_19_prior(res)
        return res

    def _eff_spec(self, tiles, total_revealed, current_shantin, form):
        eff = 0
        for drawn in range(34):
            if total_revealed[drawn] >= 4 or (form != self.QH and not self._has_adj(drawn)):
                continue
            forms = [0] * 6
            forms[form] = 1
            tiles_after = tiles + [drawn]
            hand_analiser = HandAnalyser(tiles_after, self.m34, forms, self.bonus_winds, self.revealed, self.bonus_tiles)
            if hand_analiser.shantins[form] < current_shantin:
                eff += (4 - total_revealed[drawn]) * self._get_factor(drawn)
        return eff

    def _get_factor(self, tile):
        factor = 1
        if tile < 27:
            if (tile - 2) // 9 == tile // 9 and (tile - 2) in self.bonus_tiles or \
                    (tile + 2) // 9 == tile // 9 and (tile + 2) in self.bonus_tiles:
                factor += 0.2
            if (tile - 1) // 9 == tile // 9 and (tile - 1) in self.bonus_tiles or \
                    (tile + 1) // 9 == tile // 9 and (tile + 1) in self.bonus_tiles:
                factor += 0.4
        if tile in self.bonus_tiles:
            factor += 0.7
        return factor

    def _has_adj(self, tile):
        if tile > 26:
            if tile in self.h34:
                return True
        else:
            for diff in range(-2, 3):
                if (tile + diff) // 9 == tile // 9 and (tile + diff) in self.h34:
                    return True
        return False

    def set_19_prior(self, res_lst):
        f19 = -1
        for r in res_lst:
            if r[0] in Tile.ONENINE:
                f19 = res_lst.index(r)
                break
        while f19 > 0 and abs(res_lst[f19 - 1][1] - res_lst[f19][1]) < self.current_shantin and res_lst[f19][1] > 20:
            res_lst[f19 - 1], res_lst[f19] = res_lst[f19], res_lst[f19 - 1]
            f19 -= 1


class WaitingAnalyser:

    @staticmethod
    def check_waiting_m1(bot, richii=False):
        w_dict = {}
        bonus_tiles = bot.game_table.bonus_tiles
        finished_hand, win_tile = WaitCalc.waiting_calc(bot.hand34)
        if not finished_hand or len(finished_hand) == 0:
            return w_dict
        bns = bot.cnt_total_bonus_tiles
        total_win_tiles = list(set([t for wt in win_tile for t in list(wt)]))
        w_dict = {'waitings': {}, 'remain_num': 0}
        ave_score_sum = 0
        for w in total_win_tiles:
            score, _, _, _ = WinCalc.score_calc_long_para(
                bot.hand34, w, bot.meld34, bot.minkan34, bot.ankan34, False,
                bot.player_wind, bot.round_wind, richii, bns + bonus_tiles.count(w),
                bot.game_table.honba_sticks, bot.game_table.reach_sticks, bot.is_dealer
            )
            if score > 0:
                w_dict['waitings'][w] = score
                w_dict['remain_num'] += 4 - bot.game_table.revealed_tiles[w] - bot.hand34.count(w)
                ave_score_sum += score * (4 - bot.game_table.revealed_tiles[w] - bot.hand34.count(w))
        if w_dict['remain_num'] > 0:
            w_dict['ave_score'] = ave_score_sum // w_dict['remain_num']
            return w_dict
        else:
            return {}

    @staticmethod
    def check_waiting(bot, ricchi=False):
        waiting_dict = {}
        bonus_tiles = bot.game_table.bonus_tiles
        for tile in set(bot.hand34):
            hand_after_discard = deepcopy(bot.hand34)
            hand_after_discard.remove(tile)
            finished_hand, win_tile = WaitCalc.waiting_calc(hand_after_discard)
            if not finished_hand or len(finished_hand) == 0:
                continue
            bns = bot.cnt_total_bonus_tiles - bonus_tiles.count(tile)
            if tile % 9 == 4 and tile < 27 and bot.hand34.count(tile) == 1 and tile * 4 in bot.tiles136:
                bns -= 1
            tmp_dict = {'waitings': {}, 'remain_num': 0, 's_remain': {}}
            total_win_tiles = list(set([t for wt in win_tile for t in list(wt)]))
            for w in total_win_tiles:
                score, _, _, _ = WinCalc.score_calc_long_para(
                    hand_after_discard, w, bot.meld34, bot.minkan34, bot.ankan34, False,
                    bot.player_wind, bot.round_wind, ricchi, bns + bonus_tiles.count(w),
                    bot.game_table.honba_sticks, bot.game_table.reach_sticks, bot.is_dealer
                )
                if score > 0 and (4 - bot.game_table.revealed_tiles[w] - bot.hand34.count(w)) > 0:
                    tmp_dict['waitings'][w] = score
                    tmp_dict['s_remain'][w] = 4 - bot.game_table.revealed_tiles[w] - bot.hand34.count(w)
                    tmp_dict['remain_num'] += 4 - bot.game_table.revealed_tiles[w] - bot.hand34.count(w)
            if tmp_dict['remain_num'] > 0:
                tmp_dict['ave_score'] = sum([v for k, v in tmp_dict['waitings'].items()]) // len(tmp_dict['waitings'])
                tmp_dict['w_tiles'] = [k for k, v in tmp_dict['waitings'].items()]
                waiting_dict[tile] = tmp_dict

        if len(waiting_dict) > 0:
            waiting_dict = sorted(waiting_dict.items(), key=lambda x: -x[1]['remain_num'])

        return waiting_dict

    @staticmethod
    def check_waiting_long(bonus_tiles, hand_34, hand_136, cnt_bonus, meld_34, minkan_34, ankan_34,
                           player_wind, round_wind, honba_sticks, reach_sticks, is_dealer, revealed):
        waiting_dict = {}
        for tile in set(hand_34):
            hand_after_discard = deepcopy(hand_34)
            hand_after_discard.remove(tile)
            finished_hand, win_tile = WaitCalc.waiting_calc(hand_after_discard)
            if not finished_hand or len(finished_hand) == 0:
                continue
            cnt_bonus = cnt_bonus - bonus_tiles.count(tile)
            cnt_bonus -= (tile % 9 == 4 and tile < 27 and hand_34.count(tile) == 1 and tile * 4 in hand_136)
            tmp_dict = {'waitings': {}, 'remain_num': 0}
            total_win_tiles = list(set([t for wt in win_tile for t in list(wt)]))
            for w in total_win_tiles:
                score, _, _, _ = WinCalc.score_calc_long_para(
                    hand_after_discard, w, meld_34, minkan_34, ankan_34, False,
                    player_wind, round_wind, False, cnt_bonus + bonus_tiles.count(w),
                    honba_sticks, reach_sticks, is_dealer
                )
                if score > 0:
                    tmp_dict['waitings'][w] = score
                    tmp_dict['remain_num'] += 4 - revealed[w] - hand_34.count(w)
            if tmp_dict['remain_num'] > 0:
                tmp_dict['ave_score'] = sum([v for k, v in tmp_dict['waitings'].items()]) // len(tmp_dict['waitings'])
                if tmp_dict['ave_score'] > 0:
                    waiting_dict[tile] = tmp_dict

        if len(waiting_dict) > 0:
            waiting_dict = sorted(waiting_dict.items(), key=lambda x: -x[1]['remain_num'])

        return waiting_dict

    @staticmethod
    def can_win(bot, final_tile):
        if final_tile in bot.discard34:
            return False
        finished_hand, win_tile = WaitCalc.waiting_calc(deepcopy(bot.hand34))
        if not finished_hand or len(finished_hand) == 0:
            return False
        for j in range(len(win_tile)):
            win_tiles = list(win_tile[j])
            if final_tile in win_tiles:
                hand_partition = finished_hand[j]
                f, _, m, _ = WinCalc.fan_calc_long_para(hand_partition, final_tile, bot.meld34, bot.minkan34,
                                                        bot.ankan34,
                                                        False, bot.player_wind, bot.round_wind, False)
                return f > 0 or m > 0
        return False

    @staticmethod
    def check_waiting_after_pon(bot, tile136):
        hand34 = deepcopy(bot.hand34)
        hand34.remove(tile136 // 4)
        hand34.remove(tile136 // 4)
        meld34 = deepcopy(bot.meld34)
        meld34.append([tile136 // 4] * 3)
        return WaitingAnalyser.check_waiting_long(
            bot.game_table.bonus_tiles, hand34, bot.tiles136, bot.cnt_total_bonus_tiles, meld34, bot.minkan34,
            bot.ankan34, bot.player_wind, bot.round_wind, bot.game_table.honba_sticks, bot.game_table.reach_sticks,
            bot.is_dealer, bot.game_table.revealed_tiles
        )

    @staticmethod
    def check_waiting_after_chow(bot, hand_open, tile136):
        hand34 = deepcopy(bot.hand34)
        hand34.remove(hand_open[0])
        hand34.remove(hand_open[1])
        meld34 = deepcopy(bot.meld34)
        meld34.append(sorted(hand_open + [tile136 // 4]))
        return WaitingAnalyser.check_waiting_long(
            bot.game_table.bonus_tiles, hand34, bot.tiles136, bot.cnt_total_bonus_tiles, meld34, bot.minkan34,
            bot.ankan34, bot.player_wind, bot.round_wind, bot.game_table.honba_sticks, bot.game_table.reach_sticks,
            bot.is_dealer, bot.game_table.revealed_tiles
        )

    @staticmethod
    def should_richii(bot, hand_ana):
        waiting_dict_not_richii = WaitingAnalyser.check_waiting(bot, False)
        waiting_dict = WaitingAnalyser.check_waiting(bot, True)

        if bot.is_all_last:
            if bot.current_rank == 0:
                return WaitingAnalyser.all_last_richii_rk0(waiting_dict, bot, hand_ana)
            elif bot.current_rank == 1:
                return WaitingAnalyser.all_last_richii_rk1(waiting_dict, bot, hand_ana, waiting_dict_not_richii)
            elif bot.current_rank == 2:
                return WaitingAnalyser.all_last_richii_rk2(waiting_dict, bot, hand_ana, waiting_dict_not_richii)
            else:
                return WaitingAnalyser.all_last_richii_rk3(waiting_dict, bot, hand_ana, waiting_dict_not_richii)
        else:
            return WaitingAnalyser.not_all_last_richii(waiting_dict, bot, hand_ana)

    @staticmethod
    def not_all_last_richii(waiting_riichi, bot, hand_ana):
        good_indices, bad_indices = [], []
        for index in range(len(waiting_riichi)):
            tmp_dict = waiting_riichi[index][1]
            remain = tmp_dict['remain_num']
            wtiles = tmp_dict['w_tiles']
            if remain > 4 or (remain > 2 and any(t in Tile.ONENINE for t in wtiles)):
                good_indices.append(index)
            else:
                bad_indices.append(index)
        good_indices = sorted(good_indices, key=lambda x: - waiting_riichi[x][1]['ave_score'])
        bad_indices = sorted(bad_indices, key=lambda x: - waiting_riichi[x][1]['ave_score'])
        sorted_indices = []
        i, j = 0, 0
        while i < len(good_indices) or j < len(bad_indices):
            if i == len(good_indices) and j < len(bad_indices):
                sorted_indices.append(bad_indices[j])
                j += 1
            if i < len(good_indices) and j == len(bad_indices):
                sorted_indices.append(good_indices[i])
                i += 1
            if i < len(good_indices) and j < len(bad_indices):
                score1 = waiting_riichi[good_indices[i]][1]['ave_score']
                score2 = waiting_riichi[bad_indices[j]][1]['ave_score']
                if score2 > 2 * score1:
                    sorted_indices.append(bad_indices[j])
                    j += 1
                else:
                    sorted_indices.append(good_indices[j])
                    i += 1
        for index in sorted_indices:
            to_discard = waiting_riichi[index][0]
            tmp_dict = waiting_riichi[index][1]
            remain = tmp_dict['remain_num']
            score = tmp_dict['ave_score']
            if bot.turn_num <= 6:
                if score >= 4000 and remain > 2:
                    return True, to_discard, remain, tmp_dict['waitings']
                if score >= 2000 and remain > 4:
                    return True, to_discard, remain, tmp_dict['waitings']
            elif bot.turn_num < 15:
                if bot.game_table.has_reach:
                    if score >= 8000 and remain > 2:
                        return True, to_discard, remain, tmp_dict['waitings']
                    if score >= 5000 and remain > 2 and bot.can_discard(to_discard, hand_ana):
                        return True, to_discard, remain, tmp_dict['waitings']
                    if score >= 2600 and remain > 4 and bot.can_discard(to_discard, hand_ana):
                        return True, to_discard, remain, tmp_dict['waitings']
                else:
                    if score >= 6000 and remain > 2:
                        return True, to_discard, remain, tmp_dict['waitings']
                    if score >= 4000 and remain > 2 and bot.can_discard(to_discard, hand_ana):
                        return True, to_discard, remain, tmp_dict['waitings']
                    if score >= 2000 and remain > 4 and bot.can_discard(to_discard, hand_ana):
                        return True, to_discard, remain, tmp_dict['waitings']
            elif bot.turn_num > 16:
                if not bot.game_table.has_reach:
                    if bot.can_discard(to_discard, hand_ana):
                        return True, to_discard, remain, tmp_dict['waitings']
        return False, None, None, None

    @staticmethod
    def all_last_richii_rk0(waiting_riichi, bot, hand_ana):
        good_indices, bad_indices = [], []
        for index in range(len(waiting_riichi)):
            tmp_dict = waiting_riichi[index][1]
            remain = tmp_dict['remain_num']
            wtiles = tmp_dict['w_tiles']
            if remain > 4 or (remain > 2 and any(t in Tile.ONENINE for t in wtiles)):
                good_indices.append(index)
            else:
                bad_indices.append(index)

        def expect_score(x_x):
            w_dict = waiting_riichi[x_x][1]['waitings']
            return sum([waiting_riichi[x_x][1]['s_remain'][k] * v for k, v in w_dict.items()])

        good_indices = sorted(good_indices, key=lambda x: - expect_score(x))
        bad_indices = sorted(bad_indices, key=lambda x: -expect_score(x))
        for need_score in bot.need_scores:
            for g_index in good_indices:
                to_discard = waiting_riichi[g_index][0]
                tmp_dict = waiting_riichi[g_index][1]
                total_remain = tmp_dict['remain_num']
                score = tmp_dict['ave_score']
                if score >= need_score:
                    return True, to_discard, total_remain, tmp_dict['waitings']
                if score * 2 >= need_score and bot.can_discard(to_discard, hand_ana):
                    return True, to_discard, total_remain, tmp_dict['waitings']
            for b_index in bad_indices:
                to_discard = waiting_riichi[b_index][0]
                tmp_dict = waiting_riichi[b_index][1]
                total_remain = tmp_dict['remain_num']
                score = tmp_dict['ave_score']
                if score >= need_score:
                    return True, to_discard, total_remain, tmp_dict['waitings']
                if score * 1.5 >= need_score and bot.can_discard(to_discard, hand_ana):
                    return True, to_discard, total_remain, tmp_dict['waitings']

        return False, None, None, None

    @staticmethod
    def all_last_richii_rk1(waiting_riichi, bot, hand_ana, waiting_not_riichi):
        good_indices, bad_indices = [], []
        for index in range(len(waiting_riichi)):
            tmp_dict = waiting_riichi[index][1]
            remain = tmp_dict['remain_num']
            wtiles = tmp_dict['w_tiles']
            if remain > 4 or (remain > 2 and any(t in Tile.ONENINE for t in wtiles)):
                good_indices.append(index)
            else:
                bad_indices.append(index)

        def expect_score(x_x):
            w_dict = waiting_riichi[x_x][1]['waitings']
            return sum([waiting_riichi[x_x][1]['s_remain'][k] * v for k, v in w_dict.items()])

        good_indices = sorted(good_indices, key=lambda x: - expect_score(x))
        bad_indices = sorted(bad_indices, key=lambda x: -expect_score(x))
        for need_score in bot.need_scores:
            for g_index in good_indices:
                to_discard = waiting_riichi[g_index][0]
                tmp_dict = waiting_riichi[g_index][1]
                total_remain = tmp_dict['remain_num']
                score = tmp_dict['ave_score']
                if bot.game_table.has_reach:
                    if score >= 1.5 * need_score:
                        return True, to_discard, total_remain, tmp_dict['waitings']
                    if score >= need_score and bot.can_discard(to_discard, hand_ana):
                        return True, to_discard, total_remain, tmp_dict['waitings']
                else:
                    if score >= need_score:
                        return True, to_discard, total_remain, tmp_dict['waitings']
                    if score >= 0.8 * need_score and bot.can_discard(to_discard, hand_ana):
                        return True, to_discard, total_remain, tmp_dict['waitings']
            for b_index in bad_indices:
                to_discard = waiting_riichi[b_index][0]
                tmp_dict = waiting_riichi[b_index][1]
                total_remain = tmp_dict['remain_num']
                score = tmp_dict['ave_score']
                if bot.game_table.has_reach:
                    if score >= 2 * need_score:
                        return True, to_discard, total_remain, tmp_dict['waitings']
                    if score >= 1.5 * need_score and bot.can_discard(to_discard, hand_ana):
                        return True, to_discard, total_remain, tmp_dict['waitings']
                else:
                    if score >= 1.5 * need_score:
                        return True, to_discard, total_remain, tmp_dict['waitings']
                    if score >= need_score and bot.can_discard(to_discard, hand_ana):
                        return True, to_discard, total_remain, tmp_dict['waitings']
        diff = abs(bot.score - min(bot.game_table.scores))
        if len(waiting_not_riichi) == 0 or diff > 1000:
            for index in good_indices + bad_indices:
                to_discard = waiting_riichi[index][0]
                tmp_dict = waiting_riichi[index][1]
                total_remain = tmp_dict['remain_num']
                if bot.can_discard(to_discard, hand_ana):
                    return True, to_discard, total_remain, tmp_dict['waitings']

        return False, None, None, None

    @staticmethod
    def all_last_richii_rk2(waiting_riichi, bot, hand_ana, waiting_not_riichi):
        good_indices, bad_indices = [], []
        for index in range(len(waiting_riichi)):
            tmp_dict = waiting_riichi[index][1]
            remain = tmp_dict['remain_num']
            wtiles = tmp_dict['w_tiles']
            if remain > 4 or (remain > 2 and any(t in Tile.ONENINE for t in wtiles)):
                good_indices.append(index)
            else:
                bad_indices.append(index)

        def expect_score(x_x):
            w_dict = waiting_riichi[x_x][1]['waitings']
            return sum([waiting_riichi[x_x][1]['s_remain'][k] * v for k, v in w_dict.items()])

        good_indices = sorted(good_indices, key=lambda x: - expect_score(x))
        bad_indices = sorted(bad_indices, key=lambda x: -expect_score(x))
        for need_score in bot.need_scores:
            for g_index in good_indices:
                to_discard = waiting_riichi[g_index][0]
                tmp_dict = waiting_riichi[g_index][1]
                total_remain = tmp_dict['remain_num']
                score = tmp_dict['ave_score']
                if bot.game_table.has_reach:
                    if score >= need_score:
                        return True, to_discard, total_remain, tmp_dict['waitings']
                    if score >= 0.6 * need_score and bot.can_discard(to_discard, hand_ana):
                        return True, to_discard, total_remain, tmp_dict['waitings']
                else:
                    if score >= 0.7 * need_score:
                        return True, to_discard, total_remain, tmp_dict['waitings']
                    if score >= 0.5 * need_score and bot.can_discard(to_discard, hand_ana):
                        return True, to_discard, total_remain, tmp_dict['waitings']
            for b_index in bad_indices:
                to_discard = waiting_riichi[b_index][0]
                tmp_dict = waiting_riichi[b_index][1]
                total_remain = tmp_dict['remain_num']
                score = tmp_dict['ave_score']
                if bot.game_table.has_reach:
                    if score >= 1.2 * need_score:
                        return True, to_discard, total_remain, tmp_dict['waitings']
                    if score >= need_score and bot.can_discard(to_discard, hand_ana):
                        return True, to_discard, total_remain, tmp_dict['waitings']
                else:
                    if score >= 0.9 * need_score:
                        return True, to_discard, total_remain, tmp_dict['waitings']
                    if score >= 0.7 * need_score and bot.can_discard(to_discard, hand_ana):
                        return True, to_discard, total_remain, tmp_dict['waitings']
        diff = abs(bot.score - sorted(bot.game_table.scores)[1])
        if len(waiting_not_riichi) == 0 or diff > 1000:
            for index in good_indices + bad_indices:
                to_discard = waiting_riichi[index][0]
                tmp_dict = waiting_riichi[index][1]
                total_remain = tmp_dict['remain_num']
                if bot.can_discard(to_discard, hand_ana):
                    return True, to_discard, total_remain, tmp_dict['waitings']

        return False, None, None, None

    @staticmethod
    def all_last_richii_rk3(waiting_riichi, bot, hand_ana, waiting_not_riichi):
        good_indices, bad_indices = [], []
        for index in range(len(waiting_riichi)):
            tmp_dict = waiting_riichi[index][1]
            remain = tmp_dict['remain_num']
            wtiles = tmp_dict['w_tiles']
            if remain > 4 or (remain > 2 and any(t in Tile.ONENINE for t in wtiles)):
                good_indices.append(index)
            else:
                bad_indices.append(index)

        def expect_score(x_x):
            w_dict = waiting_riichi[x_x][1]['waitings']
            return sum([waiting_riichi[x_x][1]['s_remain'][k] * v for k, v in w_dict.items()])

        good_indices = sorted(good_indices, key=lambda x: - expect_score(x))
        bad_indices = sorted(bad_indices, key=lambda x: -expect_score(x))
        diff = abs(bot.score - sorted(bot.game_table.scores)[2])
        if len(waiting_not_riichi) == 0:
            for g_index in good_indices:
                to_discard = waiting_riichi[g_index][0]
                tmp_dict = waiting_riichi[g_index][1]
                remain = tmp_dict['remain_num']
                w_dict = tmp_dict['waitings']
                score = tmp_dict['ave_score']
                if bot.can_discard(to_discard, hand_ana) and score >= (4000 if bot.is_dealer else 2000):
                    return True, to_discard, remain, w_dict
        else:
            if diff < 1000:
                if bot.turn_num <= 6:
                    for g_index in good_indices:
                        to_discard = waiting_riichi[g_index][0]
                        tmp_dict = waiting_riichi[g_index][1]
                        remain = tmp_dict['remain_num']
                        w_dict = tmp_dict['waitings']
                        score = tmp_dict['ave_score']
                        if score >= (2000 if bot.is_dealer else 1000):
                            return True, to_discard, remain, w_dict
                else:
                    return False, None, None, None
            else:
                for g_index in good_indices:
                    to_discard = waiting_riichi[g_index][0]
                    tmp_dict = waiting_riichi[g_index][1]
                    remain = tmp_dict['remain_num']
                    w_dict = tmp_dict['waitings']
                    score = tmp_dict['ave_score']
                    if bot.turn_num <= 6:
                        return True, to_discard, remain, w_dict
                    else:
                        if bot.can_discard(to_discard, hand_ana):
                            if bot.game_table.has_reach:
                                if score >= (5000 if bot.is_dealer else 3000):
                                    return True, to_discard, remain, w_dict
                            else:
                                if score >= (3000 if bot.is_dealer else 1300):
                                    return True, to_discard, remain, w_dict
        return False, None, None, None


class MLAI(AIInterface):

    def __init__(self, ensemble_clfs):
        super().__init__()
        self.ensemble_clfs = ensemble_clfs
        self.called_reach = False
        self.to_discard_after_reach = -1
        self.decided_pph = False
        self.decided_dy = False
        self.decided_qh = False
        self.not_kan = None
        self.dis_funcs = {3: self._dis_3_st, 2: self._dis_2_st, 1: self._dis_1_st, 0: self._dis_1_st}
        self.riichi_waiting = None

    def init_state(self):
        super().init_state()
        self.erase_states()

    def to_discard_tile(self):
        if self.called_reach:
            return self.tile_34_to_136(self.to_discard_after_reach)

        # for opp in range(1, 4):
        #     if self.game_table.get_player(opp).reach_status:
        #         self.handle_opponent_discard(opp)
        self.log_opponents_prediction()

        s = datetime.datetime.now()

        def wait_3():
            e = datetime.datetime.now()
            diff = (e - s).seconds
            diff < 1 and sleep(1 + random.uniform(0, 2))

        hand_ana = HandAnalyser(self.hand34, self.total_melds34, [1] * 6, self.bonus_honors, self.game_table.revealed_tiles, self.game_table.bonus_tiles)

        to_discard = self._dis_check_waiting(hand_ana)
        if to_discard >= 0:
            wait_3()
            return to_discard

        self._show_shantins(hand_ana)

        almost_qh = False
        if self.decided_qh:
            if hand_ana.shantins[hand_ana.QH] == 1:
                almost_qh = True
            if hand_ana.shantins[hand_ana.QH] == 2 and self.turn_num < 10:
                almost_qh = True
        if self._dis_should_enforce(hand_ana) or self.decided_dy or almost_qh:
            to_discard = self._dis_spec_form(hand_ana)
            if to_discard >= 0:
                wait_3()
                return to_discard

        shantin = hand_ana.current_shantin
        to_discard = self.dis_funcs.get(shantin, self._dis_3_st)(hand_ana)
        self.thclient.drawer and self.thclient.drawer.set_enforce_form('')
        if to_discard >= 0:
            wait_3()
            return to_discard

        hand_def = [tile for tile in self.hand34 if tile > 26] + sorted(self.hand34, key=lambda x: 4 - abs(x % 9 - 4))
        self.thclient.drawer and self.thclient.drawer.set_enforce_form('')
        for tile in hand_def:
            if self.can_discard(tile, hand_ana):
                wait_3()
                return self.tile_34_to_136(tile)
        self.thclient.drawer and self.thclient.drawer.set_enforce_form('')
        return self.tile_34_to_136(hand_def[0])

    def _dis_check_waiting(self, hand_ana):
        num_turn = len(self.discard34)
        waiting_dict = WaitingAnalyser.check_waiting(self, False)
        indices = list(range(len(waiting_dict)))

        def prio19(t):
            return 0 if t in Tile.ONENINE else 4 - abs(t % 9 - 4)

        indices.sort(key=lambda x: prio19(waiting_dict[x][0]))
        indices.sort(key=lambda x: -len(waiting_dict[x][1]['w_tiles']))
        indices.sort(key=lambda x: -waiting_dict[x][1]['remain_num'])
        indices.sort(key=lambda x: -waiting_dict[x][1]['ave_score'])
        # can discard
        if len(indices) > 1:
            any_can_discard = None
            for index in indices:
                to_discard = waiting_dict[index][0]
                if self.can_discard(to_discard, hand_ana):
                    any_can_discard = index
                    break
            if any_can_discard:
                to_discard = waiting_dict[any_can_discard][0]
                tmp_dict = waiting_dict[any_can_discard][1]
                self._show_waiting(tmp_dict['waitings'])
                return self.tile_34_to_136(to_discard)

        # high score
        for index in indices:
            to_discard = waiting_dict[index][0]
            tmp_dict = waiting_dict[index][1]
            score = tmp_dict['ave_score']
            remain = tmp_dict['remain_num']
            self._show_waiting(tmp_dict['waitings'])
            if num_turn <= 13:
                if (score >= 5800 and remain > 1) or self.can_discard(to_discard, hand_ana):
                    self._show_waiting(tmp_dict['waitings'])
                    return self.tile_34_to_136(to_discard)
            else:
                if (score >= 8000 and remain > 2) or self.can_discard(to_discard, hand_ana):
                    self._show_waiting(tmp_dict['waitings'])
                    return self.tile_34_to_136(to_discard)
        return -1

    def _dis_should_enforce(self, hand_ana):
        if hand_ana.shantins[hand_ana.NORMAL] == hand_ana.shantins[hand_ana.QH]:
            return True
        if hand_ana.shantins[hand_ana.NORMAL] == hand_ana.shantins[hand_ana.PPH]:
            return True
        if self.game_table.round_number >= 3:
            scores = sorted(self.game_table.scores)
            self_score = self.score
            rk = scores.index(self.score)
            if rk == 3:
                return False
            if rk == 2 and abs(self_score - scores[3]) < 1500:
                return False
            if rk < 3 and abs(self_score - scores[3]) <= 6000:
                return True
        if self.is_open_hand:
            if (self.game_table.has_reach or self.potential_fan >= 3) and self.has_dori:
                return False
        else:
            if self.potential_fan >= 3:
                return False
        return True

    def _dis_spec_form(self, hand_ana: HandAnalyser):
        enforce_eff = hand_ana.enforce_eff_vec(self.turn_num, self)
        if enforce_eff:
            self.thclient.drawer and self.thclient.drawer.set_tile_eff(enforce_eff)
            for i in range(len(enforce_eff)):
                if self.can_discard(enforce_eff[i][0], hand_ana):
                    return self.tile_34_to_136(enforce_eff[i][0])
        return -1

    def _dis_3_st(self, hand_ana: HandAnalyser):
        useless_tile = self._dis_3_st_chr()
        if useless_tile >= 0:
            return useless_tile
        discard_3shantin = self._dis_1_st(hand_ana)
        if discard_3shantin >= 0:
            return discard_3shantin
        return -1

    def _dis_3_st_chr(self):
        self.thclient.drawer and self.thclient.drawer.set_tile_eff([])
        for chr_tile in range(27, 34):
            if chr_tile not in self.bonus_honors:
                if self.hand34.count(chr_tile) == 1:
                    return self.tile_34_to_136(chr_tile)
        for chr_tile in range(27, 34):
            if chr_tile in self.bonus_honors:
                if self.hand34.count(chr_tile) == 1:
                    if self.game_table.revealed_tiles[chr_tile] > 0 and self.turn_num < 7:
                        return self.tile_34_to_136(chr_tile)

        # TODO: is this needed?
        dict19 = []
        for one in [0, 9, 18]:
            if self.hand34.count(one) == 1 and (one + 1) not in self.hand34 and (one + 2) not in self.hand34:
                dict19.append([one, 0 if one + 3 in self.hand34 else 1])
        for nine in [8, 17, 26]:
            if self.hand34.count(nine) == 1 and (nine - 1) not in self.hand34 and (nine - 2) not in self.hand34:
                dict19.append([nine, 0 if (nine - 3) in self.hand34 else 1])
        if len(dict19) > 0:
            dict19 = sorted(dict19, key=lambda x: x[1])
            return self.tile_34_to_136(dict19[0][0])

        return -1

    def _dis_2_st(self, hand_ana: HandAnalyser):
        effectiveness = hand_ana.deep_eff_vec(self)
        self.thclient.drawer and self.thclient.drawer.set_tile_eff(effectiveness)
        prios_str = ','.join(["{}-{:2.1f}".format(Tile.t34_to_g(p[0]), p[1]) for p in effectiveness])
        msg = "        🤖[2 shantin eff]: {}".format(prios_str)
        self._post_msg(msg)
        for i in range(len(effectiveness)):
            if self.can_discard(effectiveness[i][0], hand_ana):
                return self.tile_34_to_136(effectiveness[i][0])
        if len(effectiveness) == 0:
            return self._dis_1_st(hand_ana)
        else:
            return self.tile_34_to_136(effectiveness[0][0])

    def _dis_1_st(self, hand_ana: HandAnalyser):
        prios = hand_ana.norm_eff_vec(self)
        self.thclient.drawer and self.thclient.drawer.set_tile_eff(prios)
        prios_str = ','.join(["{}-{:2.1f}".format(Tile.t34_to_g(p[0]), p[1]) for p in prios])
        msg = "        🤖[1 shantin eff]: {}".format(prios_str)
        self._post_msg(msg)
        for i in range(len(prios)):
            if self.can_discard(prios[i][0], hand_ana):
                return self.tile_34_to_136(prios[i][0])
        return self.tile_34_to_136(prios[0][0])

    def _can_discard_chr(self, candidate, hand_ana):
        is_bonus_chr = (candidate in self.game_table.bonus_tiles)
        num_reaveal = self.game_table.revealed_tiles[candidate]
        hand_num = self.hand34.count(candidate)
        round_num = len(self.discard34)
        if hand_num == 3:
            return False
        if candidate in self.bonus_honors:
            if hand_num == 2:
                if is_bonus_chr:
                    return False
                want_to_make_pinhu = (hand_ana.current_shantin == hand_ana.shantins[hand_ana.PINHU] <= 2)
                if num_reaveal < 2 and not want_to_make_pinhu:
                    return False
            if hand_num:
                if is_bonus_chr:
                    if num_reaveal < 2 and round_num > 12:
                        return False
        elif is_bonus_chr:
            if hand_num == 2 or (hand_num == 1 and round_num > 12 and num_reaveal < 2):
                return False
        return True

    def can_discard(self, t34, hand_ana):
        if t34 > 26:
            return self._can_discard_chr(t34, hand_ana)
        if t34 == self.game_table.last_discard:
            return True
        if (t34 in self.game_table.last_round_discard or self.turn_num < 7) and not self.game_table.has_reach:
            return True

        wall_safe_tiles = self.game_table.barrier_safe_tiles
        # near_bonus = self._is_near_bonus(t34)

        can_discard = True
        for i in range(1, 4):
            opp_obj = self.game_table.get_player(i)
            if not opp_obj.is_valid:
                continue
            total_waiting = opp_obj.waiting_prediction
            safe_tiles = opp_obj.abs_safe_tiles
            gin_safes = opp_obj.gin_safe_tiles
            if can_discard:
                if t34 in safe_tiles:
                    continue
                elif t34 in total_waiting:
                    if opp_obj.dangerous:
                        if opp_obj.is_freezing:
                            if t34 in gin_safes + wall_safe_tiles and random.uniform(0, 1) <= 0.3:
                                continue
                            else:
                                can_discard = False
                        else:
                            if t34 in gin_safes + wall_safe_tiles and random.uniform(0, 1) <= 0.5:
                                continue
                            else:
                                can_discard = False
                    else:
                        if t34 in gin_safes + wall_safe_tiles and random.uniform(0, 1) <= 0.7:
                            continue
                        else:
                            can_discard = False
                elif opp_obj.is_freezing:
                    if t34 in gin_safes + wall_safe_tiles and random.uniform(0, 1) <= 0.5:
                        continue
                    else:
                        can_discard = False
                elif opp_obj.dangerous:
                    if (t34 % 9 < 3 and t34 + 3 in total_waiting) or (6 <= t34 % 9 and t34 - 3 in total_waiting):
                        if t34 in wall_safe_tiles + gin_safes and random.uniform(0, 1) <= 0.6:
                            continue
                        else:
                            can_discard = False

        return can_discard

    def can_call_reach(self):
        """
        :return: False, 0 if can not call reach, else True, corresponding_to_be_discarded_tile
        """
        if self.is_open_hand:
            return False, 0

        hand_ana = self._get_hand_ana()

        richii, to_discard_34, remain, win_dict = WaitingAnalyser.should_richii(self, hand_ana)
        if richii:
            self.called_reach = True
            self.to_discard_after_reach = to_discard_34
            self.thclient.drawer and self.thclient.drawer.set_shantins(hand_ana)
            self._show_waiting(win_dict)
            self.riichi_waiting = win_dict
            return True, self.tile_34_to_136(to_discard_34)

        return False, 0

    def should_call_kan(self, tile136, from_opponent):
        tile34 = tile136 // 4
        hand_ana = self._get_hand_ana()
        shantin = hand_ana.current_shantin
        if shantin > 3:
            return False, False

        def can_kan():
            if tile34 > 26:
                return True
            opens = hand_ana.all_melds
            for m in opens:
                if len(m) == 3 and m[0] != m[1]:
                    if tile34 in m:
                        msg = '        🤖 Tile is in a chow, do not KAN'
                        self._post_msg(msg)
                        return False
            return True

        if from_opponent:
            # minkan
            if not can_kan() or tile34 in self.game_table.bonus_tiles:
                self.not_kan = tile136
                return False, False
            if self.game_table.has_reach:
                self.not_kan = tile136
                self._post_msg('        🤖 Someone has reach, do not KAN')
                return False, False
            if self.game_table.kan_num >= 2:
                self.not_kan = tile136
                self._post_msg('        🤖 Too many kans, do not KAN')
                return False, False
            if hand_ana.sp_decided:
                self.not_kan = tile136
                self._post_msg('        🤖 Decide to form Seven pairs, do not KAN')
                return False, False
            should_kan = False
            if self.hand34.count(tile34) == 3:
                if tile34 in self.bonus_honors:
                    self._post_msg('        🤖 Bonus honors, KAN!')
                    should_kan = True
                if hand_ana.pp_decided or self.decided_pph:
                    self._post_msg('        🤖 Decide to form ponpon, KAN!')
                    self.decided_pph, should_kan = True, True
                if hand_ana.qh_decided(len(self.discard34)) and (tile34 // 9 in hand_ana.qh_type() or tile34 // 9 == 3):
                    self._post_msg('        🤖 Decide to form qing/hun, KAN!')
                    self.decided_qh, should_kan = True, True
                if self.decided_dy:
                    self._post_msg('        🤖 Can make danyao, KAN!')
                    self.decided_dy, should_kan = True, True
                if self.has_dori:
                    self._post_msg('        🤖 Has dori, KAN!')
                    should_kan = True
            # handle kan
            if should_kan:
                self_tiles = [t for t in self.tiles136 if t // 4 == tile34]
                for t in self_tiles:
                    self.tiles136.remove(t)
                msg = "        😊[Call minkan]: {}".format(Tile.t34_to_g([tile136 // 4] * 4))
                self._post_msg(msg)
                return Meld.KAN, tile136
            else:
                self.not_kan = tile136
        else:
            # ankan
            ankan_tile = None
            if self.hand34.count(tile34) == 4:
                ankan_tile = tile34
            else:
                own_tile = [tile for tile in set(self.hand34) if self.hand34.count(tile) == 4]
                if own_tile and len(own_tile) > 0:
                    ankan_tile = own_tile[0]
            if ankan_tile:
                if self.reach_status and not self.game_table.has_reach and can_kan():

                    self._post_msg('        🤖 Only bot riichis, KAN!')
                    msg = "        🤖[Bot calls ankan]: {}".format(Tile.t34_to_g([ankan_tile] * 4))
                    self._post_msg(msg)
                    return Meld.KAN, self.tile_34_to_136(ankan_tile)
                if not can_kan() or self.game_table.has_reach:
                    self._post_msg('        🤖 Someone called riichi, NOT KAN!')
                    return False, False
                msg = "        🤖[Bot calls ankan]: {}".format(Tile.t34_to_g([ankan_tile] * 4))
                self._post_msg(msg)
                return Meld.KAN, self.tile_34_to_136(ankan_tile)
            # chakan
            for meld in self.meld136:
                if meld.tiles[0] // 4 == meld.tiles[1] // 4 == tile34:
                    if not can_kan() or self.game_table.has_reach:
                        self._post_msg('        🤖 Someone called riichi, NOT KAN!')
                        return False, False
                    msg = "        🤖[Bot calls chakan]: {}".format(Tile.t34_to_g([tile136 // 4] * 4))
                    self._post_msg(msg)
                    return Meld.CHANKAN, tile136

        return False, False

    def try_to_call_meld(self, tile136, might_call_chi):
        # check if bot can win this tile
        if self.reach_status:
            return None, None

        if WaitingAnalyser.can_win(self, tile136 // 4):
            self._post_msg('        🤖 Can win this tile')
            return None, None

        hand_ana = self._get_hand_ana()
        shantin = hand_ana.current_shantin
        can_make_danyao = self._can_make_danyao(hand_ana)
        tile34 = tile136 // 4
        all_melds = hand_ana.all_melds

        # check if better to stay close hand
        if self._better_not_to_call_meld(hand_ana, tile34):
            return None, None

        # check if calling meld might improve waiting
        meld, tag = self._call_meld_check_waiting_improve(tile136, might_call_chi, hand_ana)
        if meld and tag == 0:
            return meld, 0
        if meld == 1 and tag == 1:
            return None, None

        # check if calling meld could make it waiting
        meld, tag = self._call_meld_check_waiting(tile136, might_call_chi, hand_ana)
        if meld:
            return meld, 0

        # if tile34 was not kanned, then also not pon
        if self.not_kan and self.not_kan == tile136:
            if tile34 > 26 or all(tile34 not in m for m in all_melds if len(m) == 3 and m[0] != m[1]):
                return None, None

        # always pon dori honors
        if self.hand34.count(tile34) == 2 and tile34 in self.bonus_honors:
            if shantin > 1 or self.game_table.revealed_tiles[tile34] > 0 or self.turn_num >= 6:
                self._post_msg('        🤖 Always call dori honors!')
                self_tiles = [t136 for t136 in self.tiles136 if t136 // 4 == tile136 // 4]
                self._post_msg("        🤖[Bot calls pon]: {}".format(Tile.t34_to_g([tile34] * 3)))
                return Meld(Meld.PON, sorted(self_tiles[0:2] + [tile136]), True, tile136), 0

        # hand tiles too bad, better not call meld
        if shantin >= 4:
            self._post_msg('        🤖 Terrible hand tiles, do not call meld!')
            return None, None

        # check pon for special form
        if self.hand34.count(tile34) >= 2:
            should_pon = False
            # Case: decided to form "ponpon"
            if hand_ana.pp_decided or self.decided_pph:
                self._post_msg('        🤖 Decide to form PPH, PON!!!')
                self.decided_pph, should_pon = True, True
            # Case: decided to form "qing/hun"
            if (hand_ana.qh_decided(self.turn_num) or self.decided_qh) and tile34 // 9 in (hand_ana.qh_type() + [3]):
                reduce_shantin = self._call_pon_reduce_shantin(
                    self.hand34, self.total_melds34, hand_ana.shantins[hand_ana.QH], hand_ana.QH, tile34
                )
                if reduce_shantin:
                    self._post_msg('        🤖 Decide to form QH, PON!!!')
                    self.decided_qh, should_pon = True, True
            # Case: neither "qing/hun" nor "seven pairs", check "danyao" and "dori"
            if not hand_ana.sp_decided:
                if self.has_dori:
                    reduce_shantin = self._call_pon_reduce_shantin(
                        self.hand34, self.total_melds34, hand_ana.shantins[hand_ana.NORMAL], hand_ana.NORMAL, tile34
                    )
                    if reduce_shantin:
                        self._post_msg('        🤖 Already have dori, PON!!!')
                        should_pon = True
                if (can_make_danyao or self.decided_dy) and tile34 not in Tile.ONENINE:
                    reduce_shantin = self._call_pon_reduce_shantin(
                        self.hand34, self.total_melds34, hand_ana.shantins[hand_ana.NO19], hand_ana.NO19, tile34
                    )
                    if reduce_shantin:
                        self._post_msg('        🤖 Can make Danyao, PON!!!')
                        self.decided_dy, should_pon = True, True

            if should_pon:
                self_tiles = [t136 for t136 in self.tiles136 if t136 // 4 == tile136 // 4]
                self._post_msg("        🤖[Bot calls pon]: {}".format(Tile.t34_to_g([tile136 // 4] * 3)))
                return Meld(Meld.PON, self_tiles[0:2] + [tile136], True, tile136), 0

        # check chow for special form
        if might_call_chi and tile34 < 27:
            if hand_ana.pp_decided or self.decided_pph:
                self._post_msg('        🤖 Is making PPH, not CHOW!!!')
                return None, None
            if hand_ana.sp_decided:
                self._post_msg('        🤖 Is making 7P, not CHOW!!!')
                return None, None
            candidates = self._get_chow_candidates(tile34)
            if len(candidates) == 0:
                return None, None
            for candidate in candidates:
                should_chow = False
                if hand_ana.qh_decided(self.turn_num) or self.decided_qh:
                    if tile34 // 9 in hand_ana.qh_type():
                        reduce_shantin = self._call_chow_reduce_shantin(
                            self.hand34, self.total_melds34, hand_ana.shantins[hand_ana.QH], hand_ana.QH,
                            candidate[0], candidate[1], tile34
                        )
                        if reduce_shantin:
                            self._post_msg('        🤖 Decide to form qing/hun, CHOW!!!')
                            self.decided_qh, should_chow = True, True
                if can_make_danyao or self.decided_dy:
                    if all(0 < tile % 9 < 8 for tile in (candidate + [tile34])):
                        reduce_shantin = self._call_chow_reduce_shantin(
                            self.hand34, self.total_melds34, hand_ana.shantins[hand_ana.NO19], hand_ana.NO19,
                            candidate[0], candidate[1], tile34
                        )
                        if reduce_shantin:
                            self._post_msg('        🤖 Decide to form Danyao, CHOW!!!')
                            self.decided_dy, should_chow = True, True
                if self.has_dori:
                    reduce_shantin = self._call_chow_reduce_shantin(
                        self.hand34, self.total_melds34, hand_ana.shantins[hand_ana.NORMAL], hand_ana.NORMAL,
                        candidate[0], candidate[1], tile34
                    )
                    if reduce_shantin:
                        self._post_msg('        🤖 Already has dori, CHOW!!!')
                        should_chow = True
                if should_chow:
                    opt1, opt2 = self.tile_34_to_136(candidate[0]), self.tile_34_to_136(candidate[1])
                    msg = "        😊[Bot calls chow]: {}".format(Tile.t34_to_g(candidate + [tile34]))
                    self._post_msg(msg)
                    return Meld(Meld.CHI, sorted([opt1, opt2, tile136]), True, tile136), 0

        return None, None

    def _call_pon_reduce_shantin(self, handtiles, melds, currentshantin, form, pontile):
        if handtiles.count(pontile) >= 2:
            tmp_handtiles = deepcopy(handtiles)
            tmp_handtiles.remove(pontile)
            tmp_handtiles.remove(pontile)
            tmp_melds = deepcopy(melds)
            tmp_melds.append([pontile] * 3)
            forms = [0] * 6
            forms[form] = 1
            tmp_handana = HandAnalyser(tmp_handtiles, tmp_melds, forms, self.bonus_honors, self.game_table.revealed_tiles, self.game_table.bonus_tiles)
            if tmp_handana.shantins[form] < currentshantin:
                return True
        return False

    def _call_chow_reduce_shantin(self, handtiles, melds, currentshantin, form, op1, op2, chowtile):
        if op1 in handtiles and op2 in handtiles:
            tmp_handtiles = deepcopy(handtiles)
            tmp_handtiles.remove(op1)
            tmp_handtiles.remove(op2)
            tmp_melds = deepcopy(melds)
            tmp_melds.append(sorted([op1, op2, chowtile]))
            forms = [0] * 6
            forms[form] = 1
            tmp_handana = HandAnalyser(tmp_handtiles, tmp_melds, forms, self.bonus_honors, self.game_table.revealed_tiles, self.game_table.bonus_tiles)
            if tmp_handana.shantins[form] < currentshantin:
                return True
        return False

    def _better_not_to_call_meld(self, hand_ana, tile34):
        # almost riichi, do not call meld
        if not self.is_open_hand:
            if self.game_table.kan_num >= 1 and hand_ana.current_shantin < 2 and self.turn_num <= 12:
                self._post_msg('        🤖 There was kan and hand tiles are not bad, better to profit from richii')
                return True
            if (tile34 in self.bonus_honors and self.game_table.revealed_tiles[tile34] == 0) \
                    or tile34 not in self.bonus_honors:
                if hand_ana.current_shantin < 2 and self.turn_num <= 6:
                    self._post_msg('        🤖 Almost riichi, do not call meld!!!')
                    return True
                if hand_ana.shantins[hand_ana.PINHU] < 2 and self.turn_num <= 9:
                    self._post_msg('        🤖 Almost riichi and pinhu, do not call meld!!!')
                    return True
        return False

    def _call_meld_check_waiting_improve(self, tile136, might_call_chi, hand_ana):
        tile34 = tile136 // 4
        # check if calling pon might improve waiting
        waiting_dict = WaitingAnalyser.check_waiting_m1(self)
        if len(waiting_dict) > 0:
            if self.hand34.count(tile34) >= 2:
                waiting_dict_after_pon = WaitingAnalyser.check_waiting_after_pon(self, tile136)
                if len(waiting_dict_after_pon) > 0 and self.is_open_hand:
                    for w_dict in waiting_dict_after_pon:
                        remain_b, remain_a = waiting_dict['remain_num'], w_dict[1]['remain_num']
                        score_b, score_a = waiting_dict['ave_score'], w_dict[1]['ave_score']
                        improve_remain_num = remain_a > remain_b and abs(remain_a - remain_b) >= 2
                        improve_score = score_b > score_a + 500
                        if (improve_remain_num or improve_score) and self.can_discard(w_dict[0], hand_ana):
                            self_tiles = [t136 for t136 in self.tiles136 if t136 // 4 == tile136 // 4]
                            m_pon = Meld(Meld.PON, sorted(self_tiles[0:2] + [tile136]), True, tile136)
                            msg = "        🤖[Bot calls pon]: {}".format(Tile.t34_to_g([tile136 // 4] * 3))
                            self._post_msg(msg)
                            return m_pon, 0
            msg = "        🤖 Is waiting now, calling pon does not improve score"
            self._post_msg(msg)
        # check if calling chow might improve waiting
        if len(waiting_dict) > 0 and might_call_chi and tile34 < 27:
            chow_candidates = self._get_chow_candidates(tile34)
            for candidate in chow_candidates:
                waiting_dict_after_chow = WaitingAnalyser.check_waiting_after_chow(self, candidate, tile136)
                if len(waiting_dict_after_chow) > 0 and self.is_open_hand:
                    for w_dict in waiting_dict_after_chow:
                        remain_b, remain_a = waiting_dict['remain_num'], w_dict[1]['remain_num']
                        score_b, score_a = waiting_dict['ave_score'], w_dict[1]['ave_score']
                        improve_remain_num = remain_a > remain_b and abs(remain_a - remain_b) >= 2
                        improve_score = score_b > score_a + 500
                        if (improve_remain_num or improve_score) and self.can_discard(w_dict[0], hand_ana):
                            t1, t2 = self.tile_34_to_136(candidate[0]), self.tile_34_to_136(candidate[1])
                            m_chi = Meld(Meld.CHI, sorted([t1, t2, tile136]), True, tile136)
                            msg = "        🤖[Bot calls chow]: {}".format(Tile.t34_to_g(candidate + [tile34]))
                            self._post_msg(msg)
                            return m_chi, 0

        if len(waiting_dict) > 0:
            return 1, 1
        else:
            return None, None

    def _call_meld_check_waiting(self, tile136, might_call_chi, hand_ana):
        # check if waiting after pon
        if self.hand34.count(tile136 // 4) >= 2:
            waiting_dict_after_pon = WaitingAnalyser.check_waiting_after_pon(self, tile136)
            if len(waiting_dict_after_pon) > 0:
                for w_dict in waiting_dict_after_pon:
                    remain = w_dict[1]['remain_num']
                    score = w_dict[1]['ave_score']
                    if score < 2000 and not self.is_open_hand:
                        continue
                    if (self.can_discard(w_dict[0], hand_ana) and remain > 3) or (score >= 4000 and remain > 3):
                        self._post_msg('        🤖 Waiting after pon, PON!!!')
                        self_tiles = [t136 for t136 in self.tiles136 if t136 // 4 == tile136 // 4]
                        self._post_msg("        🤖[Bot calls pon]: {}".format(Tile.t34_to_g([tile136 // 4] * 3)))
                        return Meld(Meld.PON, sorted(self_tiles[0:2] + [tile136]), True, tile136), 0
        if not might_call_chi or tile136 // 4 > 26:
            return None, None
        # check if waiting after chow
        chow_candidates = self._get_chow_candidates(tile136 // 4)
        if len(chow_candidates) == 0:
            return None, None
        for candidate in chow_candidates:
            waiting_dict_after_chow = WaitingAnalyser.check_waiting_after_chow(self, candidate, tile136)
            if len(waiting_dict_after_chow) > 0:
                for w_dict in waiting_dict_after_chow:
                    remain = w_dict[1]['remain_num']
                    score = w_dict[1]['ave_score']
                    if score < 2000 and not self.is_open_hand:
                        continue
                    if (self.can_discard(w_dict[0], hand_ana) and remain > 3) or (score >= 4000 and remain > 3):
                        self._post_msg('        🤖 Waiting after chow, CHOW!!!')
                        t1, t2 = self.tile_34_to_136(candidate[0]), self.tile_34_to_136(candidate[1])
                        self._post_msg("        🤖[Bot calls pon]: {}".format(Tile.t34_to_g(candidate + [tile136 // 4])))
                        return Meld(Meld.CHI, sorted([t1, t2, tile136]), True, tile136), 0
        return None, None

    def _get_chow_candidates(self, tile34):
        candidates = []
        if tile34 % 9 > 1 and (tile34 - 2) in self.hand34 and (tile34 - 1) in self.hand34:
            candidates.append([tile34 - 2, tile34 - 1])
        if 8 > tile34 % 9 > 0 and (tile34 - 1) in self.hand34 and (tile34 + 1) in self.hand34:
            candidates.append([tile34 - 1, tile34 + 1])
        if 7 > tile34 % 9 and (tile34 + 1) in self.hand34 and (tile34 + 2) in self.hand34:
            candidates.append([tile34 + 1, tile34 + 2])

        def prio(x):
            if abs(x[0] - x[1]) == 2:
                return 1
            elif x[0] % 9 == 0 or x[1] % 9 == 8:
                return 0
            else:
                return 2

        if len(candidates) > 0:
            candidates = sorted(candidates, key=prio)

        return candidates

    def _can_make_danyao(self, hand_ana: HandAnalyser):
        if self.decided_dy:
            return True
        if hand_ana.shantins[hand_ana.NORMAL] and hand_ana.shantins[hand_ana.NO19] <= 2:
            for tile in set(self.hand34):
                if tile in Tile.ONENINE and tile in self.game_table.bonus_tiles:
                    return False
            if self.cnt_total_bonus_tiles >= 3:
                return True
            if self.cnt_total_bonus_tiles >= 2 and self.turn_num >= 10:
                return True
        return False

    def handle_opponent_discard(self, opp_index):
        opponent_obj = self.game_table.get_player(opp_index)
        if opponent_obj.reach_status:
            richii_f = opponent_obj.richii_feature_225(opp_index)
            opponent_obj.add_prediction(self.ensemble_clfs.predict_richii_single_prio(richii_f))
        else:
            normal_f = opponent_obj.waiting_feature_212(opp_index)
            opponent_obj.add_prediction(self.ensemble_clfs.predict_normal_single_prio(normal_f))

        self.thclient.drawer and self.thclient.drawer.set_prediction_history(opp_index, opponent_obj.waiting_prediction)

    def _get_hand_ana(self):
        return HandAnalyser(self.hand34, self.total_melds34, [1] * 6, self.bonus_honors, self.game_table.revealed_tiles, self.game_table.bonus_tiles)

    def log_opponents_prediction(self):
        prd_str = " " * 8 + "🤖[Waiting prediction] "
        for opp_index in range(1, 4):
            opponent_obj = self.game_table.get_player(opp_index)
            waitings = opponent_obj.waiting_prediction
            if len(waitings) > 0:
                prd_str += "P{}:{}".format(opp_index, Tile.t34_to_g(waitings))
        self.thclient.both_log(prd_str)

    def _is_near_bonus(self, t34):
        if self.turn_num > 12:
            return False
        first_bonus_tile = self.game_table.bonus_tiles[0]
        near_bonus = self.turn_num >= 9
        if near_bonus and t34 < 27:
            if first_bonus_tile // 9 == t34 // 9 and abs(first_bonus_tile - t34) <= 3:
                to_be_considered = []
                (abs(first_bonus_tile - t34) == 2) and to_be_considered.append((first_bonus_tile + t34) // 2)
                if abs(first_bonus_tile - t34) == 1:
                    left = min(first_bonus_tile, t34) - 1
                    (left // 9 == first_bonus_tile) // 9 and to_be_considered.append(left)
                    right = max(first_bonus_tile, t34) + 1
                    (right // 9 == first_bonus_tile // 9) and to_be_considered.append(right)
                abs(first_bonus_tile - t34) == 3 and to_be_considered.append(min(first_bonus_tile, t34) + 1)
                abs(first_bonus_tile - t34) == 3 and to_be_considered.append(max(first_bonus_tile, t34) - 1)
                if len(to_be_considered) > 0:
                    total_revealed = deepcopy(self.game_table.revealed_tiles)
                    for t in self.hand34:
                        total_revealed[t] += 1
                    if any(total_revealed[tile] > 2 for tile in to_be_considered):
                        near_bonus = False
            else:
                near_bonus = False
        if t34 > 26 and t34 == first_bonus_tile and self.turn_num >= 9:
            near_bonus = True
        return near_bonus

    def _show_shantins(self, hand_ana):
        self.thclient.drawer and self.thclient.drawer.set_shantins(hand_ana)
        msg = '        🤖[Shantins]: {}'.format(hand_ana)
        self._post_msg(msg)

    def _show_waiting(self, waiting_dict):
        total_revealed = deepcopy(self.game_table.revealed_tiles)
        for t in self.hand34:
            total_revealed[t] += 1
        waiting_str = ','.join([
            "{} {} {}".format(4 - total_revealed[k], Tile.t34_to_g(k), v)
            for k, v in waiting_dict.items()
        ])
        total_remain = sum([4 - total_revealed[k] for k, v in waiting_dict.items()])
        msg = '        😊 [Waiting]: {}, total remain: {}'.format(waiting_str, total_remain)
        self._post_msg(msg)
        waiting_lst = [[k, v, 4 - total_revealed[k]] for k, v in waiting_dict.items()]
        self.thclient.drawer and self.thclient.drawer.set_waiting(waiting_lst)

    def show_riichi_waiting(self):
        if self.reach_status and self.riichi_waiting:
            self._show_waiting(self.riichi_waiting)

    def _post_msg(self, msg):
        self.thclient.both_log(msg)

    def erase_states(self):
        self.called_reach = False
        self.to_discard_after_reach = -1
        self.decided_pph = False
        self.decided_dy = False
        self.not_kan = None
        self.decided_qh = False
        self.riichi_waiting = None

    @property
    def has_dori(self):
        for meld in self.total_melds34:
            if meld[0] > 26 and meld[0] in self.bonus_honors:
                return True
        for tile in self.bonus_honors:
            if self.hand34.count(tile) >= 3:
                return True
        return False

    @property
    def opponents(self):
        return [self.game_table.get_player(i) for i in range(1, 4)]

    @property
    def total_tiles34(self):
        return [t // 4 for t in self.total_tiles136]

    @property
    def total_tiles136(self):
        return self.tiles136 + [t for meld in self.meld136 for t in meld.tiles]

    @property
    def potential_fan(self):
        return self.cnt_total_bonus_tiles + self.cnt_open_fan + self.cnt_hand_fan

    @property
    def cnt_total_bonus_tiles(self):
        cnt = len([t136 for t136 in self.total_tiles136 if t136 in Tile.RED_BONUS])
        cnt += sum([self.game_table.bonus_tiles.count(t) for t in self.total_tiles34])
        return cnt

    @property
    def cnt_open_fan(self):
        res = 0
        for m in self.total_melds34:
            if m[0] > 26 and m[0] in self.bonus_honors:
                res += (m[0] == self.round_wind) + (m[0] == self.player_wind) + (m[0] in Tile.THREES)
        return res

    @property
    def cnt_hand_fan(self):
        res = 0
        for tile in self.bonus_honors:
            res += self.hand34.count(tile) >= 3
        return res

    @property
    def total_revealed(self):
        revealed = deepcopy(self.game_table.revealed_tiles)
        for t in self.hand34:
            revealed[t] += 1
        return revealed

    @property
    def is_all_last(self):
        return self.game_table.round_number >= 3

    @property
    def current_rank(self):
        return sorted(self.game_table.scores).index(self.score)

    @property
    def need_scores(self):
        res = []
        for score in self.game_table.scores:
            if score > self.score:
                res.append(score - self.score)
        if max(self.game_table.scores) < 30000:
            res.append(30000 - self.score)
        return res
