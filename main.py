import kivy
import random

from kivy.app import App
from kivy.config import Config
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput

kivy.require("1.11.1")
Config.set('input', 'mouse', 'mouse,disable_multitouch')


class CellButton(Button):

    color_normal = 1, 1, 1, 1
    color_flagged = 1, 0, 0, 1
    color_revealed = .6, .6, .6, 1

    flag_count = 0

    def __init__(self, **kwargs):
        self.value = kwargs.pop("value")
        self.pos_x = kwargs.pop("pos_x")
        self.pos_y = kwargs.pop("pos_y")
        self.hidden = True
        self.flagged = False
        super(CellButton, self).__init__(**kwargs)

    def on_release(self):

        # prevent first step not blank
        if not MineGrid.ref.first_blood and self.value:
            MineGrid.ref.generate(test_pos=(self.pos_x, self.pos_y))
            return

        # disable if game ended
        if MineGrid.ref.ended:
            return

        # response accordingly
        if self.hidden:
            if not self.flagged:
                self.reveal()
        else:
            if self.value and MineGrid.ref.flagged_around(self.pos_x, self.pos_y) == self.value:
                MineGrid.ref.reveal_around(self.pos_x, self.pos_y)

    def on_touch_down(self, touch):
        if MineGrid.ref.ended:
            return True
        if touch.button == "right":
            return True
        super(CellButton, self).on_touch_down(touch)

    def on_touch_up(self, touch):
        if MineGrid.ref.ended:
            return True
        if touch.button == "right" and self.collide_point(*touch.pos):
            if self.hidden:
                self.flagged = not self.flagged
                if self.flagged:
                    self.background_color = CellButton.color_flagged
                else:
                    self.background_color = CellButton.color_normal
                return True
        return super(CellButton, self).on_touch_up(touch)

    def reveal(self):

        # commit first blood if not committed
        if not MineGrid.ref.first_blood:
            MineGrid.ref.first_blood = True

        # win loss condition
        if self.value == MineGrid.mine_id:
            MineGrid.ref.end()
        elif CellButton.flag_count == MineGrid.ref.mines:
            MineGrid.ref.end(win=True)

        # show number
        self.background_color = CellButton.color_revealed
        self.text = str(self.value)

        # reveal cells around if blank
        if not self.value and self.hidden:
            self.hidden = False
            MineGrid.ref.reveal_around(self.pos_x, self.pos_y)
        self.hidden = False


class MineGrid(GridLayout):

    ref = None
    mine_id = 'M'
    around = ((0, 1), (0, -1), (-1, 0), (1, 0), (-1, -1), (1, -1), (-1, 1), (1, 1))

    def __init__(self, **kwargs):
        self.mine_map = [[]]
        self.first_blood = False
        self.ended = False
        MineGrid.ref = self
        super(MineGrid, self).__init__(**kwargs)

    def generate(self, test_pos=None):
        self.mine_map = [[None for _ in range(self.msize)] for _ in range(self.msize)]
        self.first_blood = False
        self.ended = False

        # generate random coordinates for mines
        coordinates = []
        for x in range(self.msize):
            for y in range(self.msize):
                coordinates.append("{},{}".format(x, y))
        random.shuffle(coordinates)

        # insert mines
        for pos in coordinates[:self.mines]:
            x, y = map(int, pos.split(','))
            self.mine_map[x][y] = MineGrid.mine_id

        # calculate number of mines around each cell
        for x in range(self.msize):
            for y in range(self.msize):
                if self.mine_map[x][y] is MineGrid.mine_id:
                    continue
                count = 0
                for x_shift, y_shift in MineGrid.around:
                    try:
                        if x + x_shift < 0 or y + y_shift < 0:
                            continue
                        if self.mine_map[x + x_shift][y + y_shift] is MineGrid.mine_id:
                            count += 1
                    except IndexError:
                        pass
                self.mine_map[x][y] = count

        # graphics for new generated mine map
        self.clear_widgets()
        self.rows = self.cols = self.msize
        x = 0
        for row in self.mine_map:
            y = 0
            for cell in row:
                if not cell:
                    cell = ''
                self.add_widget(CellButton(value=cell, pos_x=x, pos_y=y))
                y += 1
            x += 1

        # test clicked position if there is any
        if test_pos:
            pos_x, pos_y = test_pos
            cell_index = len(self.children) - (pos_x * self.msize + pos_y) - 1
            self.children[cell_index].on_release()

    def around_cells(self, pos_x, pos_y):
        for x_shift, y_shift in MineGrid.around:
            try:
                neighbor_x, neighbor_y = pos_x + x_shift, pos_y + y_shift
                if neighbor_x < 0 or neighbor_y < 0 or neighbor_x >= self.msize or neighbor_y >= self.msize:
                    continue
                cell_index = len(self.children) - (neighbor_x * self.msize + neighbor_y) - 1
                yield self.children[cell_index]
            except IndexError:
                pass

    def reveal_around(self, pos_x, pos_y):
        for cell in self.around_cells(pos_x, pos_y):
            if not cell.flagged:
                cell.reveal()

    def flagged_around(self, pos_x, pos_y):
        count = 0
        for cell in self.around_cells(pos_x, pos_y):
            if cell.flagged:
                count += 1
        return count

    def end(self, win=False):
        self.ended = True
        if win:
            msg = "You have won the game!"
        else:
            msg = "Sorry. you have blown yourself up!"
        popup = Popup(title="Game Ended",
                      content=Label(text=msg),
                      size_hint=(.5, .5))
        popup.open()


class SizeInput()


class MineSweeperApp(App):
    pass


MineSweeperApp().run()
