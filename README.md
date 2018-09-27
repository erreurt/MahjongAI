# README -- MahjongAI
This file is to show how to run the intelligent Mahjong agent.

For developers who are interested in implementing own agents, instructions on how to use the client are given.

Also the test result of my Mahjong agent will be presented.

****

|Author|Jianyang Tang|
|---|---
|E-mail|jian4yang2.tang1@gmail.com

****

## Contents
* [Game rules of Japanese Riichi Mahjong](#rules)
* [How to run the proposed Mahjong agent](#run)
* [How to develop your own Mahjong agent](#dev)
***

### <a name="rules"></a>Game rules of Japanese Riichi Mahjong
Refer to https://en.wikipedia.org/wiki/Japanese_Mahjong for game rules of Japanese Riichi Mahjong. 

The implemented client allows one to run a Mahjong agent directly through the programm, instead of doing this in the web browser. The site for Japanese Riichi Mahjong is http://tenhou.net/
***

### <a name="run"></a>How to run the proposed Mahjong agent?
To run the Mahjong agent, one has to specify a few configurations. As shown in main.py:
```python
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

```

***

### <a name="dev"></a>How to develop your own Mahjong agent?

***
