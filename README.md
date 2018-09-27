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

The implemented client allows one to run a Mahjong agent directly through the programm, instead of doing this in the web browser. The site for online playing of Japanese Riichi Mahjong is http://tenhou.net/
***

### <a name="run"></a>How to run the proposed Mahjong agent?
To run the Mahjong agent, one has to specify a few configurations. As shown in the following example from main.py:
```python
def run_example_ai():
    ai_module = importlib.import_module("agents.random_ai_example")
    ai_class = getattr(ai_module, "RandomAI")
    ai_obj = ai_class()  # [1]
    player_module = importlib.import_module("client.mahjong_player")
    opponent_class = getattr(player_module, "OpponentPlayer")  # [2]
    user = "ID696E3BCC-hLHNE8Wf"  # [3]
    user_name = "tst_tio"  # [4]
    game_type = '1'  # [5]
    logger_obj = Logger("log1", user_name)  # [6]
    connect_and_play(ai_obj, opponent_class, user, user_name, '0', game_type, logger_obj)  # play one game
```

1. **AI instance**: A class instance of the Mahjong agent. In this repository two versions of Mahjong agent are provided. The first one is in ***agents.random_ai_example.py***, this is a demo class for showing potential developers how to implement his/her own agents. The second one is in ***agents.jianyang_ai.py*** and it is my own Mahjong agent for my master thesis. 

2. **Opponent player class**: The class of Opponent player. One can use the default class OpponentPlayer in ***client.mahjong_player***. If one has extended the OpponentPlayer class due to extra needs, this variable should be set to your corresponding class.

3. **User ID**: A token in the form as shown in the example that one got after registration on tenhou.net. ***ATTENTION: Please use your own user ID. If the same ID is used under different IP address too often, the account will be temperorily blocked by tenhou.net.***

4. **User name**: The corresponding user name you have created while registrating on tenhou.net. This variable is only for identifying your test logs. 

5. **Game type**: The game type is encoded as a 8-bit integer. Followings are the description for each bit.

    * 0-th: 1 play with online players, 0 play with robots
    * 1-th: 1 no red bonus tiles, 0 with red bonus tiles
    * 2-th: 1 no open tanyao, 0 with open tanyao
    * 3-th: 1 only east+south round (regurarily 8 rounds), 0 only east round (4 rounds)
    * 4-th: 1 three players (two opponents), 0 four players (three opponents)
    * 6-th: 1 fast game (7s for decision making), 0 slow game (15s)
    * 5-th & 7-th: game room 00-starter, 01-upper, 10-mega upper, 11-phoenix
    
    For examples:
    
    * "1" = "00000001": with online real human players, with red bonus tiles, with open tanyao, 4 rounds, 4 players, slow game, starter game room
    * "137" = "10001001": with online real human players, with red bonus tiles, with open tanyao, 8 rounds, 4 players, slow game, upper game room
    * "193" = "11000001": with online real human players, with red bonus tiles, with open tanyao, 4 rounds, 4 players, fast game, upper game room
    
    ```diff
    - Tenhou.net does not provide all possibility of the above specified combinations. Most online players play on configurations for example "1", "137", "193", "9"
    ```

6. **Logger**: Two parameters are required for initialising the logger. The first one is the user-defined logger's ID, such that developers can freely name his/her test history. 

After specifying all these configurations, just throw all these parameters to connect_and_play(). Then it's time watch the show of your Mahjong agent!!!

***

### <a name="dev"></a>How to develop your own Mahjong agent?

***
