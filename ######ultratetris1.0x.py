#!/usr/bin/env python3
# Ultra Tettris 1.0 - Build 9.22.25
# Hybrid Tetris + Puyo engine with SM64 HUD + Procedural OST
# Pure Python/Pygame, no PNGs, no MP3s

import pygame, sys, random, math, os

# ==============================
# CONFIG
# ==============================
GRID_WIDTH = 10
GRID_HEIGHT = 20
CELL_SIZE = 30
SCREEN_WIDTH = GRID_WIDTH * CELL_SIZE + 200
SCREEN_HEIGHT = GRID_HEIGHT * CELL_SIZE + 100
FPS = 60
SAMPLE_RATE = 44100

# ==============================
# COLORS
# ==============================
BLACK   = (0, 0, 0)
WHITE   = (255, 255, 255)
YELLOW  = (255, 255, 0)
CYAN    = (0, 255, 255)
MAGENTA = (255, 0, 255)
ORANGE  = (255, 165, 0)
RED     = (255, 0, 0)
GREEN   = (0, 255, 0)
BLUE    = (0, 0, 255)
PUYO_COLORS = [RED, BLUE, GREEN, YELLOW]

# ==============================
# TETROMINOES
# ==============================
TETROMINOES = {
    'I': [[1, 1, 1, 1]],
    'O': [[1, 1], [1, 1]],
    'T': [[0, 1, 0], [1, 1, 1]],
    'S': [[0, 1, 1], [1, 1, 0]],
    'Z': [[1, 1, 0], [0, 1, 1]],
    'J': [[1, 0, 0], [1, 1, 1]],
    'L': [[0, 0, 1], [1, 1, 1]]
}

# ==============================
# PIECE
# ==============================
class Piece:
    def __init__(self, x, y, shape, is_tetromino=True):
        self.x = x
        self.y = y
        self.is_tetromino = is_tetromino
        if is_tetromino:
            self.shape = shape
            self.color = random.choice([CYAN, YELLOW, MAGENTA, ORANGE])
        else:
            self.shape = [[1, 1]]
            self.color = random.choice(PUYO_COLORS)

    def rotate(self):
        self.shape = [list(r) for r in zip(*self.shape[::-1])]

# ==============================
# GRID FUNCTIONS
# ==============================
def create_grid(locked_positions={}):
    grid = [[BLACK for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
    for (x, y), color in locked_positions.items():
        if y >= 0:
            grid[y][x] = color
    return grid

def convert_shape_format(piece):
    positions = []
    for i, row in enumerate(piece.shape):
        for j, val in enumerate(row):
            if val == 1:
                positions.append((piece.x + j, piece.y + i))
    return positions

def valid_space(piece, grid):
    accepted = [[(x, y) for x in range(GRID_WIDTH) if grid[y][x] == BLACK] for y in range(GRID_HEIGHT)]
    accepted = [x for row in accepted for x in row]
    for pos in convert_shape_format(piece):
        if pos not in accepted and pos[1] >= 0:
            return False
    return True

def draw_grid(surface, grid):
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            pygame.draw.rect(surface, grid[y][x],
                             (x*CELL_SIZE, y*CELL_SIZE, CELL_SIZE, CELL_SIZE))
            pygame.draw.rect(surface, WHITE,
                             (x*CELL_SIZE, y*CELL_SIZE, CELL_SIZE, CELL_SIZE), 1)

# ==============================
# HUD FUNCTIONS
# ==============================
pygame.font.init()
HUD_FONT = pygame.font.SysFont("Comic Sans MS", 32, bold=True)
DIGITS = {str(i): HUD_FONT.render(str(i), True, YELLOW) for i in range(10)}

def draw_number(surface, number, x, y):
    for i, digit in enumerate(str(number)):
        if digit in DIGITS:
            surface.blit(DIGITS[digit], (x + i * 28, y))

def draw_hud(surface, score, lines, level):
    # puyo icon
    pygame.draw.circle(surface, random.choice(PUYO_COLORS), (40, 40), 15)
    draw_number(surface, f"{score:06}", 70, 25)
    # level + lines
    lbl = pygame.font.SysFont("Comic Sans MS", 24, bold=True)
    surface.blit(lbl.render("LV", True, WHITE), (SCREEN_WIDTH-160, 20))
    draw_number(surface, level, SCREEN_WIDTH-120, 20)
    surface.blit(lbl.render("LINES", True, WHITE), (SCREEN_WIDTH-180, 60))
    draw_number(surface, lines, SCREEN_WIDTH-80, 60)
    # build
    surface.blit(lbl.render("Ultra Tettris 1.0", True, MAGENTA),
                 (SCREEN_WIDTH-260, SCREEN_HEIGHT-60))
    surface.blit(lbl.render("Build 9.22.25", True, CYAN),
                 (SCREEN_WIDTH-260, SCREEN_HEIGHT-30))

# ==============================
# MUSIC ENGINE
# ==============================
pygame.mixer.pre_init(SAMPLE_RATE, -16, 1, 512)
pygame.mixer.init()

def generate_tone(freq, duration, volume=0.3):
    n_samples = int(round(duration * SAMPLE_RATE))
    buf = bytearray()
    for s in range(n_samples):
        t = s / SAMPLE_RATE
        val = volume * (1 if math.sin(2 * math.pi * freq * t) > 0 else -1)
        sample = int(val * 32767.0)
        buf += sample.to_bytes(2, byteorder="little", signed=True)
    return pygame.mixer.Sound(buffer=bytes(buf))

def random_theme():
    base = random.choice([220, 261, 330])
    notes = [base, base*4/3, base*3/2, base*2]
    melody = [random.choice(notes) for _ in range(8)]
    for f in melody:
        snd = generate_tone(f, 0.18)
        snd.play()
        pygame.time.delay(180)

# ==============================
# GAME LOOP
# ==============================
def get_shape():
    if random.choice([True, False]):
        return Piece(3, 0, random.choice(list(TETROMINOES.values())), True)
    else:
        return Piece(3, 0, None, False)

def draw_window(surface, grid, score, lines, level):
    surface.fill(BLACK)
    draw_grid(surface, grid)
    draw_hud(surface, score, lines, level)
    pygame.display.update()

def main():
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Ultra Tettris 1.0 - Puyo Puyo Tetris Hybrid")
    clock = pygame.time.Clock()
    locked_positions = {}
    current_piece = get_shape()
    fall_time = 0
    fall_speed = 500
    score, lines, level = 0, 0, 1
    random_theme()

    run = True
    while run:
        dt = clock.tick(FPS)
        fall_time += dt
        grid = create_grid(locked_positions)

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                run = False
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_LEFT:
                    current_piece.x -= 1
                    if not valid_space(current_piece, grid):
                        current_piece.x += 1
                elif e.key == pygame.K_RIGHT:
                    current_piece.x += 1
                    if not valid_space(current_piece, grid):
                        current_piece.x -= 1
                elif e.key == pygame.K_DOWN:
                    current_piece.y += 1
                    if not valid_space(current_piece, grid):
                        current_piece.y -= 1
                elif e.key == pygame.K_UP:
                    current_piece.rotate()
                    if not valid_space(current_piece, grid):
                        for _ in range(3): current_piece.rotate()

        if fall_time > fall_speed:
            current_piece.y += 1
            if not valid_space(current_piece, grid):
                current_piece.y -= 1
                for pos in convert_shape_format(current_piece):
                    locked_positions[pos] = current_piece.color
                current_piece = get_shape()
                score += 100
                lines += 1
                if lines % 10 == 0:
                    level += 1
                    fall_speed = max(100, fall_speed - 50)
                if not pygame.mixer.get_busy():
                    random_theme()
            fall_time = 0

        for pos in convert_shape_format(current_piece):
            x, y = pos
            if y >= 0:
                grid[y][x] = current_piece.color

        draw_window(screen, grid, score, lines, level)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
