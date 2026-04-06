# Python Games Collection

A collection of Python-based games where the goal is mostly to explore and learn classic game mechanics.

## Games

### Pystix
A pygame-based game inspired by the classic [Qix](https://en.wikipedia.org/wiki/Qix) arcade game where players draw to fill areas of an arena while avoiding enemies. Features multiple levels with configurable difficulty and the classic Qix enemies.

**Features:**
- Level-based progression system
- Multiple enemy types (Stix, Qix, Fuse)
- Configurable game parameters

### Tktris
A classic [Tetris-style](https://en.wikipedia.org/wiki/Tetris) game built with tkinter. Drop and arrange tetromino pieces to clear lines.

**Features:**
- Classic Tetris gameplay
- Level-based difficulty progression
- Speed increases with each level

## Requirements

Install dependencies using:
```bash
pip install -r requirements.txt
```

**Dependencies:**
- `pygame` - Required for Pystix
- `bresenham` - Line drawing algorithm used in Pystix
- `pytest` - For running tests

## Running the Games

### Pystix
```bash
python pystix.py
```

### Tktris
```bash
python tktris.py
```

## Testing

Run the test suite:
```bash
pytest test_pystix.py
```

The tests cover the core game logic for Pystix without requiring pygame.

## Project Structure

- `pystix.py` - Main Pystix game implementation
- `tktris.py` - Main Tktris game implementation
- `test_pystix.py` - Unit tests for Pystix game logic
- `requirements.txt` - Python package dependencies
