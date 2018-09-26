# -*- coding: utf-8 -*-
import random

from agents.ai_interface import AIInterface
from client.mahjong_meld import Meld
from client.mahjong_tile import Tile

__author__ = "Jianyang Tang"
__copyright__ = "Copyright 2018, Mahjong AI Master Thesis"
__email__ = "jian4yang2.tang1@gmail.com"


class RandomAI(AIInterface):

    def to_discard_tile(self):
        """
        This method has to be implemented. It has access to all information listed in the instruction.
        :return: A tile in hand to be discarded
        """
        # TODO: discard a tile by your own strategy
        l = len(self.tiles136)
        ind = random.randint(0, l-1)
        return self.tiles136[ind]

    def should_call_kan(self, tile136, from_opponent):
        """
        This method has to be implemented. It decides whether the bot should call a Kan(Quad) meld. A Kan meld is set of
        four identical tiles. There are three kinds of Quad sets. (1) MINKAN: When the bot has three identical tiles
        in hand and the opponent discards the fourth tile. (2) KAN: When the bot has all four identical tiles in hand.
        (3) CHAKAN: When the bot has an open Triplet meld and it draws the fourth tile, the bot can update this Triplet
        meld to a Kan meld
        :param tile136: The involved kan tile in 136 form
        :param from_opponent: Whether the tile was from opponent
        :return: [Kan type], [to be called tile] if should call Kan else False, False
        """
        tile34 = tile136 // 4

        if from_opponent:  # (1) Check Minkan
            should_kan = True  # TODO: should be decided by your own strategy
            if should_kan:
                # the tiles in hand should be removed from the set of hand tiles after having decided
                self_tiles = [t for t in self.tiles136 if t // 4 == tile34]
                for t in self_tiles:
                    self.tiles136.remove(t)
                # developer could access self.thclient.both_log(msg) to display content in logs
                msg = "        [Bot calls minkan]: {}".format(Tile.t34_to_g([tile136 // 4] * 4))
                self.thclient.both_log(msg)
                # return the result
                return Meld.KAN, tile136
        else:  # (2) Check Kan
            ankan_tile = None
            if self.hand34.count(tile34) == 4:  # bot gots the fourth tile at this turn
                ankan_tile = tile34
            else:
                own_tile = [tile for tile in set(self.hand34) if self.hand34.count(tile) == 4]
                if own_tile and len(own_tile) > 0:  # bot had a kan in hand before and did not call kan
                    ankan_tile = own_tile[0]
            if ankan_tile:
                should_call_ankan = True  # TODO: should be decided by your own strategy
                if should_call_ankan:
                    msg = "        🤖[Bot calls ankan]: {}".format(Tile.t34_to_g([ankan_tile] * 4))
                    self.thclient.both_log(msg)
                    return Meld.KAN, self.tile_34_to_136(ankan_tile)
            # (3) Check Chakan
            for meld in self.meld136:
                if meld.tiles[0] // 4 == meld.tiles[1] // 4 == tile34:
                    should_call_chakan = True  # TODO: should be decided by your own strategy
                    if should_call_chakan:
                        msg = "        🤖[Bot calls chakan]: {}".format(Tile.t34_to_g([tile136 // 4] * 4))
                        self.thclient.both_log(msg)
                        return Meld.CHANKAN, tile136

        return False, False

    def try_to_call_meld(self, tile136, might_call_chi):
        """
        This method has to be implemented. It decides whether to call a meld or not.
        :param tile136: the involved opponent's discard in 136 form
        :param might_call_chi: whether is it possible to call CHI
        :return: [Meld object], 0 if should call meld else return False, False
        """
        tile34 = tile136 // 4

        # (1) Check Pon
        if self.hand34.count(tile34) >= 2:
            should_call_pon = True  # TODO: should be decided by your own strategy
            if should_call_pon:
                self_tiles = [t136 for t136 in self.tiles136 if t136 // 4 == tile136 // 4]
                msg = "        🤖[Bot calls pon]: {}".format(Tile.t34_to_g([tile136 // 4] * 3))
                self.thclient.both_log(msg)
                return Meld(Meld.PON, self_tiles[0:2] + [tile136], True, tile136), 0

        # (2) Check Chi
        if might_call_chi and tile34 < 27:
            # There might be multiple possibilities to call Chi
            chi_candidates = []
            if tile34 % 9 > 1 and (tile34 - 2) in self.hand34 and (tile34 - 1) in self.hand34:
                chi_candidates.append([tile34 - 2, tile34 - 1])
            if 8 > tile34 % 9 > 0 and (tile34 - 1) in self.hand34 and (tile34 + 1) in self.hand34:
                chi_candidates.append([tile34 - 1, tile34 + 1])
            if 7 > tile34 % 9 and (tile34 + 1) in self.hand34 and (tile34 + 2) in self.hand34:
                chi_candidates.append([tile34 + 1, tile34 + 2])
            for candidate in chi_candidates:
                should_chi = True  # TODO: should be decided by your own strategy
                if should_chi:
                    opt1, opt2 = self.tile_34_to_136(candidate[0]), self.tile_34_to_136(candidate[1])
                    msg = "        😊[Bot calls chow]: {}".format(Tile.t34_to_g(candidate + [tile34]))
                    self.thclient.both_log(msg)
                    return Meld(Meld.CHI, sorted([opt1, opt2, tile136]), True, tile136), 0

        return False, False

    def can_call_reach(self):
        """
        This method has to be implemented. It decides whether to claim Riichi or not.
        :return: True, 0 if yes else False, 0
        """
        if self.is_open_hand:  # not possible to claim Riichi if bot has an open hand
            return False, 0

        should_riichi = False  # TODO: should be decided by your own strategy
        discard_after_reach = None  # TODO: should be decided by your own strategy
        if should_riichi:
            self.called_reach = True
            self.to_discard_after_reach = discard_after_reach
            return True, self.tile_34_to_136(discard_after_reach)

        return False, 0

    def handle_opponent_discard(self, opp_seat):
        """
        Optional to be implemented. Here comes the handling after any opponent discards a tile. For example updating of
        the status of opponents model etc. Once it is implemented, it will be called automatically by the client.
        :param opp_seat: seat number of opponent
        :return: none
        """
        pass