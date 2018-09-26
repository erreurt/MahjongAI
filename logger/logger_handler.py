# -*- coding: utf-8 -*-
import logging

import datetime

import os

__author__ = "Jianyang Tang"
__email__ = "jian4yang2.tang1@gmail.com"


class Logger:

    def __init__(self, log_id, ai_id, buffer_mode=False):
        self.log_id = log_id
        self.ai_id = ai_id
        self.scores_path = ""
        self.rank_path = ""
        self.buffer_mode = buffer_mode
        self.logger_buffer = []
        self._set_up_logger()
        self.lg = logging.getLogger('{}_{}'.format(log_id, ai_id))

    def _set_up_logger(self):
        root_dir = os.path.dirname(os.path.abspath("__file__"))
        logs_directory = root_dir + "/logger/{}/".format(self.log_id)
        if not os.path.isdir(logs_directory):
            os.mkdir(logs_directory)
        raw_dir = logs_directory + "raw/"
        if not os.path.isdir(raw_dir):
            os.mkdir(raw_dir)
        logger = logging.getLogger('{}_{}'.format(self.log_id, self.ai_id))
        logger.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        file_name = '{}_{}.log'.format(self.ai_id, datetime.datetime.now().strftime('%Y-%m-%d_%H_%M_%S'))
        fh = logging.FileHandler(raw_dir + file_name)
        fh.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        ch.setFormatter(formatter)
        fh.setFormatter(formatter)
        logger.addHandler(ch)
        logger.addHandler(fh)
        self.scores_path = logs_directory + "{}_result.txt".format(self.ai_id)
        self.rank_path = logs_directory + "ranks.txt"

    def add_line(self, msg):
        self.lg.info(msg)

    def flush_buffer(self):
        self.add_line('    ' + '-' * 50)
        for bf_msg in self.logger_buffer:
            self.add_line(bf_msg)
        self.logger_buffer = []

    def add_round_end_result(self, msg):
        open(self.scores_path, 'a').write(msg)

    def add_game_end_result(self, rk):
        if os.path.isfile(self.rank_path):
            ranks = [int(r.split(':')[1]) for r in open(self.rank_path, 'r').read().split("\n")[0:4]]
        else:
            ranks = [0] * 4
        ranks[rk] += 1
        open(self.rank_path, 'w').write("".join(["Rank {}: {} : {:.2f}%\n".format(i, ranks[i - 1], 100*ranks[i-1]/sum(ranks)) for i in range(1, 5)]))