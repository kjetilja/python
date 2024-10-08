import pygame
import bresenham
import random
import math


class Path(object):
    """Track the positions that are being drawn by the Player."""
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
        self.start_pos = (x, y)
        self.reset_player_state()

    def reset_player_state(self):
        self.path = Path()
        self.x, self.y = self.start_pos
        self.is_drawing = False
        self.drawing_completed = True

    def horizontal_move(self, xadjust):
        """Check whether player can be moved in horizontally by xadjust.
           Return 1 if player can move, 0 if not, and -1 if player move into a drawing line."""
        if (self.x + xadjust < 0) or (self.x + xadjust >= self.arena_width):
            return 0
        arena_position = (self.y * self.arena_width) + (self.x + xadjust)
        if self.is_drawing:
            if self.arena[arena_position] == 0:
                self.path.add_position(self.x + xadjust, self.y)
                self.arena[arena_position] = 2
                return 1
            elif self.arena[arena_position] == 1 and len(self.path.get_positions()) > 2:
                self.drawing_completed = True
                return 1
            elif self.arena[arena_position] == 2:
                print("Player moved into drawing line")
                return -1
        else:
            if self.arena[arena_position] == 1:
                return 1
        return 0

    def vertical_move(self, yadjust):
        """Check whether player can be moved in horizontally by xadjust.
           Return 1 if player can move, 0 if not, and -1 if player move into a drawing line."""
        if (self.y + yadjust < 0) or (self.y + yadjust >= self.arena_height):
            return 0
        arena_position = ((self.y + yadjust) * self.arena_width) + self.x
        if self.is_drawing:
            if self.arena[arena_position] == 0:
                self.path.add_position(self.x, self.y + yadjust)
                self.arena[arena_position] = 2
                return 1
            elif self.arena[arena_position] == 1 and len(self.path.get_positions()) > 2:
                self.drawing_completed = True
                return 1
            elif self.arena[arena_position] == 2:
                print("Player moved into drawing line")
                return -1
        else:
            if self.arena[arena_position] == 1:
                return 1
        return 0

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
    """A pile of sticks that move around the arena. If the sticks hit a line that's being drawn, life is lost."""
    def __init__(self, arena, arena_width, arena_height):
        self.arena = arena
        self.arena_width = arena_width
        self.arena_height = arena_height
        self.startx1 = 20
        self.startx2 = 23
        self.starty1 = 20
        self.starty2 = 23
        self.directions = [ (1,0),(1,1),(0,1),(-1,0),(-1,-1),(0,-1),(1,-1),(-1,1),(0,0) ]
        self.count1 = 5
        self.count2 = 5
        self.hop1 = 5
        self.hop2 = 2
        self.x1, self.y1 = random.choice(self.directions)
        self.x2, self.y2 = random.choice(self.directions)

    def move(self):
        """Return the next position to move into."""
        self.count1 -= 1
        self.intersected = False
        if self.count1 < 0:
            self.x1, self.y1 = random.choice(self.directions)
            self.x2, self.y2 = random.choice(self.directions)
            self.count1 = random.randint(5, 100)
        self.count2 -= 1
        if self.count2 < 0:
            self.x1, self.y1 = random.choice(self.directions)
            self.x2, self.y2 = random.choice(self.directions)
            self.count2 = random.randint(5, 100)

        if self.can_move_horizontally(self.startx1, self.starty1, self.x1) and \
            not self.intersects(self.startx1+self.x1, self.starty1, self.startx2, self.starty2):
            self.startx1 += self.x1
        else:
            self.x1 = 0
            self.count1 = 0
        if self.can_move_vertically(self.startx1, self.starty1, self.y1) and \
            not self.intersects(self.startx1, self.starty1+self.y1, self.startx2, self.starty2):
            self.starty1 += self.y1
        else:
            self.y1 = 0
            self.count1 = 0
        if self.can_move_horizontally(self.startx2, self.starty2, self.x2) and \
            not self.intersects(self.startx1, self.starty1, self.startx2+self.x2, self.starty2):
            self.startx2 += self.x2
        else:
            self.x2 = 0
            self.count2 = 0
        if self.can_move_vertically(self.startx2, self.starty2, self.y2) and \
            not self.intersects(self.startx1, self.starty1, self.startx2, self.starty2+self.y2):
            self.starty2 += self.y2
        else:
            self.y2 = 0
            self.count2 = 0
        return (self.startx1, self.starty1), (self.startx2, self.starty2), self.intersected

    def intersects(self, x1, y1, x2, y2):
        for (x, y) in bresenham.bresenham(x1, y1, x2, y2):
            arena_position = (y * self.arena_width) + x
            if self.arena[arena_position] != 0:
                if self.arena[arena_position] == 2:
                    print("Line intersected with drawing")
                    self.intersected = True
                return True
        return False

    def can_move_horizontally(self, x, y, xadjust):
        if (x + xadjust < 0) or (x + xadjust >= self.arena_width):
            return False
        arena_position = (y * self.arena_width) + (x + xadjust)
        return self.arena[arena_position] == 0

    def can_move_vertically(self, x, y, yadjust):
        if (y + yadjust < 0) or (y + yadjust >= self.arena_height):
            return False
        arena_position = ((y + yadjust) * self.arena_width) + x
        return self.arena[arena_position] == 0


class LineEnemy(object):
    """An enemy dot that traverse the lines. If the dot hits the player, life is lost."""
    def __init__(self, arena, x, y, arena_width, arena_height):
        self.x = x
        self.y = y
        self.arena = arena
        self.arena_width = arena_width
        self.arena_height = arena_height
        self.move_map = { 0:(1, 0), 1:(-1, 0), 2:(0, 1), 3:(0,-1), 4:(0,0) } # Meaning -> 0:x+1, 1:x-1, 2:y+1, 3:y-1, 4:x,y
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
        if len(possible_new_directions) == 0:
            # This is unexpected behavior
            print("No possible directions for line enemy to move")
            self.direction = 4
        else:
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
    """The arena where the game takes place."""
    def __init__(self, width, height, speed):
        self.arena = []
        self.arena_width = int(width/speed) + 1
        self.arena_height = int(height/speed) + 1
        self.initialize_arena()
        self.player = Player(self.arena, 0, 0, self.arena_width, self.arena_height)
        self.line_enemies = [LineEnemy(self.arena, 0, 18, self.arena_width, self.arena_height),
                             LineEnemy(self.arena, 0, 38, self.arena_width, self.arena_height)]
        self.arena_enemies = [ArenaEnemy(self.arena, self.arena_width, self.arena_height)]
        print("Initialized arena: ", width, height, speed, self.arena_width, self.arena_height)

    def initialize_arena(self):
        """Create the arena game state, with a perimeter rectangle of 1's that is filled with 0's."""
        frame = [1 for x in range(self.arena_width)]
        self.arena += frame
        walls = [1] + [0] * (self.arena_width-2) + [1]
        for x in range(self.arena_height-2):
            self.arena += walls
        self.arena += frame

    def get_free_position(self):
        """Return the first empty (i.e., not filled or being drawn) position in the arena."""
        for y in range(0, self.arena_height):
            for x in range(0, self.arena_width):
                if self.arena[(y * self.arena_width) + x] == 0:
                    return x, y
        return None

    def change_player_path_state_to(self, state_value):
        # Change all the "value 2" positions on the path to state_value
        for x, y in self.player.path.get_positions():
            arena_position = y * self.arena_width + x
            if self.arena[arena_position] == 2:
                self.arena[arena_position] = state_value

    def fill_arena(self, fill_callback):
        """
        Find the smallest empty area and fill it.
        An area with an arena enemy should not be filled, even if it is the smallest area.
        """
        areas = {}
        while True:
            free_position = self.get_free_position()
            if free_position == None:
                break
            fill_positions = self.fill_region(free_position[0], free_position[1])
            fill_positions_length = len(fill_positions)
            for arena_enemy in self.arena_enemies:
                arena_enemy_line_start = (arena_enemy.startx1, arena_enemy.starty1)
                arena_enemy_line_end = (arena_enemy.startx2, arena_enemy.starty2)
                if arena_enemy_line_start in fill_positions or arena_enemy_line_end in fill_positions:
                    print("Boosting size of area with arena enemy")
                    fill_positions_length += (self.arena_width * self.arena_height)
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
        self.change_player_path_state_to(1)

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
    """Game logic to capture player input and render objects (player, enemies, etc.) from the Arena to the screen."""
    def __init__(self, canvas):
        self.canvas = canvas
        self.canvas.create_arena_frame()
        self.start_pos = (10, 10)
        self.pixels_per_move = 5
        self.arena = Arena(self.canvas.width-20, self.canvas.height-20, self.pixels_per_move)
        self.last_n_lines = []
        self.running = True
        self.reset_player_state()

    def reset_player_state(self):
        self.next_move_callback = None
        self.xpos, self.ypos = self.start_pos
        self.canvas.create_new_drawing_surface()

    def handle_keyboard_input(self):
        """TODO: abstract and move pygame specifics into the PyGameCanvas."""
        keys = pygame.key.get_pressed()
        if keys[pygame.K_UP]: self.up()
        if keys[pygame.K_LEFT]: self.left()
        if keys[pygame.K_RIGHT]: self.right()
        if keys[pygame.K_DOWN]: self.down()
        if keys[pygame.K_SPACE]: self.initiate_drawing()

    def up(self):
        state = self.arena.player.vertical_move(-1)
        if state == 1:
            self.ypos -= self.pixels_per_move
            self.arena.player.y -= 1
            if self.arena.player.is_drawing:
                self.next_move_callback = self.up
                self.canvas.create_line((self.xpos, self.ypos + self.pixels_per_move), (self.xpos, self.ypos))
                if self.arena.player.drawing_completed:
                    self.fill_arena()
                    self.next_move_callback = None
        elif state == -1:
            self.player_failed()

    def down(self):
        state = self.arena.player.vertical_move(1)
        if state == 1:
            self.ypos += self.pixels_per_move
            self.arena.player.y += 1
            if self.arena.player.is_drawing:
                self.next_move_callback = self.down
                self.canvas.create_line((self.xpos, self.ypos - self.pixels_per_move), (self.xpos, self.ypos))
                if self.arena.player.drawing_completed:
                    self.fill_arena()
                    self.next_move_callback = None
        elif state == -1:
            self.player_failed()

    def left(self):
        state = self.arena.player.horizontal_move(-1)
        if state == 1:
            self.xpos -= self.pixels_per_move
            self.arena.player.x -= 1
            if self.arena.player.is_drawing:
                self.next_move_callback = self.left
                self.canvas.create_line((self.xpos + self.pixels_per_move, self.ypos), (self.xpos, self.ypos))
                if self.arena.player.drawing_completed:
                    self.fill_arena()
                    self.next_move_callback = None
        elif state == -1:
            self.player_failed()

    def right(self):
        state = self.arena.player.horizontal_move(1)
        if state == 1:
            self.xpos += self.pixels_per_move
            self.arena.player.x += 1
            if self.arena.player.is_drawing:
                self.next_move_callback = self.right
                self.canvas.create_line((self.xpos - self.pixels_per_move, self.ypos), (self.xpos, self.ypos))
                if self.arena.player.drawing_completed:
                    self.fill_arena()
                    self.next_move_callback = None
        elif state == -1:
            self.player_failed()

    def initiate_drawing(self):
        self.arena.player.initiate_drawing()

    def fill_arena(self):
        self.arena.fill_arena(fill_callback=self.canvas.create_arena_rect)
        self.canvas.complete_drawing()

    def render_line_enemies(self):
        for line_enemy in self.arena.line_enemies:
            move_x, move_y = line_enemy.move()
            self.canvas.create_dot(10 + (line_enemy.x * self.pixels_per_move), 10 + (line_enemy.y * self.pixels_per_move), color="red")
            if line_enemy.x == self.arena.player.x and line_enemy.y == self.arena.player.y:
                print("Line enemy hit player")
                self.player_failed()

    def render_player(self):
        self.canvas.create_dot(self.xpos, self.ypos)

    def render_arena_enemies(self):
        # Render 25 last lines
        line_start, line_end, intersected = self.arena.arena_enemies[0].move()
        pixel_line_start = (10+(line_start[0]*self.pixels_per_move), 10+(line_start[1]*self.pixels_per_move))
        pixel_line_end = (10+(line_end[0]*self.pixels_per_move), 10+(line_end[1]*self.pixels_per_move))
        if len(self.last_n_lines) > 25:
            self.last_n_lines.pop(0)
        self.last_n_lines.append((pixel_line_start, pixel_line_end))
        red_component = 5
        for (start, end) in self.last_n_lines:
            red_component += 8
            self.canvas.create_stick_line(start, end, red_component)
        # Check whether the newest line intersected with an ongoing Player drawing
        # If so, the drawing should be reverted and a player life lost
        if intersected:
            print("Arena enemy intersected with player drawing")
            self.player_failed()

    def player_failed(self):
        # Clean up the arena drawing state done by the player
        self.arena.change_player_path_state_to(0)
        # Reset player arena state (empty path, drawing state and arena position)
        self.arena.player.reset_player_state()
        # Reset player rendering state
        self.reset_player_state()
        # TODO: check for game over

    def loop(self):
        while self.running:
            # Check whether there's an input event (window close, etc.) indicating that we should exit
            self.running = self.canvas.check_for_exit()

            # Render the current arena
            self.canvas.render_arena()

            # If there's an ongoing drawing, invoke the callback to continue moving the Player in the current direction
            if self.next_move_callback != None:
                self.next_move_callback()

            # Get keyboard input
            self.handle_keyboard_input()

            # Render the player
            self.render_player()

            # Render and move enemies that traverse the lines
            self.render_line_enemies()

            # Render and move "sticks" enemies that move within the free space of the arena
            self.render_arena_enemies()

            # Render the current frame and wait for desired FPS tick
            self.canvas.render_frame(60)


class PyGameCanvas(object):
    """Canvas object that abstracts over pygame."""
    def __init__(self, width, height):
        pygame.init()
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height)) # Represents the total screen estate
        self.arena_surface = pygame.Surface((width,height)) # Represents the (evolving) arena
        self.clock = pygame.time.Clock()

    def create_new_drawing_surface(self):
        self.drawing_surface = pygame.Surface((self.width,self.height))

    def check_for_exit(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
        return True

    def create_arena_frame(self):
        rect = pygame.Rect(10, 10, self.width-20, self.height-20)
        color = pygame.Color('white')
        return pygame.draw.rect(self.arena_surface, color, rect, 1)

    def create_dot(self, x, y, rad=5, color='white'):
        pos = pygame.Vector2(x, y)
        color_value = pygame.Color(color)
        return pygame.draw.circle(self.screen, color_value, pos, rad)

    def create_line(self, start_pos, end_pos):
        color_param = pygame.Color('white')
        return pygame.draw.line(self.drawing_surface, color_param, start_pos, end_pos)

    def create_stick_line(self, start_pos, end_pos, red_component):
        color = pygame.Color(red_component, 0, 0)
        return pygame.draw.line(self.screen, color, start_pos, end_pos)

    def create_arena_rect(self, x, y):
        startx = 7 + (x * 5)
        starty = 7 + (y * 5)
        color_fill = pygame.Color('darkgreen')
        rect = pygame.Rect(startx+1, starty+1, 3, 3)
        return pygame.draw.rect(self.arena_surface, color_fill, rect)

    def draw_text(self, x, y, text, size='16'):
        pygame.font.init()
        font = pygame.font.SysFont('Consolas', size)
        text_canvas = font.render(text, False, (0, 0, 0))
        return self.screen.blit(text_canvas, (x, y))

    def complete_drawing(self):
        self.arena_surface.blit(self.drawing_surface, (0,0), special_flags=pygame.BLEND_ADD)

    def render_arena(self):
        self.screen.blit(self.arena_surface, (0,0))
        self.screen.blit(self.drawing_surface, (0,0), special_flags=pygame.BLEND_ADD)

    def render_frame(self, game_speed):
        pygame.display.flip()
        self.clock.tick(game_speed)


if __name__ == '__main__':
    canvas = PyGameCanvas(1200, 1200)
    game = Game(canvas)
    game.loop()