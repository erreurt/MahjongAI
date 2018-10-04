# -*- coding: utf-8 -*-
import datetime
import os
import socket
from threading import Thread
from time import sleep
from urllib.parse import quote

from client.mahjong_table import GameTable
from client.tenhou_parser import TenhouParser
from client.mahjong_meld import Meld
from client.mahjong_tile import Tile

__author__ = "Jianyang Tang"
__email__ = "jian4yang2.tang1@gmail.com"

TENHOU_HOST = '133.242.10.78'
TENHOU_PORT = 10080
IS_TOURNAMENT = False
JOINING_GAME_TIMEOUT = 2
MSG_LOGGER = False
BUFFER_MODE = True


class TenhouClient:

    def __init__(self, ai_obj, opponent_class, user_id, user_name, lobby_type, game_type, logger_obj, drawer=None):
        self.game_table = GameTable(ai_obj, opponent_class, self)
        self.drawer = drawer
        self.logger_obj = logger_obj
        self.user_id = user_id
        self.user_name = user_name
        self.lobby = lobby_type
        self.game_type = game_type
        self.WAIT_FOR_A_WHILE = 0.5
        self.skt = None
        self.continue_game = True
        self.looking_for_game = True
        self.keep_alive_thread = None
        self.reconnection_message = None
        self.win_suggestions = ['t="8"', 't="9"', 't="10"', 't="11"', 't="12"', 't="13"', 't="15"']

    def connect(self):
        self.skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.skt.connect((TENHOU_HOST, TENHOU_PORT))

    def authenticate(self):
        # send authentication request
        self._send('<HELO name="{}" tid="f0" sx="M" />'.format(quote(self.user_id)))
        msgs = self._get()
        auth_msg = None
        if len(msgs) > 0:
            auth_msg = msgs[0]
        else:
            self._log("    Authentication message was not received")
            return False
        # handle reconnection message
        if '<GO' in auth_msg:
            self._log('    Reconnected successfully!')
            self.drawer and self.drawer.is_searching("Reconnected successfully")
            self.reconnection_message = msgs
            game_type = int(TenhouParser.get_attribute_value(auth_msg, 'type'))
            self._parse_game_rule(game_type)
            names_and_levels = TenhouParser.parse_names_and_levels(msgs[1])
            self.game_table.set_personal_info(names_and_levels)
            return True
        # handle authentication message
        auth_code, rating, new_level = TenhouParser.parse_auth_msg(auth_msg)
        if not auth_code:
            self._log("    Authentication code was not received!")
            return False
        if new_level:
            self._log('     Achieved a new level --> {}'.format(new_level))
        # send authentication token
        auth_token = TenhouParser.generate_auth_token(auth_code)
        self._send('<AUTH val="{}"/>'.format(auth_token))
        self._send(self._pxr_tag())
        # waiting for confirmation from server
        waiting_count = 0
        authenticated = False
        while waiting_count < 11:
            msgs = self._get()
            for msg in msgs:
                if '<LN' in msg:
                    authenticated = True
                    break
            if authenticated:
                break
            waiting_count += 1
        # result
        if authenticated:
            self._keep_alive()
            self._log('    User({}) was authenticated successfully'.format(self.user_id))
            return True
        else:
            self._log('    Error: Failed to authenticate!')
            return False

    def start_game(self):
        if not self._looking_for_a_game():
            return False

        meld_tile = None
        last_reply = datetime.datetime.now()

        while self.continue_game:
            self._wait_for_a_while()
            msgs = self._get()
            was_rec = False
            if self.reconnection_message:
                was_rec = True
                msgs = self.reconnection_message + msgs
                self.reconnection_message = None

            if len(msgs) > 0:
                last_reply = datetime.datetime.now()

            for msg in msgs:
                # initialization
                '<INIT' in msg and self._handle_initial_msg(msg)

                # reconnection
                '<REINIT' in msg and self._handle_reconnection_msg(msg)

                # bot draws
                if '<T' in msg:
                    if self._win_check_after_drawing(msg):
                        continue
                    if self._handle_draw_tile(msg):
                        continue

                # opponents draw tiles
                if not was_rec:
                    who = ['<U' in msg, '<V' in msg, '<W' in msg]
                    if any(who):
                        self.both_log("    [Player {}] draws a tile...".format(who.index(True) + 1))
                        self.drawer and self.drawer.opp_draw(who.index(True) + 1)

                # new bonus indicator revealed
                '<DORA' in msg and self._handle_new_bonus_indicator(msg)

                # someone has claimed Riichi
                '<REACH' in msg and 'step="1"' in msg and self._handle_reach_claim(msg)

                # a round ends
                '<AGARI' in msg and self._handle_round_end(msg)
                '<RYUUKYOKU' in msg and self._handle_liuju(msg)

                # someone has called a Meld
                '<N who=' in msg and self._handle_meld_call(msg, meld_tile)

                # bot can win
                any(m in msg for m in self.win_suggestions) and self._call_win(msg)

                # someone discards
                if TenhouParser.is_discard_msg(msg):
                    res = self._handle_opponent_discard(msg)
                    if res == -1:
                        continue
                    elif res != -2:
                        meld_tile = res

                # the whole game ends
                'owari' in msg and self._handle_final_scores(msg)

                if '<PROF' in msg:
                    self.continue_game = False

                last_reply = datetime.datetime.now()

            if (datetime.datetime.now() - last_reply).seconds > 30:
                self.logger_obj.add_line('Socket connection might be shut down... {}s'.format(
                    (datetime.datetime.now() - last_reply).seconds))
                self.end_game(False)
                return False

        self.end_game()
        return True

    def end_game(self, success=True):
        self.continue_game = False
        if success:
            self._send('<BYE />')
        if self.keep_alive_thread:
            self.keep_alive_thread.join()
        try:
            self.skt.shutdown(socket.SHUT_RDWR)
            self.skt.close()
        except OSError as e:
            print(e)
        if success:
            self._log('    Game End')
            self._log('')
        else:
            self._log('    Game was ended unexpected')
            self._log('')

    # Following are all subroutines of function start_game(),  w.r.t. game process controlling
    def _looking_for_a_game(self):
        replay_link = ''

        # try to join into a game
        if self.reconnection_message:
            self.looking_for_game = False
            self._send('<GOK />')
            self._wait_for_a_while()
            self._log('    Reconnected. Resuming game state...')
        else:
            game_type = '{},{}'.format(self.lobby, self.game_type)
            if not IS_TOURNAMENT:
                self.drawer and self.drawer.is_searching("Search for a game...")
                self._log('    🔍Search for a game...')
                self._send('<JOIN t="{}" />'.format(game_type))
                self.drawer and self.drawer.is_searching("Join request sent...")
                self._log('    🔍Join request sent...')

            start_time = datetime.datetime.now()
            while self.looking_for_game:
                self._wait_for_a_while()
                msgs = self._get()
                for msg in msgs:
                    self.drawer and self.drawer.is_searching(
                        "Searching, {}s passed...".format((datetime.datetime.now() - start_time).seconds))

                    if '<REJOIN' in msg:
                        self._send('<JOIN t="{}, r" />'.format(game_type))
                        self._log('    🔍Rejoin request sent...')
                        self.drawer and self.drawer.is_searching("Rejoin request sent...")

                    if '<GO' in msg:
                        self._send('<GOK /')
                        self._send('<NEXTREADY />')
                        actual_game_type = TenhouParser.parse_game_type(msg)
                        rules_parsed = self._parse_game_rule(actual_game_type)
                        if not rules_parsed:
                            self.logger_obj.add_line('Three man is not supported yet!')
                            self.end_game(success=False)
                            return

                    if '<TAIKYOKU' in msg:
                        self.looking_for_game = False
                        log_referer, seat = TenhouParser.parse_log_link(msg)
                        log_title = "\n[Time] {}\n".format(datetime.datetime.now())
                        log_title += '[Game history link] http://tenhou.net/0/?log={}&tw={}\n'.format(log_referer, seat)
                        self._round_end_info_to_file(log_title)
                        replay_link += 'http://tenhou.net/0/?log={}&tw={}'.format(log_referer, seat)

                    if '<UN' in msg:
                        names_and_levels = TenhouParser.parse_names_and_levels(msg)
                        self.game_table.set_personal_info(names_and_levels)

                    if '<LN' in msg:
                        self._send(self._pxr_tag())

                current_time = datetime.datetime.now()
                time_difference = current_time - start_time

                if len(msgs):
                    self._log("    🔍{} seconds passed...".format(time_difference.seconds))

                if len(msgs) and time_difference.seconds > 60 * JOINING_GAME_TIMEOUT:
                    break

        # End game if did not found a game when time runs out
        if self.looking_for_game:
            self.logger_obj.add_line('    Cannot find any open game')
            self.drawer and self.drawer.is_searching("Can not find any game...")
            self.end_game()
            return False

        # Game started
        if not self.reconnection_message:
            self._log('    A new game started!')
            self._log('    The replay link can be found here: {}'.format(replay_link))
            self._log('    Players are: {}'.format([self.game_table.bot] + self.game_table.opponents))
            self.drawer and self.drawer.is_searching("A new game is found...")

        return True

    def _handle_reconnection_msg(self, msg):
        self.drawer and self.drawer.clear_objs()
        self._handle_initial_msg(msg)
        players = TenhouParser.parse_after_reconnection(msg)
        for i in range(0, 4):
            p = players[i]
            p_melds = []
            for discard in p['discards']:
                self.game_table.discard_tile(i, discard)
                self.drawer and self.drawer.discard(discard, i)
            for meld in p['melds']:
                self.game_table.call_meld(i, meld)
                p_melds.append(meld.tiles)
            if p['reach']:
                self.game_table.call_reach(i)
                self.drawer and self.drawer.reach(i)
            i != 0 and self.drawer and self.drawer.update_opp(p_melds, i)
            if i == 0:
                self.game_table.bot.tiles136 = sorted(self.game_table.bot.tiles136)
                self.drawer and self.drawer.update_self(self.game_table.bot.tiles136, p_melds)
        self._round_end_info_to_file("    Reconnected here: Round {}, Turn {}\n".format(
            self.game_table.round_number, len(self.game_table.bot.discard34)
        ))

    def _handle_initial_msg(self, msg):
        init_info = TenhouParser.parse_initial_states(msg)
        self.game_table.init_round(
            init_info['round_number'],
            init_info['honba_sticks'],
            init_info['reach_sticks'],
            init_info['bonus_tile_indicator'],
            init_info['dealer'],
            init_info['scores']
        )
        tiles = TenhouParser.parse_initial_hand(msg)
        tiles = sorted(tiles)
        self.game_table.bot.init_hand(tiles)

        # display in GUI
        if self.drawer:
            self.drawer.init_hand(tiles)
            self.drawer.init_round_info(
                init_info['round_number'] + 1,
                init_info['honba_sticks'],
                init_info['reach_sticks'],
                init_info['dealer']
            )
            for indicator in init_info['bonus_tile_indicator']:
                self.drawer.add_bonus_indicator(indicator)
            names = [self.game_table.get_player(i).name for i in range(0, 4)]
            scores = [self.game_table.get_player(i).score for i in range(0, 4)]
            levels = [self.game_table.get_player(i).level for i in range(0, 4)]
            self.drawer.add_name_and_scores(names, scores, levels)

        # display initial message in logs
        self._log('    ' + '-' * 50)
        self._log('    ' + self.game_table.__str__())
        self._log('    Players: {}'.format([self.game_table.bot] + self.game_table.opponents))
        self._log('    Dealer: {}'.format(self.game_table.get_player(init_info['dealer'])))
        self._log('    Round  wind: {}'.format(Tile.tile_graph_dict[self.game_table.round_wind]))
        self._log('    Player wind: {}'.format(Tile.tile_graph_dict[self.game_table.bot.player_wind]))
        self._log(' ')

    def _handle_new_bonus_indicator(self, msg):
        tile = TenhouParser.parse_bonus_indicator(msg)
        # save data to objects
        self.game_table.add_bonus_indicator(tile)
        # display in logs
        new_bi_msg = '    New bonus tile indicator revealed: {}'.format(Tile.t136_to_g([tile]))
        self.both_log(new_bi_msg)
        # display in GUI
        self.drawer and self.drawer.add_bonus_indicator(tile)
        self.drawer and self.drawer.set_remain(self.game_table.count_remaining_tiles)

    def _handle_final_scores(self, msg):
        self.logger_obj.flush_buffer()
        final_scores = TenhouParser.parse_final_scores(msg)
        # save data
        self.game_table.set_players_scores(final_scores['scores'], final_scores['uma'])
        # save game result to logs
        scores = final_scores['scores']
        self_rank = sorted(scores, key=lambda x: -x).index(scores[0])
        self.logger_obj.add_game_end_result(self_rank)
        self._round_end_info_to_file(",".join([str(self.game_table.get_player(i)) for i in range(4)]) + "\n\n")
        # display game result in logs
        self._log('    Round end: {}'.format([self.game_table.bot] + self.game_table.opponents))

    def _handle_round_end(self, msg=''):
        self.logger_obj.flush_buffer()
        self.logger_obj.add_line('')
        self.logger_obj.add_line("    {}".format(msg))

        # parse message
        who = int(TenhouParser.get_attribute_value(msg, 'who'))
        from_whom = int(TenhouParser.get_attribute_value(msg, 'fromWho'))
        win_tile_136 = int(TenhouParser.get_attribute_value(msg, 'machi'))
        hand_tiles_136 = TenhouParser.parse_initial_hand(msg)
        win_score = TenhouParser.parse_win_score(msg)
        if win_tile_136 in hand_tiles_136:
            hand_tiles_136.remove(win_tile_136)

        # save in logs
        who_str = "{}{}".format(
            who, "(Riichi)" if self.game_table.get_player(who).reach_status else ""
        )
        from_whom_str = "{}{}".format(
            from_whom, "(Riichi)" if self.game_table.get_player(from_whom).reach_status else ""
        )
        res_str = "    [Round-{} Turn-{} Dealer-{}]\n".format(
            self.game_table.round_number, len(self.game_table.bot.discard34), self.game_table.dealer_seat
        )
        res_str += "        [Win]:{}  [By]:{}  [Score]:{}  [Tile]:{} {} \n".format(
            who_str, from_whom_str, win_score, win_tile_136 // 4, Tile.t34_to_g(win_tile_136 // 4)
        )
        hand_tiles_34 = [t // 4 for t in hand_tiles_136] if who != 0 else self.game_table.bot.hand34
        win_tile_34 = win_tile_136 // 4
        meld_tiles_34 = self.game_table.get_player(who).meld34
        res_str += " " * 8 + "[Winning Hand] "
        res_str += "{}+{}+{}".format(
            Tile.t34_to_g(hand_tiles_34), ''.join([Tile.t34_to_g(m) for m in meld_tiles_34]), Tile.t34_to_g(win_tile_34)
        )
        res_str += "  {}+{}+{}\n".format(
            hand_tiles_34, ''.join(["{}".format(m) for m in meld_tiles_34]), win_tile_34
        )
        self._round_end_info_to_file(res_str)

        # display in logs
        if from_whom == who:
            win_msg = "    Player {} wins by own drawn tile {}".format(
                who, Tile.t34_to_g(win_tile_136 // 4)
            )
        else:
            win_msg = "    Player {} wins from player {}'s discard {}".format(
                who, from_whom, Tile.t34_to_g(win_tile_136 // 4)
            )
        self.both_log(win_msg)

        win_melds = self.game_table.get_player(who).meld34
        win_tiles_msg = "    {} {}+ {}, {}p".format(
            Tile.t136_to_g(hand_tiles_136),
            "+{}".format(Tile.t34_to_g(win_melds)) if len(win_melds) > 0 else '',
            Tile.t136_to_g(win_tile_136),
            win_score
        )
        self.both_log(win_tiles_msg)
        self.both_log('')

        # display in GUI
        if self.drawer:
            from_whom != who and self.drawer.lose(from_whom, win_score)
            from_whom != who and self.drawer.yong(who, win_score)
            from_whom == who and self.drawer.zimo(who, win_score)
            if who != 0:
                p_melds = [meld.tiles for meld in self.game_table.get_player(who).meld136]
                p_melds += [hand_tiles_136]
                p_melds += [[win_tile_136]]
                self.drawer.update_opp(p_melds, who, True)
            else:
                self.drawer.draw(win_tile_136)

        self._flush_buffer()
        self._wait_for_a_while()
        sleep(2)
        self._send('<NEXTREADY />')

    def _handle_liuju(self, msg):
        self._round_end_info_to_file("    [R{}T{}] NO ONE WINS, NO MORE TILES...".format(
            self.game_table.round_number, len(self.game_table.bot.discard34))
        )
        self.both_log("    NO ONE WINS, NO MORE TILES...\n")
        self.drawer and self.drawer.liuju()

        opp_tiles_dict = {}
        for i in range(1, 4):
            opp_tiles = TenhouParser.parse_opp_tiles(msg, i)
            if opp_tiles and len(opp_tiles) > 0:
                opp_tiles_dict[i] = opp_tiles
        if len(opp_tiles_dict) > 0:
            for k, v in opp_tiles_dict.items():
                tiles34 = [t // 4 for t in v]
                self._round_end_info_to_file("        FT-P{}:{}:{}\n".format(k, Tile.t34_to_g(tiles34), tiles34))
                p_melds = [meld.tiles for meld in self.game_table.get_player(k).meld136]
                p_melds += [v]
                self._log(Tile.t136_to_g(p_melds))
                if self.drawer:
                    self.drawer.update_opp(p_melds, k, True)

        # prd_str = '        WP '
        # for i in range(1, 4):
        #     waitings = self.game_table.get_player(i).waiting_prediction
        #     prd_str += "• P{}:{}:{} ".format(i, waitings, Tile.t34_to_g(waitings))
        # prd_str += '\n'
        # self._round_end_info_to_file(prd_str)

        self.logger_obj.flush_buffer()
        self._wait_for_a_while()
        sleep(2)
        self._send('<NEXTREADY />')

    def _handle_reach_claim(self, msg):
        who_called_reach = TenhouParser.parse_who_called_reach(msg)

        self.game_table.call_reach(who_called_reach)

        if self.drawer:
            self.drawer.reach(who_called_reach)

        reach_msg = '    Reach was called by {}-th player: {}'.format(
            who_called_reach, self.game_table.get_player(who_called_reach)
        )
        self.both_log(reach_msg)
        self._stream_log('')

    def _call_win(self, msg):
        self._wait_for_a_while()
        self._send('<N type="6" />')

    def _win_check_after_drawing(self, msg):
        win_suggestions = ['t="16"', 't="48"']
        if any(m in msg for m in win_suggestions):
            self._send('<N type="7" />')
            return True
        if 't="64"' in msg:  # 九種九牌
            self._send('<N type="9" />')
            return True
        return False

    def _handle_draw_tile(self, msg):
        drawn_tile_136 = TenhouParser.parse_tile(msg)
        self.drawer and self.drawer.draw(drawn_tile_136)

        if not self.game_table.bot.reach_status:
            # print own hand tiles
            own_hand_str = '    [Bot] draws a tile: {}'.format(self.game_table.bot.format_hand(drawn_tile_136))
            self.game_table.bot.draw_tile(drawn_tile_136)
            self._stream_log('')
            self.both_log(own_hand_str)
            self._wait_for_a_while()

            # check if bot can call reach
            can_call_reach, to_discard_136 = self.game_table.bot.can_call_reach()
            if can_call_reach:
                self._send('<REACH hai="{}"/>'.format(to_discard_136))
                self.game_table.bot.call_reach()
                self._wait_for_a_while()

            # check if bot can call a kan set
            kan_type, kaned_tile136 = self.game_table.bot.should_call_kan(drawn_tile_136, False)
            if kan_type and self.game_table.count_remaining_tiles > 0:
                meld_type = 5 if kan_type == Meld.CHANKAN else 4
                self._send('<N type="{}" hai="{}"/>'.format(meld_type, kaned_tile136))
                return True

            # bot decides what to discard
            discard_tile_136 = self.game_table.bot.to_discard_tile()
            self.game_table.bot.tiles136.remove(discard_tile_136)
            discard_msg = '    [Bot] discards: {} + {}'.format(
                Tile.t34_to_g(self.game_table.bot.discard34),
                Tile.t136_to_g([discard_tile_136])
            )
            self.both_log(discard_msg)
            bot_hand_msg = '    [Bot] hand tiles after discarding: {}'.format(
                self.game_table.bot.str_hand_tiles()
            )
            self.both_log(bot_hand_msg)
        else:
            discard_tile_136 = drawn_tile_136
            own_hand_str = '    Own hand: {}'.format(self.game_table.bot.format_hand(drawn_tile_136))
            self._stream_log('')
            self.both_log(own_hand_str)

            if callable(getattr(self.game_table.bot, 'log_opponents_prediction', None)):
                self.game_table.bot.log_opponents_prediction()
            if callable(getattr(self.game_table.bot, 'show_riichi_waiting', None)):
                self.game_table.bot.show_riichi_waiting()

            discard_msg = '        🤖[Bot(Richii) discards]: {} + {}'.format(
                Tile.t34_to_g(self.game_table.bot.discard34), Tile.t136_to_g([discard_tile_136])
            )
            self.both_log(discard_msg)

        self._send('<D p="{}"/>'.format(int(discard_tile_136)))
        self.game_table.discard_tile(0, discard_tile_136)

        remain_tiles_msg = '    Remaining tiles: {}'.format(self.game_table.count_remaining_tiles)
        self._stream_log('')
        self.both_log(remain_tiles_msg)

        self._flush_buffer()

        self.drawer and self.drawer.set_remain(self.game_table.count_remaining_tiles)
        self._stream_log('')

        self.drawer and self.drawer.discard(discard_tile_136, 0)

        self.game_table.bot.tiles136 = sorted(self.game_table.bot.tiles136)

        self.drawer and self.drawer.update_self(self.game_table.bot.tiles136,
                                                [meld.tiles for meld in self.game_table.bot.meld136])

        return False

    def _handle_meld_call(self, msg, meld_tile):
        player_hand = self.game_table.bot.format_hand(meld_tile) if meld_tile else ''
        meld = TenhouParser.parse_meld(msg)

        if meld.by_whom != 0:
            self.game_table.call_meld(meld.by_whom, meld)
            meld_msg = '    [Player {}] called meld: {}'.format(meld.by_whom, meld)
            self.both_log(meld_msg)
            if self.drawer:
                p_melds = [meld.tiles for meld in self.game_table.get_player(meld.by_whom).meld136]
                self.drawer.update_opp(p_melds, meld.by_whom)

        if meld.by_whom == 0:
            self.game_table.bot.call_meld(meld)
            if meld.type != Meld.KAN and meld.type != Meld.CHANKAN:

                discard_tile_136 = self.game_table.bot.to_discard_tile()
                own_hand_msg = '        [Bot] hand tiles: {}'.format(player_hand)
                discard_msg = '        [Bot] discards tile {} after called meld'.format(
                    Tile.t136_to_g([discard_tile_136]))
                self.both_log(own_hand_msg)
                self.both_log(discard_msg)
                self._stream_log('')
                self._send('<D p="{}"/>'.format(discard_tile_136))
                self.game_table.discard_tile(0, discard_tile_136)
                self.game_table.bot.tiles136.remove(discard_tile_136)

                if self.drawer:
                    self.drawer.discard(discard_tile_136, 0)
                    self.drawer.update_self(self.game_table.bot.tiles136,
                                            [meld.tiles for meld in self.game_table.bot.meld136])
            else:
                if self.drawer:
                    self.drawer.update_self(self.game_table.bot.tiles136,
                                            [meld.tiles for meld in self.game_table.bot.meld136])

        if callable(getattr(self.game_table.bot, 'handle_opponent_discard', None)):
            for i in range(1, 4):
                self.game_table.bot.handle_opponent_discard(i)

    def _handle_opponent_discard(self, msg):
        opponent_seat = TenhouParser.parse_opponent_seat(msg)
        if opponent_seat == 0:
            # if hasattr(self.game_table.bot, "update_part"):
            #     self.game_table.bot.update_part()
            return -1

        tile = TenhouParser.parse_tile(msg)
        opp_obj = self.game_table.get_player(opponent_seat)

        discard_tag = ['d', 'e', 'f', 'g']  # lower case alphabet means the player discards whatever he had drawn...
        was_direct = discard_tag[opponent_seat] in msg
        opp_obj.add_discard_type(was_direct)

        if hasattr(self.game_table.bot, "handle_opponent_discard"):
            self.game_table.bot.handle_opponent_discard(opponent_seat)

        self.game_table.discard_tile(opponent_seat, tile)
        self.drawer and self.drawer.discard(tile, opponent_seat)
        discard_msg = "    [Player {}] discards: {} + {}".format(opponent_seat, Tile.t34_to_g(opp_obj.discard34[:-1]), Tile.t136_to_g([tile]))
        discard_msg += ", melds: {}".format(Tile.t34_to_g(opp_obj.meld34)) if opp_obj.meld34 else ""
        self.both_log(discard_msg)

        # check meld call for bot
        if 't=' in msg:
            # check kan
            if 't="3"' in msg or 't="7"' in msg:
                if self.game_table.bot.should_call_kan(tile, True)[0] == Meld.KAN:
                    self._send('<N type="2" />')
                    kan_msg = '    [Bot] called an open kan: {}'.format(Tile.t34_to_g([tile // 4] * 4))
                    self.both_log(kan_msg)
                    return -1
            # check chow/pon
            may_call_chi = (msg[1].lower() == 'g')
            meld, tile_to_discard = self.game_table.bot.try_to_call_meld(tile, may_call_chi)
            if meld:
                meld_type = '3' if meld.type == Meld.CHI else '1'
                self_tiles = [t for t in meld.tiles if t != meld.called_tile]
                self._send('<N type="{}" hai0="{}" hai1="{}" />'.format(meld_type, self_tiles[0], self_tiles[1]))
                self.game_table.count_remaining_tiles += 1
                return tile
            else:
                self._wait_for_a_while()
                self._send('<N />')

        self.drawer and self.drawer.set_remain(self.game_table.count_remaining_tiles)

        return -2

    # Followling are all subroutines, different function, w.r.t. communication
    def _send(self, msg):
        msg_ = msg + '\0'
        try:
            self.skt.sendall(msg_.encode())
        except Exception as e:
            print(e)
            self.end_game(False)

    def _get(self):
        msgs = ""
        try:
            msgs = self.skt.recv(2048).decode('utf-8')
        except ConnectionResetError as er:
            print(er)
            sleep(0.1)
        msgs = msgs.split('\x00')
        return msgs[0:-1]

    def _pxr_tag(self):
        if IS_TOURNAMENT:
            return '<PXR V="-1" />'
        if self.user_id == 'NoName':
            return '<PXR V="1" />'
        else:
            return '<PXR V="9" />'

    def _keep_alive(self):
        def send_alive():
            while self.continue_game:
                self._send('<Z />')
                time_to_sleep = 15
                for i in range(2 * time_to_sleep):
                    if self.continue_game:
                        sleep(0.5)

        self.keep_alive_thread = Thread(target=send_alive)
        self.keep_alive_thread.start()

    def _wait_for_a_while(self):
        sleep(self.WAIT_FOR_A_WHILE)

    def _parse_game_rule(self, game_type):
        rules = bin(int(game_type)).replace('0b', '')[::-1]
        rules += '0' * (8 - len(rules))
        """ Game type decoding: 8-bit, 0-7 lowest-highest bit
        0-th: 1 play with online players, 0 play with robots
        1-th: 1 no red bonus tiles, 0 with red bonus tiles
        2-th: 1 no open tanyao, 0 with open tanyao
        3-th: 1 only east+south round, 0 only east round
        4-th: 1 three man, 0 four man
        6-th: 1 fast game, 0 slow game
        5-th & 7-th: game room 00-starter, 10-upper, 01-mega upper, 11-phoenix
        """
        if rules[4] == '1':  # three man game, not supported yet
            return False
        self.game_table.aka_dora = (rules[1] == '0')
        self.game_table.open_tanyao = (rules[2] == '0')
        self._log('    Game type = "Red bonus tile" : {0}, "Open tanyao" : {1}, "Game  length" : {2}'.format(
            self.game_table.aka_dora, self.game_table.open_tanyao, (rules[3] == '1') and "tonnansen" or "tonpusen"
        ))
        return True

    def _buffer_log(self, msg):
        self.logger_obj.buffer_mode and self.logger_obj.logger_buffer.append(msg)

    def _stream_log(self, msg):
        (not self.logger_obj.buffer_mode) and self.logger_obj.add_line(msg)

    def _log(self, msg):
        self.logger_obj.add_line(msg)

    def both_log(self, msg):
        self._buffer_log(msg)
        self._stream_log(msg)

    def _round_end_info_to_file(self, msg):
        self.logger_obj.add_round_end_result(msg)

    def _flush_buffer(self):
        self.logger_obj.add_line('    ' + '-' * 50)
        for bf_msg in self.logger_obj.logger_buffer:
            self.logger_obj.add_line(bf_msg)
        self.logger_obj.logger_buffer = []