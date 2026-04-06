import pygame
import bresenham
import random
import logging
import os
import json
from dataclasses import dataclass
from enum import IntEnum

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@dataclass
class LevelConfig:
    """Configuration for a single game level."""
    level_number: int
    fill_percent: float         # fraction of arena that must be filled to complete the level
    arena_width: int            # arena grid width in cells
    arena_height: int           # arena grid height in cells
    num_line_enemies: int       # numnber of line enemies patrolling the walls
    num_arena_enemies: int      # numer of arena enemies (piles of sticks) moving around the arena
    player_speed: int           # move every N frames (1 = every frame, 2 = every other, etc.)
    line_enemy_speed: int       # line enemy move every N frames (1 = every frame, 2 = every other, etc.)
    arena_enemy_speed: int      # arena enemy move every N frames (1 = every frame, 2 = every other, etc.)
    fuse_speed: int = 1         # fuse steps per player move (0 = no fuse, 1 = same speed, 2 = twice as fast)
    fuse_chance: float = 0.5    # probability (0.0-1.0) that a fuse spawns when drawing starts
    fuse_delay: int = 10        # number of player path cells before fuse starts moving


@dataclass
class GameConfig:
    """Top-level display and game settings."""
    max_window_width: int = 800
    max_window_height: int = 800
    margin: int = 10
    hud_height: int = 32
    starting_lives: int = 3
    fps: int = 60
    invincibility_seconds: float = 2.0
    high_score_file: str = "pystix_highscore.json"
    preferred_cell_size: int = 5  # target pixels per cell; shrinks only if arena exceeds max window


class GameState(IntEnum):
    TITLE = 0
    PLAYING = 1
    LEVEL_TRANSITION = 2
    GAME_OVER = 3


ARCHETYPES = ['open', 'crowded', 'edge_hell', 'fuse_panic']


class LevelGenerator:
    """Generates infinite procedural levels using base difficulty scaling + archetype modifiers."""

    def __init__(self):
        self.last_archetypes = []

    def reset(self):
        self.last_archetypes = []

    def build_level(self, level):
        """Generate a LevelConfig for the given level number (1-based)."""
        config = self._generate_base(level)
        archetype = self._choose_archetype(level)
        config = self._apply_archetype(config, archetype)
        self.last_archetypes.append(archetype)
        logger.debug("Level %d: archetype=%s, arena=%dx%d, fill=%.0f%%, "
                     "line_enemies=%d, arena_enemies=%d, fuse_chance=%.0f%%",
                     level, archetype, config.arena_width, config.arena_height,
                     config.fill_percent * 100, config.num_line_enemies,
                     config.num_arena_enemies, config.fuse_chance * 100)
        return config

    def _generate_base(self, level):
        """Create the base LevelConfig from deterministic scaling."""
        # Arena size: 100-160 with variation
        base_size = 100 + (level % 4) * 5
        arena_size = min(base_size + level * 2, 200)

        # Fill requirement: gradual increase, capped at 90%
        fill_percent = min(0.60 + level * 0.015, 0.90)

        # Arena enemies: step increases every 3 levels, capped at 3
        num_arena_enemies = min(1 + (level // 3), 3)
        # Arena enemy speed: lower = faster (move every N frames)
        arena_enemy_speed = max(3 - (level // 5), 1)

        # Line enemies: ramp every 6 levels, capped at 4
        num_line_enemies = min(1 + (level // 4), 4)
        # Line enemy speed: lower = faster
        line_enemy_speed = max(3 - (level // 4), 1)

        # Player always moves every frame
        player_speed = 1

        # Fuse: disabled for first 2 levels, then ramps
        if level <= 2:
            fuse_speed = 0
            fuse_chance = 0.0
            fuse_delay = 20
        else:
            fuse_speed = 1
            fuse_chance = min(0.15 + (level - 2) * 0.05, 0.8)
            fuse_delay = max(12 - level, 5)

        return LevelConfig(
            level_number=level,
            fill_percent=fill_percent,
            arena_width=arena_size,
            arena_height=arena_size,
            num_line_enemies=num_line_enemies,
            num_arena_enemies=num_arena_enemies,
            player_speed=player_speed,
            line_enemy_speed=line_enemy_speed,
            arena_enemy_speed=arena_enemy_speed,
            fuse_speed=fuse_speed,
            fuse_chance=fuse_chance,
            fuse_delay=fuse_delay,
        )

    def _choose_archetype(self, level):
        """Select an archetype using milestone levels, weighted pools, and anti-repetition."""
        # Milestone levels: fixed archetypes for memorable moments (unless it would triple-repeat)
        milestones = {1: 'open', 4: 'crowded', 7: 'edge_hell', 10: 'fuse_panic'}
        if level in milestones:
            candidate = milestones[level]
            if not (len(self.last_archetypes) >= 2
                    and self.last_archetypes[-1] == self.last_archetypes[-2] == candidate):
                return candidate

        # Weighted pools by game phase
        if level < 5:
            pool = ['open'] * 3 + ['crowded']
        elif level < 10:
            pool = ['open'] + ['crowded'] * 2 + ['edge_hell'] * 2 + ['fuse_panic']
        else:
            pool = ['crowded'] * 2 + ['edge_hell'] * 3 + ['fuse_panic'] * 3

        # Anti-repetition: avoid 3 of the same archetype in a row
        for _ in range(10):
            choice = random.choice(pool)
            if (len(self.last_archetypes) >= 2
                    and self.last_archetypes[-1] == self.last_archetypes[-2] == choice):
                continue
            return choice
        # Fallback: pick any archetype that isn't the repeated one
        blocked = self.last_archetypes[-1] if self.last_archetypes else None
        fallback = [a for a in pool if a != blocked]
        return random.choice(fallback) if fallback else random.choice(pool)

    def _apply_archetype(self, config, archetype):
        """Apply archetype modifiers to a base config. Returns a new LevelConfig."""
        from dataclasses import replace
        if archetype == 'open':
            return replace(config,
                           arena_width=min(config.arena_width + 10, 200),
                           arena_height=min(config.arena_height + 10, 200),
                           fill_percent=min(config.fill_percent + 0.05, 0.90))
        elif archetype == 'crowded':
            return replace(config,
                           arena_width=max(config.arena_width - 10, 50),
                           arena_height=max(config.arena_height - 10, 50),
                           num_arena_enemies=min(config.num_arena_enemies + 1, 4))
        elif archetype == 'edge_hell':
            return replace(config,
                           num_line_enemies=min(config.num_line_enemies + 1, 5),
                           line_enemy_speed=max(config.line_enemy_speed - 1, 1))
        elif archetype == 'fuse_panic':
            return replace(config,
                           fuse_speed=max(config.fuse_speed, 1),
                           fuse_chance=min(config.fuse_chance + 0.3, 1.0),
                           fuse_delay=max(config.fuse_delay - 4, 3))
        return config


class CellState(IntEnum):
    """Arena cell states:
    - FREE: empty cell that can be drawn over
    - WALL: solid wall that cannot be drawn over
    - DRAWING: currently being drawn by the player
    - FILLED: filled area after drawing is completed
    - _TEMP_REGION: temporary region used when filling arena after drawing is completed
    """
    FREE = 0
    WALL = 1
    DRAWING = 2
    FILLED = 3
    _TEMP_REGION = 4


class MoveResult(IntEnum):
    """Result of a player movement attempt."""
    DIED = -1
    BLOCKED = 0
    OK = 1


class Path(object):
    """Track the positions that are being drawn by the Player."""
    def __init__(self):
        self.reset()

    def reset(self):
        self.positions = []

    def add_position(self, x, y):
        self.positions.append((x, y))

    def get_positions(self):
        return self.positions


class Player(object):
    """The Player."""
    def __init__(self, arena, x, y):
        self.arena = arena
        self.start_pos = (x, y)
        self.reset_player_state()

    def reset_player_state(self):
        self.path = Path()
        self.x, self.y = self.start_pos
        self.is_drawing = False
        self.drawing_completed = True

    def try_move(self, dx, dy):
        """Attempt to move the player by (dx, dy).
        Returns MoveResult.OK if successful, MoveResult.BLOCKED if not,
        and MoveResult.DIED if player moved into a drawing line."""
        nx, ny = self.x + dx, self.y + dy
        if nx < 0 or nx >= self.arena.arena_width or ny < 0 or ny >= self.arena.arena_height:
            return MoveResult.BLOCKED
        cell = self.arena.get_cell(nx, ny)
        if self.is_drawing:
            if cell == CellState.FREE:
                self.path.add_position(nx, ny)
                self.arena.set_cell(nx, ny, CellState.DRAWING)
                self.x, self.y = nx, ny
                return MoveResult.OK
            elif cell == CellState.WALL and len(self.path.get_positions()) > 2:
                self.drawing_completed = True
                self.x, self.y = nx, ny
                return MoveResult.OK
            elif cell == CellState.DRAWING:
                logger.debug("Player moved into drawing line")
                return MoveResult.DIED
        else:
            if cell == CellState.WALL:
                self.x, self.y = nx, ny
                return MoveResult.OK
        return MoveResult.BLOCKED

    def initiate_drawing(self):
        """
        After initiate_drawing has completed:
            - The next move must be on a FREE or WALL cell (terminate).
            - During drawing, values under the current position are set to DRAWING.
            - If attempting move to DRAWING cell, lose a life and revert line.
            - Move to FILLED cell is considered a bug.
        """
        if not self.is_drawing and self.is_possible_to_draw():
            self.is_drawing = True
            self.drawing_completed = False
            self.path.reset()

    def is_possible_to_draw(self):
        """Return True if it is possible to start drawing from this position."""
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            nx, ny = self.x + dx, self.y + dy
            if 0 <= nx < self.arena.arena_width and 0 <= ny < self.arena.arena_height:
                if self.arena.get_cell(nx, ny) == CellState.FREE:
                    return True
        return False


class ArenaEnemy(object):
    """A pile of sticks that move around the arena. If the sticks hit a line that's being drawn, life is lost."""
    def __init__(self, arena):
        self.arena = arena
        # Place endpoints in the free interior, offset from center
        cx = arena.arena_width // 2
        cy = arena.arena_height // 2
        self.end1_x = cx - random.randint(1, 5)
        self.end1_y = cy - random.randint(1, 5)
        self.end2_x = cx + random.randint(1, 5)
        self.end2_y = cy + random.randint(1, 5)
        self.directions = [(1,0),(1,1),(0,1),(-1,0),(-1,-1),(0,-1),(1,-1),(-1,1),(0,0)]
        self.count1 = 5
        self.count2 = 5
        self.vel1_x, self.vel1_y = random.choice(self.directions)
        self.vel2_x, self.vel2_y = random.choice(self.directions)

    def move(self):
        """Return the next position to move into."""
        self.count1 -= 1
        self.intersected = False
        if self.count1 < 0:
            self.vel1_x, self.vel1_y = random.choice(self.directions)
            self.vel2_x, self.vel2_y = random.choice(self.directions)
            self.count1 = random.randint(5, 100)
        self.count2 -= 1
        if self.count2 < 0:
            self.vel1_x, self.vel1_y = random.choice(self.directions)
            self.vel2_x, self.vel2_y = random.choice(self.directions)
            self.count2 = random.randint(5, 100)

        if self.can_move(self.end1_x, self.end1_y, self.vel1_x, 0) and \
            not self.intersects(self.end1_x + self.vel1_x, self.end1_y, self.end2_x, self.end2_y):
            self.end1_x += self.vel1_x
        else:
            self.vel1_x = 0
            self.count1 = 0
        if self.can_move(self.end1_x, self.end1_y, 0, self.vel1_y) and \
            not self.intersects(self.end1_x, self.end1_y + self.vel1_y, self.end2_x, self.end2_y):
            self.end1_y += self.vel1_y
        else:
            self.vel1_y = 0
            self.count1 = 0
        if self.can_move(self.end2_x, self.end2_y, self.vel2_x, 0) and \
            not self.intersects(self.end1_x, self.end1_y, self.end2_x + self.vel2_x, self.end2_y):
            self.end2_x += self.vel2_x
        else:
            self.vel2_x = 0
            self.count2 = 0
        if self.can_move(self.end2_x, self.end2_y, 0, self.vel2_y) and \
            not self.intersects(self.end1_x, self.end1_y, self.end2_x, self.end2_y + self.vel2_y):
            self.end2_y += self.vel2_y
        else:
            self.vel2_y = 0
            self.count2 = 0
        return (self.end1_x, self.end1_y), (self.end2_x, self.end2_y), self.intersected

    def intersects(self, x1, y1, x2, y2):
        for (x, y) in bresenham.bresenham(x1, y1, x2, y2):
            cell = self.arena.get_cell(x, y)
            if cell != CellState.FREE:
                if cell == CellState.DRAWING:
                    logger.debug("Line intersected with drawing")
                    self.intersected = True
                return True
        return False

    def can_move(self, x, y, dx, dy):
        nx, ny = x + dx, y + dy
        if nx < 0 or nx >= self.arena.arena_width or ny < 0 or ny >= self.arena.arena_height:
            return False
        return self.arena.get_cell(nx, ny) == CellState.FREE


class LineEnemy(object):
    """An enemy dot that traverse the lines. If the dot hits the player, life is lost."""
    def __init__(self, arena, x, y):
        self.x = x
        self.y = y
        self.arena = arena
        self.move_map = {0: (1, 0), 1: (-1, 0), 2: (0, 1), 3: (0, -1), 4: (0, 0)}
        self.direction = random.choice([2, 3])
        self.tick = 0

    def move(self):
        """Return the next position to move into.
        Strategy is to keep moving in the current direction.
        If possible to move to different direction than the current direction,
        make a random choice between the current direction and the new direction."""
        current_direction = self.direction
        possible_new_directions = []
        if self.can_move(1, 0) and current_direction != 1:
            possible_new_directions.append(0)
        if self.can_move(-1, 0) and current_direction != 0:
            possible_new_directions.append(1)
        if self.can_move(0, 1) and current_direction != 3:
            possible_new_directions.append(2)
        if self.can_move(0, -1) and current_direction != 2:
            possible_new_directions.append(3)
        if len(possible_new_directions) == 0:
            logger.debug("No possible directions for line enemy to move")
            self.direction = 4
            return 0, 0
        next_direction = random.choice(possible_new_directions)
        self.direction = next_direction
        x, y = self.move_map[next_direction]
        self.x += x
        self.y += y
        return x, y

    def can_move(self, dx, dy):
        nx, ny = self.x + dx, self.y + dy
        if nx < 0 or nx >= self.arena.arena_width or ny < 0 or ny >= self.arena.arena_height:
            return False
        cell = self.arena.get_cell(nx, ny)
        return cell == CellState.WALL or cell == CellState.DRAWING


class FuseEnemy(object):
    """A fuse that follows the player's drawing path. Kills the player if it catches up."""
    COLOR_BRIGHT = (255, 255, 100)
    COLOR_DARK = (200, 60, 0)

    def __init__(self, path, start_x, start_y, delay=10):
        self.path = path
        self.x = start_x
        self.y = start_y
        self.path_index = 0
        self.delay = delay  # wait until path has this many positions before moving
        self.active = True

    def move(self, steps=1):
        """Advance steps along the player's path. Returns True if the fuse caught the player."""
        positions = self.path.get_positions()
        if len(positions) < self.delay:
            return False  # waiting for player to get a head start
        for _ in range(steps):
            if self.path_index < len(positions):
                self.x, self.y = positions[self.path_index]
                self.path_index += 1
            else:
                return True  # caught the player
        return False

    def get_color(self, frame_count):
        """Return a flashing fuse color."""
        if (frame_count // 4) % 2 == 0:
            return self.COLOR_BRIGHT
        return self.COLOR_DARK


class Arena(object):
    """The arena where the game takes place."""
    def __init__(self, config):
        self._cells = []
        self.arena_width = config.arena_width
        self.arena_height = config.arena_height
        self._initialize_arena()
        self.player = Player(self, 0, 0)
        self.line_enemies = self._spawn_line_enemies(config.num_line_enemies)
        self.arena_enemies = [ArenaEnemy(self) for _ in range(config.num_arena_enemies)]
        logger.debug("Initialized arena: %d x %d (level %d)",
                     self.arena_width, self.arena_height, config.level_number)

    def _spawn_line_enemies(self, count):
        """Spawn line enemies at random positions along the perimeter walls,
        avoiding the player's start position and its immediate neighbors."""
        enemies = []
        player_x, player_y = self.player.start_pos
        excluded = {(player_x + dx, player_y + dy)
                    for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
        wall_positions = []
        # Collect all wall positions on the perimeter
        for x in range(self.arena_width):
            wall_positions.append((x, 0))
            wall_positions.append((x, self.arena_height - 1))
        for y in range(1, self.arena_height - 1):
            wall_positions.append((0, y))
            wall_positions.append((self.arena_width - 1, y))
        wall_positions = [p for p in wall_positions if p not in excluded]
        random.shuffle(wall_positions)
        for i in range(count):
            x, y = wall_positions[i % len(wall_positions)]
            enemies.append(LineEnemy(self, x, y))
        return enemies

    @property
    def filled_percent(self):
        """Return the fraction of the arena that is filled (FILLED + WALL cells vs total)."""
        filled = sum(1 for c in self._cells if c == CellState.FILLED or c == CellState.WALL)
        return filled / len(self._cells)

    def get_cell(self, x, y):
        return self._cells[y * self.arena_width + x]

    def set_cell(self, x, y, value):
        self._cells[y * self.arena_width + x] = value

    def _initialize_arena(self):
        """Create the arena game state, with a perimeter rectangle of WALL cells filled with FREE cells."""
        frame = [CellState.WALL] * self.arena_width
        self._cells += frame
        row = [CellState.WALL] + [CellState.FREE] * (self.arena_width - 2) + [CellState.WALL]
        for _ in range(self.arena_height - 2):
            self._cells += row
        self._cells += frame

    def get_free_position(self):
        """Return the first empty (i.e., not filled or being drawn) position in the arena."""
        for y in range(self.arena_height):
            for x in range(self.arena_width):
                if self.get_cell(x, y) == CellState.FREE:
                    return x, y
        return None # No free position found

    def change_player_path_state_to(self, state_value):
        for x, y in self.player.path.get_positions():
            if self.get_cell(x, y) == CellState.DRAWING:
                self.set_cell(x, y, state_value)
        if state_value == CellState.FREE:
            self._respawn_stranded_line_enemies()

    def _respawn_stranded_line_enemies(self):
        """Relocate any line enemy that is no longer on a WALL or DRAWING cell."""
        wall_positions = []
        for x in range(self.arena_width):
            wall_positions.append((x, 0))
            wall_positions.append((x, self.arena_height - 1))
        for y in range(1, self.arena_height - 1):
            wall_positions.append((0, y))
            wall_positions.append((self.arena_width - 1, y))
        for enemy in self.line_enemies:
            cell = self.get_cell(enemy.x, enemy.y)
            if cell != CellState.WALL and cell != CellState.DRAWING:
                pos = random.choice(wall_positions)
                enemy.x, enemy.y = pos
                logger.debug("Respawned stranded line enemy to (%d,%d)", pos[0], pos[1])

    def fill_arena(self, fill_callback):
        # Precompute enemy positions
        enemy_positions = set()
        for enemy in self.arena_enemies:
            enemy_positions.add((enemy.end1_x, enemy.end1_y))
            enemy_positions.add((enemy.end2_x, enemy.end2_y))

        # Assign each disjoint free region a unique id
        # and track size + whether it contains an enemy
        region_id = CellState._TEMP_REGION
        region_info = {}  # region_id -> (cell_count, contains_enemy)

        for y in range(self.arena_height):
            for x in range(self.arena_width):
                if self.get_cell(x, y) == CellState.FREE:
                    count, has_enemy = self._scanline_fill(x, y, region_id, enemy_positions)
                    region_info[region_id] = (count, has_enemy)
                    region_id += 1

        if region_info:
            # Keep all regions that contain an enemy.
            # If no region has an enemy, keep the largest region.
            keep_ids = {rid for rid, (count, has_enemy) in region_info.items() if has_enemy}
            if not keep_ids:
                keep_ids = {max(region_info, key=lambda rid: region_info[rid][0])}

            # Check if every region has an enemy (nothing to fill = wasted draw)
            # This only applies when there are multiple regions — if there's just one,
            # the draw simply didn't create a closure, which is a normal outcome.
            wasted_draw = (len(region_info) > 1 and keep_ids == set(region_info.keys()))

            # Single linear pass: fill non-kept regions, reset kept regions to FREE
            for i in range(len(self._cells)):
                v = self._cells[i]
                if v >= CellState._TEMP_REGION:
                    if v in keep_ids:
                        self._cells[i] = CellState.FREE
                    else:
                        self._cells[i] = CellState.FILLED
                        fill_callback(i % self.arena_width, i // self.arena_width)
        else:
            wasted_draw = False
            logger.debug("Arena filled")

        # Update arena state: if every region had an enemy (wasted draw), revert path to FREE
        if wasted_draw:
            self.change_player_path_state_to(CellState.FREE)
        else:
            self.change_player_path_state_to(CellState.WALL)
        self.player.is_drawing = False
        self.player.drawing_completed = True
        return not wasted_draw  # True if something was filled

    def _scanline_fill(self, seedx, seedy, region_id, enemy_positions):
        """Scanline span-fill: marks all connected FREE cells with region_id.
        Returns (cell_count, contains_enemy)."""
        cells = self._cells
        w = self.arena_width
        h = self.arena_height
        count = 0
        has_enemy = False
        stack = [(seedx, seedy)]
        while stack:
            x, y = stack.pop()
            row_offset = y * w
            if cells[row_offset + x] != CellState.FREE:
                continue
            x_left = x
            while x_left > 0 and cells[row_offset + x_left - 1] == CellState.FREE:
                x_left -= 1
            x_right = x
            while x_right < w - 1 and cells[row_offset + x_right + 1] == CellState.FREE:
                x_right += 1
            for xi in range(x_left, x_right + 1):
                cells[row_offset + xi] = region_id
                count += 1
                if (xi, y) in enemy_positions:
                    has_enemy = True
            for ny in (y - 1, y + 1):
                if ny < 0 or ny >= h:
                    continue
                nrow_offset = ny * w
                xi = x_left
                while xi <= x_right:
                    if cells[nrow_offset + xi] == CellState.FREE:
                        stack.append((xi, ny))
                        while xi <= x_right and cells[nrow_offset + xi] == CellState.FREE:
                            xi += 1
                    else:
                        xi += 1
        return count, has_enemy


class Game(object):
    """Game logic to capture player input and render objects (player, enemies, etc.) from the Arena to the screen."""
    def __init__(self, canvas, game_config):
        self.canvas = canvas
        self.game_config = game_config
        self.level_generator = LevelGenerator()
        self.high_score = self._load_high_score()
        self.state = GameState.TITLE
        self.running = True
        # Set initial window size for title screen
        self.canvas.screen = pygame.display.set_mode(
            (game_config.max_window_width, game_config.max_window_height))

    def _load_high_score(self):
        path = self.game_config.high_score_file
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                    return data.get('high_score', 0)
            except (json.JSONDecodeError, OSError):
                pass
        return 0

    def _save_high_score(self):
        path = self.game_config.high_score_file
        try:
            with open(path, 'w') as f:
                json.dump({'high_score': self.high_score}, f)
        except OSError:
            logger.warning("Could not save high score to %s", path)

    def _start_new_game(self):
        """Reset all game state and start level 1."""
        self.level_generator.reset()
        self.current_level = 1
        self.last_n_lines = []
        self.lives = self.game_config.starting_lives
        self.score = 0
        self.state = GameState.PLAYING
        config = self.level_generator.build_level(self.current_level)
        self.start_level(config)

    def start_level(self, config):
        """Initialize a new level from the given config."""
        self.config = config
        self.canvas.configure(config.arena_width, config.arena_height)
        self.arena = Arena(config)
        self.canvas.create_arena_frame()
        self.last_n_lines = []
        self.frame_count = 0
        self.reset_player_state()
        self.invincibility_frames = int(self.game_config.invincibility_seconds * self.game_config.fps)
        logger.debug("Starting level %d (fill target: %.0f%%)",
                     config.level_number, config.fill_percent * 100)

    def reset_player_state(self):
        self.drawing_direction = None
        self.fuse = None
        self.death_animation_frames = 0
        self.death_particles = []
        self.invincibility_frames = 0
        self.canvas.create_new_drawing_surface()

    def handle_keyboard_input(self):
        keys = pygame.key.get_pressed()
        d = self.drawing_direction
        if keys[pygame.K_UP] and d != (0, -1): self._move(0, -1)
        if keys[pygame.K_LEFT] and d != (-1, 0): self._move(-1, 0)
        if keys[pygame.K_RIGHT] and d != (1, 0): self._move(1, 0)
        if keys[pygame.K_DOWN] and d != (0, 1): self._move(0, 1)
        if keys[pygame.K_SPACE]:
            was_drawing = self.arena.player.is_drawing
            self.arena.player.initiate_drawing()
            if not was_drawing and self.arena.player.is_drawing:
                self._try_spawn_fuse()

    def _move(self, dx, dy):
        """Attempt to move the player by (dx, dy) and handle drawing/failure."""
        result = self.arena.player.try_move(dx, dy)
        if result == MoveResult.OK:
            if self.arena.player.is_drawing:
                player = self.arena.player
                self.drawing_direction = (dx, dy)
                self.canvas.create_line_arena(player.x - dx, player.y - dy, player.x, player.y)
                if player.drawing_completed:
                    self.fill_arena()
                    self.drawing_direction = None
        elif result == MoveResult.DIED:
            self.player_failed()

    def _try_spawn_fuse(self):
        """Possibly spawn a fuse at the player's current position based on level config."""
        if self.config.fuse_speed > 0 and random.random() < self.config.fuse_chance:
            player = self.arena.player
            self.fuse = FuseEnemy(player.path, player.x, player.y, delay=self.config.fuse_delay)
            logger.debug("Fuse spawned at (%d,%d) with delay=%d", player.x, player.y, self.config.fuse_delay)

    def move_and_render_fuse(self):
        """Move the fuse along the player's drawing path and render it."""
        if self.fuse is None or not self.fuse.active:
            return
        if self.frame_count % self.config.player_speed == 0:
            caught = self.fuse.move(steps=self.config.fuse_speed)
            if caught:
                logger.debug("Fuse caught the player")
                self.player_failed()
                return
        color = self.fuse.get_color(self.frame_count)
        self.canvas.create_dot_arena(self.fuse.x, self.fuse.y, rad=4, color=color)

    def fill_arena(self):
        percent_before = self.arena.filled_percent
        path_length = len(self.arena.player.path.get_positions())
        was_filled = self.arena.fill_arena(fill_callback=self.canvas.create_arena_rect)
        if was_filled:
            self.canvas.complete_drawing()
        self.canvas.create_new_drawing_surface()
        self.fuse = None
        # Score: percentage gained * 1000 + path length * 5
        percent_gained = self.arena.filled_percent - percent_before
        self.score += int(percent_gained * 1000) + path_length * 5
        self.check_level_complete()

    def check_level_complete(self):
        """Check if the current level's fill target has been reached."""
        if self.arena.filled_percent >= self.config.fill_percent:
            # Calculate bonuses
            excess = self.arena.filled_percent - self.config.fill_percent
            self.level_complete_lives_bonus = self.lives * 1000
            self.level_complete_excess_bonus = int(excess * 1000)
            self.score += self.level_complete_lives_bonus + self.level_complete_excess_bonus
            self.level_complete_filled = self.arena.filled_percent
            logger.debug("Level %d complete! (%.0f%% filled, score: %d)",
                         self.config.level_number, self.arena.filled_percent * 100, self.score)
            # Capture the current arena scene as background for transition
            self.canvas.render_arena()
            self.render_line_enemies()
            self.render_arena_enemies()
            self.render_player()
            self.canvas.draw_hud(
                level=self.config.level_number,
                fill_percent=self.arena.filled_percent,
                fill_target=self.config.fill_percent,
                score=self.score,
                lives=self.lives,
            )
            self.transition_snapshot = self.canvas.screen.copy()
            # Pre-generate next level config for tagline
            self.next_level_config = self.level_generator.build_level(self.current_level + 1)
            self.next_level_tagline = self._build_tagline(self.config, self.next_level_config)
            # Show transition screen
            self.state = GameState.LEVEL_TRANSITION

    def _build_tagline(self, current, next_config):
        """Build a short tagline describing how the next level differs."""
        hints = []
        if next_config.arena_width > current.arena_width + 5:
            hints.append("Wider arena")
        elif next_config.arena_width < current.arena_width - 5:
            hints.append("Tighter arena")
        if next_config.fill_percent > current.fill_percent + 0.03:
            hints.append("Higher fill target")
        if next_config.num_arena_enemies > current.num_arena_enemies:
            hints.append("More arena enemies")
        if next_config.num_line_enemies > current.num_line_enemies:
            hints.append("More line enemies")
        if next_config.line_enemy_speed < current.line_enemy_speed:
            hints.append("Faster line enemies")
        if next_config.fuse_chance > current.fuse_chance + 0.1:
            hints.append("Watch for the fuse!")
        if next_config.fuse_delay < current.fuse_delay - 2:
            hints.append("Fuse burns faster")
        if not hints:
            hints.append("Stay sharp!")
        return " | ".join(hints[:3])  # max 3 hints

    def _advance_to_next_level(self):
        """Start the pre-generated next level."""
        self.current_level += 1
        self.state = GameState.PLAYING
        self.start_level(self.next_level_config)

    def move_and_render_line_enemies(self):
        player = self.arena.player
        for line_enemy in self.arena.line_enemies:
            prev_ex, prev_ey = line_enemy.x, line_enemy.y
            move_x, move_y = line_enemy.move()
            self.canvas.create_dot_arena(line_enemy.x, line_enemy.y, color="red")
            if self.invincibility_frames > 0:
                continue  # skip collision check during invincibility
            on_same_cell = (line_enemy.x == player.x and line_enemy.y == player.y)
            enemy_was_on_player = (prev_ex == player.x and prev_ey == player.y)
            if on_same_cell or enemy_was_on_player:
                logger.debug("Line enemy hit player")
                self.player_failed()
                return

    def render_line_enemies(self):
        """Render line enemies at their current position without moving them."""
        for line_enemy in self.arena.line_enemies:
            self.canvas.create_dot_arena(line_enemy.x, line_enemy.y, color="red")

    def render_player(self):
        player = self.arena.player
        if self.invincibility_frames > 0:
            # Flash: alternate white/transparent every 4 frames
            if (self.frame_count // 4) % 2 == 0:
                self.canvas.create_dot_arena(player.x, player.y, color=(200, 200, 255))
            # else: skip rendering (invisible flash frame)
        else:
            self.canvas.create_dot_arena(player.x, player.y)

    def move_and_render_arena_enemies(self):
        for enemy in self.arena.arena_enemies:
            line_start, line_end, intersected = enemy.move()
            pixel_line_start = self.canvas.arena_to_pixel(line_start[0], line_start[1])
            pixel_line_end = self.canvas.arena_to_pixel(line_end[0], line_end[1])
            if len(self.last_n_lines) > 25:
                self.last_n_lines.pop(0)
            self.last_n_lines.append((pixel_line_start, pixel_line_end))
            if intersected:
                logger.debug("Arena enemy intersected with player drawing")
                self.player_failed()
        # Render all recent stick lines
        red_component = 5
        for (start, end) in self.last_n_lines:
            red_component += 8
            self.canvas.create_stick_line(start, end, red_component)

    def render_arena_enemies(self):
        """Render arena enemies at their current position without moving them."""
        red_component = 5
        for (start, end) in self.last_n_lines:
            red_component += 8
            self.canvas.create_stick_line(start, end, red_component)

    def player_failed(self):
        """Start the death explosion animation. Resets game state immediately, delays respawn visually."""
        if self.death_animation_frames > 0:
            return  # already dying, ignore further collisions
        player = self.arena.player
        px, py = self.canvas.arena_to_pixel(player.x, player.y)
        # Immediately clean up arena state to prevent re-triggering
        self.arena.change_player_path_state_to(CellState.FREE)
        self.canvas.create_new_drawing_surface()
        self.fuse = None
        self.drawing_direction = None
        self.lives -= 1
        if self.lives <= 0:
            logger.debug("Game over!")
        self._start_death_animation(px, py)

    def _handle_game_over(self):
        """Transition to game over state and update high score."""
        if self.score > self.high_score:
            self.high_score = self.score
            self._save_high_score()
        self.state = GameState.GAME_OVER

    def _start_death_animation(self, px, py):
        """Create explosion particles at the given pixel position."""
        self.death_animation_frames = 45
        self.death_particles = []
        for _ in range(30):
            angle = random.uniform(0, 2 * 3.14159)
            speed = random.uniform(1.5, 6.0)
            self.death_particles.append({
                'x': float(px),
                'y': float(py),
                'vx': speed * random.uniform(-1, 1),
                'vy': speed * random.uniform(-1, 1),
                'life': random.randint(20, 45),
                'radius': random.uniform(2.0, 5.0),
                'color': (255, 255, 255),
            })

    def _update_death_animation(self):
        """Advance the death animation by one frame. Returns True while still animating."""
        if self.death_animation_frames <= 0:
            return False
        self.death_animation_frames -= 1
        for p in self.death_particles:
            if p['life'] > 0:
                p['x'] += p['vx']
                p['y'] += p['vy']
                p['vy'] += 0.1  # gravity
                p['life'] -= 1
                p['radius'] *= 0.96
                # Fade from white -> yellow -> red -> dark
                t = p['life'] / 45.0
                r = max(0, min(255, int(255 * t + 100 * (1 - t))))
                g = max(0, min(255, int(255 * t * t)))
                b = 0
                p['color'] = (r, g, b)
        self.canvas.render_explosion(self.death_particles)
        return True

    def _finish_death(self):
        """Complete the death sequence: reset player or trigger game over."""
        self.death_particles = []
        self.death_animation_frames = 0
        if self.lives <= 0:
            self._handle_game_over()
            return
        self.arena.player.reset_player_state()
        self.invincibility_frames = int(self.game_config.invincibility_seconds * self.game_config.fps)
        self.canvas.create_new_drawing_surface()

    def loop(self):
        while self.running:
            self.running = self.canvas.check_for_exit()

            if self.state == GameState.TITLE:
                self._loop_title()
            elif self.state == GameState.PLAYING:
                self._loop_playing()
            elif self.state == GameState.LEVEL_TRANSITION:
                self._loop_level_transition()
            elif self.state == GameState.GAME_OVER:
                self._loop_game_over()

            self.canvas.render_frame(self.game_config.fps)

    def _loop_title(self):
        """Render title screen. Press SPACE to start."""
        self.canvas.screen.fill((0, 0, 0))
        self.canvas.draw_title_screen(self.high_score)
        if self.canvas.space_pressed():
            self._start_new_game()

    def _loop_level_transition(self):
        """Show level complete stats overlaid on the captured arena snapshot. Press SPACE to continue."""
        self.canvas.screen.blit(self.transition_snapshot, (0, 0))
        self.canvas.draw_level_complete_screen(
            level=self.config.level_number,
            filled=self.level_complete_filled,
            target=self.config.fill_percent,
            excess_bonus=self.level_complete_excess_bonus,
            lives_bonus=self.level_complete_lives_bonus,
            score=self.score,
            tagline=self.next_level_tagline,
            frame_count=self.frame_count,
        )
        self.frame_count += 1
        if self.canvas.space_pressed():
            self._advance_to_next_level()

    def _loop_game_over(self):
        """Show game over screen. Press SPACE to return to title."""
        self.canvas.screen.fill((0, 0, 0))
        self.canvas.draw_game_over_screen(self.score, self.high_score)
        if self.canvas.space_pressed():
            self.state = GameState.TITLE

    def _loop_playing(self):
        self.canvas.render_arena()

        # If death animation is playing, only render it and skip gameplay
        if self.death_animation_frames > 0:
            self._update_death_animation()
            if self.death_animation_frames <= 0:
                self._finish_death()
        else:
            # Player movement: auto-continue drawing direction + keyboard input
            if self.frame_count % self.config.player_speed == 0:
                if self.drawing_direction is not None:
                    self._move(*self.drawing_direction)
                self.handle_keyboard_input()

            # Line enemies: move on their tick, render every frame
            if self.frame_count % self.config.line_enemy_speed == 0:
                self.move_and_render_line_enemies()
            else:
                self.render_line_enemies()

            # Arena enemies: move on their tick, render every frame
            if self.frame_count % self.config.arena_enemy_speed == 0:
                self.move_and_render_arena_enemies()
            else:
                self.render_arena_enemies()

            # Fuse: move and render if active
            self.move_and_render_fuse()

            self.render_player()

            if self.invincibility_frames > 0:
                self.invincibility_frames -= 1

        # Draw HUD
        self.canvas.draw_hud(
            level=self.config.level_number,
            fill_percent=self.arena.filled_percent,
            fill_target=self.config.fill_percent,
            score=self.score,
            lives=self.lives,
        )
        self.frame_count += 1


class PyGameCanvas(object):
    """Canvas object that abstracts over pygame."""
    def __init__(self, game_config):
        pygame.init()
        self.max_width = game_config.max_window_width
        self.max_height = game_config.max_window_height
        self.width = self.max_width
        self.height = self.max_height
        self.margin = game_config.margin
        self.hud_height = game_config.hud_height
        self.preferred_cell_size = game_config.preferred_cell_size
        self.cell_size = 1  # will be set by configure()
        self.screen = pygame.display.set_mode((self.width, self.height))
        self.arena_surface = pygame.Surface((self.width, self.height))
        self.clock = pygame.time.Clock()
        pygame.font.init()
        self.hud_font = pygame.font.SysFont('Consolas', 16)

    def configure(self, arena_width, arena_height):
        """Set cell_size (preferred, capped to fit max window) and resize window to match."""
        self.arena_grid_width = arena_width
        self.arena_grid_height = arena_height
        # Use preferred cell_size, but shrink if the arena would exceed max window
        max_cell_w = (self.max_width - 2 * self.margin) // max(arena_width - 1, 1)
        max_cell_h = (self.max_height - 2 * self.margin - self.hud_height) // max(arena_height - 1, 1)
        self.cell_size = min(self.preferred_cell_size, max_cell_w, max_cell_h)
        self.cell_size = max(1, self.cell_size)
        # Resize window to fit the arena grid exactly
        actual_w = (arena_width - 1) * self.cell_size + 2 * self.margin
        actual_h = (arena_height - 1) * self.cell_size + 2 * self.margin + self.hud_height
        self.width = actual_w
        self.height = actual_h
        self.screen = pygame.display.set_mode((actual_w, actual_h))
        self.arena_surface = pygame.Surface((actual_w, actual_h))

    def arena_to_pixel(self, ax, ay):
        """Convert arena coordinates to pixel coordinates."""
        return (self.margin + ax * self.cell_size,
                self.margin + self.hud_height + ay * self.cell_size)

    def create_new_drawing_surface(self):
        self.drawing_surface = pygame.Surface((self.width, self.height))

    def check_for_exit(self):
        self._space_pressed_this_frame = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                self._space_pressed_this_frame = True
        return True

    def space_pressed(self):
        """Return True if SPACE was pressed (not held) this frame."""
        return self._space_pressed_this_frame

    def create_arena_frame(self):
        """Draw the arena perimeter rectangle matching the actual cell grid."""
        top_left = self.arena_to_pixel(0, 0)
        bottom_right = self.arena_to_pixel(self.arena_grid_width - 1, self.arena_grid_height - 1)
        rect = pygame.Rect(top_left[0], top_left[1],
                           bottom_right[0] - top_left[0],
                           bottom_right[1] - top_left[1])
        color = pygame.Color('white')
        return pygame.draw.rect(self.arena_surface, color, rect, 1)

    def create_dot_arena(self, ax, ay, rad=5, color='white'):
        """Draw a dot at arena coordinates."""
        px, py = self.arena_to_pixel(ax, ay)
        pos = pygame.Vector2(px, py)
        color_value = pygame.Color(color)
        return pygame.draw.circle(self.screen, color_value, pos, rad)

    def create_line_arena(self, ax1, ay1, ax2, ay2):
        """Draw a line between two arena coordinates."""
        start_pos = self.arena_to_pixel(ax1, ay1)
        end_pos = self.arena_to_pixel(ax2, ay2)
        color_param = pygame.Color('white')
        return pygame.draw.line(self.drawing_surface, color_param, start_pos, end_pos)

    def create_stick_line(self, start_pos, end_pos, red_component):
        color = pygame.Color(red_component, 0, 0)
        return pygame.draw.line(self.screen, color, start_pos, end_pos)

    def create_arena_rect(self, ax, ay):
        """Fill a cell at arena coordinates."""
        px, py = self.arena_to_pixel(ax, ay)
        half = self.cell_size // 2
        color_fill = pygame.Color('darkgreen')
        rect = pygame.Rect(px - half, py - half, self.cell_size, self.cell_size)
        return pygame.draw.rect(self.arena_surface, color_fill, rect)

    def draw_text(self, x, y, text, size=14):
        font = pygame.font.SysFont('Consolas', size)
        text_canvas = font.render(text, True, (255, 255, 255))
        return self.screen.blit(text_canvas, (x, y))

    def draw_hud(self, level, fill_percent, fill_target, score, lives):
        """Draw the HUD bar at the top of the screen."""
        hud_y = self.margin
        x = self.margin
        gap = 20
        texts = [
            f"Level: {level:02d}",
            f"Filled: {fill_percent:03.0%} ({fill_target:.0%})",
            f"Lives: {lives}",
            f"Score: {score}",
        ]
        for text in texts:
            surface = self.hud_font.render(text, True, (255, 255, 255))
            self.screen.blit(surface, (x, hud_y))
            x += surface.get_width() + gap

    def complete_drawing(self):
        self.arena_surface.blit(self.drawing_surface, (0, 0), special_flags=pygame.BLEND_ADD)

    def render_arena(self):
        self.screen.blit(self.arena_surface, (0, 0))
        self.screen.blit(self.drawing_surface, (0, 0), special_flags=pygame.BLEND_ADD)

    def render_explosion(self, particles):
        """Render explosion particles on screen."""
        for p in particles:
            if p['life'] > 0:
                pygame.draw.circle(self.screen, p['color'],
                                   (int(p['x']), int(p['y'])), max(1, int(p['radius'])))

    def draw_title_screen(self, high_score):
        """Draw the title screen with game name, high score, and start prompt."""
        cx = self.width // 2
        cy = self.height // 2
        title_font = pygame.font.SysFont('Consolas', 48, bold=True)
        sub_font = pygame.font.SysFont('Consolas', 20)
        prompt_font = pygame.font.SysFont('Consolas', 16)

        title = title_font.render("PyStix", True, (255, 255, 255))
        self.screen.blit(title, (cx - title.get_width() // 2, cy - 80))

        hs_text = sub_font.render(f"High Score: {high_score}", True, (200, 200, 100))
        self.screen.blit(hs_text, (cx - hs_text.get_width() // 2, cy))

        prompt = prompt_font.render("Press SPACE to start", True, (150, 150, 150))
        self.screen.blit(prompt, (cx - prompt.get_width() // 2, cy + 60))

    def draw_level_complete_screen(self, level, filled, target, excess_bonus, lives_bonus, score, tagline="", frame_count=0):
        """Draw the level complete stats overlaid on the arena."""
        # Semi-transparent dark overlay
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        cx = self.width // 2
        cy = self.height // 2
        title_font = pygame.font.SysFont('Consolas', 28, bold=True)
        stat_font = pygame.font.SysFont('Consolas', 18)

        title = title_font.render(f"Level {level} Complete!", True, (100, 255, 100))
        self.screen.blit(title, (cx - title.get_width() // 2, cy - 100))

        lines = [
            f"Filled: {filled:.0%}  (target: {target:.0%})",
            f"Excess bonus: +{excess_bonus}",
            f"Lives bonus:  +{lives_bonus}",
            f"Total score:  {score}",
        ]
        y = cy - 30
        for line in lines:
            surface = stat_font.render(line, True, (255, 255, 255))
            self.screen.blit(surface, (cx - surface.get_width() // 2, y))
            y += 30

        # Tagline for next level (flashing)
        if tagline:
            tagline_font = pygame.font.SysFont('Consolas', 14)
            if (frame_count // 15) % 2 == 0:
                tagline_color = (255, 200, 100)
            else:
                tagline_color = (180, 120, 50)
            tagline_surface = tagline_font.render(f"Next: {tagline}", True, tagline_color)
            self.screen.blit(tagline_surface, (cx - tagline_surface.get_width() // 2, y + 10))
            y += 30

        prompt_font = pygame.font.SysFont('Consolas', 16)
        prompt = prompt_font.render("Press SPACE to continue", True, (150, 150, 150))
        self.screen.blit(prompt, (cx - prompt.get_width() // 2, y + 10))

    def draw_game_over_screen(self, score, high_score):
        """Draw the game over screen."""
        cx = self.width // 2
        cy = self.height // 2
        title_font = pygame.font.SysFont('Consolas', 36, bold=True)
        stat_font = pygame.font.SysFont('Consolas', 20)
        prompt_font = pygame.font.SysFont('Consolas', 16)

        title = title_font.render("GAME OVER", True, (255, 50, 50))
        self.screen.blit(title, (cx - title.get_width() // 2, cy - 80))

        score_text = stat_font.render(f"Score: {score}", True, (255, 255, 255))
        self.screen.blit(score_text, (cx - score_text.get_width() // 2, cy - 20))

        if score >= high_score and score > 0:
            hs_text = stat_font.render("NEW HIGH SCORE!", True, (255, 255, 100))
        else:
            hs_text = stat_font.render(f"High Score: {high_score}", True, (200, 200, 100))
        self.screen.blit(hs_text, (cx - hs_text.get_width() // 2, cy + 20))

        prompt = prompt_font.render("Press SPACE to continue", True, (150, 150, 150))
        self.screen.blit(prompt, (cx - prompt.get_width() // 2, cy + 80))

    def render_frame(self, game_speed):
        pygame.display.flip()
        self.clock.tick(game_speed)


if __name__ == '__main__':
    game_config = GameConfig()
    canvas = PyGameCanvas(game_config)
    game = Game(canvas, game_config)
    game.loop()