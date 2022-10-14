import kivy
import random

from kivy.app import App
from kivy.clock import Clock
from kivy.config import Config
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup

kivy.require("1.10.1")

# disable multi-touch to enable right click
Config.set('input', 'mouse', 'mouse,disable_multitouch')

# set screen size
Config.set('graphics', 'width', '960')
Config.set('graphics', 'height', '600')


class CellButton(Button):

    color_normal = 1, 1, 1, 1
    color_flagged = 1, 0, 0, 1
    color_revealed = .6, .6, .6, 1
    color_mine = 1, .6, 0, 1
    color_flagging = 1, .5, .5, 1

    def __init__(self, **kwargs):
        self.value = kwargs.pop("value")
        self.pos_x = kwargs.pop("pos_x")
        self.pos_y = kwargs.pop("pos_y")
        self.hidden = True
        self._flagged = False
        self.flagging = False
        self.font_resize()
        super(CellButton, self).__init__(**kwargs)

    @property
    def flagged(self):
        return self._flagged

    @flagged.setter
    def flagged(self, value):
        if not self._flagged and value:
            MineGrid.ref.flag_count += 1
        elif self._flagged and not value:
            MineGrid.ref.flag_count -= 1
        self._flagged = value

    def font_resize(self):
        # dynamically resize font size using its height
        length = MineGrid.ref.height / MineGrid.ref.msize
        self.font_size = .65 * length

    def on_release(self):

        # disable if game ended
        if MineGrid.ref.ended:
            return

        # prevent first step not blank
        if not MineGrid.ref.first_blood and self.value:
            MineGrid.ref.generate(test_pos=(self.pos_x, self.pos_y))
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
        if touch.button == "right" and self.collide_point(*touch.pos):
            # color change at start of pending flagging action
            if MineGrid.ref.first_blood and self.hidden:
                self.flagging = True
                self.background_color = CellButton.color_flagging
            return True
        super(CellButton, self).on_touch_down(touch)

    def on_touch_move(self, touch):
        if MineGrid.ref.ended:
            return True
        if touch.button == "right":
            if self.flagging:
                if self.collide_point(*touch.pos):
                    # remain flag changing color for pending actions
                    self.background_color = CellButton.color_flagging
                # revert flag color if action is about to be abandoned
                elif self.flagged:
                    self.background_color = CellButton.color_flagged
                else:
                    self.background_color = CellButton.color_normal
                return True
        super(CellButton, self).on_touch_move(touch)

    def on_touch_up(self, touch):
        if MineGrid.ref.ended:
            return True
        if touch.button == "right" and self.collide_point(*touch.pos):
            # flagging action
            if self.flagging and MineGrid.ref.first_blood:
                self.flagging = False
                self.flagged = not self.flagged
                # inverse flag color
                if self.flagged:
                    self.background_color = CellButton.color_flagged
                else:
                    self.background_color = CellButton.color_normal
                return True
        return super(CellButton, self).on_touch_up(touch)

    # display cell number or mine and background
    def show(self):
        if self.value == MineGrid.mine_id:
            if not self.flagged:
                self.background_color = CellButton.color_mine
        else:
            self.background_color = CellButton.color_revealed
        self.text = str(self.value)

    def reveal(self):

        if self.hidden:
            MineGrid.ref.reveal_count += 1

        # commit first blood if not committed
        if not MineGrid.ref.first_blood:
            MineGrid.ref.first_blood = True
            MineGrid.ref.stats_refresh()

        # win loss condition
        if self.value == MineGrid.mine_id:
            MineGrid.ref.end()
        elif MineGrid.ref.reveal_count + MineGrid.ref.mines == MineGrid.ref.msize ** 2:
            MineGrid.ref.end(win=True)

        # show this cell
        self.show()

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
        self.mine_pos = []
        self.first_blood = False
        self.ended = True
        self.reveal_count = 0
        self.flag_count = 0
        MineGrid.ref = self

        # schedule events
        self.stats_refresh = Clock.schedule_interval(self.stats, 0)
        self.stats_refresh.cancel()
        super(MineGrid, self).__init__(**kwargs)

    def on_width(self, *args):
        # dynamically changes font size upon window resize
        for cell in self.children:
            cell.font_resize()
        return args

    # return cells around a given cell as widgets
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

    # provoke the reveal function of cells around a given cell
    def reveal_around(self, pos_x, pos_y):
        for cell in self.around_cells(pos_x, pos_y):
            if not cell.flagged:
                cell.reveal()

    # count the cells that are flagged around a given cell
    def flagged_around(self, pos_x, pos_y):
        count = 0
        for cell in self.around_cells(pos_x, pos_y):
            if cell.flagged:
                count += 1
        return count

    # renew statistics section
    def stats(self, d_time):
        self.timer.value += d_time * .5
        self.revealed.value = self.reveal_count
        self.flagged.value = self.flag_count

    # start a new game
    def new_game(self):

        # need confirmation if game has not ended
        if not self.ended:
            # create layout
            pop_layout = BoxLayout(orientation="vertical")
            btn_layout = BoxLayout(size_hint_y=None, height=50)
            confirm_btn = Button(text="Confirm")
            cancel_btn = Button(text="Cancel")
            pop_layout.add_widget(Label(text="Current game has not ended.\n"
                                             "Generating a new game will overwrite existing game.\n"
                                             "Are you sure?"))
            btn_layout.add_widget(confirm_btn)
            btn_layout.add_widget(cancel_btn)
            pop_layout.add_widget(btn_layout)

            # create and open popup
            popup = Popup(title="Warning",
                          content=pop_layout,
                          size_hint=(.5, .5))
            popup.open()

            # bind functions to buttons
            confirm_btn.bind(on_press=lambda _: self.generate())
            confirm_btn.bind(on_press=popup.dismiss)
            cancel_btn.bind(on_press=popup.dismiss)
        else:
            self.generate()

    # generate a new mine map
    def generate(self, test_pos=None):

        self.revealed.max = self.msize ** 2 - self.mines
        self.flagged.max = self.mines

        self.mine_map = [[None for _ in range(self.msize)] for _ in range(self.msize)]
        self.first_blood = False
        self.ended = False
        self.reveal_count = 0
        self.flag_count = 0

        # generate random coordinates for mines
        coordinates = []
        for x in range(self.msize):
            for y in range(self.msize):
                coordinates.append("{},{}".format(x, y))

        if test_pos:  # avoid generating mine at first cell
            center_x, center_y = test_pos
            coordinates.remove("{},{}".format(center_x, center_y))
            for x_shift, y_shift in MineGrid.around:
                try:
                    neighbor_x, neighbor_y = center_x + x_shift, center_y + y_shift
                    if neighbor_x < 0 or neighbor_y < 0 or neighbor_x >= self.msize or neighbor_y >= self.msize:
                        continue
                    coordinates.remove("{},{}".format(neighbor_x, neighbor_y))
                except IndexError:
                    pass

        random.shuffle(coordinates)
        self.mine_pos = coordinates[:self.mines]

        # insert mines
        for pos in self.mine_pos:
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

        # if pressed reveal cell
        if test_pos:
            center_index = len(self.children) - (center_x * self.msize + center_y) - 1
            self.children[center_index].reveal()

        # reset timer
        self.timer.value = 0

    def end(self, win=False):
        self.stats_refresh.cancel()
        self.ended = True
        self.reveal_count = 0
        self.flag_count = 0
        self.revealed.value = 0
        self.revealed.max = 0
        self.flagged.value = 0
        self.flagged.max = 0

        # show win loss statement
        if win:
            msg = "You have won the game!"
            msg += "\nYou spent {} seconds on this map.".format(int(self.timer.value))
        else:
            # reveal all mines
            for pos in self.mine_pos:
                x, y = map(int, pos.split(','))
                cell_index = len(self.children) - (x * self.msize + y) - 1
                self.children[cell_index].show()
            msg = "You have blown up yourself!"
        msg += "\n\n[i]Click anywhere ELSE to close this popup.[/i]"
        popup = Popup(title="Game Ended",
                      content=Label(markup=True, text=msg),
                      size_hint=(.5, .5))
        popup.open()


class MineSweeperApp(App):
    pass


MineSweeperApp().run()
