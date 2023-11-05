import tkinter as tk
import random

class Path(object):
    """Track the positions that are being drawed."""
    def __init__(self, arena_width, arena_height):
        self.arena_width = arena_width
        self.arena_height = arena_height
        self.reset()

    def reset(self):
        self.positions = []

    def add_position(self, x, y):
        self.positions.append((x,y))

    def get_free_position(self, arena):
        for y in range(0, self.arena_height):
            for x in range(0, self.arena_width):
                if arena[(y * self.arena_width)+x] == 0:
                    return x, y
        return None

class Arena(object):
    def __init__(self, width, height, speed):
        self.arena = []
        self.arena_width = int(width/speed) + 1
        self.arena_height = int(height/speed) + 1
        self.path = Path(self.arena_width, self.arena_height)
        self.arena_xpos = 0
        self.arena_ypos = 0
        self.is_drawing = False
        self.drawing_completed = False
        self.initialize_arena_state()

    def initialize_arena_state(self):
        """Create the arena game state, a rectangle with 1's (wall) filled with 0's."""
        frame = [1 for x in range(self.arena_width)]
        self.arena += frame
        walls = [1] + [0] * (self.arena_width-2) + [1]
        for x in range(self.arena_height-2):
            self.arena += walls
        self.arena += frame

    def can_move_horizontally(self, xadjust):
        """Check whether dot can be moved in horizontally by xadjust, return True if so, False otherwise."""
        if (self.arena_xpos + xadjust < 0) or (self.arena_xpos + xadjust >= self.arena_width):
            return False 
        arena_position = (self.arena_ypos * self.arena_width) + (self.arena_xpos + xadjust)
        if self.is_drawing:
            if self.arena[arena_position] == 0:
                self.path.add_position(self.arena_xpos + xadjust, self.arena_ypos)
                self.arena[arena_position] = 2
                return True
            elif self.arena[arena_position] == 1 and len(self.path.positions) > 2:
                self.drawing_completed = True
                return True
            elif self.arena[arena_position] == 2:
                print("FAIL") # TODO: lose a life
                return False
        else:
            if self.arena[arena_position] == 1:
                return True
        return False

    def can_move_vertically(self, yadjust):
        """Check whether dot can be moved in vertically by yadjust, return True if so, False otherwise."""
        if (self.arena_ypos + yadjust < 0) or (self.arena_ypos + yadjust >= self.arena_height):
            return False
        arena_position = ((self.arena_ypos + yadjust) * self.arena_width) + self.arena_xpos
        if self.is_drawing:
            if self.arena[arena_position] == 0:
                self.path.add_position(self.arena_xpos, self.arena_ypos + yadjust)
                self.arena[arena_position] = 2
                return True
            elif self.arena[arena_position] == 1 and len(self.path.positions) > 2:
                self.drawing_completed = True
                return True
            elif self.arena[arena_position] == 2:
                print("FAIL") # TODO: lose a life
                return False
        else:
            if self.arena[arena_position] == 1:
                return True
        return False

    def initiate_drawing(self):
        """
        After drawing initiated:
            - The next move must be on a value 0 (free) or value 1 (terminate).
            - During drawing, values under the current position are set to 2.
            - If attempting move to value 2, lose a life and revert line.
            - Move to value 3 (filled) is considered a bug.
        """
        if not self.is_drawing and self.is_possible_to_draw():
            self.is_drawing = True
            self.drawing_completed = False
            self.path.reset()

    def is_possible_to_draw(self):
        """Return True if it is possible to start drawing from this position."""
        if self.arena_xpos > 0:
            arena_position = (self.arena_ypos * self.arena_width) + self.arena_xpos - 1
            if self.arena[arena_position] == 0: return True
        if self.arena_xpos < self.arena_width:
            arena_position = (self.arena_ypos * self.arena_width) + self.arena_xpos + 1
            if self.arena[arena_position] == 0: return True
        if self.arena_ypos > 0:
            arena_position = ((self.arena_ypos - 1) * self.arena_width) + self.arena_xpos
            if self.arena[arena_position] == 0: return True
        if self.arena_ypos < self.arena_width:
            arena_position = ((self.arena_ypos + 1) * self.arena_width) + self.arena_xpos
            if self.arena[arena_position] == 0: return True

    def fill_arena(self, box_callback):
        """Find all areas in the arena that must be filled"""
        areas = {}
        while True:
            free_position = self.path.get_free_position(self.arena)
            if free_position == None:
                break
            fill_positions = self.fill_region(free_position[0], free_position[1], 3)
            areas[len(fill_positions)] = fill_positions
        area_sizes = list(areas.keys())
        area_sizes.sort()
        print("area sizes", area_sizes)

        # Check that there exist a fillable area - if not, we have exhausted all free positions on the arena
        if len(area_sizes) > 0: # TODO: improve to check whether level is completed
            largest_area = area_sizes[-1]

            # The largest area is not filled
            for x, y in areas[largest_area]:
                arena_position = y * self.arena_width + x
                self.arena[arena_position] = 0

            # All other areas are filled
            for fill_area in area_sizes[:-1]: # TODO: handle case with area_sizes == 1
                for x, y in areas[fill_area]:
                    box_callback(x, y)
        else:
            # No fillable position on the arena remain
            print("Arena filled") # TODO: set state to indicate that level completed

        # Change all the value 2 position on the path to value 1 so they can be traversed
        for x, y in self.path.positions:
            arena_position = y * self.arena_width + x
            if self.arena[arena_position] == 2:
                self.arena[arena_position] = 1

        # Update state variables to indicate completion
        self.is_drawing = False
        self.drawing_completed = True

    def fill_region(self, seedx, seedy, position_value):
        fill_positions = []
        positions_list = [(seedx, seedy)]
        while len(positions_list) > 0:
            x, y = positions_list.pop()
            if x < 0 or x >= self.arena_width or y < 0 or y >= self.arena_height:
                continue
            arena_position = y * self.arena_width + x
            if self.arena[arena_position] == 0:
                self.arena[arena_position] = position_value
                fill_positions.append((x, y))
                positions_list.append((x + 1, y))
                positions_list.append((x - 1, y))
                positions_list.append((x, y + 1))
                positions_list.append((x, y - 1))
        return fill_positions
            
class Game(object):
    def __init__(self, canvas):
        self.canvas = canvas
        self.canvas.bind_key('<Up>', lambda _: self.up())
        self.canvas.bind_key('<Left>', lambda _: self.left())
        self.canvas.bind_key('<Right>', lambda _: self.right())
        self.canvas.bind_key('<Down>', lambda _: self.down())
        self.canvas.bind_key('<space>', lambda _: self.initiate_drawing())
        self.canvas.create_frame()
        self.xpos = 10
        self.ypos = 10
        self.dot = self.canvas.create_dot(self.xpos, self.ypos)
        self.game_speed = 40
        self.pixels_per_move = 5
        self.arena = Arena(self.canvas.width-20, self.canvas.height-20, self.pixels_per_move)
        self.next_move_callback = None
        self.game_loop()

    def up(self):
        if self.arena.can_move_vertically(-1):
            self.ypos -= self.pixels_per_move
            self.canvas.move(self.dot, 0, -self.pixels_per_move)
            self.arena.arena_ypos -= 1
            if self.arena.is_drawing:
                self.next_move_callback = self.up
                self.canvas.create_line(self.xpos, self.ypos + self.pixels_per_move, self.xpos, self.ypos)
                if self.arena.drawing_completed:
                    self.fill_arena()
            else:
                self.next_move_callback = None

    def down(self):
        if self.arena.can_move_vertically(1):
            self.ypos += self.pixels_per_move
            self.canvas.move(self.dot, 0, self.pixels_per_move)
            self.arena.arena_ypos += 1
            if self.arena.is_drawing:
                self.next_move_callback = self.down
                self.canvas.create_line(self.xpos, self.ypos - self.pixels_per_move, self.xpos, self.ypos)
                if self.arena.drawing_completed:
                    self.fill_arena()
            else:
                self.next_move_callback = None

    def left(self):
        if self.arena.can_move_horizontally(-1):
            self.xpos -= self.pixels_per_move
            self.canvas.move(self.dot, -self.pixels_per_move, 0)
            self.arena.arena_xpos -= 1
            if self.arena.is_drawing:
                self.next_move_callback = self.left
                self.canvas.create_line(self.xpos + self.pixels_per_move, self.ypos, self.xpos, self.ypos)
                if self.arena.drawing_completed:
                    self.fill_arena()
            else:
                self.next_move_callback = None

    def right(self):
        if self.arena.can_move_horizontally(1):
            self.xpos += self.pixels_per_move
            self.canvas.move(self.dot, self.pixels_per_move, 0)
            self.arena.arena_xpos += 1
            if self.arena.is_drawing:
                self.next_move_callback = self.right
                self.canvas.create_line(self.xpos - self.pixels_per_move, self.ypos, self.xpos, self.ypos)
                if self.arena.drawing_completed:
                    self.fill_arena()
            else:
                self.next_move_callback = None

    def initiate_drawing(self):
        self.arena.initiate_drawing()

    def fill_arena(self):
        self.arena.fill_arena(self.canvas.create_rect)

    def new_game(self):
        self.score = 0
        self.level = 1

    def game_loop(self):
        if self.next_move_callback != None:
            self.next_move_callback()
        self.canvas.invoke_callback(self.game_speed, self.game_loop)

class Canvas(tk.Frame):
    def __init__(self, width, height):
        root = tk.Tk()
        root.title('TkStix')
        super(Canvas, self).__init__(root)
        self.width = width
        self.height = height
        self.canvas = tk.Canvas(root, bg='black', width=self.width, height=self.height)
        self.canvas.pack()
        self.canvas.focus_set()
        self.pack()

    def create_frame(self):
        return self.canvas.create_rectangle(10, 10, self.width-10, self.height-10, outline='white')

    def create_dot(self, x, y, rad=10):
        return self.canvas.create_oval(x-(rad/2), y-(rad/2), x+(rad/2), y+(rad/2), fill='white')

    def create_line(self, x1, y1, x2, y2):
        return self.canvas.create_line(x1, y1, x2, y2, fill='white')

    def create_rect(self, x, y):
        startx = 7 + (x * 5)
        starty = 7 + (y * 5)
        return self.canvas.create_rectangle(startx, starty, startx+5, starty+5, outline='black', fill='green')

    def move(self, obj, xpos, ypos):
        return self.canvas.move(obj, xpos, ypos)

    def draw_text(self, x, y, text, size='16'):
        font = ('Consolas', size)
        return self.canvas.create_text(x, y, text=text, font=font, fill='white')

    def bind_key(self, key, func):
        self.canvas.bind(key, func)

    def clear_all(self):
        self.canvas.create_rectangle(0, 0, self.width, self.height, fill='black')

    def invoke_callback(self, game_speed, game_loop):
        self.after(game_speed, game_loop)

if __name__ == '__main__':
    canvas = Canvas(600, 600)
    game = Game(canvas)
    canvas.mainloop()