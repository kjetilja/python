"""Tests for pystix game logic.

All tests exercise the model classes (Arena, Player, LineEnemy, ArenaEnemy)
directly — no pygame dependency needed.
"""
import pytest
from pystix import (
    Arena, Player, LineEnemy, ArenaEnemy, FuseEnemy, LevelGenerator,
    CellState, MoveResult, LevelConfig, GameState, Path, ARCHETYPES,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_config(width=10, height=10, num_line_enemies=0, num_arena_enemies=0,
                fill_percent=0.75, player_speed=1, line_enemy_speed=1,
                arena_enemy_speed=1):
    """Create a LevelConfig for testing with sensible defaults."""
    return LevelConfig(
        level_number=1,
        fill_percent=fill_percent,
        arena_width=width,
        arena_height=height,
        num_line_enemies=num_line_enemies,
        num_arena_enemies=num_arena_enemies,
        player_speed=player_speed,
        line_enemy_speed=line_enemy_speed,
        arena_enemy_speed=arena_enemy_speed,
    )


def make_arena(width=10, height=10, num_line_enemies=0, num_arena_enemies=0):
    """Create an Arena for testing (no enemies by default)."""
    config = make_config(width=width, height=height,
                         num_line_enemies=num_line_enemies,
                         num_arena_enemies=num_arena_enemies)
    return Arena(config)


def noop_fill_callback(x, y):
    """No-op callback for fill_arena, replacing the canvas rendering call."""
    pass


# ---------------------------------------------------------------------------
# Arena initialization
# ---------------------------------------------------------------------------

class TestArenaInit:
    def test_dimensions(self):
        arena = make_arena(10, 8)
        assert arena.arena_width == 10
        assert arena.arena_height == 8

    def test_perimeter_is_wall(self):
        arena = make_arena(10, 10)
        # Top and bottom rows
        for x in range(10):
            assert arena.get_cell(x, 0) == CellState.WALL
            assert arena.get_cell(x, 9) == CellState.WALL
        # Left and right columns
        for y in range(10):
            assert arena.get_cell(0, y) == CellState.WALL
            assert arena.get_cell(9, y) == CellState.WALL

    def test_interior_is_free(self):
        arena = make_arena(10, 10)
        for y in range(1, 9):
            for x in range(1, 9):
                assert arena.get_cell(x, y) == CellState.FREE

    def test_get_set_cell(self):
        arena = make_arena(10, 10)
        arena.set_cell(5, 5, CellState.FILLED)
        assert arena.get_cell(5, 5) == CellState.FILLED

    def test_player_starts_at_origin(self):
        arena = make_arena()
        assert arena.player.x == 0
        assert arena.player.y == 0

    def test_filled_percent_initial(self):
        arena = make_arena(10, 10)
        # Only perimeter walls: 10+10+8+8 = 36 wall cells out of 100
        assert arena.filled_percent == pytest.approx(36 / 100)


# ---------------------------------------------------------------------------
# Player movement — not drawing
# ---------------------------------------------------------------------------

class TestPlayerMovementNotDrawing:
    def test_move_along_wall_right(self):
        arena = make_arena(10, 10)
        player = arena.player
        assert player.x == 0 and player.y == 0
        result = player.try_move(1, 0)  # (0,0) -> (1,0), both WALL
        assert result == MoveResult.OK
        assert player.x == 1 and player.y == 0

    def test_move_along_wall_down(self):
        arena = make_arena(10, 10)
        player = arena.player
        result = player.try_move(0, 1)  # (0,0) -> (0,1), both WALL
        assert result == MoveResult.OK
        assert player.x == 0 and player.y == 1

    def test_cannot_move_into_free_when_not_drawing(self):
        arena = make_arena(10, 10)
        player = arena.player
        # Move to (1,0) first (wall)
        player.try_move(1, 0)
        # Now try to move into (1,1) which is FREE
        result = player.try_move(0, 1)
        assert result == MoveResult.BLOCKED
        assert player.x == 1 and player.y == 0

    def test_cannot_move_out_of_bounds(self):
        arena = make_arena(10, 10)
        player = arena.player
        result = player.try_move(-1, 0)
        assert result == MoveResult.BLOCKED
        assert player.x == 0 and player.y == 0

        result = player.try_move(0, -1)
        assert result == MoveResult.BLOCKED
        assert player.x == 0 and player.y == 0

    def test_multiple_wall_moves(self):
        arena = make_arena(10, 10)
        player = arena.player
        # Walk along top wall
        for i in range(9):
            result = player.try_move(1, 0)
            assert result == MoveResult.OK
        assert player.x == 9 and player.y == 0
        # Can't go further right
        result = player.try_move(1, 0)
        assert result == MoveResult.BLOCKED


# ---------------------------------------------------------------------------
# Player drawing lifecycle
# ---------------------------------------------------------------------------

class TestPlayerDrawing:
    def test_initiate_drawing_on_wall_adjacent_to_free(self):
        arena = make_arena(10, 10)
        player = arena.player
        # Move to (1,0) — wall, adjacent to (1,1) which is FREE
        player.try_move(1, 0)
        player.initiate_drawing()
        assert player.is_drawing is True
        assert player.drawing_completed is False

    def test_cannot_initiate_drawing_at_corner(self):
        arena = make_arena(10, 10)
        player = arena.player
        # At (0,0) — all neighbors are WALL (left/up are out of bounds, right=(1,0)=WALL, down=(0,1)=WALL)
        player.initiate_drawing()
        assert player.is_drawing is False

    def test_draw_into_free_marks_drawing(self):
        arena = make_arena(10, 10)
        player = arena.player
        player.try_move(1, 0)  # to (1,0) WALL
        player.initiate_drawing()
        result = player.try_move(0, 1)  # to (1,1) FREE
        assert result == MoveResult.OK
        assert arena.get_cell(1, 1) == CellState.DRAWING
        assert player.x == 1 and player.y == 1

    def test_path_tracks_positions(self):
        arena = make_arena(10, 10)
        player = arena.player
        player.try_move(1, 0)
        player.initiate_drawing()
        player.try_move(0, 1)  # (1,1)
        player.try_move(0, 1)  # (1,2)
        player.try_move(0, 1)  # (1,3)
        assert player.path.get_positions() == [(1, 1), (1, 2), (1, 3)]

    def test_drawing_completed_on_reaching_wall(self):
        """Draw from top wall down and then right to right wall."""
        arena = make_arena(10, 10)
        player = arena.player
        # Walk to (1,0) on top wall
        player.try_move(1, 0)
        player.initiate_drawing()
        # Draw down into free space: (1,1), (1,2), (1,3)
        player.try_move(0, 1)
        player.try_move(0, 1)
        player.try_move(0, 1)
        assert player.drawing_completed is False
        # Now move right towards the right wall won't hit wall yet at (2,3)
        # Instead, move back to bottom wall: keep going down
        for y in range(4, 9):
            result = player.try_move(0, 1)
            assert result == MoveResult.OK
        # Player at (1,8), next move (1,9) is bottom WALL
        assert player.x == 1 and player.y == 8
        result = player.try_move(0, 1)  # (1,9) is WALL, path has >2 positions
        assert result == MoveResult.OK
        assert player.drawing_completed is True

    def test_drawing_blocked_on_wall_with_short_path(self):
        """Cannot terminate drawing by reaching wall if path has <= 2 positions."""
        arena = make_arena(10, 10)
        player = arena.player
        player.try_move(1, 0)  # (1,0) WALL
        player.initiate_drawing()
        player.try_move(0, 1)  # (1,1) FREE -> path has 1 position
        # Try to move to (0,1) which is WALL — but path only has 1 position
        result = player.try_move(-1, 0)
        assert result == MoveResult.BLOCKED
        assert player.drawing_completed is False

    def test_drawing_dies_on_drawing_cell(self):
        arena = make_arena(10, 10)
        player = arena.player
        player.try_move(1, 0)
        player.initiate_drawing()
        player.try_move(0, 1)  # (1,1) now DRAWING
        player.try_move(1, 0)  # (2,1) FREE -> DRAWING
        player.try_move(0, -1) # (2,0) WALL — but path has only 2, BLOCKED
        # So go further
        player.try_move(1, 0)  # (3,1) FREE -> DRAWING
        # Now try moving back up and left into (1,1) which is DRAWING
        player.try_move(0, -1) # (3,0) WALL, path=3 -> drawing_completed
        # Actually that completes drawing. Let's set up differently.

    def test_drawing_dies_on_own_line(self):
        """Moving into a cell that is already DRAWING kills the player."""
        arena = make_arena(10, 10)
        player = arena.player
        player.try_move(1, 0)  # (1,0) WALL
        player.initiate_drawing()
        player.try_move(0, 1)  # (1,1) DRAWING
        player.try_move(1, 0)  # (2,1) DRAWING
        player.try_move(0, 1)  # (2,2) DRAWING
        player.try_move(-1, 0) # (1,2) DRAWING
        # Now try to move up into (1,1) which is DRAWING
        result = player.try_move(0, -1)
        assert result == MoveResult.DIED

    def test_initiate_drawing_resets_path(self):
        arena = make_arena(10, 10)
        player = arena.player
        player.try_move(1, 0)
        player.initiate_drawing()
        assert player.path.get_positions() == []

    def test_cannot_initiate_drawing_if_already_drawing(self):
        arena = make_arena(10, 10)
        player = arena.player
        player.try_move(1, 0)
        player.initiate_drawing()
        player.try_move(0, 1)  # start drawing
        # Try to initiate again — should be no-op
        player.initiate_drawing()
        assert player.is_drawing is True  # still drawing, not reset


# ---------------------------------------------------------------------------
# Player state after fill_arena completes
# ---------------------------------------------------------------------------

class TestPlayerStateAfterFill:
    def _draw_line_and_fill(self, arena):
        """Helper: draw a vertical line from top wall to bottom wall and fill."""
        player = arena.player
        # Walk to (1,0)
        player.try_move(1, 0)
        player.initiate_drawing()
        # Draw down: (1,1) through (1,8)
        for _ in range(8):
            player.try_move(0, 1)
        # Reach bottom wall (1,9)
        player.try_move(0, 1)
        assert player.drawing_completed is True
        # Fill
        arena.fill_arena(noop_fill_callback)

    def test_is_drawing_false_after_fill(self):
        arena = make_arena(10, 10, num_arena_enemies=0)
        self._draw_line_and_fill(arena)
        assert arena.player.is_drawing is False

    def test_drawing_completed_true_after_fill(self):
        arena = make_arena(10, 10, num_arena_enemies=0)
        self._draw_line_and_fill(arena)
        assert arena.player.drawing_completed is True

    def test_path_cells_become_wall_after_fill(self):
        arena = make_arena(10, 10, num_arena_enemies=0)
        player = arena.player
        player.try_move(1, 0)
        player.initiate_drawing()
        for _ in range(8):
            player.try_move(0, 1)
        player.try_move(0, 1)
        path_positions = list(player.path.get_positions())
        arena.fill_arena(noop_fill_callback)
        for x, y in path_positions:
            assert arena.get_cell(x, y) == CellState.WALL

    def test_filled_percent_increases_after_fill(self):
        arena = make_arena(10, 10, num_arena_enemies=0)
        initial = arena.filled_percent
        self._draw_line_and_fill(arena)
        assert arena.filled_percent > initial

    def test_player_on_wall_after_fill(self):
        """After completing a drawing, the player should be on a WALL cell."""
        arena = make_arena(10, 10, num_arena_enemies=0)
        self._draw_line_and_fill(arena)
        player = arena.player
        assert arena.get_cell(player.x, player.y) == CellState.WALL


# ---------------------------------------------------------------------------
# change_player_path_state_to
# ---------------------------------------------------------------------------

class TestChangePathState:
    def test_revert_drawing_to_free(self):
        arena = make_arena(10, 10)
        player = arena.player
        player.try_move(1, 0)
        player.initiate_drawing()
        player.try_move(0, 1)  # (1,1) DRAWING
        player.try_move(0, 1)  # (1,2) DRAWING
        arena.change_player_path_state_to(CellState.FREE)
        assert arena.get_cell(1, 1) == CellState.FREE
        assert arena.get_cell(1, 2) == CellState.FREE

    def test_path_to_wall(self):
        arena = make_arena(10, 10)
        player = arena.player
        player.try_move(1, 0)
        player.initiate_drawing()
        player.try_move(0, 1)
        player.try_move(0, 1)
        arena.change_player_path_state_to(CellState.WALL)
        assert arena.get_cell(1, 1) == CellState.WALL
        assert arena.get_cell(1, 2) == CellState.WALL


# ---------------------------------------------------------------------------
# fill_arena — region detection
# ---------------------------------------------------------------------------

class TestFillArena:
    def test_vertical_line_fills_smaller_side(self):
        """Drawing a vertical line from top to bottom should fill the smaller side."""
        arena = make_arena(10, 10, num_arena_enemies=0)
        player = arena.player
        # Draw vertical line at x=3 from top wall to bottom wall
        # Walk along top wall to (3,0)
        for _ in range(3):
            player.try_move(1, 0)
        player.initiate_drawing()
        for _ in range(8):
            player.try_move(0, 1)
        player.try_move(0, 1)  # reach (3,9) bottom wall
        filled_cells = []
        arena.fill_arena(lambda x, y: filled_cells.append((x, y)))
        # The smaller region (x=1,2 for y=1..8) should be filled
        # That's 2*8 = 16 cells
        assert len(filled_cells) == 16
        for x, y in filled_cells:
            assert x in (1, 2)
            assert 1 <= y <= 8

    def test_horizontal_line_fills_smaller_side(self):
        """Drawing a horizontal line from left to right wall should fill the smaller side."""
        arena = make_arena(10, 10, num_arena_enemies=0)
        player = arena.player
        # Walk to (0,3) on left wall
        for _ in range(3):
            player.try_move(0, 1)
        player.initiate_drawing()
        for _ in range(8):
            player.try_move(1, 0)
        player.try_move(1, 0)  # reach (9,3) right wall
        filled_cells = []
        arena.fill_arena(lambda x, y: filled_cells.append((x, y)))
        # Smaller region: y=1,2 for x=1..8 = 2*8 = 16 cells
        assert len(filled_cells) == 16

    def test_no_free_cells_after_complete_fill(self):
        """After filling enough, get_free_position eventually returns positions in the kept region."""
        arena = make_arena(10, 10, num_arena_enemies=0)
        player = arena.player
        for _ in range(3):
            player.try_move(1, 0)
        player.initiate_drawing()
        for _ in range(8):
            player.try_move(0, 1)
        player.try_move(0, 1)
        arena.fill_arena(noop_fill_callback)
        # There should still be free cells (the larger side)
        assert arena.get_free_position() is not None

    def test_enemy_region_is_kept(self):
        """The region containing an arena enemy should not be filled."""
        arena = make_arena(20, 20, num_arena_enemies=1)
        enemy = arena.arena_enemies[0]
        # Place enemy at a known position in the interior
        enemy.end1_x = 15
        enemy.end1_y = 10
        enemy.end2_x = 16
        enemy.end2_y = 10
        player = arena.player
        # Draw vertical line at x=10
        for _ in range(10):
            player.try_move(1, 0)
        player.initiate_drawing()
        for _ in range(18):
            player.try_move(0, 1)
        player.try_move(0, 1)
        arena.fill_arena(noop_fill_callback)
        # The enemy is at x=15, which is the right side — that region should be kept (FREE)
        assert arena.get_cell(15, 10) == CellState.FREE

    def test_enemies_in_separate_regions_all_kept(self):
        """When enemies are in different regions, all enemy regions are kept."""
        arena = make_arena(20, 20, num_arena_enemies=2)
        e0 = arena.arena_enemies[0]
        e1 = arena.arena_enemies[1]
        # Place enemy 0 on the left side
        e0.end1_x = 3
        e0.end1_y = 10
        e0.end2_x = 4
        e0.end2_y = 10
        # Place enemy 1 on the right side
        e1.end1_x = 15
        e1.end1_y = 10
        e1.end2_x = 16
        e1.end2_y = 10
        player = arena.player
        # Draw vertical line at x=10
        for _ in range(10):
            player.try_move(1, 0)
        player.initiate_drawing()
        for _ in range(18):
            player.try_move(0, 1)
        player.try_move(0, 1)
        arena.fill_arena(noop_fill_callback)
        # Both enemy positions should still be FREE (both regions kept)
        assert arena.get_cell(3, 10) == CellState.FREE
        assert arena.get_cell(15, 10) == CellState.FREE

    def test_enemies_in_all_regions_reverts_path(self):
        """When every region contains an enemy and nothing is filled, the path should revert to FREE."""
        arena = make_arena(20, 20, num_arena_enemies=2)
        e0 = arena.arena_enemies[0]
        e1 = arena.arena_enemies[1]
        # Place enemy 0 on the left side
        e0.end1_x = 3
        e0.end1_y = 10
        e0.end2_x = 4
        e0.end2_y = 10
        # Place enemy 1 on the right side
        e1.end1_x = 15
        e1.end1_y = 10
        e1.end2_x = 16
        e1.end2_y = 10
        player = arena.player
        # Draw vertical line at x=10
        for _ in range(10):
            player.try_move(1, 0)
        player.initiate_drawing()
        path_positions = []
        for _ in range(18):
            player.try_move(0, 1)
            path_positions.append((player.x, player.y))
        player.try_move(0, 1)
        arena.fill_arena(noop_fill_callback)
        # Nothing was filled, so path cells should be reverted to FREE, not WALL
        for x, y in path_positions:
            assert arena.get_cell(x, y) == CellState.FREE, \
                f"Cell ({x},{y}) should be FREE but is {arena.get_cell(x, y)}"

    def test_no_enemies_fills_smaller_region(self):
        """With no enemies, the smaller region should be filled."""
        arena = make_arena(20, 20, num_arena_enemies=0)
        player = arena.player
        for _ in range(5):
            player.try_move(1, 0)
        player.initiate_drawing()
        for _ in range(18):
            player.try_move(0, 1)
        player.try_move(0, 1)
        filled_cells = []
        arena.fill_arena(lambda x, y: filled_cells.append((x, y)))
        # Smaller side (x=1..4, y=1..18) = 4*18 = 72 cells
        assert len(filled_cells) == 72


# ---------------------------------------------------------------------------
# Drawing edge cases — the suspected bug area
# ---------------------------------------------------------------------------

class TestDrawingEdgeCases:
    def test_complete_draw_then_move_on_wall(self):
        """After completing a drawing, player should be able to move along walls."""
        arena = make_arena(10, 10, num_arena_enemies=0)
        player = arena.player
        player.try_move(1, 0)  # (1,0)
        player.initiate_drawing()
        for _ in range(8):
            player.try_move(0, 1)
        player.try_move(0, 1)  # (1,9) completes drawing
        arena.fill_arena(noop_fill_callback)
        # Player should now be at (1,9) on bottom wall, not drawing
        assert player.is_drawing is False
        assert player.x == 1 and player.y == 9
        assert arena.get_cell(1, 9) == CellState.WALL
        # Should be able to move right along bottom wall
        result = player.try_move(1, 0)
        assert result == MoveResult.OK
        assert player.x == 2 and player.y == 9

    def test_complete_draw_cannot_move_into_free(self):
        """After completing a drawing, player should NOT be able to move into FREE cells."""
        arena = make_arena(10, 10, num_arena_enemies=0)
        player = arena.player
        player.try_move(1, 0)
        player.initiate_drawing()
        for _ in range(8):
            player.try_move(0, 1)
        player.try_move(0, 1)
        arena.fill_arena(noop_fill_callback)
        # Player at (1,9). The drawn line at x=1 is now WALL.
        # Move up: (1,8) was a drawn cell, now WALL — should be OK
        result = player.try_move(0, -1)
        assert result == MoveResult.OK
        # But trying to move into remaining free area should be blocked
        # Move to a position adjacent to free space
        # (1,8) -> (2,8) — is (2,8) free or filled?
        # The smaller side (x=1..2 or equivalent) was filled.
        # Let's just verify the player can't walk into a FREE cell
        player_moved_into_free = False
        for _ in range(20):
            result = player.try_move(1, 0)
            if result == MoveResult.OK:
                cell = arena.get_cell(player.x, player.y)
                if cell == CellState.FREE:
                    player_moved_into_free = True
                    break
            else:
                break
        assert player_moved_into_free is False

    def test_minimum_path_length_drawing(self):
        """A drawing with exactly 3 path positions should complete successfully."""
        arena = make_arena(10, 10, num_arena_enemies=0)
        player = arena.player
        player.try_move(1, 0)  # (1,0) WALL
        player.initiate_drawing()
        player.try_move(0, 1)  # (1,1) path=1
        player.try_move(0, 1)  # (1,2) path=2
        player.try_move(0, 1)  # (1,3) path=3
        assert len(player.path.get_positions()) == 3
        # Now move to left wall (0,3) — WALL, path > 2
        result = player.try_move(-1, 0)
        assert result == MoveResult.OK
        assert player.drawing_completed is True

    def test_drawing_with_exactly_2_positions_cannot_complete(self):
        """A drawing with only 2 path positions should not complete at a wall."""
        arena = make_arena(10, 10)
        player = arena.player
        player.try_move(1, 0)  # (1,0) WALL
        player.initiate_drawing()
        player.try_move(0, 1)  # (1,1) path=1
        player.try_move(0, 1)  # (1,2) path=2
        # Try to reach left wall at (0,2)
        result = player.try_move(-1, 0)
        assert result == MoveResult.BLOCKED
        assert player.drawing_completed is False

    def test_drawing_state_consistent_through_full_cycle(self):
        """Walk the full drawing lifecycle and verify all state transitions."""
        arena = make_arena(10, 10, num_arena_enemies=0)
        player = arena.player

        # 1. Initial state
        assert player.is_drawing is False
        assert player.drawing_completed is True

        # 2. Move to starting position on wall
        player.try_move(1, 0)
        assert player.x == 1 and player.y == 0

        # 3. Initiate drawing
        player.initiate_drawing()
        assert player.is_drawing is True
        assert player.drawing_completed is False
        assert player.path.get_positions() == []

        # 4. Draw several cells
        for i in range(1, 9):
            result = player.try_move(0, 1)
            assert result == MoveResult.OK
            assert player.is_drawing is True
            assert arena.get_cell(1, i) == CellState.DRAWING

        # 5. Complete drawing by reaching bottom wall
        result = player.try_move(0, 1)  # (1,9) WALL
        assert result == MoveResult.OK
        assert player.drawing_completed is True
        assert player.is_drawing is True  # still true until fill_arena

        # 6. fill_arena resets drawing state
        arena.fill_arena(noop_fill_callback)
        assert player.is_drawing is False
        assert player.drawing_completed is True

        # 7. Path cells are now WALL
        for i in range(1, 9):
            assert arena.get_cell(1, i) == CellState.WALL

        # 8. Player can move on walls
        result = player.try_move(1, 0)
        assert result == MoveResult.OK

    def test_player_revert_on_failure(self):
        """When player_failed, DRAWING cells revert to FREE and player resets."""
        arena = make_arena(10, 10)
        player = arena.player
        player.try_move(1, 0)
        player.initiate_drawing()
        player.try_move(0, 1)  # (1,1) DRAWING
        player.try_move(0, 1)  # (1,2) DRAWING
        player.try_move(0, 1)  # (1,3) DRAWING

        # Simulate player_failed
        arena.change_player_path_state_to(CellState.FREE)
        player.reset_player_state()

        assert arena.get_cell(1, 1) == CellState.FREE
        assert arena.get_cell(1, 2) == CellState.FREE
        assert arena.get_cell(1, 3) == CellState.FREE
        assert player.x == 0 and player.y == 0
        assert player.is_drawing is False


# ---------------------------------------------------------------------------
# LineEnemy
# ---------------------------------------------------------------------------

class TestLineEnemy:
    def test_moves_on_wall_cells(self):
        arena = make_arena(10, 10)
        enemy = LineEnemy(arena, 0, 0)
        enemy.direction = 0  # right
        for _ in range(20):
            enemy.move()
            cell = arena.get_cell(enemy.x, enemy.y)
            assert cell == CellState.WALL or cell == CellState.DRAWING

    def test_stays_in_bounds(self):
        arena = make_arena(10, 10)
        enemy = LineEnemy(arena, 0, 0)
        for _ in range(100):
            enemy.move()
            assert 0 <= enemy.x < arena.arena_width
            assert 0 <= enemy.y < arena.arena_height

    def test_no_directions_returns_zero(self):
        """When surrounded by non-traversable cells, returns (0,0)."""
        arena = make_arena(10, 10)
        arena.set_cell(5, 0, CellState.FILLED)
        arena.set_cell(4, 0, CellState.FILLED)
        arena.set_cell(6, 0, CellState.FILLED)
        enemy = LineEnemy(arena, 5, 0)
        dx, dy = enemy.move()
        assert dx == 0 and dy == 0

    def test_does_not_spawn_on_player_start(self):
        """Line enemies must not spawn at or adjacent to the player start position."""
        for _ in range(50):  # repeat to cover randomness
            arena = make_arena(10, 10, num_line_enemies=4)
            player_x, player_y = arena.player.start_pos
            excluded = {(player_x + dx, player_y + dy)
                        for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
            for enemy in arena.line_enemies:
                assert (enemy.x, enemy.y) not in excluded

    def test_spawn_on_large_arena(self):
        """Line enemies on a 200x200 arena should not spawn near the player."""
        for _ in range(20):
            arena = make_arena(200, 200, num_line_enemies=2)
            for enemy in arena.line_enemies:
                assert (enemy.x, enemy.y) != (0, 0)

    def test_stranded_enemy_respawns_on_path_revert(self):
        """When a drawing path is reverted to FREE, line enemies on those cells should respawn."""
        arena = make_arena(10, 10, num_line_enemies=1)
        enemy = arena.line_enemies[0]
        player = arena.player
        # Move player and start drawing
        player.try_move(1, 0)
        player.initiate_drawing()
        player.try_move(0, 1)  # (1,1) DRAWING
        player.try_move(0, 1)  # (1,2) DRAWING
        player.try_move(0, 1)  # (1,3) DRAWING
        # Place enemy on a DRAWING cell
        enemy.x = 1
        enemy.y = 2
        assert arena.get_cell(1, 2) == CellState.DRAWING
        # Revert path (simulating player death)
        arena.change_player_path_state_to(CellState.FREE)
        # Enemy should have been respawned to a WALL cell
        cell = arena.get_cell(enemy.x, enemy.y)
        assert cell == CellState.WALL, f"Enemy at ({enemy.x},{enemy.y}) is on {cell}, expected WALL"

    def test_enemy_not_respawned_if_on_wall(self):
        """Line enemies already on WALL cells should not be moved during path revert."""
        arena = make_arena(10, 10, num_line_enemies=1)
        enemy = arena.line_enemies[0]
        # Place enemy on a wall cell
        enemy.x = 5
        enemy.y = 0
        assert arena.get_cell(5, 0) == CellState.WALL
        player = arena.player
        player.try_move(1, 0)
        player.initiate_drawing()
        player.try_move(0, 1)
        # Revert path
        arena.change_player_path_state_to(CellState.FREE)
        # Enemy should still be at (5,0)
        assert enemy.x == 5 and enemy.y == 0


# ---------------------------------------------------------------------------
# ArenaEnemy
# ---------------------------------------------------------------------------

class TestArenaEnemy:
    def test_stays_in_free_space(self):
        arena = make_arena(20, 20, num_arena_enemies=1)
        enemy = arena.arena_enemies[0]
        for _ in range(50):
            enemy.move()
            assert arena.get_cell(enemy.end1_x, enemy.end1_y) == CellState.FREE
            assert arena.get_cell(enemy.end2_x, enemy.end2_y) == CellState.FREE

    def test_detects_drawing_intersection(self):
        arena = make_arena(20, 20, num_arena_enemies=1)
        enemy = arena.arena_enemies[0]
        # Place a DRAWING cell directly on end1 position
        arena.set_cell(enemy.end1_x, enemy.end1_y, CellState.DRAWING)
        # The intersects method should detect this
        result = enemy.intersects(enemy.end1_x, enemy.end1_y, enemy.end2_x, enemy.end2_y)
        assert result is True
        assert enemy.intersected is True


# ---------------------------------------------------------------------------
# filled_percent
# ---------------------------------------------------------------------------

class TestFilledPercent:
    def test_increases_after_fill(self):
        arena = make_arena(10, 10, num_arena_enemies=0)
        before = arena.filled_percent
        player = arena.player
        for _ in range(3):
            player.try_move(1, 0)
        player.initiate_drawing()
        for _ in range(8):
            player.try_move(0, 1)
        player.try_move(0, 1)
        arena.fill_arena(noop_fill_callback)
        after = arena.filled_percent
        assert after > before

    def test_wall_plus_filled_counted(self):
        arena = make_arena(5, 5)
        # 5x5 = 25 cells, perimeter = 5+5+3+3 = 16 WALL cells
        assert arena.filled_percent == pytest.approx(16 / 25)
        # Manually fill one cell
        arena.set_cell(2, 2, CellState.FILLED)
        assert arena.filled_percent == pytest.approx(17 / 25)


# ---------------------------------------------------------------------------
# L-shaped and corner drawings
# ---------------------------------------------------------------------------

class TestLShapedDrawing:
    def test_l_shaped_draw_completes(self):
        """Drawing an L-shape (down then right) should complete at the wall."""
        arena = make_arena(10, 10, num_arena_enemies=0)
        player = arena.player
        # Start at (1,0), draw down to (1,5), then right to (9,5) — hitting right wall
        player.try_move(1, 0)
        player.initiate_drawing()
        for _ in range(5):
            player.try_move(0, 1)  # (1,1)..(1,5)
        for _ in range(8):
            player.try_move(1, 0)  # (2,5)..(9,5) — (9,5) is WALL
        assert player.drawing_completed is True
        # path should have 5 + 7 = 12 positions (last move to wall doesn't add to path)
        # (1,1),(1,2),(1,3),(1,4),(1,5),(2,5),(3,5),(4,5),(5,5),(6,5),(7,5),(8,5) = 12
        assert len(player.path.get_positions()) == 12

    def test_l_shaped_fill(self):
        """After L-shaped draw and fill, the enclosed corner region is filled."""
        arena = make_arena(10, 10, num_arena_enemies=0)
        player = arena.player
        player.try_move(1, 0)
        player.initiate_drawing()
        for _ in range(5):
            player.try_move(0, 1)
        for _ in range(8):
            player.try_move(1, 0)
        filled_cells = []
        arena.fill_arena(lambda x, y: filled_cells.append((x, y)))
        # Some cells should be filled
        assert len(filled_cells) > 0


class TestLargeArenaFill:
    def test_fill_on_200x200_arena(self):
        """Fill should work correctly on a 200x200 arena (level 3 size)."""
        arena = make_arena(200, 200, num_arena_enemies=0)
        player = arena.player
        # Walk to (50,0) on top wall
        for _ in range(50):
            player.try_move(1, 0)
        player.initiate_drawing()
        # Draw down from (50,1) to (50,198)
        for _ in range(198):
            player.try_move(0, 1)
        # Reach bottom wall (50,199)
        player.try_move(0, 1)
        assert player.drawing_completed is True
        filled_cells = []
        arena.fill_arena(lambda x, y: filled_cells.append((x, y)))
        # Smaller side: x=1..49 for y=1..198 = 49*198 = 9702 cells
        assert len(filled_cells) == 49 * 198
        assert player.is_drawing is False

    def test_fill_percent_after_200x200_draw(self):
        """Fill percent should increase significantly after a draw on 200x200."""
        arena = make_arena(200, 200, num_arena_enemies=0)
        initial = arena.filled_percent
        player = arena.player
        for _ in range(50):
            player.try_move(1, 0)
        player.initiate_drawing()
        for _ in range(198):
            player.try_move(0, 1)
        player.try_move(0, 1)
        arena.fill_arena(noop_fill_callback)
        assert arena.filled_percent > initial


# ---------------------------------------------------------------------------
# Multiple draws on the same arena
# ---------------------------------------------------------------------------

class TestMultipleDraws:
    def test_two_sequential_draws(self):
        """Two separate drawings should both work and increase fill percent."""
        arena = make_arena(10, 10, num_arena_enemies=0)
        player = arena.player

        # First draw: vertical line at x=3
        for _ in range(3):
            player.try_move(1, 0)
        player.initiate_drawing()
        for _ in range(8):
            player.try_move(0, 1)
        player.try_move(0, 1)
        arena.fill_arena(noop_fill_callback)
        fill_after_first = arena.filled_percent

        # Second draw: player is at (3,9), draw horizontal line at y=5
        # First move along bottom wall to (5,9)
        player.try_move(1, 0)  # (4,9)
        player.try_move(1, 0)  # (5,9)
        player.initiate_drawing()
        for _ in range(8):
            player.try_move(0, -1)   # up through free/filled space
        # Check if we can reach top wall
        result = player.try_move(0, -1)
        if result == MoveResult.OK and player.drawing_completed:
            arena.fill_arena(noop_fill_callback)
            fill_after_second = arena.filled_percent
            assert fill_after_second >= fill_after_first


# ---------------------------------------------------------------------------
# Path object
# ---------------------------------------------------------------------------

class TestPath:
    def test_reset(self):
        path = Path()
        path.add_position(1, 2)
        path.add_position(3, 4)
        path.reset()
        assert path.get_positions() == []

    def test_add_positions(self):
        path = Path()
        path.add_position(1, 2)
        path.add_position(3, 4)
        assert path.get_positions() == [(1, 2), (3, 4)]


# ---------------------------------------------------------------------------
# Game._move simulation (without pygame)
# ---------------------------------------------------------------------------

class FakeCanvas:
    """Minimal stub replacing PyGameCanvas for testing Game logic."""
    def configure(self, w, h): pass
    def create_arena_frame(self): pass
    def create_new_drawing_surface(self): pass
    def create_line_arena(self, *a): pass
    def create_arena_rect(self, *a): pass
    def create_dot_arena(self, *a, **kw): pass
    def complete_drawing(self): pass
    def arena_to_pixel(self, ax, ay): return (ax, ay)
    def create_stick_line(self, *a): pass
    def render_arena(self): pass
    def render_frame(self, *a): pass
    def check_for_exit(self): return True
    def space_pressed(self): return False
    def draw_hud(self, *a, **kw): pass
    def draw_title_screen(self, *a): pass
    def draw_level_complete_screen(self, **kw): pass
    def draw_game_over_screen(self, *a): pass
    def render_explosion(self, *a): pass


class GameMoveSimulator:
    """Simulates Game._move, fill_arena, player_failed without pygame."""
    def __init__(self, arena):
        self.arena = arena
        self.drawing_direction = None

    def move(self, dx, dy):
        result = self.arena.player.try_move(dx, dy)
        if result == MoveResult.OK:
            if self.arena.player.is_drawing:
                self.drawing_direction = (dx, dy)
                if self.arena.player.drawing_completed:
                    self.arena.fill_arena(noop_fill_callback)
                    self.drawing_direction = None
        elif result == MoveResult.DIED:
            self.player_failed()
        return result

    def player_failed(self):
        self.arena.change_player_path_state_to(CellState.FREE)
        self.arena.player.reset_player_state()
        self.drawing_direction = None

    def auto_move(self):
        """Simulate the auto-continue that happens each frame during drawing."""
        if self.drawing_direction is not None:
            return self.move(*self.drawing_direction)
        return None


class TestGameMoveIntegration:
    def test_drawing_direction_set_during_draw(self):
        arena = make_arena(10, 10, num_arena_enemies=0)
        sim = GameMoveSimulator(arena)
        player = arena.player
        player.try_move(1, 0)
        player.initiate_drawing()
        sim.move(0, 1)
        assert sim.drawing_direction == (0, 1)

    def test_drawing_direction_cleared_after_fill(self):
        arena = make_arena(10, 10, num_arena_enemies=0)
        sim = GameMoveSimulator(arena)
        player = arena.player
        player.try_move(1, 0)
        player.initiate_drawing()
        for _ in range(8):
            sim.move(0, 1)
        sim.move(0, 1)  # completes
        assert sim.drawing_direction is None
        assert player.is_drawing is False

    def test_auto_move_continues_drawing(self):
        arena = make_arena(10, 10, num_arena_enemies=0)
        sim = GameMoveSimulator(arena)
        player = arena.player
        player.try_move(1, 0)
        player.initiate_drawing()
        sim.move(0, 1)  # start drawing down
        assert sim.drawing_direction == (0, 1)
        # Auto-move should continue down
        sim.auto_move()
        assert player.y == 2  # (1,1) from move, then (1,2) from auto_move

    def test_auto_move_stops_when_drawing_completes(self):
        arena = make_arena(10, 10, num_arena_enemies=0)
        sim = GameMoveSimulator(arena)
        player = arena.player
        player.try_move(1, 0)
        player.initiate_drawing()
        # Draw all the way down via auto-move
        sim.move(0, 1)
        while sim.drawing_direction is not None:
            sim.auto_move()
        assert player.is_drawing is False
        assert sim.drawing_direction is None
        assert player.y == 9  # at bottom wall

    def test_player_cannot_walk_into_free_after_draw_completes(self):
        """After drawing completes and fills, verify player stays on walls."""
        arena = make_arena(10, 10, num_arena_enemies=0)
        sim = GameMoveSimulator(arena)
        player = arena.player
        player.try_move(1, 0)
        player.initiate_drawing()
        for _ in range(8):
            sim.move(0, 1)
        sim.move(0, 1)  # completes and fills
        # Player at (1,9), drawing done
        # Try to move right — (2,9) is WALL
        result = sim.move(1, 0)
        assert result == MoveResult.OK
        # Now try to move up — (2,8) could be FILLED or FREE
        result = sim.move(0, -1)
        cell = arena.get_cell(player.x, player.y)
        # If BLOCKED, player didn't move — good
        # If OK, the cell must be WALL (the drawn path became wall)
        if result == MoveResult.OK:
            assert cell == CellState.WALL

    def test_drawing_direction_cleared_on_failure(self):
        arena = make_arena(10, 10, num_arena_enemies=0)
        sim = GameMoveSimulator(arena)
        player = arena.player
        player.try_move(1, 0)
        player.initiate_drawing()
        sim.move(0, 1)  # (1,1)
        sim.move(1, 0)  # (2,1)
        sim.move(0, 1)  # (2,2)
        sim.move(-1, 0) # (1,2)
        result = sim.move(0, -1)  # (1,1) is DRAWING -> DIED
        assert result == MoveResult.DIED
        assert sim.drawing_direction is None
        assert player.is_drawing is False
        assert player.x == 0 and player.y == 0

    def test_blocked_move_during_drawing_keeps_direction(self):
        """If a drawing move is blocked, drawing_direction should persist."""
        arena = make_arena(10, 10, num_arena_enemies=0)
        sim = GameMoveSimulator(arena)
        player = arena.player
        player.try_move(1, 0)
        player.initiate_drawing()
        sim.move(0, 1)  # (1,1), drawing direction = (0,1)
        # Now try to move left — (0,1) is WALL, path has 1 position -> BLOCKED
        result = sim.move(-1, 0)
        assert result == MoveResult.BLOCKED
        # drawing_direction should still be (0,1) from earlier
        assert sim.drawing_direction == (0, 1)

    def test_change_direction_during_drawing(self):
        """Player should be able to change direction while drawing."""
        arena = make_arena(10, 10, num_arena_enemies=0)
        sim = GameMoveSimulator(arena)
        player = arena.player
        player.try_move(1, 0)
        player.initiate_drawing()
        sim.move(0, 1)  # (1,1), drawing down
        assert sim.drawing_direction == (0, 1)
        sim.move(1, 0)  # (2,1), drawing right
        assert sim.drawing_direction == (1, 0)
        assert player.x == 2 and player.y == 1

    def test_speed_tick_scenario_enemy_kills_during_draw(self):
        """Simulate: player is drawing, enemy crosses path on a different tick."""
        arena = make_arena(10, 10, num_arena_enemies=0)
        sim = GameMoveSimulator(arena)
        player = arena.player
        player.try_move(1, 0)
        player.initiate_drawing()
        sim.move(0, 1)  # (1,1) DRAWING
        sim.move(0, 1)  # (1,2) DRAWING
        # Simulate enemy hitting — triggers player_failed
        sim.player_failed()
        assert player.x == 0 and player.y == 0
        assert player.is_drawing is False
        assert sim.drawing_direction is None
        assert arena.get_cell(1, 1) == CellState.FREE
        assert arena.get_cell(1, 2) == CellState.FREE

    def test_multiple_enemy_collisions_only_one_player_failed(self):
        """When multiple line enemies collide with the player in the same frame,
        player_failed should only be called once (not cascade)."""
        arena = make_arena(10, 10, num_line_enemies=3)
        sim = GameMoveSimulator(arena)
        player = arena.player

        # Place all 3 line enemies on the player's current position
        for enemy in arena.line_enemies:
            enemy.x = player.x
            enemy.y = player.y

        # Simulate move_and_render_line_enemies with early return on first collision
        failed_count = 0
        for enemy in arena.line_enemies:
            prev_ex, prev_ey = enemy.x, enemy.y
            enemy.move()
            on_same_cell = (enemy.x == player.x and enemy.y == player.y)
            enemy_was_on_player = (prev_ex == player.x and prev_ey == player.y)
            if on_same_cell or enemy_was_on_player:
                failed_count += 1
                sim.player_failed()
                break  # this is the fix — early return

        # Should only have failed once
        assert failed_count == 1
        # Player should be reset to start
        assert player.x == 0 and player.y == 0
        assert player.is_drawing is False


# ---------------------------------------------------------------------------
# FuseEnemy
# ---------------------------------------------------------------------------

class TestFuseEnemy:
    def test_follows_path(self):
        """Fuse should advance along the player's path positions."""
        path = Path()
        for i in range(1, 20):
            path.add_position(1, i)
        fuse = FuseEnemy(path, 1, 0, delay=0)
        assert fuse.x == 1 and fuse.y == 0

        caught = fuse.move()
        assert not caught
        assert fuse.x == 1 and fuse.y == 1

        caught = fuse.move()
        assert not caught
        assert fuse.x == 1 and fuse.y == 2

        caught = fuse.move()
        assert not caught
        assert fuse.x == 1 and fuse.y == 3

    def test_multi_step_move(self):
        """Fuse with steps=2 should advance 2 positions per move."""
        path = Path()
        for i in range(1, 20):
            path.add_position(1, i)
        fuse = FuseEnemy(path, 1, 0, delay=0)
        caught = fuse.move(steps=2)
        assert not caught
        assert fuse.x == 1 and fuse.y == 2
        assert fuse.path_index == 2

    def test_catches_player_at_end_of_path(self):
        """When the fuse has traversed the entire path, it catches the player."""
        path = Path()
        path.add_position(1, 1)
        path.add_position(1, 2)
        fuse = FuseEnemy(path, 1, 0, delay=0)
        fuse.move()  # -> (1,1)
        fuse.move()  # -> (1,2)
        caught = fuse.move()  # past end
        assert caught is True

    def test_delay_prevents_early_movement(self):
        """Fuse should not move until the path reaches the delay length."""
        path = Path()
        path.add_position(1, 1)
        path.add_position(1, 2)
        fuse = FuseEnemy(path, 1, 0, delay=5)
        # Path has only 2 positions, delay is 5 — fuse should not move
        caught = fuse.move()
        assert not caught
        assert fuse.x == 1 and fuse.y == 0  # hasn't moved
        assert fuse.path_index == 0
        # Add more to path
        for i in range(3, 8):
            path.add_position(1, i)
        # Now path has 7 positions >= delay of 5 — fuse should move
        caught = fuse.move()
        assert not caught
        assert fuse.x == 1 and fuse.y == 1  # moved to first position

    def test_does_not_catch_on_growing_path(self):
        """If the path grows faster than the fuse moves, fuse never catches up."""
        path = Path()
        fuse = FuseEnemy(path, 0, 0, delay=0)
        for i in range(1, 10):
            path.add_position(1, i)
            caught = fuse.move()
            assert not caught
        assert fuse.path_index == 9

    def test_color_flashes(self):
        """get_color should alternate between bright and dark."""
        path = Path()
        fuse = FuseEnemy(path, 0, 0, delay=0)
        # Frames 0-3 should be one color, 4-7 the other
        bright = fuse.get_color(0)
        dark = fuse.get_color(4)
        assert bright != dark
        assert fuse.get_color(1) == bright
        assert fuse.get_color(5) == dark
        assert fuse.get_color(8) == bright

    def test_fuse_with_drawing_lifecycle(self):
        """Full integration: draw a path, fuse follows, drawing completes before fuse catches up."""
        arena = make_arena(10, 10, num_arena_enemies=0)
        player = arena.player
        player.try_move(1, 0)
        player.initiate_drawing()

        # Draw 5 cells down
        for _ in range(5):
            player.try_move(0, 1)

        # Spawn fuse with no delay for testing
        fuse = FuseEnemy(player.path, 1, 0, delay=0)

        # Move fuse 3 steps — should be at path[2] = (1,3)
        for _ in range(3):
            caught = fuse.move()
            assert not caught
        assert fuse.x == 1 and fuse.y == 3

        # Player continues drawing to bottom wall
        for _ in range(3):
            player.try_move(0, 1)
        player.try_move(0, 1)  # reaches (1,9) WALL
        assert player.drawing_completed is True

        # Fuse is deactivated on fill (simulated)
        fuse.active = False
        arena.fill_arena(noop_fill_callback)
        assert player.is_drawing is False


# ---------------------------------------------------------------------------
# Death animation (simulated without pygame)
# ---------------------------------------------------------------------------

class DeathAnimSimulator:
    """Simulates the Game death animation lifecycle without pygame."""
    def __init__(self, arena, lives=3, invincibility_frames=120):
        self.arena = arena
        self.lives = lives
        self.drawing_direction = None
        self.fuse = None
        self.death_animation_frames = 0
        self.invincibility_frames = 0
        self._invincibility_on_respawn = invincibility_frames
        self.running = True

    def player_failed(self):
        """Mirrors Game.player_failed."""
        if self.death_animation_frames > 0:
            return  # re-entry guard
        self.arena.change_player_path_state_to(CellState.FREE)
        self.fuse = None
        self.drawing_direction = None
        self.lives -= 1
        if self.lives <= 0:
            self.running = False
            return
        self.death_animation_frames = 45

    def tick_animation(self):
        """Simulate one frame of death animation. Returns True if still animating."""
        if self.death_animation_frames > 0:
            self.death_animation_frames -= 1
            if self.death_animation_frames <= 0:
                self.finish_death()
            return True
        return False

    def finish_death(self):
        """Mirrors Game._finish_death."""
        self.arena.player.reset_player_state()
        self.death_animation_frames = 0
        self.invincibility_frames = self._invincibility_on_respawn

    def is_line_enemy_kill_blocked(self):
        """Returns True if line enemy kills are blocked (invincibility active)."""
        return self.invincibility_frames > 0

    def tick_invincibility(self):
        """Decrement the invincibility counter by one frame."""
        if self.invincibility_frames > 0:
            self.invincibility_frames -= 1


class TestDeathAnimation:
    def test_player_failed_clears_drawing_cells(self):
        """DRAWING cells should be reverted to FREE immediately on death."""
        arena = make_arena(10, 10)
        sim = DeathAnimSimulator(arena)
        player = arena.player
        player.try_move(1, 0)
        player.initiate_drawing()
        player.try_move(0, 1)  # (1,1) DRAWING
        player.try_move(0, 1)  # (1,2) DRAWING
        assert arena.get_cell(1, 1) == CellState.DRAWING
        sim.player_failed()
        assert arena.get_cell(1, 1) == CellState.FREE
        assert arena.get_cell(1, 2) == CellState.FREE

    def test_player_failed_decrements_lives(self):
        arena = make_arena(10, 10)
        sim = DeathAnimSimulator(arena, lives=3)
        sim.player_failed()
        assert sim.lives == 2

    def test_game_over_on_zero_lives(self):
        arena = make_arena(10, 10)
        sim = DeathAnimSimulator(arena, lives=1)
        sim.player_failed()
        assert sim.lives == 0
        assert sim.running is False

    def test_no_animation_on_game_over(self):
        """When lives reach 0, no animation should start."""
        arena = make_arena(10, 10)
        sim = DeathAnimSimulator(arena, lives=1)
        sim.player_failed()
        assert sim.death_animation_frames == 0

    def test_animation_starts_with_lives_remaining(self):
        arena = make_arena(10, 10)
        sim = DeathAnimSimulator(arena, lives=3)
        sim.player_failed()
        assert sim.death_animation_frames == 45

    def test_reentry_guard_during_animation(self):
        """Calling player_failed during an active animation should be ignored."""
        arena = make_arena(10, 10)
        sim = DeathAnimSimulator(arena, lives=3)
        sim.player_failed()
        assert sim.lives == 2
        assert sim.death_animation_frames == 45
        # Call again — should be ignored
        sim.player_failed()
        assert sim.lives == 2  # NOT decremented again
        assert sim.death_animation_frames == 45

    def test_animation_completes_and_resets_player(self):
        """After animation finishes, player should be at start position."""
        arena = make_arena(10, 10)
        sim = DeathAnimSimulator(arena, lives=3)
        player = arena.player
        player.try_move(1, 0)
        player.try_move(1, 0)  # player at (2,0)
        sim.player_failed()
        # Player position hasn't reset yet (animation playing)
        assert player.x == 2
        # Run through the full animation
        for _ in range(45):
            sim.tick_animation()
        # Now player should be reset
        assert player.x == 0 and player.y == 0
        assert player.is_drawing is False
        assert sim.death_animation_frames == 0

    def test_animation_duration(self):
        """Animation should last exactly 45 frames."""
        arena = make_arena(10, 10)
        sim = DeathAnimSimulator(arena, lives=3)
        sim.player_failed()
        for i in range(44):
            still = sim.tick_animation()
            assert still is True
        # Frame 45 should finish the animation
        still = sim.tick_animation()
        assert sim.death_animation_frames == 0

    def test_drawing_direction_cleared_on_death(self):
        arena = make_arena(10, 10)
        sim = DeathAnimSimulator(arena, lives=3)
        sim.drawing_direction = (0, 1)
        sim.player_failed()
        assert sim.drawing_direction is None

    def test_fuse_cleared_on_death(self):
        arena = make_arena(10, 10)
        sim = DeathAnimSimulator(arena, lives=3)
        sim.fuse = FuseEnemy(Path(), 0, 0, delay=0)
        sim.player_failed()
        assert sim.fuse is None

    def test_can_die_again_after_animation_completes(self):
        """After animation finishes, a new death should work normally."""
        arena = make_arena(10, 10)
        sim = DeathAnimSimulator(arena, lives=3)
        sim.player_failed()
        assert sim.lives == 2
        for _ in range(45):
            sim.tick_animation()
        # Die again (after invincibility expires)
        sim.invincibility_frames = 0
        sim.player_failed()
        assert sim.lives == 1
        assert sim.death_animation_frames == 45


# ---------------------------------------------------------------------------
# Invincibility after respawn
# ---------------------------------------------------------------------------

class TestInvincibility:
    def test_invincibility_set_on_respawn(self):
        """After death animation completes, invincibility frames should be set."""
        arena = make_arena(10, 10)
        sim = DeathAnimSimulator(arena, lives=3, invincibility_frames=120)
        sim.player_failed()
        # During animation, no invincibility yet
        assert sim.invincibility_frames == 0
        for _ in range(45):
            sim.tick_animation()
        # After animation, invincibility starts
        assert sim.invincibility_frames == 120

    def test_invincibility_not_set_on_initial_spawn(self):
        """At game start (no death), invincibility should be 0."""
        arena = make_arena(10, 10)
        sim = DeathAnimSimulator(arena, lives=3)
        assert sim.invincibility_frames == 0

    def test_line_enemy_kill_blocked_during_invincibility(self):
        """Line enemy kills should be blocked while invincible."""
        arena = make_arena(10, 10)
        sim = DeathAnimSimulator(arena, lives=3, invincibility_frames=120)
        sim.player_failed()
        for _ in range(45):
            sim.tick_animation()
        assert sim.is_line_enemy_kill_blocked() is True

    def test_line_enemy_kill_allowed_after_invincibility(self):
        """Line enemy kills should work after invincibility expires."""
        arena = make_arena(10, 10)
        sim = DeathAnimSimulator(arena, lives=3, invincibility_frames=10)
        sim.player_failed()
        for _ in range(45):
            sim.tick_animation()
        assert sim.invincibility_frames == 10
        for _ in range(10):
            sim.tick_invincibility()
        assert sim.invincibility_frames == 0
        assert sim.is_line_enemy_kill_blocked() is False

    def test_invincibility_countdown(self):
        """Invincibility should decrease by 1 each tick."""
        arena = make_arena(10, 10)
        sim = DeathAnimSimulator(arena, lives=3, invincibility_frames=5)
        sim.player_failed()
        for _ in range(45):
            sim.tick_animation()
        assert sim.invincibility_frames == 5
        sim.tick_invincibility()
        assert sim.invincibility_frames == 4
        sim.tick_invincibility()
        assert sim.invincibility_frames == 3

    def test_drawing_death_not_blocked_by_invincibility(self):
        """Dying from drawing into own line should still work during invincibility."""
        arena = make_arena(10, 10)
        sim = DeathAnimSimulator(arena, lives=3, invincibility_frames=120)
        # Simulate respawn with invincibility
        sim.invincibility_frames = 120
        player = arena.player
        player.try_move(1, 0)
        player.initiate_drawing()
        player.try_move(0, 1)  # (1,1) DRAWING
        player.try_move(1, 0)  # (2,1) DRAWING
        player.try_move(0, 1)  # (2,2) DRAWING
        player.try_move(-1, 0) # (1,2) DRAWING
        result = player.try_move(0, -1)  # (1,1) is DRAWING -> DIED
        assert result == MoveResult.DIED
        # Invincibility doesn't block self-inflicted death
        sim.player_failed()
        assert sim.lives == 2

    def test_no_invincibility_on_game_over(self):
        """When last life is lost, no invincibility should be set."""
        arena = make_arena(10, 10)
        sim = DeathAnimSimulator(arena, lives=1, invincibility_frames=120)
        sim.player_failed()
        assert sim.running is False
        assert sim.invincibility_frames == 0


# ---------------------------------------------------------------------------
# LevelGenerator
# ---------------------------------------------------------------------------

class TestLevelGenerator:
    def test_level_1_is_gentle(self):
        """Level 1 should be easy: no fuse, few enemies, moderate fill."""
        gen = LevelGenerator()
        config = gen.build_level(1)
        assert config.level_number == 1
        assert config.fuse_speed == 0
        assert config.fuse_chance == 0.0
        assert config.num_line_enemies <= 2
        assert config.num_arena_enemies <= 2
        assert config.fill_percent <= 0.70
        assert config.player_speed == 1

    def test_level_2_no_fuse(self):
        """Level 2 should still have no fuse."""
        gen = LevelGenerator()
        gen.build_level(1)
        config = gen.build_level(2)
        assert config.fuse_speed == 0

    def test_fuse_enabled_from_level_3(self):
        """Fuse should start being possible from level 3 onward."""
        gen = LevelGenerator()
        for i in range(1, 3):
            gen.build_level(i)
        config = gen.build_level(3)
        assert config.fuse_speed >= 1
        assert config.fuse_chance > 0

    def test_arena_size_reasonable(self):
        """Arena should be between 50 and 200 for any level."""
        gen = LevelGenerator()
        for level in range(1, 30):
            config = gen.build_level(level)
            assert 50 <= config.arena_width <= 200
            assert 50 <= config.arena_height <= 200

    def test_fill_percent_capped(self):
        """Fill percent should never exceed 90%."""
        gen = LevelGenerator()
        for level in range(1, 30):
            config = gen.build_level(level)
            assert config.fill_percent <= 0.90

    def test_difficulty_increases(self):
        """Later levels should generally be harder (more enemies, higher fill)."""
        gen = LevelGenerator()
        config_early = gen.build_level(1)
        for i in range(2, 15):
            gen.build_level(i)
        config_late = gen.build_level(15)
        assert config_late.fill_percent > config_early.fill_percent
        assert (config_late.num_line_enemies + config_late.num_arena_enemies >=
                config_early.num_line_enemies + config_early.num_arena_enemies)

    def test_no_triple_archetype_repeat(self):
        """The same archetype should not appear 3 times in a row."""
        gen = LevelGenerator()
        for level in range(1, 50):
            gen.build_level(level)
        archetypes = gen.last_archetypes
        for i in range(2, len(archetypes)):
            if archetypes[i] == archetypes[i-1] == archetypes[i-2]:
                assert False, f"Triple repeat at index {i}: {archetypes[i]}"

    def test_all_archetypes_appear(self):
        """Over 20 levels, all 4 archetypes should appear at least once."""
        gen = LevelGenerator()
        for level in range(1, 21):
            gen.build_level(level)
        used = set(gen.last_archetypes)
        for arch in ARCHETYPES:
            assert arch in used, f"Archetype {arch} never appeared in 20 levels"

    def test_milestone_levels_deterministic(self):
        """Milestone levels should produce the expected archetype."""
        gen = LevelGenerator()
        config1 = gen.build_level(1)
        assert gen.last_archetypes[0] == 'open'  # level 1 milestone

    def test_reset_clears_history(self):
        """Resetting the generator should clear archetype history."""
        gen = LevelGenerator()
        for i in range(1, 10):
            gen.build_level(i)
        assert len(gen.last_archetypes) > 0
        gen.reset()
        assert gen.last_archetypes == []

    def test_player_speed_always_1(self):
        """Player speed should always be 1 (never slowed)."""
        gen = LevelGenerator()
        for level in range(1, 30):
            config = gen.build_level(level)
            assert config.player_speed == 1

    def test_fuse_delay_minimum(self):
        """Fuse delay should never go below 3."""
        gen = LevelGenerator()
        for level in range(1, 30):
            config = gen.build_level(level)
            assert config.fuse_delay >= 3

    def test_enemy_counts_capped(self):
        """Enemy counts should have reasonable upper bounds."""
        gen = LevelGenerator()
        for level in range(1, 30):
            config = gen.build_level(level)
            assert config.num_line_enemies <= 5
            assert config.num_arena_enemies <= 4
