# -*- coding: utf-8 -*-
import importlib

from logger.logger_handler import Logger
from client.tenhou_client import TenhouClient

__author__ = "Jianyang Tang"
__email__ = "jian4yang2.tang1@gmail.com"


def connect_and_play(ai_obj, opponent_class, user, username, lobbytype, gametype, logger_obj, drawer=None):
    client = TenhouClient(ai_obj, opponent_class, user, username, lobbytype, gametype, logger_obj, drawer)
    client.connect()
    try:
        success_auth = client.authenticate()
        if success_auth:
            return client.start_game()
        else:
            client.end_game()
            return False
    except KeyboardInterrupt:
        logger_obj.add_line('End the game...')
        client.end_game()
    except Exception as e:
        logger_obj.lg.exception('Unexpected exception', exc_info=e)
        logger_obj.add_line('End the game...')
        client.end_game(False)
        return False


def run_example_ai():
    # the OBJECT of your own implemented Mahjong agent
    ai_module = importlib.import_module("agents.random_ai_example")
    ai_class = getattr(ai_module, "RandomAI")
    ai_obj = ai_class()

    # the CLASS of your extended OpponentPlayer, or the default one in mahjong_player.py
    player_module = importlib.import_module("client.mahjong_player")
    opponent_class = getattr(player_module, "OpponentPlayer")

    user = "ID696E3BCC-hLHNE8Wf"      # the user ID that you got after having registered in tenhou.net
    user_name = "tst_tio"      # the user name that you have created while registration in tenhou.net

    game_type = '1'      # '137' 南 '193' 东速高

    logger_obj = Logger("log1", user_name)      # two arguments: id of your test epoch, user name

    connect_and_play(ai_obj, opponent_class, user, user_name, '0', game_type, logger_obj)  # play one game


def run_jianyang_ai(drawer=None):
    ai_module = importlib.import_module("agents.experiment_ai")
    waiting_prediction_class = getattr(ai_module, "EnsembleCLF")
    ensemble_clfs = waiting_prediction_class()
    ai_class = getattr(ai_module, "MLAI")
    ai_obj = ai_class(ensemble_clfs)
    opponent_class = getattr(ai_module, "OppPlayer")

    user = "ID696E3BCC-hLHNE8Wf"  # the user ID that you got after having registered in tenhou.net
    user_name = "tst_tio"  # the user name that you have created while registration in tenhou.net

    game_type = '1'  # '137' 南 '193' 东速高

    logger_obj = Logger("log_jianyang_ai_1", user_name)  # two arguments: id of your test epoch, user name

    connect_and_play(ai_obj, opponent_class, user, user_name, '0', game_type, logger_obj, drawer)  # play one game


def main():
    run_jianyang_ai()


if __name__ == '__main__':
    main()