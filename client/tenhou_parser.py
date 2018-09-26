# -*- coding: utf-8 -*-
import re
from urllib.parse import unquote

from client.mahjong_meld import Meld

__author__ = "Jianyang Tang"
__email__ = "jian4yang2.tang1@gmail.com"


class TenhouParser:

    LEVELS = [u'新人', u'9級', u'8級', u'7級', u'6級', u'5級', u'4級', u'3級', u'2級', u'1級',
              u'初段', u'二段', u'三段', u'四段', u'五段', u'六段', u'七段', u'八段', u'九段', u'十段',
              u'天鳳位']

    opponent_seat_dict = {'d': 0, 'e': 1, 'f': 2, 'g': 3}

    @staticmethod
    def parse_auth_msg(msg):
        rating, auth_code, new_level = '', '', ''
        if 'auth=' in msg:
            auth_code = TenhouParser.get_attribute_value(msg, 'auth')
            if 'PF4=' in msg:
                rating = TenhouParser.get_attribute_value(msg, 'PF4')
        if 'nintei' in msg:
            new_level = unquote(TenhouParser.get_attribute_value(msg, 'nintei'))
        return auth_code, rating, new_level

    @staticmethod
    def parse_names_and_levels(msg):
        levels = [int(level) for level in TenhouParser.get_attribute_value(msg, 'dan').split(',')]
        res = [{}, {}, {}, {}]
        for i in range(0, 4):
            res[i]['name'] = unquote(TenhouParser.get_attribute_value(msg, 'n{}'.format(i)))
            res[i]['level'] = TenhouParser.LEVELS[levels[i]]
        return res

    @staticmethod
    def parse_game_type(msg):
        return int(TenhouParser.get_attribute_value(msg, 'type'))

    @staticmethod
    def parse_log_link(msg):
        seat = int(TenhouParser.get_attribute_value(msg,'oya'))
        seat = (4 - seat) % 4
        log_referer = TenhouParser.get_attribute_value(msg, 'log')
        return log_referer, seat

    @staticmethod
    def parse_initial_states(msg):
        round_info = [int(s) for s in TenhouParser.get_attribute_value(msg, 'seed').split(',')]
        scores = [int(score) for score in TenhouParser.get_attribute_value(msg, 'ten').split(',')]
        dealer = int(TenhouParser.get_attribute_value(msg, 'oya'))
        return {
            'round_number': round_info[0],
            'honba_sticks': round_info[1],
            'reach_sticks': round_info[2],
            'bonus_tile_indicator': round_info[5:],
            'dealer': dealer,
            'scores': scores
        }

    @staticmethod
    def parse_initial_hand(msg):
        return [int(tile) for tile in TenhouParser.get_attribute_value(msg, 'hai').split(',')]

    @staticmethod
    def parse_opp_tiles(msg, player):
        attribute = 'hai{}'.format(player)
        if attribute in msg:
            return [int(tile) for tile in TenhouParser.get_attribute_value(msg, attribute).split(',')]

    @staticmethod
    def parse_win_score(msg):
        return [int(s) for s in TenhouParser.get_attribute_value(msg,'ten').split(',')][1]

    @staticmethod
    def parse_after_reconnection(msg):
        players = []
        for i in range(0, 4):
            player = {'discards': [], 'melds': [], 'reach': False}
            # parse discards
            discard_attr = 'kawa{}'.format(i)
            if discard_attr in msg:
                discards = TenhouParser.get_attribute_value(msg, discard_attr)
                discards = [int(x) for x in discards.split(',')]
                was_reach = 255 in discards
                if was_reach:
                    discards.remove(255)
                    player['reach'] = True
                player['discards'] = discards
            # parse melds
            melds_attr = 'm{}'.format(i)
            if melds_attr in msg:
                melds = TenhouParser.get_attribute_value(msg, melds_attr)
                melds = [int(x) for x in melds.split(',')]
                for meld in melds:
                    meld_message = '<N who="{}" m="{}" />'.format(i, meld)
                    meld = TenhouParser.parse_meld(meld_message)
                    player['melds'].append(meld)
            players.append(player)
        for p in players:
            for meld in p['melds']:
                players[meld.from_whom]['discards'].append(meld.called_tile)
        return players

    @staticmethod
    def parse_meld(msg):
        data = int(TenhouParser.get_attribute_value(msg, 'm'))
        meld = Meld()
        meld.by_whom = int(TenhouParser.get_attribute_value(msg, 'who'))
        meld.from_whom = data & 0x3  # '11'

        if data & 0x4:  # '100'
            meld = TenhouParser.parse_chi(data, meld)
        elif data & 0x18:  # '11000'
            TenhouParser.parse_pon(data, meld)
        elif data & 0x20:  # '100000'
            TenhouParser.parse_nuki(data, meld)
        else:
            TenhouParser.parse_kan(data, meld)
        return meld

    @staticmethod
    def parse_chi(data, meld):
        # chow encoding     xxxxxx    |    0    |    xx    |    xx     |   xx   |   x        |   xx
        #                base/which                 tile3     tile2      tile1     is chow       who called
        # e.g. 100000       0       11      01        00      1      11
        # 11: player 3 called this meld
        # 1: is a chow set
        # 00: first of four tiles
        # 01: second of four tiles
        # 11: fourth of four tiles
        # 0: no meaning
        # 100000: =32  32//3 = 10 --> the tenth chow set is 456p
        #              32 % 3 = 2 --> the third tile was the called tile
        # totally: player 3 called the meld 456p with 6p
        meld.type = Meld.CHI
        t0, t1, t2 = (data >> 3) & 0x3, (data >> 5) & 0x3, (data >> 7) & 0x3
        base_and_called = data >> 10
        base = base_and_called // 3
        called = base_and_called % 3
        base = (base // 7) * 9 + base % 7
        meld.tiles = [t0 + 4 * (base + 0), t1 + 4 * (base + 1), t2 + 4 * (base + 2)]
        meld.called_tile = meld.tiles[called]
        return meld

    @staticmethod
    def parse_pon(data, meld):
        t4 = (data >> 5) & 0x3
        t0, t1, t2 = ((1, 2, 3), (0, 2, 3), (0, 1, 3), (0, 1, 2))[t4]
        base_and_called = data >> 9
        base = base_and_called // 3
        called = base_and_called % 3
        if data & 0x8:
            meld.type = Meld.PON
            meld.tiles = [t0 + 4 * base, t1 + 4 * base, t2 + 4 * base]
            meld.called_tile = meld.tiles[called]
        else:
            meld.type = Meld.CHANKAN
            meld.tiles = [t0 + 4 * base, t1 + 4 * base, t2 + 4 * base, t4 + 4 * base]
            meld.called_tile = meld.tiles[3]

    @staticmethod
    def parse_kan(data, meld):
        base_and_called = data >> 8
        base = base_and_called // 4
        meld.type = Meld.KAN
        meld.tiles = [4 * base, 1 + 4 * base, 2 + 4 * base, 3 + 4 * base]
        called = base_and_called % 4
        meld.called_tile = meld.tiles[called]
        # to mark closed\opened kans
        meld.open = meld.by_whom != meld.from_whom

    @staticmethod
    def parse_nuki(data, meld):
        meld.type = Meld.NUKI
        meld.tiles = [data >> 8]

    @staticmethod
    def parse_tile(msg):
        result = re.match(r'^<[tefgEFGTUVWD]+\d*', msg).group()
        return int(result[2:])

    @staticmethod
    def parse_bonus_indicator(msg):
        return int(TenhouParser.get_attribute_value(msg, 'hai'))

    @staticmethod
    def parse_who_called_reach(msg):
        return int(TenhouParser.get_attribute_value(msg, 'who'))

    @staticmethod
    def parse_final_scores(msg):
        data = TenhouParser.get_attribute_value(msg, 'owari')
        data = [float(i) for i in data.split(',')]
        return {'scores': data[::2], 'uma': data[1::2]}

    @staticmethod
    def parse_opponent_seat(msg):
        return TenhouParser.opponent_seat_dict[msg.lower()[1]]

    @staticmethod
    def is_discard_msg(msg):
        if '<GO' in msg:
            return False
        if '<FURITEN' in msg:
            return False
        match_discard = re.match(r"^<[defgDEFG]+\d*", msg)
        if match_discard:
            return True
        return False

    @staticmethod
    def get_attribute_value(msg, attr_name):
        result = re.findall(r'{}="([^"]*)"'.format(attr_name), msg)
        return result and result[0] or None

    @staticmethod
    def generate_auth_token(auth_code):
        translation_table = [63006, 9570, 49216, 45888, 9822, 23121, 59830, 51114, 54831, 4189, 580, 5203, 42174, 59972,
                             55457, 59009, 59347, 64456, 8673, 52710, 49975, 2006, 62677, 3463, 17754, 5357]

        parts = auth_code.split('-')
        if len(parts) != 2:
            return False
        first_part, second_part = parts[0], parts[1]
        if len(first_part) != 8 or len(second_part) != 8:
            return False

        table_index = int('2' + first_part[2:8]) % (12 - int(first_part[7:8])) * 2
        a = translation_table[table_index] ^ int(second_part[0:4], 16)
        b = translation_table[table_index + 1] ^ int(second_part[4:8], 16)
        postfix = format(a, '2x') + format(b, '2x')

        return first_part + '-' + postfix
