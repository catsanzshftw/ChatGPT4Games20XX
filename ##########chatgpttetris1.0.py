import sys, random, threading, time
import numpy as np

# ---------- Optional audio backend ----------
AUDIO_ENABLED = True
try:
    import sounddevice as sd  # PortAudio backend
except Exception:
    sd = None
    AUDIO_ENABLED = False

import pygame

# ------------------------------
# OST ENGINE (Full Tetris Theme)
# ------------------------------
SR     = 44100
BPM    = 120
BEAT   = 60.0 / BPM

# Korobeiniki (Tetris A-Type) – one pass of the main form (approx. phrasing)
FULL_TETRIS_THEME = [
    # Phrase 1
    ("E5", 0.5), ("B4", 0.25), ("C5", 0.25), ("D5", 0.5), ("C5", 0.25), ("B4", 0.25),
    ("A4", 1.0), ("A4", 0.25), ("C5", 0.25), ("E5", 0.5), ("D5", 0.25), ("C5", 0.25),
    ("B4", 1.5), ("C5", 0.25), ("D5", 0.5), ("E5", 0.5),
    ("C5", 0.5), ("A4", 0.5), ("A4", 1.0),

    # Phrase 2 (slight variant)
    ("D5", 0.5), ("F5", 0.25), ("A5", 0.5), ("G5", 0.25), ("F5", 0.25),
    ("E5", 0.5), ("C5", 0.25), ("E5", 0.5), ("D5", 0.25), ("C5", 0.25),
    ("B4", 1.5), ("C5", 0.25), ("D5", 0.5), ("E5", 0.5),
    ("C5", 0.5), ("A4", 0.5), ("A4", 1.0),

    # Phrase 3
    ("E5", 0.5), ("C5", 0.5), ("D5", 0.5), ("B4", 0.5),
    ("C5", 0.5), ("A4", 0.5), ("A4", 0.25), ("B4", 0.25),
    ("G4", 1.0), ("G4", 0.25), ("B4", 0.25), ("E5", 0.5), ("D5", 0.25), ("C5", 0.25),
    ("B4", 1.5), ("C5", 0.25), ("D5", 0.5), ("E5", 0.5),
    ("C5", 0.5), ("A4", 0.5), ("A4", 1.0),

    # Final phrase
    ("E5", 0.5), ("C5", 0.5), ("D5", 0.5), ("B4", 0.5),
    ("C5", 0.5), ("A4", 0.5), ("A4", 0.25), ("B4", 0.25),
    ("E5", 0.5), ("C5", 0.5), ("D5", 0.5), ("B4", 0.5),
    ("C5", 1.0), ("E5", 1.0), ("A4", 2.0)
]

BASS_PATTERN = ["E3", "A3", "D3", "G3", "C4", "F3", "B3", "E3"]  # will be looped
BASS_NOTE_BEATS = 2.0

# --- Note utilities (universal across octaves) ---
_SEMI = {
    "C": -9, "C#": -8, "Db": -8, "D": -7, "D#": -6, "Eb": -6,
    "E": -5, "F": -4, "F#": -3, "Gb": -3, "G": -2, "G#": -1, "Ab": -1,
    "A": 0, "A#": 1, "Bb": 1, "B": 2
}
def note_to_freq(note: str) -> float:
    """Convert note like 'C#4' or 'Bb3' to frequency (Hz), A4 = 440."""
    if len(note) < 2:
        raise ValueError(f"Bad note: {note}")
    if note[1] in ("#", "b"):
        name, octv = note[:2], int(note[2:])
    else:
        name, octv = note[:1], int(note[1:])
    offset = _SEMI[name] + 12 * (octv - 4)
    return 440.0 * (2.0 ** (offset / 12.0))

def square_wave(freq: float, dur_s: float, vol: float = 0.30) -> np.ndarray:
    """Anti-click square wave: short attack/release envelope."""
    n = max(1, int(SR * dur_s))
    t = np.linspace(0.0, dur_s, n, endpoint=False)
    y = np.sign(np.sin(2 * np.pi * freq * t)).astype(np.float32)
    # tiny linear fades
    a = max(1, int(0.004 * SR))
    r = max(1, int(0.006 * SR))
    env = np.ones(n, dtype=np.float32)
    env[:a] = np.linspace(0.0, 1.0, a, dtype=np.float32)
    env[-r:] = np.linspace(1.0, 0.0, r, dtype=np.float32)
    return (vol * y * env).astype(np.float32)

def silence(dur_s: float) -> np.ndarray:
    return np.zeros(max(1, int(SR * dur_s)), dtype=np.float32)

def synth_note(note: str, beats: float, vol: float = 0.30) -> np.ndarray:
    """Square wave, optional occasional power chord (5th)."""
    dur = beats * BEAT
    f = note_to_freq(note)
    if random.random() < 0.20:  # simple power chord: root + fifth
        w1 = square_wave(f, dur, vol * 0.65)
        w2 = square_wave(f * (2 ** (7 / 12)), dur, vol * 0.50)
        w = w1 + w2
        # soft normalize this chord
        peak = max(1e-6, float(np.max(np.abs(w))))
        return (0.9 * w / peak).astype(np.float32)
    return square_wave(f, dur, vol)

def build_theme_once() -> np.ndarray:
    """Render one full pass of the theme with bass, return mixed buffer."""
    # Melody
    mel_parts = []
    for n, b in FULL_TETRIS_THEME:
        mel_parts.append(synth_note(n, b, vol=0.28))
    melody = np.concatenate(mel_parts)

    # Bassline, fill to melody duration
    target = len(melody)
    bass_parts, wrote = [], 0
    i = 0
    while wrote < target:
        note = BASS_PATTERN[i % len(BASS_PATTERN)]
        seg = square_wave(note_to_freq(note), BASS_NOTE_BEATS * BEAT, vol=0.14)
        bass_parts.append(seg)
        wrote += len(seg)
        i += 1
    bass = np.concatenate(bass_parts)[:target]  # exact length match

    mix = melody + bass
    peak = float(np.max(np.abs(mix))) if mix.size else 1.0
    if peak < 1e-6:
        return mix.astype(np.float32)
    return (0.85 * mix / peak).astype(np.float32)

def play_theme():
    """Continuously loop the full theme in a background thread."""
    if not AUDIO_ENABLED:
        return
    while True:
        buf = build_theme_once()
        sd.play(buf, SR, blocking=True)

# ------------------------------
# TETRIS ENGINE
# ------------------------------
COLS, ROWS = 10, 20
BLOCK = 30
MARGIN = 2
BOARD_W, BOARD_H = COLS * BLOCK, ROWS * BLOCK
SIDE_W = 220
WIN_W, WIN_H = BOARD_W + SIDE_W, BOARD_H

BG = (16, 18, 22)
GRID_LINE = (32, 36, 40)
PANEL_BG = (22, 24, 28)
TEXT = (225, 225, 230)

PIECE_COLORS = {
    'I': (0, 240, 240), 'J': (0, 80, 240), 'L': (240, 160, 0),
    'O': (240, 240, 0), 'S': (0, 240, 0), 'T': (160, 0, 240), 'Z': (240, 0, 0)
}
SHAPES = {
    'I': ["....", "1111", "....", "...."],
    'J': ["1...", "111.", "....", "...."],
    'L': ["..1.", "111.", "....", "...."],
    'O': [".11.", ".11.", "....", "...."],
    'S': [".11.", "11..", "....", "...."],
    'T': [".1..", "111.", "....", "...."],
    'Z': ["11..", ".11.", "....", "...."],
}

def rotate_cw(shape):
    grid = [list(r) for r in shape]
    return [''.join(row) for row in zip(*grid[::-1])]

def rotate_ccw(shape):
    grid = [list(r) for r in shape]
    return [''.join(row) for row in zip(*grid)][::-1]

def cells(shape, x, y):
    for r in range(4):
        for c in range(4):
            if shape[r][c] == "1":
                yield (x + c, y + r)

def can_place(grid, shape, x, y):
    for cx, cy in cells(shape, x, y):
        if cx < 0 or cx >= COLS or cy >= ROWS:
            return False
        if cy >= 0 and grid[cy][cx] is not None:
            return False
    return True

from collections import deque

def new_bag():
    bag = list(SHAPES.keys())
    random.shuffle(bag)
    return deque(bag)

def clear_lines(grid):
    new_rows = [r for r in grid if any(cell is None for cell in r)]
    cleared = ROWS - len(new_rows)
    for _ in range(cleared):
        new_rows.insert(0, [None for _ in range(COLS)])
    return new_rows, cleared

def drop_interval(level):
    return max(0.05, 0.8 - (level - 1) * 0.06)

def draw_text(surf, text, size, x, y, color=TEXT, align="topleft"):
    # Try a monospace, fall back gracefully
    try:
        font = pygame.font.SysFont(["consolas", "dejavusansmono", "monospace"], size)
    except Exception:
        font = pygame.font.Font(None, size)
    rend = font.render(text, True, color)
    rect = rend.get_rect()
    setattr(rect, align, (x, y))
    surf.blit(rend, rect)

def draw_cell(surf, x, y, color, ghost=False):
    px, py = x * BLOCK, y * BLOCK
    if ghost:
        ghost_rect = pygame.Rect(px, py, BLOCK, BLOCK)
        s = pygame.Surface((BLOCK, BLOCK), pygame.SRCALPHA)
        s.fill((*color, 60))
        surf.blit(s, ghost_rect)
        pygame.draw.rect(surf, (*color, 180), ghost_rect, 1)
    else:
        rect = pygame.Rect(px + MARGIN, py + MARGIN, BLOCK - 2 * MARGIN, BLOCK - 2 * MARGIN)
        pygame.draw.rect(surf, color, rect, border_radius=4)

def draw_board(surface, grid):
    surface.fill(BG)
    for x in range(COLS + 1):
        pygame.draw.line(surface, GRID_LINE, (x * BLOCK, 0), (x * BLOCK, BOARD_H))
    for y in range(ROWS + 1):
        pygame.draw.line(surface, GRID_LINE, (0, y * BLOCK), (BOARD_W, y * BLOCK))
    for r in range(ROWS):
        for c in range(COLS):
            clr = grid[r][c]
            if clr is not None:
                draw_cell(surface, c, r, clr)

def piece_spawn_x():
    return COLS // 2 - 2

class Piece:
    def __init__(self, name):
        self.name = name
        self.shape = SHAPES[name][:]
        self.x = piece_spawn_x()
        self.y = -2
        self.color = PIECE_COLORS[name]
        self.hold_locked = False

    def move(self, grid, dx, dy):
        if can_place(grid, self.shape, self.x + dx, self.y + dy):
            self.x += dx
            self.y += dy
            return True
        return False

    def rotate(self, grid, cw=True):
        rotated = rotate_cw(self.shape) if cw else rotate_ccw(self.shape)
        for ox, oy in [(0, 0), (1, 0), (-1, 0), (0, -1)]:
            if can_place(grid, rotated, self.x + ox, self.y + oy):
                self.shape = rotated
                self.x += ox
                self.y += oy
                return True
        return False

    def hard_drop_distance(self, grid):
        dy = 0
        while can_place(grid, self.shape, self.x, self.y + dy + 1):
            dy += 1
        return dy

    def ghost_y(self, grid):
        return self.y + self.hard_drop_distance(grid)

def draw_piece(surface, piece, ghost=False):
    for cx, cy in cells(piece.shape, piece.x, piece.y):
        if cy >= 0:
            draw_cell(surface, cx, cy, piece.color, ghost)

def main():
    pygame.init()
    pygame.display.set_caption("Tetris — with Full OST")
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    clock = pygame.time.Clock()
    pygame.key.set_repeat(150, 50)

    board_surface = pygame.Surface((BOARD_W, BOARD_H))
    panel_surface = pygame.Surface((SIDE_W, BOARD_H))

    grid = [[None for _ in range(COLS)] for _ in range(ROWS)]
    bag = new_bag()
    next_queue = deque()
    while len(next_queue) < 5:
        if not bag:
            bag = new_bag()
        next_queue.append(bag.popleft())
    current = Piece(next_queue.popleft())
    hold = None
    can_hold = True

    score = 0
    total_lines = 0
    level = 1
    fall_timer = 0.0
    paused = False
    game_over = False

    def spawn_new_piece():
        nonlocal current, can_hold, bag, next_queue, game_over
        if not bag:
            bag = new_bag()
        next_queue.append(bag.popleft())
        current = Piece(next_queue.popleft())
        can_hold = True
        return can_place(grid, current.shape, current.x, current.y)

    # Start full Tetris theme in background (if audio available)
    if AUDIO_ENABLED:
        threading.Thread(target=play_theme, daemon=True).start()

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if paused and event.key != pygame.K_p:
                    continue
                if event.key == pygame.K_p:
                    paused = not paused
                elif event.key in (pygame.K_UP, pygame.K_x):
                    current.rotate(grid, True)
                elif event.key == pygame.K_z:
                    current.rotate(grid, False)
                elif event.key == pygame.K_LEFT:
                    current.move(grid, -1, 0)
                elif event.key == pygame.K_RIGHT:
                    current.move(grid, 1, 0)
                elif event.key == pygame.K_DOWN:
                    if current.move(grid, 0, 1):
                        score += 1
                elif event.key == pygame.K_SPACE:
                    dy = current.hard_drop_distance(grid)
                    current.y += dy
                    score += 2 * dy
                    for cx, cy in cells(current.shape, current.x, current.y):
                        if cy >= 0:
                            grid[cy][cx] = current.color
                    grid, cleared = clear_lines(grid)
                    if cleared:
                        score += {1: 100, 2: 300, 3: 500, 4: 800}[cleared] * level
                        total_lines += cleared
                        level = 1 + total_lines // 10
                    if not spawn_new_piece():
                        game_over = True

        if not paused and not game_over:
            fall_timer += dt
            interval = drop_interval(level)
            if fall_timer >= interval:
                fall_timer -= interval
                if not current.move(grid, 0, 1):
                    for cx, cy in cells(current.shape, current.x, current.y):
                        if cy >= 0:
                            grid[cy][cx] = current.color
                    grid, cleared = clear_lines(grid)
                    if cleared:
                        score += {1: 100, 2: 300, 3: 500, 4: 800}[cleared] * level
                        total_lines += cleared
                        level = 1 + total_lines // 10
                    if not spawn_new_piece():
                        game_over = True

        # --- draw ---
        draw_board(board_surface, grid)
        if not game_over:
            gy = current.ghost_y(grid)
            ghost_piece = Piece(current.name)
            ghost_piece.shape = current.shape[:]
            ghost_piece.x = current.x
            ghost_piece.y = gy
            draw_piece(board_surface, ghost_piece, True)
            draw_piece(board_surface, current)

        screen.blit(board_surface, (0, 0))
        panel_surface.fill(PANEL_BG)
        draw_text(panel_surface, "Score", 22, 12, 12);  draw_text(panel_surface, str(score), 28, 12, 36)
        draw_text(panel_surface, "Level", 22, 12, 78);  draw_text(panel_surface, str(level), 28, 12, 102)
        draw_text(panel_surface, "Lines", 22, 12, 144); draw_text(panel_surface, str(total_lines), 28, 12, 168)
        if AUDIO_ENABLED:
            draw_text(panel_surface, "Full Tetris", 22, 12, 210)
            draw_text(panel_surface, "Theme Playing", 18, 12, 240)
        else:
            draw_text(panel_surface, "Audio", 22, 12, 210)
            draw_text(panel_surface, "Disabled (no backend)", 18, 12, 240)
        screen.blit(panel_surface, (BOARD_W, 0))
        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
