# program.py
# -----------------------------------------------------------------------------
# Clean-room, SMB-inspired platformer prototype (Python + Pygame)
# Window: 600x400, fixed-step update ≈ Famicom 60.0988 FPS
#
# IMPORTANT COPYRIGHT NOTE:
# This file implements an original, from-scratch platformer engine with
# placeholder art and *procedurally generated* demo levels. It does NOT ship
# Nintendo ROMs, assets, or 1:1 level data from Super Mario Bros. If you need
# the original game, obtain a legal copy; do not use this program to load or
# distribute copyrighted content.
#
# What you get:
# - Fixed-timestep update loop (≈ 60.0988 FPS) for consistent physics
# - 600x400 window (tile size 20px → visible grid 30x20 tiles)
# - Side-scrolling camera, tile collisions, gravity, jumping
# - Simple enemies (Goombas), coins, pipes, bricks, question blocks
# - Flagpole finish to advance to the next *procedurally generated* level
# - No external assets: everything is drawn with rectangles/lines
#
# Controls:
#   Left/Right or A/D  : Move
#   Z or Space         : Jump (variable height if held briefly)
#   R                  : Reset level
#   F1                 : Toggle FPS display
#   Esc                : Quit
#
# Dependencies:
#   pip install pygame
#
# Run:
#   python program.py
# -----------------------------------------------------------------------------

import math
import random
import sys
from dataclasses import dataclass
from typing import List, Tuple

import pygame


# --- Config ------------------------------------------------------------------
WIDTH, HEIGHT = 600, 400
TILE = 20                      # 600x400 → 30x20 tiles
VIEW_TILES_X = WIDTH // TILE
VIEW_TILES_Y = HEIGHT // TILE

FPS_TARGET = 60.0988           # Famicom-ish refresh
FIXED_DT = 1.0 / FPS_TARGET    # fixed-step seconds per tick

# Physics (pixels per second^2, etc.)
GRAVITY = 2200.0
MOVE_ACCEL = 2400.0
AIR_ACCEL = 1800.0
GROUND_FRICTION = 2200.0
MAX_WALK_SPEED = 180.0
MAX_RUN_SPEED = 220.0
JUMP_SPEED = 520.0
JUMP_HOLD_TIME = 0.09          # seconds of extra hold to extend jump a bit
JUMP_HOLD_FORCE = 2300.0
STOMP_BOUNCE = 360.0

# Colors
SKY = (148, 200, 255)
GROUND = (140, 110, 60)
BRICK = (170, 50, 50)
BLOCK_Q = (230, 200, 60)
BLOCK_SOLID = (150, 150, 150)
PIPE = (70, 160, 90)
FLAG = (40, 170, 60)
COIN = (255, 215, 0)
ENEMY = (170, 90, 40)
PLAYER_OUTLINE = (10, 10, 10)
PLAYER_FILL = (240, 60, 60)


# --- Utility -----------------------------------------------------------------
def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def sign(x):
    return -1 if x < 0 else (1 if x > 0 else 0)


# --- Level -------------------------------------------------------------------
class Level:
    """
    Tile codes:
      ' ' = empty
      'X' = ground block (solid)
      'B' = brick block (solid)
      '?' = question block (solid from sides/below, can be hit from below to spawn coin)
      'H' = hard block (solid)
      'L' = pipe (solid)
      '|' = flag pole (non-solid; contact ends level)
      'C' = coin (non-solid pickup)
    """
    SOLID = {'X', 'B', '?', 'H', 'L'}

    def __init__(self, width_tiles: int, height_tiles: int):
        self.wt = width_tiles
        self.ht = height_tiles
        self.grid = [[' ' for _ in range(self.wt)] for _ in range(self.ht)]
        self.spawn_px = (TILE * 2, TILE * (self.ht - 5))  # default
        self.flag_x = self.wt - 5                         # tile x of flag
        self.coins: List[pygame.Rect] = []
        self.enemies: List['Goomba'] = []

    # --- Tile helpers
    def in_bounds(self, tx, ty):
        return 0 <= tx < self.wt and 0 <= ty < self.ht

    def get(self, tx, ty):
        if not self.in_bounds(tx, ty):
            return ' '
        return self.grid[ty][tx]

    def set(self, tx, ty, ch):
        if self.in_bounds(tx, ty):
            self.grid[ty][tx] = ch

    def is_solid(self, tx, ty):
        return self.get(tx, ty) in Level.SOLID

    def tile_rect(self, tx, ty):
        return pygame.Rect(tx * TILE, ty * TILE, TILE, TILE)

    def tiles_in_rect(self, rect: pygame.Rect):
        # iterate candidate tiles overlapping rect
        left = max(int(rect.left // TILE), 0)
        right = min(int((rect.right - 1) // TILE), self.wt - 1)
        top = max(int(rect.top // TILE), 0)
        bottom = min(int((rect.bottom - 1) // TILE), self.ht - 1)
        for ty in range(top, bottom + 1):
            for tx in range(left, right + 1):
                yield tx, ty

    # --- Content helpers
    def add_coin(self, tx, ty):
        r = self.tile_rect(tx, ty).inflate(-6, -6)
        self.coins.append(r)

    def add_goomba(self, tx, ty):
        gx = tx * TILE + TILE // 2 - 8
        gy = ty * TILE + TILE - 16
        self.enemies.append(Goomba(gx, gy))

    # --- Generation -----------------------------------------------------------
    @staticmethod
    def gen_level1(width_tiles: int, height_tiles: int):
        lvl = Level(width_tiles, height_tiles)
        ground_y = height_tiles - 2

        # Base ground
        for tx in range(width_tiles):
            lvl.set(tx, ground_y, 'X')
            lvl.set(tx, ground_y + 1, 'X')

        # Gentle hills and platforms
        for base in range(10, width_tiles - 20, 26):
            for step in range(5):
                h = ground_y - step - 1
                lvl.set(base + step, h, 'B')
                if step % 2 == 0:
                    lvl.add_coin(base + step, h - 2)

        # Question blocks & bricks clusters
        clusters = [18, 36, 64, 88, 124, 152, 184]
        for cx in clusters:
            row = ground_y - 5
            for tx in range(cx, cx + 5):
                lvl.set(tx, row, 'B')
            lvl.set(cx + 2, row - 2, '?')
            lvl.add_coin(cx + 2, row - 3)

        # Pipes
        pipe_positions = [28, 54, 90, 140, 172, 206]
        for i, px in enumerate(pipe_positions):
            height = 2 + (i % 3)
            for dy in range(height):
                lvl.set(px, ground_y - dy, 'L')
                lvl.set(px + 1, ground_y - dy, 'L')

        # Enemies
        for gx in [22, 35, 50, 67, 84, 120, 136, 150, 166, 190]:
            lvl.add_goomba(gx, ground_y - 1)

        lvl.spawn_px = (TILE * 2, TILE * (ground_y - 3))
        lvl.flag_x = width_tiles - 6
        for ty in range(ground_y - 8, ground_y + 1):
            lvl.set(lvl.flag_x, ty, '|')
        for tx in range(lvl.flag_x - 2, lvl.flag_x + 8):
            lvl.set(tx, ground_y + 1, 'X')

        return lvl

    @staticmethod
    def gen_level2(width_tiles: int, height_tiles: int):
        lvl = Level(width_tiles, height_tiles)
        ground_y = height_tiles - 2

        # Base ground
        for tx in range(width_tiles):
            lvl.set(tx, ground_y, 'X')
            lvl.set(tx, ground_y + 1, 'X')

        # Floating platforms & gaps
        for base in range(14, width_tiles - 14, 22):
            # a short gap
            for gap in range(2):
                lvl.set(base + gap, ground_y, ' ')
                lvl.set(base + gap, ground_y + 1, ' ')
            # platform
            py = ground_y - random.choice([5, 6, 7])
            for tx in range(base + 3, base + 3 + random.randint(3, 7)):
                lvl.set(tx, py, 'H')
                if random.random() < 0.6:
                    lvl.add_coin(tx, py - 2)

        # Pipes as barriers
        for px in [32, 64, 96, 128, 160, 192]:
            for dy in range(random.choice([2, 3, 4])):
                lvl.set(px, ground_y - dy, 'L')
                lvl.set(px + 1, ground_y - dy, 'L')

        # Question block ladders
        for cx in [40, 70, 110, 150, 180]:
            for k in range(3):
                lvl.set(cx + k, ground_y - (5 + k), '?')
                lvl.add_coin(cx + k, ground_y - (6 + k))

        # Enemies patrols
        for gx in [18, 26, 42, 58, 75, 90, 106, 122, 138, 154, 170, 186, 202]:
            lvl.add_goomba(gx, ground_y - 1)

        lvl.spawn_px = (TILE * 3, TILE * (ground_y - 3))
        lvl.flag_x = width_tiles - 6
        for ty in range(ground_y - 9, ground_y + 1):
            lvl.set(lvl.flag_x, ty, '|')
        for tx in range(lvl.flag_x - 2, lvl.flag_x + 8):
            lvl.set(tx, ground_y + 1, 'X')

        return lvl


# --- Entities ----------------------------------------------------------------
@dataclass
class Player:
    rect: pygame.Rect
    vx: float = 0.0
    vy: float = 0.0
    on_ground: bool = False
    jump_time: float = 0.0
    alive: bool = True
    coins: int = 0

    def update(self, lvl: Level, keys, dt: float):
        if not self.alive:
            return

        # Horizontal input
        accel = 0.0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            accel -= MOVE_ACCEL if self.on_ground else AIR_ACCEL
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            accel += MOVE_ACCEL if self.on_ground else AIR_ACCEL

        # Friction
        if self.on_ground and abs(accel) < 1e-3:
            if abs(self.vx) <= GROUND_FRICTION * dt:
                self.vx = 0.0
            else:
                self.vx -= GROUND_FRICTION * dt * sign(self.vx)

        # Integrate horizontal
        self.vx += accel * dt
        max_speed = MAX_RUN_SPEED if (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]) else MAX_WALK_SPEED
        self.vx = clamp(self.vx, -max_speed, max_speed)

        # Jumping
        want_jump = keys[pygame.K_z] or keys[pygame.K_SPACE]
        if want_jump and self.on_ground:
            self.vy = -JUMP_SPEED
            self.on_ground = False
            self.jump_time = JUMP_HOLD_TIME
        elif want_jump and self.jump_time > 0.0:
            # Allow a tiny extra upward force while held
            self.vy -= JUMP_HOLD_FORCE * dt
            self.jump_time -= dt
        else:
            self.jump_time = 0.0

        # Gravity
        self.vy += GRAVITY * dt
        self.vy = min(self.vy, GRAVITY)  # clamp fall speed somewhat

        # Move and collide
        self.rect, self.on_ground = move_and_collide(self.rect, self.vx * dt, self.vy * dt, lvl)

        # Collect coins
        self.collect_coins(lvl)

        # Death on fall
        if self.rect.top > lvl.ht * TILE + 200:
            self.alive = False

    def stomp_bounce(self):
        self.vy = -STOMP_BOUNCE
        self.on_ground = False

    def collect_coins(self, lvl: Level):
        keep = []
        for r in lvl.coins:
            if self.rect.colliderect(r):
                self.coins += 1
            else:
                keep.append(r)
        lvl.coins = keep

    def draw(self, surface: pygame.Surface, camx: int):
        r = self.rect.move(-camx, 0)
        # Simple "sprite": body
        pygame.draw.rect(surface, PLAYER_FILL, r)
        pygame.draw.rect(surface, PLAYER_OUTLINE, r, 2)
        # Little eyes
        eye = pygame.Rect(r.left + 4, r.top + 5, 3, 3)
        pygame.draw.rect(surface, (0, 0, 0), eye)


@dataclass
class Goomba:
    x: float
    y: float
    vx: float = -50.0
    alive: bool = True
    width: int = 16
    height: int = 16
    on_ground: bool = False

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    def update(self, lvl: Level, dt: float):
        if not self.alive:
            return
        # Simple walker
        ax = 0.0
        self.vx = clamp(self.vx, -90.0, 90.0)

        # Gravity
        vy = 0.0
        vy += GRAVITY * dt

        new_rect, on_ground = move_and_collide(self.rect, self.vx * dt, vy * dt, lvl)
        # Hit a wall? flip direction
        if new_rect.left == self.rect.left and self.vx < 0:
            self.vx = abs(self.vx)
        elif new_rect.left == self.rect.left and self.vx > 0:
            self.vx = -abs(self.vx)

        self.x, self.y = new_rect.left, new_rect.top
        self.on_ground = on_ground

        # Death if falls far below
        if self.y > lvl.ht * TILE + 200:
            self.alive = False

    def draw(self, surface: pygame.Surface, camx: int):
        if not self.alive:
            return
        r = self.rect.move(-camx, 0)
        pygame.draw.rect(surface, ENEMY, r)
        pygame.draw.rect(surface, (0, 0, 0), r, 1)


# --- Collision ---------------------------------------------------------------
def move_and_collide(rect: pygame.Rect, dx: float, dy: float, lvl: Level) -> Tuple[pygame.Rect, bool]:
    """Move rect by (dx, dy) with tile collisions. Returns (rect, on_ground)."""
    r = rect.copy()
    on_ground = False

    # Horizontal
    if dx != 0.0:
        r.x += int(round(dx))
        # Resolve collisions
        for tx, ty in lvl.tiles_in_rect(r):
            if lvl.is_solid(tx, ty):
                tile_r = lvl.tile_rect(tx, ty)
                if dx > 0 and r.colliderect(tile_r):
                    r.right = tile_r.left
                elif dx < 0 and r.colliderect(tile_r):
                    r.left = tile_r.right

    # Vertical
    if dy != 0.0:
        r.y += int(round(dy))
        collided_above = False
        for tx, ty in lvl.tiles_in_rect(r):
            ch = lvl.get(tx, ty)
            if ch in Level.SOLID:
                tile_r = lvl.tile_rect(tx, ty)
                if dy > 0 and r.colliderect(tile_r):
                    r.bottom = tile_r.top
                    on_ground = True
                elif dy < 0 and r.colliderect(tile_r):
                    r.top = tile_r.bottom
                    collided_above = True
        if collided_above:
            # Check for hitting '?' block from below
            txs = [int((r.centerx) // TILE)]
            ty_above = int((r.top) // TILE)
            for tx in txs:
                if lvl.get(tx, ty_above) == '?':
                    # pop a coin and convert to solid block
                    lvl.set(tx, ty_above, 'B')
                    lvl.add_coin(tx, ty_above - 1)

    return r, on_ground


# --- Camera ------------------------------------------------------------------
class Camera:
    def __init__(self):
        self.x = 0.0

    def update(self, target_rect: pygame.Rect, lvl: Level, dt: float):
        # Follow target with slight smoothing
        desired = target_rect.centerx - WIDTH * 0.35
        self.x += (desired - self.x) * min(1.0, 10.0 * dt)
        self.x = clamp(self.x, 0, lvl.wt * TILE - WIDTH)


# --- Rendering ---------------------------------------------------------------
def draw_grid(surface):
    # optional: faint grid for debug
    for x in range(0, WIDTH, TILE):
        pygame.draw.line(surface, (200, 200, 200), (x, 0), (x, HEIGHT), 1)
    for y in range(0, HEIGHT, TILE):
        pygame.draw.line(surface, (200, 200, 200), (0, y), (WIDTH, y), 1)


def draw_level(surface: pygame.Surface, lvl: Level, camx: int):
    # Background sky
    surface.fill(SKY)

    # Determine visible tile range
    start_tx = max(0, int(camx // TILE) - 1)
    end_tx = min(lvl.wt, start_tx + VIEW_TILES_X + 3)

    # Draw tiles
    for ty in range(lvl.ht):
        for tx in range(start_tx, end_tx):
            ch = lvl.get(tx, ty)
            if ch == ' ':
                continue
            r = pygame.Rect(tx * TILE - camx, ty * TILE, TILE, TILE)
            if ch == 'X':
                pygame.draw.rect(surface, GROUND, r)
            elif ch == 'B':
                pygame.draw.rect(surface, BRICK, r)
                pygame.draw.rect(surface, (0, 0, 0), r, 1)
                # brick pattern
                pygame.draw.line(surface, (50, 10, 10), (r.left, r.centery), (r.right, r.centery), 1)
                pygame.draw.line(surface, (50, 10, 10), (r.left + r.width // 2, r.top), (r.left + r.width // 2, r.centery), 1)
            elif ch == '?':
                pygame.draw.rect(surface, BLOCK_Q, r)
                pygame.draw.rect(surface, (0, 0, 0), r, 1)
                pygame.draw.rect(surface, (255, 255, 255), r.inflate(-10, -10))
            elif ch == 'H':
                pygame.draw.rect(surface, BLOCK_SOLID, r)
                pygame.draw.rect(surface, (0, 0, 0), r, 1)
            elif ch == 'L':
                # pipe: two tiles wide, draw outline
                pygame.draw.rect(surface, PIPE, r)
                pygame.draw.rect(surface, (0, 0, 0), r, 1)
            elif ch == '|':
                pygame.draw.rect(surface, FLAG, r)

    # Coins
    for c in lvl.coins:
        rc = c.move(-camx, 0)
        pygame.draw.ellipse(surface, COIN, rc)
        pygame.draw.ellipse(surface, (130, 100, 0), rc, 1)


def draw_hud(surface: pygame.Surface, font, player: Player, level_index: int, fps: float, show_fps: bool):
    text = f"LEVEL {level_index + 1}   COINS {player.coins}"
    hud = font.render(text, True, (0, 0, 0))
    surface.blit(hud, (10, 8))

    if show_fps:
        fps_text = font.render(f"{fps:5.1f} FPS", True, (0, 0, 0))
        surface.blit(fps_text, (WIDTH - 100, 8))


# --- Game loop ---------------------------------------------------------------
def main():
    pygame.init()
    pygame.display.set_caption("SMB-inspired prototype — 600x400 @ ~60.1 FPS")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 16)

    # Generate a couple of demo levels (procedural, not Nintendo data).
    random.seed(1337)
    levels = [
        Level.gen_level1(240, 20),
        Level.gen_level2(260, 20),
    ]
    level_index = 0
    lvl = levels[level_index]

    player = Player(pygame.Rect(lvl.spawn_px[0], lvl.spawn_px[1], 14, 18))
    cam = Camera()

    running = True
    show_fps = False
    accumulator = 0.0
    time_scale = 1.0  # keep for potential tuning

    while running:
        # Handle events (non-blocking)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_F1:
                    show_fps = not show_fps
                elif event.key == pygame.K_r:
                    # reset level
                    levels[level_index] = Level.gen_level1(240, 20) if level_index == 0 else Level.gen_level2(260, 20)
                    lvl = levels[level_index]
                    player = Player(pygame.Rect(lvl.spawn_px[0], lvl.spawn_px[1], 14, 18))
                    cam = Camera()

        # Frame time
        dt_real = clock.tick_busy_loop(int(FPS_TARGET)) / 1000.0
        accumulator += dt_real * time_scale

        # Fixed-step updates (avoid spiral by capping iterations)
        iterations = 0
        while accumulator >= FIXED_DT and iterations < 8:
            keys = pygame.key.get_pressed()

            # Update entities
            player.update(lvl, keys, FIXED_DT)
            for e in lvl.enemies:
                e.update(lvl, FIXED_DT)

            # Player vs enemies (stomp or hurt)
            for e in lvl.enemies:
                if not e.alive:
                    continue
                if player.rect.colliderect(e.rect):
                    # stomp check: player's feet versus enemy top with downward motion
                    if player.vy > 50 and (player.rect.bottom - e.rect.top) <= 10:
                        e.alive = False
                        player.stomp_bounce()
                    else:
                        # hurt → simple reset
                        player.alive = False

            # Remove dead enemies
            lvl.enemies = [e for e in lvl.enemies if e.alive]

            # Question-blocks bouncing handled in move_and_collide()

            # Camera after player moves
            cam.update(player.rect, lvl, FIXED_DT)

            # Check flag (finish)
            if player.rect.centerx // TILE >= lvl.flag_x:
                # advance level
                level_index = (level_index + 1) % len(levels)
                lvl = levels[level_index]
                player = Player(pygame.Rect(lvl.spawn_px[0], lvl.spawn_px[1], 14, 18))
                cam = Camera()

            # Respawn if died
            if not player.alive:
                player = Player(pygame.Rect(lvl.spawn_px[0], lvl.spawn_px[1], 14, 18))
                cam = Camera()

            accumulator -= FIXED_DT
            iterations += 1

        # Render
        draw_level(screen, lvl, int(cam.x))
        for e in lvl.enemies:
            e.draw(screen, int(cam.x))
        player.draw(screen, int(cam.x))

        draw_hud(screen, font, player, level_index, clock.get_fps(), show_fps)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("Unhandled error:", e, file=sys.stderr)
        pygame.quit()
        sys.exit(1)
