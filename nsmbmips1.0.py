#!/usr/bin/env python3
"""
NSMB-Style PC Port — 5 Worlds x 3 Levels (Single-File Prototype)
Enhanced with more NSMB-like features: slopes, enemies, coins, varied terrain

Controls
- Overworld: ←/→ move selection, ENTER to play, ESC quits program
- In Level : ←/→ move, Z/SPACE jump, X run (slightly faster), ESC overworld, R restart

Notes
- This is an original fan-style engine. No Nintendo assets or code are used.
- Procedural, deterministic levels with NSMB-style elements
- SCALED + DOUBLEBUF display; tries vsync if backend supports it.

Tested with pygame 2.5+.
"""

import math, random, sys
import pygame

# -------------------------------------------------
# Config
# -------------------------------------------------
W, H = 960, 540              # Window size (16:9)
TILE = 32                    # Tile size in pixels
FPS  = 60
FIXED_DT = 1.0 / FPS

# Movement/physics (pixel/second-based)
GRAVITY      = 1800.0
JUMP_VEL     = -640.0
MOVE_ACCEL   = 2400.0
MAX_WALK     = 220.0
MAX_RUN      = 300.0
AIR_CONTROL  = 0.75
FRICTION_GND = 0.86
FRICTION_AIR = 0.98

# Tiles
T_EMPTY     = 0
T_GROUND    = 1
T_BLOCK     = 2
T_QBLOCK    = 3
T_PIPE      = 4
T_SLOPE_U   = 5   # Upward slope (left low, right high)
T_SLOPE_D   = 6   # Downward slope (left high, right low)
T_COIN      = 7
T_SPIKE     = 8
T_BRICK     = 9
T_PLATFORM  = 10  # marker (not on grid; platforms are entities)

SOLID_TILES  = {T_GROUND, T_BLOCK, T_QBLOCK, T_PIPE, T_BRICK}
SLOPE_TILES  = {T_SLOPE_U, T_SLOPE_D}
HAZARD_TILES = {T_SPIKE}

# Colors (enhanced NSMB palette)
COLORS = {
    'sky'        : (120, 190, 255),
    'cloud'      : (240, 250, 255),
    'soil'       : (166, 110,  68),
    'grass'      : (100, 200,  80),
    'block'      : (170, 120,  70),
    'qblock'     : (245, 200,  70),
    'outline'    : ( 50,  35,  20),
    'pipe'       : ( 56, 176,  64),
    'pipe_dark'  : ( 32, 112,  40),
    'ui'         : ( 10,  10,  10),
    'ui2'        : (255, 255, 255),
    'path'       : (255, 238, 180),
    'node_locked': (110, 110, 110),
    'node_open'  : (255, 255, 255),
    'node_clear' : (255, 225,  90),
    'water'      : ( 90, 150, 230),
    'land'       : (140, 210,  90),
    'coin'       : (255, 215,   0),
    'coin_shine' : (255, 240, 150),
    'spike'      : (160, 160, 160),
    'brick'      : (200,  76,  12),
    'platform'   : (180, 180, 200),
    'goomba'     : (150,  80,  60),
    'koopa_green': ( 60, 180,  60),
    'koopa_red'  : (220,  60,  60),
    'flag'       : ( 50, 200,  50),
}

# Worlds meta with more distinct themes
WORLD_INFO = [
    ("World 1 — Plains",  (140, 210,  90), "green"),
    ("World 2 — Desert",  (220, 200,  90), "desert"),
    ("World 3 — Beach",   (140, 200, 210), "beach"),
    ("World 4 — Forest",  (110, 180, 110), "forest"),
    ("World 5 — Volcano", (200,  90,  60), "volcano"),
]

# -------------------------------------------------
# Init Pygame
# -------------------------------------------------
pygame.init()
pygame.display.set_caption("NSMB-Style PC Port — Enhanced with NSMB Features")
pygame.event.set_allowed([pygame.QUIT, pygame.KEYDOWN, pygame.KEYUP])

_flags = pygame.SCALED | pygame.DOUBLEBUF
try:
    screen = pygame.display.set_mode((W, H), _flags, vsync=1)
except TypeError:
    screen = pygame.display.set_mode((W, H), _flags)

clock = pygame.time.Clock()
FONT  = pygame.font.SysFont("Arial", 18, bold=True)
FONT2 = pygame.font.SysFont("Arial", 14)

# -------------------------------------------------
# Helpers
# -------------------------------------------------
def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v

def draw_text(surf, text, pos, color=COLORS['ui'], font=FONT):
    surf.blit(font.render(text, True, color), pos)

# -------------------------------------------------
# Entities (Enemies, Coins, Platforms)
# -------------------------------------------------
class Goomba:
    def __init__(self, x, y):
        self.x = float(x); self.y = float(y)
        self.vx = -40.0; self.vy = 0.0
        self.width = 24; self.height = 24
        self.alive = True; self.squish_timer = 0.0
        self.direction = -1
        
    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)
        
    def update(self, dt, level):
        if not self.alive and self.squish_timer <= 0: return True
        if self.squish_timer > 0:
            self.squish_timer -= dt
            return False

        self.vx = 60.0 * self.direction
        
        # edge check
        check_x = self.x + (10 * self.direction)
        check_y = self.y + self.height + 2
        tx, ty  = int(check_x // TILE), int(check_y // TILE)
        if (ty >= level.h_tiles or tx >= level.w_tiles or 
            tx < 0 or level.grid[ty][tx] == T_EMPTY):
            self.direction *= -1
            
        # move
        self.x += self.vx * dt
        self.vy += GRAVITY * 0.8 * dt
        self.y += self.vy * dt
        
        # ground collide
        ground_rect = pygame.Rect(int(self.x), int(self.y + self.height), self.width, 2)
        for s in level.solid_rects_around(ground_rect):
            if ground_rect.colliderect(s) and self.vy >= 0:
                self.y = s.top - self.height; self.vy = 0
                break
                
        # side collide -> turn
        side_rect = pygame.Rect(int(self.x + self.vx * dt * 2), int(self.y), self.width, self.height)
        for s in level.solid_rects_around(side_rect):
            if side_rect.colliderect(s):
                self.direction *= -1; break
        return False
        
    def draw(self, surf, camera_x):
        if not self.alive and self.squish_timer <= 0: return
        rx, ry = int(self.x - camera_x), int(self.y)
        if self.squish_timer > 0:
            height = max(8, int(self.height * (self.squish_timer / 0.3)))
            body = pygame.Rect(rx, ry + self.height - height, self.width, height)
        else:
            body = pygame.Rect(rx, ry, self.width, self.height)
        pygame.draw.rect(surf, COLORS['goomba'], body)
        pygame.draw.ellipse(surf, (80, 40, 30), (rx + 4, ry + 4, 16, 12))
        eye_x = rx + (8 if self.direction > 0 else 12)
        pygame.draw.circle(surf, (255,255,255), (eye_x, ry + 10), 3)

class Koopa:
    def __init__(self, x, y, color="green"):
        self.x = float(x); self.y = float(y)
        self.vx = -60.0; self.vy = 0.0
        self.width = 24; self.height = 32
        self.alive = True; self.shell_mode = False
        self.shell_timer = 0.0; self.direction = -1
        self.color = color
        
    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)
        
    def update(self, dt, level):
        if self.shell_mode and self.shell_timer > 0:
            self.shell_timer -= dt
            if self.shell_timer <= 0:
                self.shell_mode = False; self.height = 32
            return False
            
        self.vx = 80.0 * self.direction if not self.shell_mode else 0.0
        
        # edge detection
        check_x = self.x + (10 * self.direction)
        check_y = self.y + self.height + 2
        tx, ty  = int(check_x // TILE), int(check_y // TILE)
        if (ty >= level.h_tiles or tx >= level.w_tiles or 
            tx < 0 or level.grid[ty][tx] == T_EMPTY):
            self.direction *= -1
            
        self.x += self.vx * dt
        self.vy += GRAVITY * 0.8 * dt
        self.y += self.vy * dt
        
        ground_rect = pygame.Rect(int(self.x), int(self.y + self.height), self.width, 2)
        for s in level.solid_rects_around(ground_rect):
            if ground_rect.colliderect(s) and self.vy >= 0:
                self.y = s.top - self.height; self.vy = 0; break
                
        side_rect = pygame.Rect(int(self.x + self.vx * dt * 2), int(self.y), self.width, self.height)
        for s in level.solid_rects_around(side_rect):
            if side_rect.colliderect(s):
                self.direction *= -1; break
        return False
        
    def draw(self, surf, camera_x):
        rx, ry = int(self.x - camera_x), int(self.y)
        color = COLORS['koopa_green'] if self.color == "green" else COLORS['koopa_red']
        if self.shell_mode:
            shell_rect = pygame.Rect(rx, ry + 16, self.width, 16)
            pygame.draw.ellipse(surf, color, shell_rect)
            pygame.draw.ellipse(surf, (40,100,40) if self.color=="green" else (100,40,40),
                                (rx+4, ry+20, self.width-8, 8))
        else:
            body = pygame.Rect(rx, ry, self.width, self.height)
            pygame.draw.rect(surf, color, body)
            pygame.draw.ellipse(surf, color, (rx, ry+12, self.width, 20))
            pygame.draw.rect(surf, color, (rx+6, ry, 12, 16))

class Coin:
    def __init__(self, x, y):
        self.x = float(x); self.y = float(y)
        self.width = 16; self.height = 16
        self.collected = False; self.bounce_offset = 0.0; self.spin_angle = 0.0
        
    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)
        
    def update(self, dt):
        self.bounce_offset = math.sin(pygame.time.get_ticks() * 0.01) * 3
        self.spin_angle += dt * 10
        
    def draw(self, surf, camera_x):
        if self.collected: return
        rx, ry = int(self.x - camera_x), int(self.y + self.bounce_offset)
        coin_rect = pygame.Rect(rx, ry, self.width, self.height)
        pygame.draw.ellipse(surf, COLORS['coin'], coin_rect)
        pygame.draw.ellipse(surf, COLORS['coin_shine'], (rx+3, ry+3, self.width-6, self.height-6), 1)

class MovingPlatform:
    def __init__(self, x, y, width_tiles, move_range, vertical=False):
        self.x = float(x); self.y = float(y)
        self.width = width_tiles * TILE; self.height = TILE // 2
        self.start_x = x; self.start_y = y
        self.move_range = float(move_range)
        self.vertical = vertical; self.speed = 40.0
        self.direction = 1; self.travel = 0.0
        
    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)
        
    def update(self, dt):
        self.travel += self.direction * self.speed * dt
        if abs(self.travel) >= self.move_range:
            self.direction *= -1
            self.travel = self.move_range * self.direction
        if self.vertical: self.y = self.start_y + self.travel
        else:             self.x = self.start_x + self.travel
            
    def draw(self, surf, camera_x):
        rx, ry = int(self.x - camera_x), int(self.y)
        platform_rect = pygame.Rect(rx, ry, self.width, self.height)
        pygame.draw.rect(surf, COLORS['platform'], platform_rect)
        pygame.draw.rect(surf, COLORS['outline'], platform_rect, 2)
        for i in range(int(self.width // 8)):
            pygame.draw.line(surf, (120,120,140), (rx + i*8, ry+2), (rx + i*8, ry + self.height - 4), 1)

# -------------------------------------------------
# Level generation / rendering
# -------------------------------------------------
class Level:
    def __init__(self, world_idx: int, level_idx: int):
        self.world_idx = world_idx
        self.level_idx = level_idx
        self.theme = WORLD_INFO[world_idx][2]
        self.title = f"W{world_idx+1}-{level_idx+1} ({WORLD_INFO[world_idx][0]})"
        
        # World-specific parameters
        world_params = {
            "green":   {"enemy_density": 0.30, "platforms": True,  "slopes": True },
            "desert":  {"enemy_density": 0.20, "platforms": False, "slopes": False},
            "beach":   {"enemy_density": 0.25, "platforms": True,  "slopes": False},
            "forest":  {"enemy_density": 0.35, "platforms": True,  "slopes": True },
            "volcano": {"enemy_density": 0.40, "platforms": False, "slopes": False},
        }
        self.params = world_params.get(self.theme, world_params["green"])
        
        seed = (world_idx+1) * 1000 + (level_idx+1) * 13
        self.rng = random.Random(seed)

        # Size scaling per world/level
        base_w = 96
        self.w_tiles = base_w + world_idx * 12 + level_idx * 8
        self.h_tiles = 17
        self.pixel_w = self.w_tiles * TILE
        self.pixel_h = self.h_tiles * TILE

        self.grid = [[T_EMPTY for _ in range(self.w_tiles)] for __ in range(self.h_tiles)]
        self.spawn_px = (TILE*2, TILE*8)
        self.flag_rect = pygame.Rect(0, 0, TILE//2, int(TILE*4.5))
        
        # Entities
        self.enemies: list = []
        self.coins:   list = []
        self.platforms: list = []
        
        self._gen()

    # ---------- generation helpers ----------
    def _ground_y(self):  # top surface row
        return self.h_tiles - 3

    def _add_ground(self, g_y:int):
        # base ground fill
        for x in range(self.w_tiles):
            for y in range(g_y, self.h_tiles):
                self.grid[y][x] = T_GROUND

    def _add_plateau(self, x_start:int, top_y:int, length:int):
        """Raise terrain between top_y..ground for a segment (tile units)."""
        g = self._ground_y()
        for xx in range(x_start, min(x_start + length, self.w_tiles)):
            for yy in range(top_y, g):
                if 0 <= yy < self.h_tiles:
                    self.grid[yy][xx] = T_GROUND

    def _add_slope(self, x:int, y:int, upward:bool):
        slope_type = T_SLOPE_U if upward else T_SLOPE_D
        length = self.rng.randint(4, 8)
        for i in range(length):
            xx = x + i
            if xx >= self.w_tiles: break
            yy = y + i if upward else y - i
            if 0 <= yy < self.h_tiles:
                self.grid[yy][xx] = slope_type

    def _add_platform(self, x:int, y:int, width:int, vertical:bool):
        move_range = self.rng.randint(60, 120)
        self.platforms.append(MovingPlatform(x * TILE, y * TILE, width, move_range, vertical))

    def _add_coins(self, x0:int, x1:int, y_base:int, pattern="line"):
        if pattern == "line":
            step = 3
            for x in range(x0, x1, step):
                if self.rng.random() < 0.7:
                    self.coins.append(Coin(x * TILE + 8, y_base * TILE - 20))
        elif pattern == "arc":
            for i in range(5):
                xx = x0 + i * 2
                yy = y_base - abs(i - 2)
                self.coins.append(Coin(xx * TILE + 8, yy * TILE - 20))

    def _add_enemies(self, x0:int, x1:int, g_y:int):
        density = self.params["enemy_density"]
        for x in range(x0, x1, 5):
            if self.rng.random() < density:
                enemy_type = self.rng.choice(["goomba", "koopa"])
                y_pos = (g_y - 1) * TILE
                if enemy_type == "goomba":
                    self.enemies.append(Goomba(x * TILE, y_pos - 24))
                else:
                    color = "red" if self.rng.random() < 0.3 else "green"
                    self.enemies.append(Koopa(x * TILE, y_pos - 32, color))

    def _add_blocks(self, x0:int, x1:int, top_y:int, density:float=0.3):
        """Scatter bricks and ?-blocks above the terrain."""
        for x in range(x0, x1):
            if self.rng.random() < density:
                h = self.rng.choice([top_y-2, top_y-3])
                if 2 <= h < self.h_tiles:
                    self.grid[h][x] = self.rng.choice([T_QBLOCK, T_BRICK, T_BLOCK])

    def _add_pipes(self, x0:int, x1:int, g:int, step:int=24):
        """Place short pipes on the ground between x0..x1 (tile coords)."""
        x = x0 + self.rng.randint(0, 6)
        while x < x1:
            height = self.rng.choice([2, 3, 4])
            for yy in range(g - height, g):
                if 0 <= yy < self.h_tiles and 0 <= x < self.w_tiles:
                    self.grid[yy][x] = T_PIPE
                    if x+1 < self.w_tiles: self.grid[yy][x+1] = T_PIPE
            x += self.rng.randint(max(8, step-6), step+6)

    # ---------- world build ----------
    def _gen(self):
        g = self._ground_y()
        self._add_ground(g)

        # terrain walk in TILE units (bugfix: was pixels before)
        x = 3
        pos = 4
        section = 0
        
        while x < self.w_tiles - 10:
            length = self.rng.randint(8, 16)
            section += 1
            
            delta = self.rng.choice([-2, -1, 0, 0, 1, 2])
            pos = clamp(pos + delta, 2, 10)
            top_y = g - pos
            
            # plateau
            self._add_plateau(x, top_y, length)
            
            # slopes
            if section % 3 == 0 and self.params["slopes"]:
                upward = self.rng.random() < 0.5
                self._add_slope(x + 2, top_y, upward)
            
            # moving platforms
            if section % 4 == 0 and self.params["platforms"]:
                plat_y = top_y - self.rng.randint(3, 6)
                plat_width = self.rng.randint(3, 6)
                vertical = self.rng.random() < 0.3
                self._add_platform(x + 2, plat_y, plat_width, vertical)
                self._add_coins(x + 2, x + 2 + plat_width, plat_y, "line")
            
            # blocks & ?-blocks
            self._add_blocks(x + 2, x + length - 2, top_y, density=0.30)
            
            # coin patterns
            if self.rng.random() < 0.6:
                pattern = self.rng.choice(["line", "arc"])
                self._add_coins(x + 2, x + length - 2, top_y, pattern)
            
            # enemies
            self._add_enemies(x + 2, x + length - 2, g)
            
            # pipes sometimes
            if self.rng.random() < 0.4:
                self._add_pipes(x + 2, x + length - 2, g, step=self.rng.randint(18, 28))
            
            x += length

        # Final flag area
        flag_x_tile = self.w_tiles - 8
        self.flag_rect.topleft = (flag_x_tile * TILE + TILE // 2, (g - 5) * TILE)
        
        for xx in range(flag_x_tile - 3, self.w_tiles):
            for yy in range(g - 1, self.h_tiles):
                self.grid[yy][xx] = T_GROUND
        
        # Victory platform before flag
        self._add_plateau(flag_x_tile - 4, g - 2, 3)

    # ---------- collision helpers ----------
    def solid_rects_around(self, rect: pygame.Rect):
        rects = []
        x0 = clamp(rect.left  // TILE - 2, 0, self.w_tiles - 1)
        x1 = clamp(rect.right // TILE + 2, 0, self.w_tiles - 1)
        y0 = clamp(rect.top   // TILE - 2, 0, self.h_tiles - 1)
        y1 = clamp(rect.bottom// TILE + 2, 0, self.h_tiles - 1)
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                t = self.grid[y][x]
                if t in SOLID_TILES or t in SLOPE_TILES:
                    rects.append(pygame.Rect(x * TILE, y * TILE, TILE, TILE))
        return rects

    def on_head_bump(self, tx:int, ty:int, player):
        """Handle hitting blocks from below."""
        if not (0 <= ty < self.h_tiles and 0 <= tx < self.w_tiles): return
        t = self.grid[ty][tx]
        if t == T_QBLOCK:
            # spawn a coin, turn into used block
            self.grid[ty][tx] = T_BLOCK
            self.coins.append(Coin(tx * TILE + 8, (ty - 1) * TILE + 8))
        elif t == T_BRICK:
            if player.state == "big":
                # break brick
                self.grid[ty][tx] = T_EMPTY
                self.coins.append(Coin(tx * TILE + 8, (ty - 1) * TILE + 8))
            else:
                # small -> just bounce (no state change needed here)
                pass

    # ---------- rendering ----------
    def draw_bg(self, surf, camera_x):
        if self.theme == "desert":
            surf.fill((240, 220, 150))
            pygame.draw.circle(surf, (255, 240, 180), (int(800 - camera_x * 0.1), 80), 60)
        elif self.theme == "beach":
            for y in range(H):
                shade = int(120 + y * 0.3)
                pygame.draw.line(surf, (shade, 190, 255), (0, y), (W, y))
        elif self.theme == "volcano":
            surf.fill((80, 60, 80))
            for i in range(8):
                cx = (i * 180 - camera_x * 0.3) % (self.pixel_w + 400) - 200
                cy = 80 + (i * 30 % 100)
                radius = 40 + math.sin(pygame.time.get_ticks() * 0.001 + i) * 10
                pygame.draw.circle(surf, (60, 60, 70), (int(cx), cy), int(radius))
        else:
            surf.fill(COLORS['sky'])
        if self.theme != "volcano":
            for i in range(14):
                cx = (i * 220 - (camera_x * 0.4) + (i * 37 % 2000)) % (self.pixel_w + 400) - 200
                cy = 60 + (i * 23 % 140)
                pygame.draw.ellipse(surf, COLORS['cloud'], (cx, cy, 140, 40))

    def _draw_ground_tile(self, surf, rx, ry, x, y):
        if self.theme == "desert":
            color, top_color = (210,190,120), (220,200,130)
        elif self.theme == "volcano":
            color, top_color = (120, 60, 40), (140, 70, 50)
        else:
            color, top_color = COLORS['soil'], COLORS['grass']
        r = pygame.Rect(rx, ry, TILE, TILE)
        pygame.draw.rect(surf, color, r)
        # draw top lip if above is not ground
        if y == 0 or self.grid[y-1][x] != T_GROUND:
            pygame.draw.rect(surf, top_color, (rx, ry, TILE, 6))
            pygame.draw.line(surf, COLORS['outline'], (rx, ry+6), (rx+TILE, ry+6))

    def _draw_slope(self, surf, rx, ry, slope_type):
        color = COLORS['soil']
        if slope_type == T_SLOPE_U:
            points = [(rx, ry + TILE), (rx + TILE, ry), (rx + TILE, ry + TILE)]
        else:  # T_SLOPE_D
            points = [(rx, ry), (rx + TILE, ry + TILE), (rx, ry + TILE)]
        pygame.draw.polygon(surf, color, points)
        pygame.draw.polygon(surf, COLORS['outline'], points, 2)

    def _draw_brick(self, surf, rx, ry):
        r = pygame.Rect(rx, ry, TILE, TILE)
        pygame.draw.rect(surf, COLORS['brick'], r)
        pygame.draw.line(surf, (150, 50, 0), (rx, ry + TILE//2), (rx + TILE, ry + TILE//2))
        pygame.draw.line(surf, (150, 50, 0), (rx + TILE//2, ry), (rx + TILE//2, ry + TILE))

    def _draw_block(self, surf, rx, ry):
        r = pygame.Rect(rx, ry, TILE, TILE)
        pygame.draw.rect(surf, COLORS['block'], r)
        pygame.draw.rect(surf, COLORS['outline'], r, 2)

    def _draw_qblock(self, surf, rx, ry):
        r = pygame.Rect(rx, ry, TILE, TILE)
        pygame.draw.rect(surf, COLORS['qblock'], r)
        pygame.draw.rect(surf, COLORS['outline'], r, 2)
        # "?" simplified
        pygame.draw.rect(surf, COLORS['outline'], (rx + 12, ry + 8, 8, 8), 2)
        pygame.draw.rect(surf, COLORS['outline'], (rx + 15, ry + 18, 2, 2))

    def _draw_pipe(self, surf, rx, ry, x, y):
        body = pygame.Rect(rx, ry, TILE, TILE)
        pygame.draw.rect(surf, COLORS['pipe'], body)
        # cap if top of a pipe stack
        if y-1 < 0 or self.grid[y-1][x] != T_PIPE:
            pygame.draw.rect(surf, COLORS['pipe_dark'], (rx-2, ry-6, TILE+4, 8))
            pygame.draw.rect(surf, COLORS['outline'], (rx-2, ry-6, TILE+4, 8), 2)

    def _draw_flag(self, surf, camera_x):
        rx = self.flag_rect.x - int(camera_x)
        ry = self.flag_rect.y
        pole = pygame.Rect(rx, ry, self.flag_rect.w, self.flag_rect.h)
        pygame.draw.rect(surf, COLORS['ui2'], pole)
        # triangle flag
        pygame.draw.polygon(surf, COLORS['flag'], [(rx + self.flag_rect.w, ry + 10),
                                                   (rx + self.flag_rect.w + 24, ry + 22),
                                                   (rx + self.flag_rect.w, ry + 34)])

    def draw_tiles(self, surf, camera_x):
        x0 = clamp(int(camera_x // TILE) - 2, 0, self.w_tiles - 1)
        x1 = clamp(int((camera_x + W) // TILE) + 2, 0, self.w_tiles - 1)
        for y in range(self.h_tiles):
            for x in range(x0, x1 + 1):
                t = self.grid[y][x]
                if t == T_EMPTY: 
                    continue
                rx = x * TILE - int(camera_x)
                ry = y * TILE
                if   t == T_GROUND:  self._draw_ground_tile(surf, rx, ry, x, y)
                elif t == T_BLOCK:   self._draw_block(surf, rx, ry)
                elif t == T_QBLOCK:  self._draw_qblock(surf, rx, ry)
                elif t == T_PIPE:    self._draw_pipe(surf, rx, ry, x, y)
                elif t == T_BRICK:   self._draw_brick(surf, rx, ry)
                elif t in SLOPE_TILES: self._draw_slope(surf, rx, ry, t)
        self._draw_flag(surf, camera_x)

# -------------------------------------------------
# Player
# -------------------------------------------------
class Player:
    def __init__(self, x, y):
        self.x = float(x); self.y = float(y)
        self.vx = 0.0; self.vy = 0.0
        self.on_ground = False; self.facing = 1
        self.width = 20; self.height = 28
        self.state = "small"  # small, big, fire (visual only here)
        self.invincible_timer = 0.0
        self.coins = 0; self.score = 0
        
    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    def move_and_collide(self, level: Level, dt: float, hold_run: bool, input_x: int, jump_pressed: bool):
        max_speed = MAX_RUN if hold_run else MAX_WALK
        accel = MOVE_ACCEL * (AIR_CONTROL if not self.on_ground else 1.0)

        if input_x:
            self.vx += input_x * accel * dt
            self.facing = input_x
        else:
            self.vx *= (FRICTION_GND if self.on_ground else FRICTION_AIR)
            if abs(self.vx) < 3: 
                self.vx = 0

        self.vx = clamp(self.vx, -max_speed, max_speed)

        if jump_pressed and self.on_ground:
            self.vy = JUMP_VEL
            self.on_ground = False

        self.vy += GRAVITY * dt
        if self.vy > 1400: 
            self.vy = 1400

        self._move_with_slope_collision(level, dt)

        if self.invincible_timer > 0:
            self.invincible_timer -= dt

    def _move_with_slope_collision(self, level: Level, dt: float):
        # Horizontal
        new_rect = self.rect.move(self.vx * dt, 0)
        for s in level.solid_rects_around(new_rect):
            if new_rect.colliderect(s):
                if self.vx > 0: new_rect.right = s.left
                elif self.vx < 0: new_rect.left = s.right
                self.vx = 0
        self.x, self.y = new_rect.x, new_rect.y

        # Vertical
        new_rect = self.rect.move(0, self.vy * dt)
        collided = False
        bumped_tile = None
        for s in level.solid_rects_around(new_rect):
            if new_rect.colliderect(s):
                collided = True
                if self.vy > 0:
                    new_rect.bottom = s.top
                    self.on_ground = True
                elif self.vy < 0:
                    # head-bump: convert rect->tile and notify level
                    new_rect.top = s.bottom
                    tx, ty = s.x // TILE, s.y // TILE
                    bumped_tile = (tx, ty)
                self.vy = 0
        if bumped_tile is not None:
            level.on_head_bump(bumped_tile[0], bumped_tile[1], self)
        if not collided:
            self.on_ground = False

        self.x, self.y = new_rect.x, new_rect.y

    def draw(self, surf, camera_x):
        if self.invincible_timer > 0 and int(self.invincible_timer * 10) % 2 == 0:
            return  # flash
        r = self.rect
        rx = r.x - int(camera_x)
        color = (240, 64, 64) if self.state == "small" else (240, 120, 80) if self.state == "big" else (240, 160, 40)
        body = pygame.Rect(rx, r.y, r.w, r.h)
        pygame.draw.rect(surf, color, body)
        pygame.draw.rect(surf, (250, 220, 180), (rx + 4, r.y + 2, 12, 10))
        ex = rx + (10 if self.facing >= 0 else 6)
        pygame.draw.rect(surf, (20, 20, 20), (ex, r.y + 6, 3, 3))

# -------------------------------------------------
# Overworld
# -------------------------------------------------
class OverworldNode:
    def __init__(self, x, y, world, level, radius=20):
        self.x = x; self.y = y
        self.world = world; self.level = level
        self.radius = radius
        self.completed = False
        self.locked = level > 0  # lock beyond first in world by default

class Overworld:
    def __init__(self):
        self.nodes = []
        self.current_node_index = 0
        self.setup_overworld()

    def setup_overworld(self):
        # 5 worlds × 3 levels each (linear strip with gentle offsets)
        for world in range(5):
            for level in range(3):
                x = 110 + world * 170
                y = 220 + level * 72
                node = OverworldNode(x, y, world, level)
                if world == 0 and level == 0:
                    node.locked = False
                self.nodes.append(node)

    def set_cleared(self, index):
        if 0 <= index < len(self.nodes):
            self.nodes[index].completed = True
            # unlock next in same world
            if index + 1 < len(self.nodes):
                current = self.nodes[index]
                next_node = self.nodes[index + 1]
                if next_node.world == current.world:
                    next_node.locked = False

# -------------------------------------------------
# Game
# -------------------------------------------------
class Game:
    def __init__(self):
        self.state = 'OVERWORLD'
        self.overworld = Overworld()
        self.level: Level | None = None
        self.player: Player | None = None
        self.camera_x = 0
        self.level_index_linear = 0
        self._flash_timer = 0.0
        self.lives = 3
        self.total_coins = 0

    # --- high-level tick (fixed-step) ---
    def tick(self, dt: float, events):
        if self.state == 'LEVEL':
            self.update_level(dt, events)
        else:
            self.update_overworld(dt, events)

    # --- state transitions ---
    def start_level(self, index:int):
        node = self.overworld.nodes[index]
        if node.locked:  # ignore safety
            return
        self.level = Level(node.world, node.level)
        self.player = Player(self.level.spawn_px[0], self.level.spawn_px[1])
        self.camera_x = 0
        self.level_index_linear = index
        self.state = 'LEVEL'

    def return_to_overworld(self, cleared:bool):
        if cleared:
            self.overworld.set_cleared(self.level_index_linear)
            self._flash_timer = 0.8
        self.level = None
        self.player = None
        self.state = 'OVERWORLD'

    # --- OVERWORLD ---
    def update_overworld(self, dt, events):
        # input
        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_RIGHT, pygame.K_d):
                    self.overworld.current_node_index = clamp(self.overworld.current_node_index + 1, 0, len(self.overworld.nodes)-1)
                elif e.key in (pygame.K_LEFT, pygame.K_a):
                    self.overworld.current_node_index = clamp(self.overworld.current_node_index - 1, 0, len(self.overworld.nodes)-1)
                elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    idx = self.overworld.current_node_index
                    if not self.overworld.nodes[idx].locked:
                        self.start_level(idx)
                elif e.key == pygame.K_ESCAPE:
                    # quit from overworld
                    pygame.event.post(pygame.event.Event(pygame.QUIT))

        # draw bg
        screen.fill((170, 205, 255))
        # land strip
        pygame.draw.rect(screen, COLORS['land'], (0, H-120, W, 120))

        # path lines & nodes
        for i, n in enumerate(self.overworld.nodes):
            if i+1 < len(self.overworld.nodes):
                n2 = self.overworld.nodes[i+1]
                pygame.draw.line(screen, COLORS['path'], (n.x, n.y), (n2.x, n2.y), 4)

        for i, n in enumerate(self.overworld.nodes):
            fill = COLORS['node_locked'] if n.locked else (COLORS['node_clear'] if n.completed else COLORS['node_open'])
            pygame.draw.circle(screen, fill, (n.x, n.y), n.radius)
            pygame.draw.circle(screen, COLORS['outline'], (n.x, n.y), n.radius, 2)
            draw_text(screen, f"W{n.world+1}-{n.level+1}", (n.x - 20, n.y - 42), COLORS['ui'], FONT2)

        # selection highlight
        cur = self.overworld.nodes[self.overworld.current_node_index]
        pygame.draw.circle(screen, (0,0,0), (cur.x, cur.y), cur.radius + 6, 2)

        # UI
        world_name, _, _theme = WORLD_INFO[cur.world]
        draw_text(screen, f"{world_name}", (16, 12))
        draw_text(screen, "←/→ select   Enter: play   ESC: quit", (16, 40), COLORS['ui'], FONT2)

        # flash when clearing
        if self._flash_timer > 0:
            self._flash_timer -= dt
            alpha = int(180 * max(0.0, self._flash_timer / 0.8))
            s = pygame.Surface((W, H), pygame.SRCALPHA)
            s.fill((255, 255, 255, alpha))
            screen.blit(s, (0,0))

    # --- LEVEL ---
    def update_level(self, dt, events):
        assert self.level and self.player
        lvl, ply = self.level, self.player
        
        # events
        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    self.return_to_overworld(False)
                elif e.key == pygame.K_r:
                    self.start_level(self.level_index_linear)

        # input state
        keys = pygame.key.get_pressed()
        input_x = (1 if (keys[pygame.K_RIGHT] or keys[pygame.K_d]) else 0) + (-1 if (keys[pygame.K_LEFT] or keys[pygame.K_a]) else 0)
        hold_run = keys[pygame.K_x]
        jump_pressed = keys[pygame.K_SPACE] or keys[pygame.K_z]

        # update entities
        lvl.enemies = [e for e in lvl.enemies if not e.update(dt, lvl)]
        for coin in lvl.coins: coin.update(dt)
        for platform in lvl.platforms: platform.update(dt)

        # move player
        ply.move_and_collide(lvl, dt, hold_run, input_x, jump_pressed)

        # camera
        target = ply.x - (W//2 - ply.width//2)
        self.camera_x = clamp(target, 0, max(0, lvl.pixel_w - W))

        # goal
        if ply.rect.colliderect(lvl.flag_rect):
            self.return_to_overworld(True); return

        # DRAW
        lvl.draw_bg(screen, self.camera_x)
        lvl.draw_tiles(screen, self.camera_x)

        for platform in lvl.platforms: platform.draw(screen, self.camera_x)
        for enemy in lvl.enemies: enemy.draw(screen, self.camera_x)
        for coin in lvl.coins: coin.draw(screen, self.camera_x)
        ply.draw(screen, self.camera_x)

        # HUD
        draw_text(screen, f"{lvl.title}", (12, 10))
        draw_text(screen, f"Coins: {self.total_coins}   Lives: {self.lives}", (W - 260, 10))
        draw_text(screen, "ESC: overworld  |  R: restart  |  ←/→ move  |  Z/SPACE jump  |  X run", (12, 34), COLORS['ui'], FONT2)

        # entity collisions after draw (so feedback feels immediate)
        self._handle_entity_collisions()

    def _handle_entity_collisions(self):
        lvl, ply = self.level, self.player
        if not lvl or not ply: return

        # coins
        for coin in lvl.coins[:]:
            if not coin.collected and ply.rect.colliderect(coin.rect):
                coin.collected = True
                self.total_coins += 1
                ply.score += 200
                if self.total_coins >= 100:
                    self.total_coins = 0; self.lives += 1
                
        # enemies
        for enemy in lvl.enemies[:]:
            if ply.rect.colliderect(enemy.rect):
                if ply.vy > 0 and ply.rect.bottom <= enemy.rect.centery + 4:
                    if isinstance(enemy, Goomba):
                        enemy.alive = False; enemy.squish_timer = 0.3
                    elif isinstance(enemy, Koopa):
                        if not enemy.shell_mode:
                            enemy.shell_mode = True; enemy.shell_timer = 5.0; enemy.height = 16
                    ply.vy = JUMP_VEL * 0.7; ply.score += 100
                else:
                    if ply.state == "small":
                        self.lives -= 1
                        if self.lives <= 0:
                            self.return_to_overworld(False)
                        else:
                            ply.x, ply.y = lvl.spawn_px
                            ply.vx = ply.vy = 0
                    else:
                        ply.state = "small"
                        ply.invincible_timer = 2.0

        # moving platforms (one-way from above)
        for platform in lvl.platforms:
            if (ply.vy > 0 and 
                ply.rect.move(0, 2).colliderect(platform.rect) and
                ply.rect.bottom <= platform.rect.top + 5):
                ply.y = platform.rect.top - ply.height
                ply.vy = 0
                ply.on_ground = True
                ply.x += platform.speed * platform.direction * FIXED_DT

# -------------------------------------------------
# Main
# -------------------------------------------------
def main():
    game = Game()
    running = True
    accumulator = 0.0

    while running:
        dt = min(clock.tick(FPS) / 1000.0, 0.05)
        accumulator += dt

        # gather events once per frame
        events = []
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            else:
                events.append(e)

        # fixed-step updates; only process input on first step to avoid repeats
        first_step = True
        while accumulator >= FIXED_DT:
            game.tick(FIXED_DT, events if first_step else ())
            accumulator -= FIXED_DT
            first_step = False

        pygame.display.flip()

    pygame.quit()
    sys.exit(0)

if __name__ == '__main__':
    main()
