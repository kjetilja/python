import tkinter as tk
import random

class Path(object):
    """Track the positions that are being drawed by the Player."""
    def __init__(self):
        self.reset()

    def reset(self):
        self.positions = []

    def add_position(self, x, y):
        self.positions.append((x,y))

    def get_positions(self):
        return self.positions


class Player(object):
    """The Player."""
    def __init__(self, arena, x, y, arena_width, arena_height):
        self.arena = arena
        self.arena_width = arena_width
        self.arena_height = arena_height
        self.x = x
        self.y = y
        self.is_drawing = False
        self.drawing_completed = True
        self.path = Path()

    def can_move_horizontally(self, xadjust):
        """Check whether player can be moved in horizontally by xadjust, return True if so, False otherwise."""
        if (self.x + xadjust < 0) or (self.x + xadjust >= self.arena_width):
            return False 
        arena_position = (self.y * self.arena_width) + (self.x + xadjust)
        if self.is_drawing:
            if self.arena[arena_position] == 0:
                self.path.add_position(self.x + xadjust, self.y)
                self.arena[arena_position] = 2
                return True
            elif self.arena[arena_position] == 1 and len(self.path.get_positions()) > 2:
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
        """Check whether player can be moved in vertically by yadjust, return True if so, False otherwise."""
        if (self.y + yadjust < 0) or (self.y + yadjust >= self.arena_height):
            return False
        arena_position = ((self.y + yadjust) * self.arena_width) + self.x
        if self.is_drawing:
            if self.arena[arena_position] == 0:
                self.path.add_position(self.x, self.y + yadjust)
                self.arena[arena_position] = 2
                return True
            elif self.arena[arena_position] == 1 and len(self.path.get_positions()) > 2:
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
        After initiate_drawing has completed:
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
        if self.x > 0:
            arena_position = (self.y * self.arena_width) + self.x - 1
            if self.arena[arena_position] == 0: return True
        if self.x < self.arena_width-1:
            arena_position = (self.y * self.arena_width) + self.x + 1
            if self.arena[arena_position] == 0: return True
        if self.y > 0:
            arena_position = ((self.y - 1) * self.arena_width) + self.x
            if self.arena[arena_position] == 0: return True
        if self.y < self.arena_height-1:
            arena_position = ((self.y + 1) * self.arena_width) + self.x
            if self.arena[arena_position] == 0: return True


class ArenaEnemy(object):
    """An enemy dot that bounces within the lines."""
    def __init__(self, arena, x, y, arena_width, arena_height):
        self.x = x
        self.y = y
        self.arena = arena
        self.arena_width = arena_width
        self.arena_height = arena_height

    def move(self):
        """Return the next position to move into."""
        pass


class LineEnemy(object):
    """An enemy dot that traverse the lines."""
    def __init__(self, arena, x, y, arena_width, arena_height):
        self.x = x
        self.y = y
        self.arena = arena
        self.arena_width = arena_width
        self.arena_height = arena_height
        self.move_map = { 0:(1, 0), 1:(-1, 0), 2:(0, 1), 3:(0,-1) } # Meaning -> 0:x+1, 1:x-1, 2:y+1, 3:y-1
        self.direction = random.choice([2,3])
        self.tick = 0

    def move(self):
        """Return the next position to move into."""
        # Strategy is to keep moving in the current direction.
        # If possible to move to different direction than the current direction,
        # make a random choice between the current direction and the new direction.
        current_direction = self.direction
        possible_new_directions = []
        if self.can_move_horizontally(1) and not current_direction == 1:
            possible_new_directions.append(0)
        if self.can_move_horizontally(-1) and not current_direction == 0:
            possible_new_directions.append(1)
        if self.can_move_vertically(1) and not current_direction == 3:
            possible_new_directions.append(2)
        if self.can_move_vertically(-1) and not current_direction == 2:
            possible_new_directions.append(3)
        next_direction = random.choice(possible_new_directions)
        self.direction = next_direction
        x, y = self.move_map[next_direction]
        self.x += x
        self.y += y
        return x, y

    def can_move_horizontally(self, xadjust):
        if (self.x + xadjust < 0) or (self.x + xadjust >= self.arena_width):
            return False
        arena_position = (self.y * self.arena_width) + (self.x + xadjust)
        return self.arena[arena_position] == 1 or self.arena[arena_position] == 2

    def can_move_vertically(self, yadjust):
        if (self.y + yadjust < 0) or (self.y + yadjust >= self.arena_height):
            return False
        arena_position = ((self.y + yadjust) * self.arena_width) + self.x
        return self.arena[arena_position] == 1 or self.arena[arena_position] == 2


class Arena(object):
    def __init__(self, width, height, speed):
        self.arena = []
        self.arena_width = int(width/speed) + 1
        self.arena_height = int(height/speed) + 1
        self.initialize_arena_state()
        self.player = Player(self.arena, 0, 0, self.arena_width, self.arena_height)
        self.line_enemies = [LineEnemy(self.arena, 0, 18, self.arena_width, self.arena_height),
                             LineEnemy(self.arena, 0, 38, self.arena_width, self.arena_height)]
        print("Initialized arena: ", width, height, speed, self.arena_width, self.arena_height)

    def initialize_arena_state(self):
        """Create the arena game state, wtih a perimeter rectangle 1's that is filled with 0's."""
        frame = [1 for x in range(self.arena_width)]
        self.arena += frame
        walls = [1] + [0] * (self.arena_width-2) + [1]
        for x in range(self.arena_height-2):
            self.arena += walls
        self.arena += frame

    def get_free_position(self):
        """Return the first empty position in the arena."""
        for y in range(0, self.arena_height):
            for x in range(0, self.arena_width):
                if self.arena[(y * self.arena_width) + x] == 0:
                    return x, y
        return None

    def fill_arena(self, fill_callback):
        """Find the smallest empty area and fill it."""
        areas = {}
        while True:
            free_position = self.get_free_position()
            if free_position == None:
                break
            fill_positions = self.fill_region(free_position[0], free_position[1])
            fill_positions_length = len(fill_positions)
            while True:
                if fill_positions_length in areas:
                    fill_positions_length += 1
                else:
                    areas[fill_positions_length] = fill_positions
                    break
        area_sizes = list(areas.keys())
        area_sizes.sort()
        print("Area sizes", area_sizes)

        # Check that there exist a fillable area - if not, we have exhausted all free positions on the arena
        if len(area_sizes) > 0: # TODO: improve level completion check
            largest_area = area_sizes[-1]
            # The largest area should not be filled...
            for x, y in areas[largest_area]:
                arena_position = y * self.arena_width + x
                self.arena[arena_position] = 0
            # ... but all other areas are filled
            for fill_area in area_sizes[:-1]: # TODO: handle case with area_sizes == 1
                for x, y in areas[fill_area]:
                    fill_callback(x, y)
        else:
            # No fillable position on the arena remain
            print("Arena filled") # TODO: set state to indicate that level completed

        # Change all the "value 2" positions on the path to value 1 so they can be traversed by the Player
        for x, y in self.player.path.get_positions():
            arena_position = y * self.arena_width + x
            if self.arena[arena_position] == 2:
                self.arena[arena_position] = 1

        # Update state variables to indicate completion of the drawing
        self.player.is_drawing = False
        self.player.drawing_completed = True

    def fill_region(self, seedx, seedy):
        """Simple flood fill, starting with the seed positions."""
        fill_positions = []
        positions_list = [(seedx, seedy)]
        while len(positions_list) > 0:
            x, y = positions_list.pop()
            if x < 0 or x >= self.arena_width or y < 0 or y >= self.arena_height:
                continue
            arena_position = y * self.arena_width + x
            if self.arena[arena_position] == 0:
                self.arena[arena_position] = 3
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
        self.line_enemies = [self.canvas.create_dot(10, 100, fill="red"),
                             self.canvas.create_dot(10, 200, fill="red")]
        self.game_speed = 40
        self.pixels_per_move = 5
        self.arena = Arena(self.canvas.width-20, self.canvas.height-20, self.pixels_per_move)
        self.next_move_callback = None
        self.game_loop()

    def up(self):
        if self.arena.player.can_move_vertically(-1):
            self.ypos -= self.pixels_per_move
            self.canvas.move(self.dot, 0, -self.pixels_per_move)
            self.arena.player.y -= 1
            if self.arena.player.is_drawing:
                self.next_move_callback = self.up
                self.canvas.create_line(self.xpos, self.ypos + self.pixels_per_move, self.xpos, self.ypos)
                if self.arena.player.drawing_completed:
                    self.fill_arena()
                    self.next_move_callback = None

    def down(self):
        if self.arena.player.can_move_vertically(1):
            self.ypos += self.pixels_per_move
            self.canvas.move(self.dot, 0, self.pixels_per_move)
            self.arena.player.y += 1
            if self.arena.player.is_drawing:
                self.next_move_callback = self.down
                self.canvas.create_line(self.xpos, self.ypos - self.pixels_per_move, self.xpos, self.ypos)
                if self.arena.player.drawing_completed:
                    self.fill_arena()
                    self.next_move_callback = None

    def left(self):
        if self.arena.player.can_move_horizontally(-1):
            self.xpos -= self.pixels_per_move
            self.canvas.move(self.dot, -self.pixels_per_move, 0)
            self.arena.player.x -= 1
            if self.arena.player.is_drawing:
                self.next_move_callback = self.left
                self.canvas.create_line(self.xpos + self.pixels_per_move, self.ypos, self.xpos, self.ypos)
                if self.arena.player.drawing_completed:
                    self.fill_arena()
                    self.next_move_callback = None

    def right(self):
        if self.arena.player.can_move_horizontally(1):
            self.xpos += self.pixels_per_move
            self.canvas.move(self.dot, self.pixels_per_move, 0)
            self.arena.player.x += 1
            if self.arena.player.is_drawing:
                self.next_move_callback = self.right
                self.canvas.create_line(self.xpos - self.pixels_per_move, self.ypos, self.xpos, self.ypos)
                if self.arena.player.drawing_completed:
                    self.fill_arena()
                    self.next_move_callback = None

    def initiate_drawing(self):
        self.arena.player.initiate_drawing()

    def fill_arena(self):
        self.arena.fill_arena(self.canvas.create_rect)

    def new_game(self):
        self.score = 0
        self.level = 1

    def move_line_enemies(self):
        move_x, move_y = self.arena.line_enemies[0].move()
        self.canvas.move(self.line_enemies[0], self.pixels_per_move * move_x, self.pixels_per_move * move_y)
        move_x, move_y = self.arena.line_enemies[1].move()
        self.canvas.move(self.line_enemies[1], self.pixels_per_move * move_x, self.pixels_per_move * move_y)

    def game_loop(self):
        # If there's an ongoing drawing, invoke the callback to continue moving the dot in the current direction
        if self.next_move_callback != None:
            self.next_move_callback()
        # Move enemies that traverse the lines
        self.move_line_enemies()
        # Repeat
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

    def create_dot(self, x, y, rad=10, fill='white'):
        return self.canvas.create_oval(x-(rad/2), y-(rad/2), x+(rad/2), y+(rad/2), fill=fill)

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