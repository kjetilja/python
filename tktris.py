import tkinter as tk
import random

class Tetronimo(object):
    """Logical representation of the tetronimo."""
    def __init__(self, arena, canvas, shape_data, colorid):
        self.arena = arena
        self.canvas = canvas
        self.shape_data = shape_data
        self.colorid = colorid
        self.index = 0
        self.xpos = 4 # start xpos
        self.ypos = 0 # start ypos
    
    def will_collide(self, xpos, ypos, index):
        """Check whether the given position and rotation index will trigger a collision on the arena."""
        arena_start_index = (self.arena.arena_width * (ypos+1)) + xpos + 1
        shape_index = index * 4
        for entry in self.shape_data[shape_index:shape_index+4]:
            column = entry % 4
            row = int(entry/4)
            arena_entry = self.arena.arena[arena_start_index + (row*self.arena.arena_width) + column]
            if arena_entry != 0:
                return True
        return False

    def rotate(self):
        """Rotate tetronimo unless the rotation cause it to collide."""
        new_index = (self.index + 1) % 4
        if not self.will_collide(self.xpos, self.ypos, new_index):
            self.render(0)
            self.index = new_index
            self.render(self.colorid)

    def drop(self):
        """Drop tetronimo one position down. If dropping cause collision, the tetronimo is put into the arena state."""
        new_position = self.ypos + 1
        if not self.will_collide(self.xpos, new_position, self.index):
            self.render(0)
            self.ypos += 1
            self.render(self.colorid)
            return True
        else:
            arena_start_index = (self.arena.arena_width * (self.ypos+1)) + self.xpos + 1
            shape_index = self.index * 4
            for entry in self.shape_data[shape_index:shape_index+4]:
                column = entry % 4
                row = int(entry/4)
                self.arena.arena[arena_start_index + (row*self.arena.arena_width) + column] = self.colorid
            return False

    def drop_fast(self):
        """Drop tetronimo until it collides."""
        start_position = self.ypos
        new_position = self.ypos + 1
        while True:
            if not self.will_collide(self.xpos, new_position, self.index):
                self.render(0)
                self.ypos = new_position
                self.render(self.colorid)
                new_position += 1
            else:
                break
        return self.ypos - start_position # used to calculate the score

    def move(self, xoffset):
        """Move tetronimo horizontally."""
        new_position = self.xpos + xoffset
        if not self.will_collide(new_position, self.ypos, self.index):
            self.render(0)
            self.xpos = new_position
            self.render(self.colorid)

    def render(self, colorid):
        """Render tetronimo on the game arena."""
        shape_index = self.index * 4
        tile_size = self.canvas.tile_size
        for entry in self.shape_data[shape_index:shape_index+4]:
            column = entry % 4
            row = int(entry/4)
            self.canvas.create_tile(tile_size + (self.xpos * tile_size) + column * tile_size,
                                    tile_size + (self.ypos * tile_size) + row * tile_size,
                                    colorid)

    def render_next_tile(self):
        """Render tetronimo as the next that will be played on the game arena."""
        xpos = 16
        ypos = 5
        tile_size = self.canvas.tile_size
        for entry in self.shape_data[0:4]:
            column = entry % 4
            row = int(entry/4)
            self.canvas.create_tile((xpos * tile_size) + column * tile_size,
                                    (ypos * tile_size) + row * tile_size,
                                    self.colorid)

class Arena(object):
    """Logical represenation of the game arena."""
    def __init__(self, canvas):
        self.arena = []
        self.arena_width = 12
        self.arena_height = 22
        self.canvas = canvas
        self.create()

    def create(self):
        """Create initial area based on dimensions from https://en.wikipedia.org/wiki/Tetris."""
        frame = [1 for x in range(self.arena_width)]
        self.arena += frame
        walls = [1] + [0] * (self.arena_width-2) + [1]
        for x in range(self.arena_height-2):
            self.arena += walls
        self.arena += frame

    def check_for_full_rows(self):
        """Check whether there are full rows in the area, and remove them if so."""
        for row in range(1, self.arena_height-1):
            full_row = True
            for column in range(self.arena_width):
                if self.arena[row*self.arena_width + column] == 0:
                    full_row = False
            if full_row:
                clean_row = [1] + [0] * (self.arena_width-2) + [1]
                new_arena = self.arena[0:self.arena_width] + clean_row + \
                    self.arena[self.arena_width:row*self.arena_width] + self.arena[(row+1)*self.arena_width:]
                self.arena = new_arena
                self.render()

    def render(self):
        """Render the arena based on the current arena state."""
        for row in range(self.arena_height):
            for column in range(self.arena_width):
                tile_entry = self.arena[(row * self.arena_width) + column]
                self.canvas.create_tile(column * self.canvas.tile_size,
                                        row * self.canvas.tile_size,
                                        tile_entry)

class Game(object):
    """Game state and control flows."""
    def __init__(self, canvas):
        self.canvas = canvas
        self.canvas.bind_key('<Up>', lambda _: self.current_tetronimo.rotate())
        self.canvas.bind_key('<Left>', lambda _: self.current_tetronimo.move(-1))
        self.canvas.bind_key('<Right>', lambda _: self.current_tetronimo.move(1))
        self.canvas.bind_key('<Down>', lambda _: self.drop_tetronimo_fast())
        self.canvas.bind_key('<space>', lambda _: self.start_game())
        self.game_speed = 1000
        self.start_screen()
        self.game_started = False
        self.game_loop()

    def start_screen(self):
        self.canvas.draw_text(200, 200, "Press Space to start!")
        self.game_over = 0

    def game_over_screen(self):
        self.canvas.draw_text(200, 200, "Game over!", size='32')
        self.game_over = 3

    def start_game(self):
        if not self.game_started:
            self.canvas.clear_all()
            self.new_game()

    def generate_tetronimo(self):
        blue = ([0, 4, 5, 6, 0, 1, 4, 8, 0, 1, 2, 6, 1, 5, 8, 9], 6)
        green = ([1, 2, 4, 5, 0, 4, 5, 9, 1, 2, 4, 5, 0, 4, 5, 9], 2)
        cyan = ([4, 5, 6, 7, 1, 5, 9, 13, 4, 5, 6, 7, 1, 5, 9, 13], 5)
        yellow = ([0, 1, 4, 5, 0, 1, 4, 5, 0, 1, 4, 5, 0, 1, 4, 5], 3)
        red = ([0, 1, 5, 6, 1, 4, 5, 8, 0, 1, 5, 6, 1, 4, 5, 8], 4)
        magenta = ([1, 4, 5, 6, 0, 4, 5, 8, 0, 1, 2, 5, 1, 4, 5, 9], 7)
        brown = ([2, 4, 5, 6, 0, 1, 5, 9, 0, 1, 2, 4, 1, 5, 8, 9], 8)
        shape_list = [blue, green, cyan, yellow, red, magenta, brown]
        shape_data, colorid = random.choice(shape_list)
        return Tetronimo(self.arena, self.canvas, shape_data, colorid)

    def generate_level(self):
        self.tetronimo_sequence = [self.generate_tetronimo() for x in range(self.tetronimos_per_level)]
        self.current_tetronimo_index = 0

    def get_tetronimo(self):
        next = self.tetronimo_sequence[self.current_tetronimo_index]
        self.current_tetronimo_index += 1
        return next

    def render_next_tetronimo(self):
        if self.current_tetronimo_index < self.tetronimos_per_level:
            next = self.tetronimo_sequence[self.current_tetronimo_index]
            next.render_next_tile()        

    def new_game(self):
        self.arena = Arena(self.canvas)
        self.arena.render()
        self.score = 0
        self.level = 1
        self.tetronimos_per_level = 50
        self.game_speed = 1000
        self.generate_level()
        self.render_game_stats()
        self.current_tetronimo = self.get_tetronimo()
        self.render_next_tetronimo()
        self.game_started = True

    def render_game_stats(self):
        self.canvas.clear_game_stats()
        self.canvas.draw_text(18*16, 150, "Score")
        self.canvas.draw_text(18*16, 180, self.score)
        self.canvas.draw_text(18*16, 220, "Level")
        self.canvas.draw_text(18*16, 250, self.level)
        self.canvas.draw_text(18*16, 290, "Left")
        self.canvas.draw_text(18*16, 320, str(len(self.tetronimo_sequence)-max(1, self.current_tetronimo_index)))

    def game_loop(self):
        if self.game_started:
            self.tetronimo_loop()
        if self.game_over > 0:
            self.game_over -= 1
            if self.game_over == 0:
                self.canvas.clear_all()
                self.start_screen()
        self.canvas.invoke_callback(self.game_speed, self.game_loop)

    def tetronimo_loop(self, score_factor=1):
        if self.current_tetronimo.drop() == False:
            self.arena.check_for_full_rows()
            if self.current_tetronimo_index == self.tetronimos_per_level:
                self.level += 1
                self.generate_level()
                self.game_speed = max(100, 1000-(self.level*100))
            next_tetronimo = self.get_tetronimo()
            if next_tetronimo.will_collide(4, 0, 0): # check if it is possible to render the next tetronimo on arena
                self.game_over_screen()
                self.game_started = False
                self.game_speed = 1000
            else:
                self.score += 50 + (5 * score_factor)
                self.render_game_stats()
                self.current_tetronimo = next_tetronimo
                self.render_next_tetronimo()

    def drop_tetronimo_fast(self):
        score_factor = self.current_tetronimo.drop_fast()
        self.tetronimo_loop(score_factor)

class Canvas(tk.Frame):
    """TkInter based canvas to display the game arena, tetronimos and game stats."""
    def __init__(self):
        root = tk.Tk()
        root.title('TkTris')
        super(Canvas, self).__init__(root)
        self.canvas = tk.Canvas(root, bg='black', width=400, height=400)
        self.canvas.pack()
        self.canvas.focus_set()
        self.pack()
        self.setup()

    def setup(self):
        self.colormap = {0:"black", 1:"grey", 2:"green", 3:"yellow", 4:"red", 5:"cyan", 6:"blue", 7:"magenta", 8:"brown"}
        self.tile_size = 16 # in pixels

    def create_tile(self, x, y, tile_entry):
        return self.canvas.create_rectangle(x, y, x + self.tile_size, y + self.tile_size, fill=self.colormap[tile_entry])

    def draw_text(self, x, y, text, size='16'):
        font = ('Consolas', size)
        return self.canvas.create_text(x, y, text=text, font=font, fill='white')

    def bind_key(self, key, func):
        self.canvas.bind(key, func)

    def clear_all(self):
        self.canvas.create_rectangle(0, 0, 400, 400, fill='black')

    def clear_game_stats(self):
        self.canvas.create_rectangle(15*self.tile_size, 0, 24*self.tile_size, 350, fill='black')

    def invoke_callback(self, game_speed, game_loop):
        self.after(game_speed, game_loop)

if __name__ == '__main__':
    canvas = Canvas()
    game = Game(canvas)
    canvas.mainloop()