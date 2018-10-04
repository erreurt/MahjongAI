# -*- coding: utf-8 -*-
import os
from tkinter import *
from PIL import ImageTk, Image, ImageFont, ImageDraw
from main import run_jianyang_ai


__author__ = "Jianyang Tang"
__copyright__ = "Copyright 2018, Mahjong AI Master Thesis"
__email__ = "jian4yang2.tang1@gmail.com"


MSG_BAR = 15
HEIGHT = 730
WIDTH = int(2.6 * HEIGHT / 2 + MSG_BAR)
dark_green_blue = "#17252a"  # "#242424" # "#001a19"  # "#002d2c"
light_green_blue = "#74a4a4"  # "#548383"
lighter_gray = "#eeeeee"  # "#8e8e8e"
darker_gray = "#8e8e8e"
fresh_red = "#ff2c2d"
fresh_blue = '#337499'
dark_blue = "#3b6491"


def get_alpha_color(original, bg, alpha):
    r1 = int(bg[1:3], base=16)
    g1 = int(bg[3:5], base=16)
    b1 = int(bg[5:7], base=16)
    r2 = int(original[1:3], base=16)
    g2 = int(original[3:5], base=16)
    b2 = int(original[5:7], base=16)
    r3 = r2 + int((r1 - r2) * alpha)
    g3 = g2 + int((g1 - g2) * alpha)
    b3 = b2 + int((b1 - b2) * alpha)
    return '#' + "{:02x}".format(r3) + "{:02x}".format(g3) + "{:02x}".format(b3)


def load_bg_image(num):
    imfile = os.path.dirname(os.path.abspath(__file__)) + '/client/tilespng/bg{}.jpg'.format(num)
    image = Image.open(imfile)
    basewidth = WIDTH + (180 if num == 1 else 230)
    wpercent = (basewidth / float(image.size[0]))
    hsize = int((float(image.size[1]) * float(wpercent)))
    image = image.resize((basewidth, hsize), Image.ANTIALIAS)
    return image


bg_image = load_bg_image(1)


class BgColor:

    left_table = lighter_gray
    side_bar = "#2b7a78"
    down_bar = darker_gray
    inner_table = dark_green_blue
    dice_dealer = fresh_red
    dice_other = "white"
    table_label = fresh_blue  # "#3aafa9" # "#1473a3"

    name_opp = darker_gray
    name_self = fresh_red

    button = lighter_gray
    on_button = fresh_red
    button_clicked = dark_green_blue

    status_monitor = darker_gray
    status_discard = fresh_red

    status_reach = fresh_red
    status_waiting = "yellow"

    waiting_prd = side_bar

    goal_form = dark_green_blue
    goal_form_label = dark_green_blue

    message_bar = "white"


class TxtColor:

    round_info = "white"
    bonus_ind_label = "white"
    honba = "yellow"
    remain_num = "yellow"
    searching_game = "white"

    liuju = "green"
    lose = "green"
    yong = fresh_red
    zimo = fresh_red

    name = "white"

    goal_form = "white"
    goal_label = "white"

    waiting_pred_label = "white"
    status_label = "white"

    button = dark_green_blue
    on_button = "white"
    button_clicked = "white"

    message = "white"


class ChosenRect:
    single_rect = fresh_red
    multi_rect = light_green_blue


class TableDisplay:

    init_x, table_width, pic_width = 18, 800, 40
    init_y, table_height, pic_height = 18, 800, 53
    first_tile_x, incre_x, incre_x_s = [100, 725, 600, 18], [pic_width, 0, - pic_width, 0], [pic_width // 5, 0, - pic_width // 5, 0]
    first_tile_y, incre_y, incre_y_s = [725, 660, 18, 100], [0, - pic_width, 0, pic_width], [0, - pic_width // 5, 0, pic_width // 5]

    first_discard_x, discard_incre_x = [285, 530, 475, 217], [pic_width, pic_height, - pic_width, -pic_height]
    first_discard_y, discard_incre_y = [530, 485,  217, 285], [pic_height, - pic_width, - pic_height, pic_width]

    red_dict = {16: 35, 52: 36, 88: 37}

    def __init__(self, canvas):
        self.canvas_width = int(canvas.cget('width'))
        self.canvas_height = int(canvas.cget('height'))
        self.zooming_x = (self.canvas_height - MSG_BAR - self.init_x) / 800
        self.zooming_y = (self.canvas_height - MSG_BAR - self.init_y) / 800
        self.cvs = canvas
        self.photes = [[], [], [], []]
        self.small_photoes = []
        self._load_photoes()

        self.num_bonus_indicators = 0
        self.round_info_objs = []
        self.drop_objs = []
        self.tiles_objs = [[], [], [], []]
        self.drop_tiles = [[], [], [], []]
        self.meld_tiles = [None, None, None, None]

        self.draw_obj = None
        self.draw_pos = None
        self.drawn_tile = None
        self.hand_tiles = []
        self.hand_tiles_coords = []

        self.win_status_objs = []
        self.is_reach = [False, False, False, False]
        self.chosen_rec_obj = None
        self.chosen_recs_obj = []
        self.discard_label_objs = [[], [], [], []]
        self.warning_label_objs = [[], [], [], []]
        self.shantin_label_objs = [[], [], [], [], [], []]
        self.shantin_objs = []
        self.waiting_prediction_objs = [[], [], [], []]
        self.searching_obj = None
        self.remain_obj = None
        self.hr_obj = None
        self.pdraw_coords = [[], [], []]
        self.pdraw_objs = [None, None, None]
        self.tile_eff_objs = []
        self.waiting_objs = []
        self.enforce_form_obj = []
        self.was_opp_draw = False

        self.draw_game_table()
        # self.message_obj = self.cvs.create_text(
        #     25, self.canvas_height - MSG_BAR + 12,
        #     font=("Futura", 15), fill=TxtColor.message,
        #     text="Message", anchor="nw"
        # )
        x1, y1, x2, y2 = self._abs_x(270), self._abs_y(270), self._abs_x(528), self._abs_y(528)
        r = self._abs_wx(40)
        self._create_rounded(x1, y1, x2, y2, r, BgColor.inner_table)

    def clear_objs(self):
        self._clear_objs(self.round_info_objs)
        self._clear_objs(self.drop_objs)
        self._clear_objs(self.tiles_objs)
        self._clear_objs(self.win_status_objs)
        self._clear_objs(self.discard_label_objs)
        self._clear_objs(self.warning_label_objs)
        self._clear_objs(self.waiting_prediction_objs)
        self._clear_objs(self.shantin_objs)
        self._clear_objs(self.shantin_label_objs)
        self._clear_objs(self.tile_eff_objs)
        self.cvs.delete(self.remain_obj)
        self.cvs.delete(self.hr_obj)
        self._clear_objs(self.enforce_form_obj)
        self._clear_objs(self.waiting_objs)
        self._clear_objs(self.pdraw_objs)

        self.num_bonus_indicators = 0
        self.round_info_objs = []
        self.drop_objs = []
        self.tiles_objs = [[], [], [], []]
        self.drop_tiles = [[], [], [], []]
        self.meld_tiles = [None, None, None, None]
        self.pdraw_objs = [None, None, None]

        self.draw_obj = None
        self.draw_pos = None
        self.drawn_tile = None
        self.hand_tiles = []
        self.hand_tiles_coords = []

        self.win_status_objs = []
        self.is_reach = [False, False, False, False]
        self.chosen_rec_obj = None
        self.chosen_recs_obj = []

        self.discard_label_objs = [[], [], [], []]
        self.warning_label_objs = [[], [], [], []]
        self.waiting_prediction_objs = [[], [], [], []]
        self.shantin_objs = []
        self.shantin_label_objs = [[], [], [], [], [], []]
        self.remain_obj = None
        self.hr_obj = None
        self.tile_eff_objs = []
        self.enforce_form_obj = []
        self.waiting_objs = []
        self.pdraw_coords = [[], [], []]

        self.cvs.update()

    def tmp_test_func(self):
        self.init_round_info(1,1,1,1)
        self.set_remain(28)
        # tile_eff_dict = [[i, i*2] for i in range(12)]
        # self.set_tile_eff(tile_eff_dict)
        # for i in range(1, 5):
        #     self.set_enforce_form(str(i))
        #     sleep(3)
        self.set_waiting([[1,3000, 2], [2, 5200, 3], [3, 1000, 1]])

    def draw_game_table(self):
        rgbIm = bg_image.convert("RGB")
        x1, y1 = self._abs_x(0), self._abs_y(0)
        x2, y2 = self._abs_x(800), self._abs_y(800)
        xc, yc = (x1 + x2) / 2, (y1 + y2) / 2
        longest = abs(x1 - xc) + abs(y1 - yc)
        for i in range(x1, x2, 5):
            for j in range(y1, y2, 5):
                r, g, b = rgbIm.getpixel((i, j))
                alpha = 0.5 + (1 - (abs(i-xc) + abs(j-yc)) / longest) * 0.5
                cl = get_alpha_color(BgColor.left_table, "#{:02x}{:02x}{:02x}".format(r, g, b), alpha)
                self.cvs.create_rectangle(i, j, i + 5, j + 5, fill=cl, width=0)

    def _load_photoes(self):
        root_dir = os.path.dirname(os.path.abspath(__file__))
        for j in range(0, 4):
            for p in range(0, 38):
                imfile = root_dir + '/client/tilespng/{}.png'.format(p)
                image = Image.open(imfile)
                image = image.resize((self._abs_wx(self.pic_width), self._abs_wy(self.pic_height)), Image.ANTIALIAS)
                image = image.rotate(j * 90, expand=True)
                img = ImageTk.PhotoImage(image)
                self.photes[j].append(img)
        # print("{}x{}".format(self._abs_lwx(40), self._abs_lwy(40)))
        for p in range(0, 35):
            imfile = root_dir + '/client/tilespng/{}.png'.format(p)
            image = Image.open(imfile)
            image = image.resize((self._abs_lwx(40), self._abs_lwy(40)), Image.ANTIALIAS)
            img = ImageTk.PhotoImage(image)
            self.small_photoes.append(img)

    def show_tenhou_protocol(self, msg):
        self.cvs.itemconfig(self.message_obj, text=msg)
        self.cvs.update()

    def init_hand(self, hand136):
        if self.searching_obj:
            self.cvs.delete(self.searching_obj)
            self.searching_obj = None
        self.clear_objs()
        self.update_self(hand136, [])
        self.update_opp([], 1)
        self.update_opp([], 2)
        self.update_opp([], 3)
        self.cvs.update()

    def init_round_info(self, round, honba, reach, dealer):
        if self.searching_obj:
            self.cvs.delete(self.searching_obj)
            self.searching_obj = None

        wind = {0:"东", 1:"南", 2:"西", 3:"北"}
        # draw table
        x1, y1, x2, y2 = self._abs_x(270), self._abs_y(270), self._abs_x(528), self._abs_y(528)
        r = self._abs_wx(40)
        self._create_rounded(x1, y1, x2, y2, r, BgColor.inner_table)
        # draw round info rectangle
        x1, y1, x2, y2 = self._abs_x(350), self._abs_y(330), self._abs_x(450), self._abs_y(370)
        r = self._abs_wx(10)
        self._create_rounded(x1, y1, x2, y2, r, BgColor.table_label)

        x, y, w = self._abs_x(364), self._abs_y(331), self._abs_wx(28)
        self._add_round_info_text(x, y, w, "{}{}局".format(wind[(round - 1)//4], (round - 1) % 4 + 1), TxtColor.round_info)

        coords = [[386, 380], [474, 335], [386, 288], [295, 335]]
        for i in range(4):
            x, y = coords[i][0], coords[i][1]
            if i == dealer:
                self._draw_dice(x, y, BgColor.dice_dealer)
            else:
                self._draw_dice(x, y, BgColor.dice_other)

        if not self.remain_obj:
            self.remain_obj = self.cvs.create_text(
                self._abs_x(490), self._abs_y(300),
                text="R", font=("Futura", self._abs_wx(30)),
                fill=TxtColor.remain_num
            )
        if not self.hr_obj:
            self.hr_obj = self.cvs.create_text(
                self._abs_x(315), self._abs_y(300),
                text="H{}R{}".format(honba, reach), font=("Futura", self._abs_wx(25)),
                fill=TxtColor.honba
            )

        self.init_monitor_labels()
        self.init_waiting_prediction_labels()
        self.init_shantin_labels()
        self.init_eff_labels()

        self.cvs.update()

    def init_monitor_labels(self):
        # monitor labels
        x, y = 830, 25
        x1, y1, x2, y2, r = self._abs_lx(x), self._abs_ly(y), self._abs_lx(x + 220), self._abs_ly(
            y + 40), self._abs_lwx(20)
        self._create_rounded_bound(self.round_info_objs, x1, y1, x2, y2, r, fresh_blue)
        x1, y1, w = self._abs_lx(x + 110), self._abs_ly(y + 18), self._abs_lwx(40)
        self.round_info_objs.append(
            self.cvs.create_text(
                x1, y1,
                text="Opponents",
                font=('Futura', w),
                fill='white'
            )
        )
        # player lables
        x, y = 830, 85
        for i in range(0, 4):
            x1, y1, x2, y2, r = self._abs_lx(x), self._abs_ly(y), self._abs_lx(x + 70), self._abs_ly(y + 50), self._abs_lwx(20)
            self._create_rounded_bound(self.discard_label_objs[i], x1, y1, x2, y2, r, BgColor.status_monitor)
            x1, y1, w = self._abs_lx(x + 36), self._abs_ly(y + 25), self._abs_lwx(40)
            self.round_info_objs.append(
                self.cvs.create_text(
                    x1, y1,
                    text="P{}".format(i) if i != 0 else "Bot",
                    font=('Futura', w),
                    fill=TxtColor.status_label
                )
            )
            x += 90
        # monitor tags
        x = 830
        for i in range(0, 4):
            x1, y1, x2, y2, r = self._abs_lx(x), self._abs_ly(y + 60), self._abs_lx(x + 70), self._abs_ly(y + 75), self._abs_lwx(14)
            self._create_rounded_bound(self.warning_label_objs[i], x1, y1, x2, y2, r, BgColor.side_bar)
            x += 90

    def init_waiting_prediction_labels(self):
        x = 830
        y = 180
        for i in range(1, 4):
            x1, y1, x2, y2, r = self._abs_lx(x), self._abs_ly(y), self._abs_lx(x + 50), self._abs_ly(y + 40), self._abs_lwx(10)
            self._create_rounded_bound(self.round_info_objs, x1, y1, x2, y2, r, BgColor.waiting_prd)
            xt, yt, wt = self._abs_lx(x + 25), self._abs_ly(y + 20), self._abs_lwx(30)
            self.round_info_objs.append(
                self.cvs.create_text(
                    xt, yt,
                    text="P{}".format(i),
                    fill=TxtColor.waiting_pred_label,
                    font=('Futura', wt)
                )
            )
            cx = x + 65
            cy = y
            for j in range(0, 5):
                px, py = self._abs_lx(cx), self._abs_ly(cy)
                self.waiting_prediction_objs[i].append(
                    self.cvs.create_image(
                        px, py,
                        anchor='nw',
                        image=self.small_photoes[34]
                    )
                )
                cx += 59
            y += 51

    def init_shantin_labels(self):
        # shantin labels
        x, y = 830, 355
        x1, y1, x2, y2, r = self._abs_lx(x), self._abs_ly(y), self._abs_lx(x + 150), self._abs_ly(y + 40), self._abs_lwx(20)
        self._create_rounded_bound(self.round_info_objs, x1, y1, x2, y2, r, fresh_blue)
        x1, y1, w = self._abs_lx(x + 74), self._abs_ly(y + 20), self._abs_lwx(40)
        self.round_info_objs.append(
            self.cvs.create_text(
                x1, y1,
                text="Shantin",
                font=('Futura', w),
                fill='white'
            )
        )
        # shantin types
        x, y = 830, 415
        forms = ['NM', 'PH', 'DY', 'PP', 'SV', 'QH']
        for i in range(6):
            x1, y1, x2, y2, r = self._abs_lx(x), self._abs_ly(y), self._abs_lx(x + 50), self._abs_ly(y + 30), self._abs_lwx(20)
            self._create_rounded_bound(self.shantin_label_objs[i], x1, y1, x2, y2, r, BgColor.status_monitor)
            x1, y1, w = self._abs_lx(x + 27), self._abs_ly(y + 15), self._abs_lwx(23)
            self.round_info_objs.append(
                self.cvs.create_text(
                    x1, y1,
                    text=forms[i],
                    font=('Futura', w),
                    fill='white'
                )
            )
            x += 60
        # shantin nums
        x, y = 830, 455
        for i in range(6):
            x1, y1, x2, y2, r = self._abs_lx(x), self._abs_ly(y), self._abs_lx(x + 50), self._abs_ly(
                y + 40), self._abs_lwx(20)
            self._create_rounded_bound(self.round_info_objs, x1, y1, x2, y2, r, BgColor.side_bar)
            x1, y1, w = self._abs_lx(x + 27), self._abs_ly(y + 20), self._abs_lwx(35)
            self.shantin_objs.append(
                self.cvs.create_text(
                    x1, y1,
                    text='∞',
                    font=('Futura', w),
                    fill='white'
                )
            )
            x += 60

    def init_eff_labels(self):
        x, y = 830, 530
        x1, y1, x2, y2, r = self._abs_lx(x), self._abs_ly(y), self._abs_lx(x + 150), self._abs_ly(
            y + 40), self._abs_lwx(20)
        self._create_rounded_bound(self.round_info_objs, x1, y1, x2, y2, r, fresh_blue)
        x1, y1, w = self._abs_lx(x + 74), self._abs_ly(y + 20), self._abs_lwx(40)
        self.round_info_objs.append(
            self.cvs.create_text(
                x1, y1,
                text="Tile Eff",
                font=('Futura', w),
                fill='white'
            )
        )

    def set_enforce_form(self, form):
        self._clear_objs(self.enforce_form_obj)
        self.enforce_form_obj = []
        if form != '':
            x, y = 830, 530
            x1, x2, y1, y2, r = self._abs_lx(x + 230), self._abs_ly(y), self._abs_lx(x + 330), self._abs_ly(y + 40), self._abs_lwx(20)
            self._create_rounded_bound(self.enforce_form_obj, x1, x2, y1, y2, r, fresh_red)
            x1, y1, w = self._abs_lx(x + 280), self._abs_ly(y + 20), self._abs_lwx(40)
            self.enforce_form_obj.append(
                self.cvs.create_text(
                    x1, y1,
                    text=form,
                    font=('Futura', w),
                    fill='white'
                )
            )
            self.cvs.update()

    def set_waiting(self, waiting):
        self._clear_objs(self.waiting_objs)
        self._clear_objs(self.tile_eff_objs)
        x, y = 900, 590
        waiting = sorted(waiting, key=lambda x: -x[1])
        for w in waiting[:3]:
            tile, score, remain = w[0], w[1], w[2]
            cx, cy = x, y
            px, py = self._abs_lx(cx), self._abs_ly(cy)
            self.waiting_objs.append(
                self.cvs.create_image(
                    px, py,
                    anchor='nw',
                    image=self.small_photoes[tile]
                )
            )
            self.tile_eff_objs.append(
                self.cvs.create_text(
                    px + self._abs_lwx(105), py + self._abs_lwy(20),
                    text="{}".format(score),
                    font=('Futura', self._abs_lwx(40)),
                    fill='white'
                )
            )
            self.tile_eff_objs.append(
                self.cvs.create_text(
                    px + self._abs_lwx(190), py + self._abs_lwy(20),
                    text="{}".format(remain),
                    font=('Futura', self._abs_lwx(55)),
                    fill='yellow'
                )
            )
            y += 50
        self.cvs.update()

    def set_tile_eff(self, tile_eff_vec):
        self._clear_objs(self.waiting_objs)
        self._clear_objs(self.tile_eff_objs)
        self.tile_eff_objs = []
        x, y = 830, 590
        for i in range(len(tile_eff_vec)):
            tile = tile_eff_vec[i][0]
            eff = tile_eff_vec[i][1]
            cx, cy = x, y
            px, py = self._abs_lx(cx), self._abs_ly(cy)
            self.tile_eff_objs.append(
                self.cvs.create_image(
                    px, py,
                    anchor='nw',
                    image=self.small_photoes[tile]
                )
            )
            self.tile_eff_objs.append(
                self.cvs.create_text(
                    px + self._abs_lwx(20), py + self._abs_lwy(51),
                    text="{:2.1f}".format(eff),
                    font=('Futura', self._abs_lwx(22)),
                    fill='white'
                )
            )
            x += 50
            if i == 6:
                y += 80
                x = 830
        self.cvs.update()

    def set_remain(self, num):
        self.cvs.itemconfig(self.remain_obj, text="{}".format(num))

    def add_name_and_scores(self, names, scores, levels):
        coords = [[540, 610], [610, 130], [130, 90], [90, 540]]
        for i in range(4):
            level = "Bot  {}".format(levels[i]) if i == 0 else "P{}  {}".format(i, levels[i])
            self._draw_name(coords[i][0], coords[i][1], names[i], scores[i], level, i)
        self.cvs.update()

    def add_bonus_indicator(self, tile136):
        self._bonus_indicator_label(290, 480)
        self._bonus_indicator(296, 420, tile136)
        self.cvs.update()

    def opp_draw(self, player):
        self._set_discard_labels(player)
        self.was_opp_draw = True
        self._add_tile_image(self.pdraw_coords[player-1][0], self.pdraw_coords[player-1][1], 34, player)
        self.cvs.update()

    def update_opp(self, melds136, player, final=False):
        self._set_discard_labels(player)
        melds = [[self.red_dict.get(t, t // 4) for t in meld] for meld in melds136]
        if melds != self.meld_tiles[player]:
            self.meld_tiles[player] = melds
            x, y = self.first_tile_x[player], self.first_tile_y[player]
            for obj in self.tiles_objs[player]:
                if obj:
                    self.cvs.delete(obj)
            for meld in melds:
                for m in meld:
                    self._add_tile_image(x, y, m, player)
                    x += self.incre_x[player]
                    y += self.incre_y[player]
                x += self.incre_x_s[player]
                y += self.incre_y_s[player]
            unrevealed = 13 - 3 * len(melds)
            if not final:
                for i in range(unrevealed):
                    self._add_tile_image(x, y, 34, player)
                    x += self.incre_x[player]
                    y += self.incre_y[player]

            x += int(self.incre_x[player] * 0.2)
            y += int(self.incre_y[player] * 0.2)
            self.pdraw_coords[player-1] = [x, y]
            self.cvs.update()

    def update_self(self, hand136, meld136):
        hand34 = [self.red_dict.get(t, t // 4) for t in hand136]
        meld34 = [[self.red_dict.get(t, t // 4) for t in m] for m in meld136]
        self.hand_tiles = hand34
        x, y = self.first_tile_x[0], self.first_tile_y[0]
        for obj in self.tiles_objs[0]:
            if obj:
                self.cvs.delete(obj)
        self.cvs.delete(self.draw_obj)
        self.tiles_objs[0] = []
        for meld in meld34:
            for m in meld:
                self._add_tile_image(x, y, m, 0)
                x += self.incre_x[0]
                y += self.incre_y[0]
            x += self.incre_x_s[0]
            y += self.incre_y_s[0]
        self.hand_tiles_coords = []
        for tile in hand34:
            self.hand_tiles_coords.append([x, y])
            self._add_tile_image(x, y, tile, 0)
            x += self.incre_x[0]
            y += self.incre_y[0]
        self.draw_pos = [x + 8, y]
        self.cvs.update()

    def set_shantins(self, hand_ana):
        self._set_back_shantin_color()
        shantin = hand_ana.current_shantin
        shantins = hand_ana.shantins
        for i in range(len(shantins)):
            shantin_str = str(shantins[i]) if shantins[i] < 10 else '∞'
            self.cvs.itemconfig(self.shantin_objs[i], text=shantin_str)
            if shantins[i] == shantin:
                self._set_shantin_color(i)
        self.cvs.update()

    def _set_shantin_color(self, index):
        for obj in self.shantin_label_objs[index]:
            self.cvs.itemconfig(obj, fill=fresh_red, outline=fresh_red)

    def _set_back_shantin_color(self):
        for objs in self.shantin_label_objs:
            for obj in objs:
                self.cvs.itemconfig(obj, fill=BgColor.status_monitor, outline=BgColor.status_monitor)

    def set_prediction_history(self, player, tiles34):
        if not self.is_reach[player]:
            if len(tiles34):
                self._set_waiting_color(player)
            else:
                self._set_back_waiting_color(player)
        for i in range(min(len(tiles34), 5)):
            self.cvs.itemconfig(self.waiting_prediction_objs[player][i], image=self.small_photoes[tiles34[i]])
        if len(tiles34) < 5:
            for i in range(len(tiles34), 5):
                self.cvs.itemconfig(self.waiting_prediction_objs[player][i], image=self.small_photoes[34])
        self.cvs.update()

    def _set_waiting_color(self, player):
        if not self.is_reach[player]:
            for obj in self.warning_label_objs[player]:
                self.cvs.itemconfig(obj, fill=BgColor.status_waiting, outline=BgColor.status_waiting)

    def _set_back_waiting_color(self, player):
        if not self.is_reach[player]:
            for obj in self.warning_label_objs[player]:
                self.cvs.itemconfig(obj, fill=BgColor.side_bar, outline=BgColor.side_bar)

    def is_searching(self, txt):
        if not self.searching_obj:
            self.searching_obj = self.cvs.create_text(
                self._abs_x(400), self._abs_y(460),
                text=txt,
                font=("Futura", self._abs_wx(23)),
                fill=TxtColor.searching_game
            )
        else:
            self.clear_objs()
            self.cvs.itemconfig(self.searching_obj, text=txt)
        self.cvs.update()

    def draw(self, tile136):
        self._set_discard_labels(0)
        tile = self.red_dict.get(tile136, tile136 // 4)
        self.drawn_tile = tile136 // 4
        self._add_tile_image(self.draw_pos[0], self.draw_pos[1], tile, 0)
        self.cvs.update()

    def discard(self, tile136, player):
        self._set_discard_labels(player)
        self.drop_tiles[player].append(tile136)
        discard_len = len(self.drop_tiles[player]) - 1
        x, y = self.first_discard_x[player], self.first_discard_y[player]
        x += self.discard_incre_x[player] * (discard_len % 6 if player % 2 == 0 else discard_len // 6)
        y += self.discard_incre_y[player] * (discard_len // 6 if player % 2 == 0 else discard_len % 6)
        self._add_drop(x, y, self.red_dict.get(tile136, tile136 // 4), player)
        if player > 0 and self.was_opp_draw:
            self.was_opp_draw = False
            self.cvs.delete(self.tiles_objs[player][-1])
            self.tiles_objs[player] = self.tiles_objs[player][:-1]
        self.cvs.update()

    def _set_discard_labels(self, player):
        self._set_back_discard_labels()
        for obj in self.discard_label_objs[player]:
            self.cvs.itemconfig(obj, fill=BgColor.status_discard, outline=BgColor.status_discard)
        self.cvs.update()

    def _set_back_discard_labels(self):
        for objs in self.discard_label_objs:
            for obj in objs:
                self.cvs.itemconfig(obj, fill=BgColor.status_monitor, outline=BgColor.status_monitor)

    def reach(self, player):
        self._set_reach_color(player)
        self.is_reach[player] = True

        discard_len = len(self.drop_tiles[player]) - (1 if player == 0 else 0)
        x, y = self.first_discard_x[player], self.first_discard_y[player]
        x += self.discard_incre_x[player] * (discard_len % 6 if player % 2 == 0 else discard_len // 6)
        y += self.discard_incre_y[player] * (discard_len // 6 if player % 2 == 0 else discard_len % 6)
        w, h = self.pic_width, self.pic_height
        if player % 2 == 1:
            w, h = h, w
        self.win_status_objs.append(
            self.cvs.create_rectangle(
                self._abs_x(x),
                self._abs_y(y),
                self._abs_x(x + w),
                self._abs_y(y + h),
                outline=fresh_red,
                width=5
            )
        )

    def _set_reach_color(self, player):
        for obj in self.warning_label_objs[player]:
            self.cvs.itemconfig(obj, fill=BgColor.status_reach, outline=BgColor.status_reach)

    def zimo(self, player, score):
        coords = [[520, 570], [570, 280], [275, 220], [220, 520]]
        xt, yt, wt = self._abs_x(coords[player][0]), self._abs_y(coords[player][1]), self._abs_wx(30)
        self.win_status_objs.append(
            self.cvs.create_text(
                xt, yt,
                text='ツモ! +{}'.format(score),
                font=('Futura', wt),
                anchor='nw',
                fill=TxtColor.zimo,
                angle=player*90
            )
        )
        self.cvs.update()

    def yong(self, player, score):
        coords = [[520, 570], [570, 280], [275, 220], [220, 520]]
        xt, yt, wt = self._abs_x(coords[player][0]), self._abs_y(coords[player][1]), self._abs_wx(30)
        self.win_status_objs.append(
            self.cvs.create_text(
                xt, yt,
                text='ロン! +{}'.format(score),
                font=('Futura', wt),
                anchor='nw',
                fill=TxtColor.yong,
                angle=player*90
            )
        )
        self.cvs.update()

    def lose(self, player, score):
        coords = [[520, 570], [570, 280], [275, 220], [220, 520]]
        xt, yt, wt = self._abs_x(coords[player][0]), self._abs_y(coords[player][1]), self._abs_wx(30)
        self.win_status_objs.append(
            self.cvs.create_text(
                xt, yt,
                text='Lose! -{}'.format(score),
                font=('Futura', wt),
                anchor='nw',
                fill=TxtColor.lose,
                angle=player*90
            )
        )
        self.cvs.update()

    def liuju(self):
        x, y, w = self._abs_x(460), self._abs_y(445), self._abs_wx(50)
        self.win_status_objs.append(
            self.cvs.create_text(
                x, y,
                text='流局!',
                font=('Futura', w),
                fill=TxtColor.liuju
            )
        )

    def chosen_rectangle(self, num):
        index = -1
        if num in self.hand_tiles:
            index = self.hand_tiles.index(num)

        if index == -1:
            x, y = self.draw_pos[0], self.draw_pos[1]
            w, h = self.pic_width, self.pic_height
            x1, y1, x2, y2 = self._abs_x(x), self._abs_y(y), self._abs_x(x + w), self._abs_y(y + h)
            self.chosen_rec_obj = self.cvs.create_rectangle(x1, y1, x2, y2, outline=ChosenRect.single_rect, width=4)
        else:
            x, y = self.hand_tiles_coords[index][0], self.hand_tiles_coords[index][1]
            w, h = self.pic_width, self.pic_height
            x1, y1, x2, y2 = self._abs_x(x), self._abs_y(y), self._abs_x(x + w), self._abs_y(y + h)
            self.chosen_rec_obj = self.cvs.create_rectangle(x1, y1, x2, y2, outline=ChosenRect.single_rect, width=4)
        self.cvs.update()

    def unchoose_rectangle(self):
        self.cvs.delete(self.chosen_rec_obj)
        self.chosen_rec_obj = None

    def chosen_all_rectangles(self, nums):
        indices = []
        for n in nums:
            if n in self.hand_tiles:
                indices.append(self.hand_tiles.index(n))
            else:
                indices.append(-1)
        for index in indices:
            if index == -1:
                x, y = self.draw_pos[0], self.draw_pos[1]
                w, h = self.pic_width, self.pic_height
                x1, y1, x2, y2 = self._abs_x(x), self._abs_y(y), self._abs_x(x + w), self._abs_y(y + h)
                self.chosen_recs_obj.append(self.cvs.create_rectangle(x1, y1, x2, y2, outline=ChosenRect.multi_rect, width=3))
            else:
                x, y = self.hand_tiles_coords[index][0], self.hand_tiles_coords[index][1]
                w, h = self.pic_width, self.pic_height
                x1, y1, x2, y2 = self._abs_x(x), self._abs_y(y), self._abs_x(x + w), self._abs_y(y + h)
                self.chosen_recs_obj.append(self.cvs.create_rectangle(x1, y1, x2, y2, outline=ChosenRect.multi_rect, width=3))
        self.cvs.update()

    def clear_chosen(self):
        self._clear_objs(self.chosen_recs_obj)
        self.chosen_recs_obj = []

    def _draw_dice(self, x, y, fil):
        x1, y1, x2, y2, r = self._abs_x(x), self._abs_y(y), self._abs_x(x + 30), self._abs_y(y + 30), self._abs_wx(10)
        self._create_rounded(x1, y1, x2, y2, r, fil)
        x1, y1, x2, y2, r = self._abs_x(x + 19), self._abs_y(y + 5), self._abs_x(x + 25), self._abs_y(y + 11), self._abs_wx(6)
        self._create_rounded(x1, y1, x2, y2, r, BgColor.inner_table)
        x1, y1, x2, y2, r = self._abs_x(x + 5), self._abs_y(y + 19), self._abs_x(x + 11), self._abs_y(y + 25), self._abs_wx(6)
        self._create_rounded(x1, y1, x2, y2, r, BgColor.inner_table)

    def _draw_name(self, x, y, name, score, level, index):
        ag = "{}".format(90 * index)
        x1, y1 = self._abs_x(x), self._abs_y(y)
        x2 = self._abs_x(x + (130 if index % 2 == 0 else 90))
        y2 = self._abs_y(y + (90 if index % 2 == 0 else 130))
        r = self._abs_wx(20)
        self.round_info_objs.append(
            self._create_rounded(x1, y1, x2, y2, r, BgColor.name_opp if index != 0 else BgColor.name_self)
        )
        x_incre, y_incre = [65, 15, 65, 75], [15, 65, 75, 65]
        xt, yt, wt = self._abs_x(x + x_incre[index]), self._abs_y(y + y_incre[index]), self._abs_wx(20)
        self.round_info_objs.append(
            self.cvs.create_text(
                xt, yt,
                text=name,
                font=('Futura', wt),
                fill=TxtColor.name, angle=ag
            )
        )
        x_incre, y_incre = [65, 42, 65, 48], [42, 65, 48, 65]
        xt, yt, wt = self._abs_x(x + x_incre[index]), self._abs_y(y + y_incre[index]), self._abs_wx(22)
        self.round_info_objs.append(
            self.cvs.create_text(
                xt, yt,
                text=level,
                font=('Futura', wt),
                fill=TxtColor.name, angle=ag
            )
        )
        x_incre, y_incre = [65, 70, 65, 20], [70, 65, 20, 65]
        xt, yt, wt = self._abs_x(x + x_incre[index]), self._abs_y(y + y_incre[index]), self._abs_wx(25)

        self.round_info_objs.append(
            self.cvs.create_text(
                xt, yt,
                text='{:,d}'.format(score),
                font=('Futura', wt),
                fill=TxtColor.name, angle=ag
            )
        )

    def _bonus_indicator_label(self, x, y):
        if self.num_bonus_indicators == 0:
            x1, y1, x2, y2, r = self._abs_x(x), self._abs_y(y), self._abs_x(x + 215), self._abs_y(y + 30), self._abs_wx(10)
            self._create_rounded(x1, y1, x2, y2, r, BgColor.table_label)
            x, y, w = self._abs_x(x + 15), self._abs_y(y + 2), self._abs_wx(20)
            self._add_round_info_text(x, y, w, 'Bonus Tile Indicator', TxtColor.bonus_ind_label)

    def _bonus_indicator(self, x, y, tile):
        tile = self.red_dict.get(tile, tile // 4)
        self.round_info_objs.append(
            self.cvs.create_image(self._abs_x(x) + self.num_bonus_indicators * self._abs_wx(self.pic_width),
                                  self._abs_y(y), image=self.photes[0][tile], anchor='nw'))
        self.num_bonus_indicators += 1

    def _add_drop(self, x, y, tile, player):
        x, y = self._abs_x(x), self._abs_y(y)
        self.drop_objs.append(
            self.cvs.create_image(
                x, y, image=self.photes[player][tile], anchor='nw'
            )
        )
        self.cvs.update()

    def _add_tile_image(self, x, y, tile, player):
        x, y = self._abs_x(x), self._abs_y(y)
        self.tiles_objs[player].append(
            self.cvs.create_image(
                x, y, image=self.photes[player][tile], anchor='nw'
            )
        )

    def _abs_x(self, num):
        return self.init_x + int(num * self.zooming_x)

    def _abs_y(self, num):
        return self.init_y + int(num * self.zooming_y)

    def _abs_wx(self, num):
        return int(num * self.zooming_x)

    def _abs_wy(self, num):
        return int(num * self.zooming_y)

    def _abs_lx(self, num):
        return int((num - 800) * (self.canvas_width - self.canvas_height + MSG_BAR) / 400) + self.canvas_height - MSG_BAR

    def _abs_ly(self, num):
        return int(num * (self.canvas_height - MSG_BAR) / 740)

    def _abs_lwx(self, num):
        return int(num * (self.canvas_width - self.canvas_height + MSG_BAR) / 400)

    def _abs_lwy(self, num):
        return int(num * (self.canvas_height - MSG_BAR) / 740)

    def _add_round_info_text(self, x0, y0, w, txt, fil):
        self.round_info_objs.append(
            self.cvs.create_text(
                x0,
                y0,
                text=txt,
                font=('Futura', w),
                anchor='nw',
                fill=fil)
        )

    def _create_rounded_bound(self, objs, x1, y1, x2, y2, r, fil):
        objs.append(
            self.cvs.create_arc(
                x1, y1, x1 + r, y1 + r,
                start=90, extent=90, style=PIESLICE, fill=fil, outline=fil
            )
        )
        objs.append(
            self.cvs.create_arc(
                x2 - r, y1, x2, y1 + r,
                start=0, extent=90, style=PIESLICE, fill=fil, outline=fil
            )
        )
        objs.append(
            self.cvs.create_arc(
                x1, y2 - r, x1 + r, y2,
                start=180, extent=90, style=PIESLICE, fill=fil, outline=fil
            )
        )
        objs.append(
            self.cvs.create_arc(
                x2 - r, y2 - r, x2, y2,
                start=270, extent=90, style=PIESLICE, fill=fil, outline=fil
            )
        )
        objs.append(
            self.cvs.create_rectangle(
                x1 + r / 2, y1, x2 - r / 2, y2,
                fill=fil, outline=fil
            )
        )
        objs.append(
            self.cvs.create_rectangle(
                x1, y1 + r / 2, x2, y2 - r / 2,
                fill=fil, outline=fil
            )
        )

    def _create_rounded(self, x1, y1, x2, y2, r, fil):
        self.round_info_objs.append(
            self.cvs.create_arc(
                x1, y1, x1 + r, y1 + r,
                start=90, extent=90, style=PIESLICE, fill=fil, outline=fil
            )
        )
        self.round_info_objs.append(
            self.cvs.create_arc(
                x2 - r, y1, x2, y1 + r,
                start=0, extent=90, style=PIESLICE, fill=fil, outline=fil
            )
        )
        self.round_info_objs.append(
            self.cvs.create_arc(
                x1, y2 - r, x1 + r, y2,
                start=180, extent=90, style=PIESLICE, fill=fil, outline=fil
            )
        )
        self.round_info_objs.append(
            self.cvs.create_arc(
                x2 - r, y2 - r, x2, y2,
                start=270, extent=90, style=PIESLICE, fill=fil, outline=fil
            )
        )
        self.round_info_objs.append(
            self.cvs.create_rectangle(
                x1 + r / 2, y1, x2 - r / 2, y2,
                fill=fil, outline=fil
            )
        )
        self.round_info_objs.append(
            self.cvs.create_rectangle(
                x1, y1 + r / 2, x2, y2 - r / 2,
                fill=fil, outline=fil
            )
        )

    def _clear_objs(self, nums):
        if isinstance(nums, list):
            if len(nums) > 0 and isinstance(nums[0], list):
                for objs in nums:
                    for obj in objs:
                        if obj:
                            self.cvs.delete(obj)
            else:
                for obj in nums:
                    if obj:
                        self.cvs.delete(obj)


def main():
    root = Tk()
    canvas = Canvas(root, bg=BgColor.side_bar, width=WIDTH, height=HEIGHT)
    canvas.pack(expand=YES)
    img = ImageTk.PhotoImage(bg_image)
    canvas.create_image(0, 0, image=img, anchor="nw")
    drawer = TableDisplay(canvas)
    run_jianyang_ai(drawer)
    root.mainloop()


if __name__ == '__main__':
    main()