#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Ultra Mario Forever — NSMB-like single-file engine (6 worlds x 5 levels)
# -----------------------------------------------------------------------------
# This is a from-scratch, original platformer engine implemented in Python
# using pygame. It is inspired by "NSMB-style" platforming feel (coyote time,
# jump buffering, variable jump height, smooth acceleration), but it does NOT
# use or include any Nintendo IP or assets. All visuals are procedurally
# generated rectangles and text so you can ship this as a single .py file.
#
# Run locally:
#   pip install pygame
#   python program.py
#
# Controls (in-level):
#   Left/Right:   Arrow keys or A/D
#   Jump:         Space or K
#   Run/Dash:     Left Shift or J
#   Pause:        Enter
#   Exit level:   Esc (back to Select)
#
# Controls (Select screen):
#   Move:         Arrow keys or WASD
#   Start level:  Enter
#   Quit:         Esc
#
# Worlds/Themes:
#   1 Grass, 2 Desert, 3 Snow, 4 Jungle, 5 Volcano, 6 Sky
#
# File layout: all code is contained in this single file.
# -----------------------------------------------------------------------------

import math
import os
import random
import sys
from dataclasses import dataclass

import pygame

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

VERSION = "1.0.0"
WIDTH, HEIGHT = 16 * 32, 15 * 32  # 512 x 480
TILE = 32
FPS = 60

NUM_WORLDS = 6
LEVELS_PER_WORLD = 5

# Physics tuned for a NSMB-like "feel" (approximate, not identical).
GRAVITY = 0.60
MAX_RUN_SPEED = 5.6
AIR_CTRL = 0.65
GROUND_ACCEL = 0.50
AIR_ACCEL = GROUND_ACCEL * AIR_CTRL
FRICTION = 0.82
JUMP_VEL = -12.2
SHORT_HOP_CUTOFF = 0.45   # percentage of upward speed kept if jump is released early
COYOTE_FRAMES = 8         # grace frames after leaving ground
JUMP_BUFFER_FRAMES = 7    # register jump slightly before landing

# Colors per theme (bg, solid, accent, coin, hazard):
THEMES = [
    ((135, 206, 235), (93, 173, 64), (60, 120, 60), (255, 215, 0), (220, 60, 60)),   # 1 Grassland
    ((240, 220, 170), (210, 180, 140), (160, 120, 80), (255, 215, 0), (180, 90, 40)),# 2 Desert
    ((200, 225, 255), (190, 220, 240), (140, 180, 210), (250, 230, 80), (160, 200, 255)), # 3 Snow
    ((160, 215, 170), (90, 140, 70), (60, 110, 70), (255, 230, 80), (70, 110, 60)), # 4 Jungle
    ((255, 180, 160), (120, 50, 40), (90, 40, 35), (255, 220, 80), (255, 80, 60)),  # 5 Volcano
    ((210, 230, 255), (180, 200, 230), (140, 160, 200), (250, 230, 80), (130, 160, 255)), # 6 Sky
]

FONT_NAME = pygame.font.get_default_font()

# Tile identifiers
EMPTY = "."
SOLID = "#"
COIN = "o"
HAZARD = "x"
FLAG = "F"
ENEMY = "E"
QBLOCK = "?"
PLATFORM = "="  # semi-solid
MOVING = "M"
SPAWN = "S"

COLLIDE_TILES = {SOLID, PLATFORM, MOVING}
KILL_TILES = {HAZARD}

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v

def rect_from_tile(tx, ty):
    return pygame.Rect(tx * TILE, ty * TILE, TILE, TILE)

# -----------------------------------------------------------------------------
# Camera
# -----------------------------------------------------------------------------

class Camera:
    def __init__(self, w, h):
        self.x = 0
        self.y = 0
        self.w = w
        self.h = h

    def apply(self, rect):
        return rect.move(-self.x, -self.y)

    def update(self, target_rect):
        # Soft follow with horizontal dead zone
        dead_w = WIDTH // 4
        center_x = self.x + WIDTH // 2
        dx = target_rect.centerx - center_x
        if abs(dx) > dead_w:
            self.x += (dx - math.copysign(dead_w, dx)) * 0.1

        # Lock vertical gently
        self.y += (target_rect.centery - (self.y + HEIGHT // 2)) * 0.06

        self.x = clamp(self.x, 0, max(0, self.w - WIDTH))
        self.y = clamp(self.y, 0, max(0, self.h - HEIGHT))

# -----------------------------------------------------------------------------
# Level generation
# -----------------------------------------------------------------------------

@dataclass
class LevelSpec:
    width: int
    height: int
    theme_idx: int
    slippery: bool = False
    low_gravity: bool = False
    lava_floor: bool = False

class Level:
    def __init__(self, world_idx, level_idx):
        self.world_idx = world_idx
        self.level_idx = level_idx
        self.spec = self._make_spec(world_idx)
        self.grid = self._generate_grid(self.spec, world_idx, level_idx)
        self.width_px = self.spec.width * TILE
        self.height_px = self.spec.height * TILE
        self.enemies = self._spawn_enemies()
        self.movers = self._spawn_movers()
        self.spawn = self._find_spawn()
        self.flag_rect = self._find_flag()

    @staticmethod
    def _make_spec(world_idx):
        # Basic theme flags per world
        theme = world_idx
        slippery = (world_idx == 2)  # Snow
        low_g = (world_idx == 5)     # Sky
        lava = (world_idx == 4)      # Volcano
        return LevelSpec(width=180, height=15, theme_idx=theme,
                         slippery=slippery, low_gravity=low_g, lava_floor=lava)

    def _generate_grid(self, spec: LevelSpec, world_idx, level_idx):
        random.seed((world_idx + 1) * 1000 + (level_idx + 1) * 77)
        W, H = spec.width, spec.height
        G = [[EMPTY for _ in range(W)] for _ in range(H)]

        # Baseline floor height profile per world
        if world_idx in (0, 3):  # Grass/Jungle
            base = H - 3
        elif world_idx == 1:  # Desert
            base = H - 4
        elif world_idx == 2:  # Snow
            base = H - 3
        elif world_idx == 4:  # Volcano
            base = H - 2
        else:  # Sky
            base = H - 8

        # Build ground or islands
        holes = []
        x = 0
        while x < W:
            hole_len = 0
            if world_idx != 5 and random.random() < 0.08:  # fewer holes in Sky (islands instead)
                hole_len = random.randint(2, 4 + world_idx)  # more in later worlds
                holes.append((x, x + hole_len))
            seg_len = random.randint(6, 12)
            for i in range(seg_len):
                col = x + i
                if col >= W:
                    break
                if hole_len and x <= col < x + hole_len:
                    continue
                # Vary the floor height slightly
                floor = base + int(1.5 * math.sin(col * 0.15 + world_idx))
                floor = clamp(floor, 4, H - 2)
                for y in range(floor, H):
                    G[y][col] = SOLID
                # occasional top blocks/platforms
                if random.random() < 0.08:
                    hh = floor - random.randint(3, 5)
                    if 2 <= hh < H - 2:
                        G[hh][col] = SOLID
                # coins arcs
                if random.random() < 0.12:
                    arc_h = floor - random.randint(4, 6)
                    if arc_h >= 2:
                        for j in range(-2, 3):
                            c = col + j
                            if 0 <= c < W:
                                G[arc_h + int(1.2 * math.sin(j))][c] = COIN
                # q-blocks
                if random.random() < 0.06 and floor - 3 >= 2:
                    G[floor - 3][col] = QBLOCK
            x += seg_len + hole_len

        # Sky world: generate islands
        if world_idx == 5:
            for _ in range(36):
                cx = random.randint(3, W - 6)
                cy = random.randint(3, H - 6)
                length = random.randint(3, 7)
                for i in range(-length // 2, length // 2 + 1):
                    if 0 <= cx + i < W:
                        G[cy][cx + i] = SOLID
                        if random.random() < 0.35 and cy - 3 >= 0:
                            G[cy - 3][cx + i] = PLATFORM

        # Volcano world: lava floor segments
        if spec.lava_floor:
            for col in range(W):
                if random.random() < 0.09:
                    for y in range(H - 2, H):
                        G[y][col] = HAZARD

        # Place spawn and flag
        self._drop_spawn_flag(G)

        # Enemy spawns on tops of columns
        for col in range(8, W - 4, random.randint(7, 12)):
            top = self._col_top(G, col)
            if top and random.random() < 0.6:
                G[top - 1][col] = ENEMY

        # Moving platforms in Jungle/Sky
        if world_idx in (3, 5):
            for _ in range(10 if world_idx == 5 else 6):
                cx = random.randint(6, W - 6)
                cy = random.randint(4, H - 6)
                if G[cy][cx] == EMPTY:
                    G[cy][cx] = MOVING

        return G

    def _drop_spawn_flag(self, G):
        H = len(G)
        W = len(G[0])
        # Spawn near left
        sx = 2
        sy = self._col_top(G, sx) - 1 if self._col_top(G, sx) else H - 4
        sy = clamp(sy, 2, H - 4)
        G[sy][sx] = SPAWN
        # Flag near right
        fx = W - 5
        fy = self._col_top(G, fx) - 1 if self._col_top(G, fx) else H - 4
        fy = clamp(fy, 2, H - 4)
        G[fy][fx] = FLAG

    def _col_top(self, G, col):
        H = len(G)
        for y in range(H):
            if G[y][col] in (SOLID, PLATFORM, MOVING):
                return y
        return None

    def _spawn_enemies(self):
        enemies = []
        for y, row in enumerate(self.grid):
            for x, ch in enumerate(row):
                if ch == ENEMY:
                    enemies.append(Walker(x * TILE, y * TILE))
                    self.grid[y][x] = EMPTY
        return enemies

    def _spawn_movers(self):
        movers = []
        for y, row in enumerate(self.grid):
            for x, ch in enumerate(row):
                if ch == MOVING:
                    movers.append(MovingPlatform(x * TILE, y * TILE))
                    self.grid[y][x] = EMPTY
        return movers

    def _find_spawn(self):
        for y, row in enumerate(self.grid):
            for x, ch in enumerate(row):
                if ch == SPAWN:
                    return pygame.Rect(x * TILE, y * TILE, TILE, TILE)
        # fallback
        return pygame.Rect(64, 64, TILE, TILE)

    def _find_flag(self):
        for y, row in enumerate(self.grid):
            for x, ch in enumerate(row):
                if ch == FLAG:
                    return pygame.Rect(x * TILE, y * TILE, TILE, TILE)
        return pygame.Rect(self.width_px - 3*TILE, 6*TILE, TILE, 5*TILE)

    def tiles_in_rect(self, rect):
        G = self.grid
        H = len(G)
        W = len(G[0])
        x0 = clamp(rect.left // TILE - 1, 0, W - 1)
        x1 = clamp(rect.right // TILE + 1, 0, W - 1)
        y0 = clamp(rect.top // TILE - 1, 0, H - 1)
        y1 = clamp(rect.bottom // TILE + 1, 0, H - 1)
        for ty in range(y0, y1 + 1):
            for tx in range(x0, x1 + 1):
                yield tx, ty, G[ty][tx]

    def draw(self, surf, camera):
        bg, solid_c, accent, coin_c, hazard_c = THEMES[self.spec.theme_idx]
        surf.fill(bg)

        # Draw tiles
        for ty, row in enumerate(self.grid):
            for tx, ch in enumerate(row):
                r = pygame.Rect(tx * TILE, ty * TILE, TILE, TILE)
                if not camera.apply(r).colliderect(surf.get_rect()):
                    continue
                if ch == SOLID:
                    pygame.draw.rect(surf, solid_c, camera.apply(r))
                    pygame.draw.rect(surf, (0, 0, 0), camera.apply(r), 1)
                elif ch == PLATFORM:
                    rr = camera.apply(r).inflate(0, -20).move(0, 10)
                    pygame.draw.rect(surf, accent, rr)
                elif ch == COIN:
                    pygame.draw.circle(surf, coin_c, camera.apply(r).center, 6)
                elif ch == HAZARD:
                    rr = camera.apply(r)
                    pygame.draw.rect(surf, hazard_c, rr)
                elif ch == QBLOCK:
                    pygame.draw.rect(surf, (230, 180, 60), camera.apply(r))
                    pygame.draw.rect(surf, (80, 50, 20), camera.apply(r), 2)
                elif ch == FLAG:
                    rr = camera.apply(r)
                    pygame.draw.rect(surf, (30, 30, 30), rr.move(12, -TILE).inflate(-20, TILE * 2))
                    pygame.draw.polygon(surf, (230, 60, 60),
                        [(rr.left+16, rr.top-20), (rr.left+16, rr.top-4), (rr.left+16+28, rr.top-12)])

        # Movers
        for m in self.movers:
            pygame.draw.rect(surf, (100, 100, 160), camera.apply(m.rect))

        # Enemies
        for e in self.enemies:
            e.draw(surf, camera, accent)

# -----------------------------------------------------------------------------
# Entities
# -----------------------------------------------------------------------------

class MovingPlatform:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, TILE, TILE // 3)
        self.t = random.random() * 6.28
        self.ampl = random.randint(40, 120)
        self.speed = random.uniform(0.6, 1.2)
        self.axis = random.choice(("x", "y"))
        self.origin = (x, y)

    def update(self, level):
        self.t += 0.02 * self.speed
        ox, oy = self.origin
        if self.axis == "x":
            self.rect.x = int(ox + math.sin(self.t) * self.ampl)
        else:
            self.rect.y = int(oy + math.sin(self.t) * self.ampl)

class Walker:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, TILE, TILE - 6)
        self.vx = random.choice([-1.4, 1.4])
        self.alive = True
        self.on_ground = False

    def update(self, level):
        if not self.alive:
            return
        self.vx = clamp(self.vx, -2.0, 2.0)
        self.rect.x += int(self.vx)

        # Horizontal collisions
        for tx, ty, ch in level.tiles_in_rect(self.rect):
            if ch in COLLIDE_TILES:
                r = rect_from_tile(tx, ty)
                if self.rect.colliderect(r):
                    if self.vx > 0:
                        self.rect.right = r.left
                        self.vx = -abs(self.vx)
                    elif self.vx < 0:
                        self.rect.left = r.right
                        self.vx = abs(self.vx)

        # Gravity
        self.rect.y += 4
        self.on_ground = False
        for tx, ty, ch in level.tiles_in_rect(self.rect):
            if ch in COLLIDE_TILES:
                r = rect_from_tile(tx, ty)
                if self.rect.colliderect(r):
                    if self.rect.bottom > r.top and self.rect.centery < r.centery:
                        self.rect.bottom = r.top
                        self.on_ground = True

        if not self.on_ground:
            # if at edge, turn around sometimes
            if random.random() < 0.02:
                self.vx *= -1

    def stomp(self):
        self.alive = False

    def draw(self, surf, camera, color):
        if not self.alive:
            return
        rr = camera.apply(self.rect)
        pygame.draw.rect(surf, (170, 90, 80), rr)
        eye = pygame.Rect(rr.x+6, rr.y+8, 6, 6)
        pygame.draw.rect(surf, (255, 255, 255), eye)
        pygame.draw.rect(surf, (0, 0, 0), eye.inflate(-4, -4))

# -----------------------------------------------------------------------------
# Player
# -----------------------------------------------------------------------------

class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, TILE - 6, TILE - 2)
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = False
        self.coyote = 0
        self.jump_buf = 0
        self.facing = 1
        self.coins = 0
        self.invuln = 0
        self.alive = True
        self.respawn_point = (x, y)

    def update(self, keys, level: Level):
        if not self.alive:
            return

        accel = GROUND_ACCEL if self.on_ground else AIR_ACCEL
        left = keys[pygame.K_LEFT] or keys[pygame.K_a]
        right = keys[pygame.K_RIGHT] or keys[pygame.K_d]
        run = keys[pygame.K_LSHIFT] or keys[pygame.K_j]
        want_jump = keys[pygame.K_SPACE] or keys[pygame.K_k]

        # Jump buffer & coyote time
        if want_jump:
            self.jump_buf = JUMP_BUFFER_FRAMES
        else:
            self.jump_buf = max(0, self.jump_buf - 1)

        if self.on_ground:
            self.coyote = COYOTE_FRAMES
        else:
            self.coyote = max(0, self.coyote - 1)

        # Horizontal input
        if left ^ right:
            self.facing = -1 if left else 1
            target = MAX_RUN_SPEED * (1.25 if run else 1.0)
            self.vx += (-accel if left else accel)
            self.vx = clamp(self.vx, -target, target)
        else:
            # friction
            if self.on_ground:
                self.vx *= FRICTION
                if abs(self.vx) < 0.01:
                    self.vx = 0.0

        # Jump
        if self.jump_buf and self.coyote:
            self.vy = JUMP_VEL * (0.92 if run else 1.0)
            self.on_ground = False
            self.jump_buf = 0
            self.coyote = 0

        # Variable jump height
        if self.vy < 0 and not want_jump:
            self.vy *= SHORT_HOP_CUTOFF

        # Gravity
        g = GRAVITY * (0.78 if level.spec.low_gravity else 1.0)
        self.vy += g
        self.vy = clamp(self.vy, -50, 18)

        # Move X
        self.rect.x += int(self.vx)
        self._collide_x(level)

        # Movers carry player if standing on them
        for m in level.movers:
            prev_bottom = self.rect.bottom
            m.update(level)
            if self.rect.move(0, 1).colliderect(m.rect) and prev_bottom <= m.rect.top + 4:
                self.rect.bottom = m.rect.top
                self.on_ground = True
                self.vy = 0
                self.rect.x += int((m.rect.x - (m.origin[0] + math.sin(m.t - 0.02 * m.speed) * m.ampl)))

        # Move Y
        self.rect.y += int(self.vy)
        self._collide_y(level)

        # Coins & blocks
        for tx, ty, ch in level.tiles_in_rect(self.rect.inflate(0, 1)):
            if ch == COIN:
                level.grid[ty][tx] = EMPTY
                self.coins += 1
            elif ch == QBLOCK and self.rect.top <= ty * TILE + TILE and self.vy < 0:
                # Hit from below -> convert to coin and pop
                level.grid[ty][tx] = COIN

        # Enemies
        for e in level.enemies:
            if not e.alive:
                continue
            if self.rect.colliderect(e.rect):
                if self.vy > 1 and self.rect.bottom - e.rect.top < 14:
                    e.stomp()
                    self.vy = JUMP_VEL * 0.55
                    self.on_ground = False
                else:
                    self._hurt()

        # Hazards
        for tx, ty, ch in level.tiles_in_rect(self.rect):
            if ch in KILL_TILES:
                self._die()

        # Out of bounds
        if self.rect.top > level.height_px + 200:
            self._die()

    def _hurt(self):
        if self.invuln > 0:
            return
        self.invuln = FPS  # 1s
        self._die()  # simple: die on touch (could be power states)

    def _die(self):
        self.alive = False

    def respawn(self):
        self.rect.topleft = self.respawn_point
        self.vx = 0
        self.vy = 0
        self.on_ground = False
        self.coyote = 0
        self.jump_buf = 0
        self.invuln = 0
        self.alive = True

    def _collide_x(self, level: Level):
        for tx, ty, ch in level.tiles_in_rect(self.rect):
            if ch in COLLIDE_TILES:
                r = rect_from_tile(tx, ty)
                if self.rect.colliderect(r):
                    if self.vx > 0:
                        self.rect.right = r.left
                    elif self.vx < 0:
                        self.rect.left = r.right
                    self.vx = 0

    def _collide_y(self, level: Level):
        self.on_ground = False
        for tx, ty, ch in level.tiles_in_rect(self.rect):
            if ch in COLLIDE_TILES:
                r = rect_from_tile(tx, ty)
                if self.rect.colliderect(r):
                    if self.vy > 0 and self.rect.bottom <= r.bottom:
                        self.rect.bottom = r.top
                        self.vy = 0
                        self.on_ground = True
                    elif self.vy < 0 and self.rect.top >= r.top:
                        self.rect.top = r.bottom
                        self.vy = 0

    def draw(self, surf, camera):
        rr = camera.apply(self.rect)
        body = rr.copy()
        color = (250, 120, 90) if (pygame.time.get_ticks() // 100) % 2 == 0 or self.invuln == 0 else (250, 200, 200)
        pygame.draw.rect(surf, color, body)
        # A simple face to give character
        eye = pygame.Rect(body.x + (8 if self.facing > 0 else body.width - 14), body.y + 8, 6, 6)
        pygame.draw.rect(surf, (255, 255, 255), eye)
        pygame.draw.rect(surf, (0, 0, 0), eye.inflate(-4, -4))

# -----------------------------------------------------------------------------
# UI & Game State
# -----------------------------------------------------------------------------

class SelectScreen:
    def __init__(self, progress):
        self.sel_world = 0
        self.sel_level = 0
        self.progress = progress  # set of (w,l) completed

    def handle_input(self, events, keys):
        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_DOWN, pygame.K_s):
                    self.sel_world = clamp(self.sel_world + 1, 0, NUM_WORLDS - 1)
                elif e.key in (pygame.K_UP, pygame.K_w):
                    self.sel_world = clamp(self.sel_world - 1, 0, NUM_WORLDS - 1)
                elif e.key in (pygame.K_RIGHT, pygame.K_d):
                    self.sel_level = clamp(self.sel_level + 1, 0, LEVELS_PER_WORLD - 1)
                elif e.key in (pygame.K_LEFT, pygame.K_a):
                    self.sel_level = clamp(self.sel_level - 1, 0, LEVELS_PER_WORLD - 1)
                elif e.key == pygame.K_RETURN:
                    return ("start", self.sel_world, self.sel_level)
        return None

    def draw(self, surf, font_small, font_big):
        surf.fill((18, 18, 22))
        title = font_big.render(f"Ultra Mario Forever  —  Worlds {NUM_WORLDS} × Levels {LEVELS_PER_WORLD}", True, (240, 240, 240))
        surf.blit(title, (WIDTH // 2 - title.get_width() // 2, 18))

        cell_w, cell_h = WIDTH // (LEVELS_PER_WORLD + 2), (HEIGHT - 100) // (NUM_WORLDS + 1)
        y = 80
        for w in range(NUM_WORLDS):
            world_name = ["Grassland", "Desert", "Snow", "Jungle", "Volcano", "Sky"][w]
            label = font_small.render(f"World {w+1} — {world_name}", True, (200, 200, 210))
            surf.blit(label, (28, y - 20))

            for l in range(LEVELS_PER_WORLD):
                rect = pygame.Rect(28 + l * cell_w + 20, y, cell_w - 14, cell_h - 10)
                locked = not self._is_unlocked(w, l)
                color = (60, 60, 70) if locked else (50, 140, 220)
                if (w, l) in self.progress:
                    color = (65, 180, 100)  # completed
                pygame.draw.rect(surf, color, rect, border_radius=6)
                if w == self.sel_world and l == self.sel_level:
                    pygame.draw.rect(surf, (255, 255, 255), rect, 3, border_radius=6)

                txt = font_small.render(f"{l+1}", True, (10, 10, 12))
                surf.blit(txt, (rect.centerx - txt.get_width() // 2, rect.centery - txt.get_height() // 2))
            y += cell_h

        hint = font_small.render("Enter: Start level • Arrows/WASD: Move • Esc: Quit", True, (200, 200, 210))
        surf.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT - 28))

    def _is_unlocked(self, w, l):
        if w == 0 and l == 0:
            return True
        # unlocked if previous (w,l-1) completed or previous world last level completed
        if l > 0:
            return (w, l - 1) in self.progress
        else:
            return (w - 1, LEVELS_PER_WORLD - 1) in self.progress

class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Ultra Mario Forever (NSMB-like)")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font_small = pygame.font.SysFont(FONT_NAME, 18)
        self.font_big = pygame.font.SysFont(FONT_NAME, 28)

        self.state = "select"
        self.progress = set()
        self.select = SelectScreen(self.progress)

        self.level = None
        self.player = None
        self.camera = None
        self.paused = False
        self.win_timer = 0

    def start_level(self, w, l):
        self.level = Level(w, l)
        spawn = self.level.spawn
        self.player = Player(spawn.x, spawn.y - 4)
        self.player.respawn_point = (spawn.x, spawn.y - 4)
        self.camera = Camera(self.level.width_px, self.level.height_px)
        self.paused = False
        self.win_timer = 0
        self.state = "play"

    def run(self):
        while True:
            dt = self.clock.tick(FPS)
            events = pygame.event.get()
            keys = pygame.key.get_pressed()
            for e in events:
                if e.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                    if self.state == "play":
                        self.state = "select"
                    else:
                        pygame.quit()
                        sys.exit()

            if self.state == "select":
                action = self.select.handle_input(events, keys)
                self.select.draw(self.screen, self.font_small, self.font_big)
                if action and action[0] == "start":
                    w, l = action[1], action[2]
                    if self.select._is_unlocked(w, l):
                        self.start_level(w, l)
                pygame.display.flip()
                continue

            if self.state == "play":
                for e in events:
                    if e.type == pygame.KEYDOWN and e.key == pygame.K_RETURN:
                        self.paused = not self.paused

                if not self.paused:
                    self.player.update(keys, self.level)
                    for enemy in self.level.enemies:
                        enemy.update(self.level)
                    for mover in self.level.movers:
                        mover.update(self.level)

                    # Camera
                    self.camera.update(self.player.rect)

                    # Death/Respawn
                    if not self.player.alive:
                        self._draw_world()
                        self._draw_hud()
                        self._draw_center_text("You Died!  Respawning...", (255, 240, 240))
                        pygame.display.flip()
                        pygame.time.delay(900)
                        self.player.respawn()
                        continue

                    # Win check
                    if self.player.rect.colliderect(self.level.flag_rect):
                        self.win_timer += 1
                        if self.win_timer > FPS // 2:
                            self.progress.add((self.level.world_idx, self.level.level_idx))
                            self.state = "select"
                            continue

                self._draw_world()
                self._draw_hud()

                if self.paused:
                    self._draw_center_text("Paused — Enter to Resume", (255, 255, 255))

                if self.win_timer > 0:
                    self._draw_center_text("Course Clear!", (255, 255, 120))

                pygame.display.flip()

    def _draw_world(self):
        self.level.draw(self.screen, self.camera)
        for enemy in self.level.enemies:
            enemy.draw(self.screen, self.camera, THEMES[self.level.spec.theme_idx][2])
        self.player.draw(self.screen, self.camera)

    def _draw_hud(self):
        bg, _, _, _, _ = THEMES[self.level.spec.theme_idx]
        hud = pygame.Surface((WIDTH, 28), pygame.SRCALPHA)
        hud.fill((0, 0, 0, 120))
        self.screen.blit(hud, (0, 0))

        txt = self.font_small.render(
            f"W{self.level.world_idx+1}-{self.level.level_idx+1}   Coins: {self.player.coins}   v{VERSION}", True, (255, 255, 255)
        )
        self.screen.blit(txt, (8, 6))

    def _draw_center_text(self, text, color):
        s = self.font_big.render(text, True, color)
        self.screen.blit(s, (WIDTH // 2 - s.get_width() // 2, HEIGHT // 2 - s.get_height() // 2))

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        Game().run()
    except Exception as e:
        pygame.quit()
        raise
