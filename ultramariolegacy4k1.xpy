# Program.py
# -----------------------------------------------------------------------------
# Ultra mario legacy 2d bros [a fan mod of b3313 smb1]
# (Original NES‑style homage — not a ROM/mod, no Nintendo IP used.)
# FlamesCo‑ChatGPT‑OS build. Uses your vibe_mario.py palette if present.
#
# This project is an original fan‑made platformer that *does not* contain or
# reuse Nintendo code, assets, or level layouts. The "fan mod" wording is
# thematic only; this is a standalone game for educational/non‑commercial use.
#
# Controls:
#   Left/Right or A/D = Move
#   Z / Space         = Jump
#   P                 = Pause (in‑level)
#   Esc               = Quit
#
# Requirements:
#   pip install pygame
#
# Palette vibe:
#   If a local "vibe_mario.py" exists, we detect its color constants
#   SKY / GROUND / BLOCK / PLAYER and apply them here to match your vibe.
# -----------------------------------------------------------------------------
import os, sys, math, random, ast, re
import pygame

# ------------------------- Virtual "NES-like" setup --------------------------
VW, VH = 256, 240         # NES‑ish internal resolution
SCALE  = 3                # scale to window size (256x240)*SCALE
TILE   = 16               # tile size
W, H   = VW*SCALE, VH*SCALE

TITLE = "Ultra mario legacy 2d bros [a fan mod of b3313 smb1] — NES‑Vibe (Original)"
TOTAL_LEVELS = 32
LEVELS_PER_WORLD = 4
WORLDS = TOTAL_LEVELS // LEVELS_PER_WORLD

# Default palette (soft retro). If vibe_mario.py exists, override key colors.
PALETTE = {
    'sky'   : (138, 235, 244),
    'ground': (155, 118,  83),
    'block' : (255, 200,  50),
    'player': (255,  80,  80),
    'white' : (240, 240, 240),
    'dark'  : ( 30,  30,  50),
    'shadow': ( 90,  72,  45),
    'accent': ( 64, 120, 255),
    'grass' : ( 67, 160,  71),
    'hill'  : ( 52, 132,  97),
}

def _safe_literal_tuple(s):
    try:
        v = ast.literal_eval(s.strip())
        if isinstance(v, (tuple, list)) and len(v) == 3:
            return tuple(int(max(0, min(255, c))) for c in v)
    except Exception:
        pass
    return None

def load_vibe_palette():
    """If vibe_mario.py is present, reuse its four key colors to honor the vibe."""
    try:
        with open('vibe_mario.py', 'r', encoding='utf-8') as f:
            code = f.read()
        for name, key in [('SKY','sky'), ('GROUND','ground'),
                          ('BLOCK','block'), ('PLAYER','player')]:
            m = re.search(rf'^\s*{name}\s*=\s*(\([^)]+\))', code, flags=re.MULTILINE)
            if m:
                tup = _safe_literal_tuple(m.group(1))
                if tup: PALETTE[key] = tup
    except Exception:
        # It's fine if the file isn't there — we keep defaults.
        pass

load_vibe_palette()

# ------------------------------ Pygame bootstrap ----------------------------
pygame.init()
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption(TITLE)
clock = pygame.time.Clock()
vpix = pygame.Surface((VW, VH))

# Fonts
def get_font(size=8):
    try:
        return pygame.font.Font(None, size)
    except Exception:
        return pygame.font.SysFont("Arial", size)

FONT8  = get_font(8)
FONT12 = get_font(12)
FONT16 = get_font(16)

# ----------------------------- Utility helpers ------------------------------
def draw_text(surf, text, x, y, color, font, center=False):
    img = font.render(text, True, color)
    r = img.get_rect()
    if center: r.center = (x, y)
    else: r.topleft = (x, y)
    surf.blit(img, r)

def clamp(v, lo, hi):
    return lo if v < lo else (hi if v > hi else v)

def world_stage(level_idx):
    w = (level_idx-1)//LEVELS_PER_WORLD + 1
    s = (level_idx-1)%LEVELS_PER_WORLD + 1
    return w, s

# Nearby-solid collection window (in tiles)
NEAR_TILES = 5

# ------------------------------- Level system -------------------------------
SOLIDS = {'X','B','#'}      # Ground, block, hard tile
GOAL = 'E'                  # Level exit bell

class Level:
    """Deterministically generated level given level_id (1..32)."""
    def __init__(self, level_id):
        self.level_id = level_id
        self.world, self.stage = world_stage(level_id)
        self.rows = VH // TILE

        # Difficulty and size scale by world
        difficulty = self.world
        random.seed(424242 + level_id*99991)

        base_cols = 180 + difficulty*20 + random.randint(0, 24)
        self.cols = min(320, base_cols)

        self.grid = [[' ' for _ in range(self.cols)] for _ in range(self.rows)]
        self.spawn = (2*TILE, 12*TILE)
        self.stars = []       # list of rect for pickups
        self.enemies = []     # list of Slime
        self.goal_rect = None

        self._build(difficulty, random)

    def _gnd_row(self):
        return self.rows - 2

    def _add_enemy(self, tx, ty):
        world_x = tx*TILE
        world_y = ty*TILE - 2
        self.enemies.append(Slime(world_x, world_y))

    def fill_ground(self, x0, x1, height=1):
        g = self._gnd_row()
        for x in range(x0, min(x1, self.cols)):
            for h in range(height):
                r = g - h
                if 0 <= r < self.rows and 0 <= x < self.cols:
                    self.grid[r][x] = 'X'
            for r in range(g+1, self.rows):
                self.grid[r][x] = 'X'

    def clear_gap(self, x0, width):
        g = self._gnd_row()
        for x in range(x0, min(x0+width, self.cols)):
            for r in range(g, self.rows):
                self.grid[r][x] = ' '

    def place_block_line(self, x0, count, y):
        for i in range(count):
            x = x0 + i
            if 0 <= x < self.cols and 0 <= y < self.rows:
                self.grid[y][x] = 'B'

    def place_star_cell(self, x, y):
        if 0 <= x < self.cols and 0 <= y < self.rows:
            self.grid[y][x] = 'C'

    def set_goal(self, x):
        g = self._gnd_row()
        x = clamp(x, 8, self.cols-4)
        for r in range(g-4, g+1):
            if 0 <= r < self.rows and 0 <= x < self.cols:
                self.grid[r][x] = '#'
        self.grid[g-5][x] = 'E'
        self.goal_rect = pygame.Rect(x*TILE, (g-6)*TILE, TILE, 6*TILE)

    def set_spawn(self, x, y):
        self.spawn = (x*TILE, y*TILE)

    def _build(self, difficulty, rng):
        # Base ground
        self.fill_ground(0, self.cols, height=1)

        # Rolling mounds (varies per world)
        i = 8
        while i < self.cols-24:
            w = rng.randint(6, 12)
            h = 1 + rng.randint(0, 1 + (difficulty>3))
            self.fill_ground(i, i+w, height=1+h)
            i += w + rng.randint(6, 14)

        # Gaps tuned to be jumpable: width <= 4 tiles, with helper blocks
        n_gaps = clamp(1 + difficulty, 1, 6)
        start_safe = 24
        end_safe = 16
        gap_spots = []
        for _ in range(n_gaps*2):  # try a few times to get non-overlapping gaps
            gx = rng.randint(start_safe, self.cols - end_safe - 6)
            if all(abs(gx - other) > 10 for other in gap_spots):
                gap_spots.append(gx)
                if len(gap_spots) >= n_gaps:
                    break
        for gx in gap_spots:
            width = rng.randint(2, 2 + min(2, difficulty))  # 2..4
            self.clear_gap(gx, width)
            by = self._gnd_row() - (3 + rng.randint(0, 2 + (difficulty>5)))
            self.place_block_line(gx-1, width+2, by)

        # Floating blocks & star arcs
        for _ in range(3 + difficulty):
            bx = rng.randint(12, self.cols-20)
            by = self._gnd_row() - rng.randint(4, 7)
            self.place_block_line(bx, rng.randint(2, 4), by)
            # place stars above some blocks
            if rng.random() < 0.6:
                for i in range(rng.randint(2, 5)):
                    self.place_star_cell(bx+i, by-2 - (i%2==0))

        # Random "stairs" near late section
        for _ in range(2 + difficulty//2):
            sx = rng.randint(self.cols//2, self.cols-12)
            sh = rng.randint(1, 3 + (difficulty>6))
            self.fill_ground(sx, sx + rng.randint(3, 7), height=1+sh)

        # Enemies along flats (avoid spawn/goal vicinity)
        for _ in range(4 + difficulty*2):
            ex = rng.randint(10, self.cols-12)
            ey = self._gnd_row()-1
            # don't place inside gaps
            if self.grid[ey+1][ex] == 'X':
                self._add_enemy(ex, ey)

        # Place star clusters here and there
        for _ in range(3 + difficulty):
            cx = rng.randint(8, self.cols-10)
            cy = self._gnd_row()-rng.randint(5, 8)
            for i in range(rng.randint(2, 5)):
                self.place_star_cell(cx+i, cy + (i%2))

        # Player spawn & goal
        self.set_spawn(2, self._gnd_row()-4)
        self.set_goal(self.cols-6)

        # Bake stars rects
        self.stars = []
        for y in range(self.rows):
            for x in range(self.cols):
                if self.grid[y][x] == 'C':
                    self.stars.append(pygame.Rect(x*TILE+3, y*TILE+3, TILE-6, TILE-6))

    def solid_rects_near(self, rect):
        cx = rect.centerx // TILE
        cy = rect.centery // TILE
        rlist = []
        for ty in range(int(cy-NEAR_TILES), int(cy+NEAR_TILES)+1):
            if 0 <= ty < self.rows:
                row = self.grid[ty]
                for tx in range(int(cx-NEAR_TILES), int(cx+NEAR_TILES)+1):
                    if 0 <= tx < self.cols and row[tx] in SOLIDS:
                        rlist.append(pygame.Rect(tx*TILE, ty*TILE, TILE, TILE))
        return rlist

    def draw_bg(self, surf, camx):
        # World‑dependent hue tweak for variety
        surf.fill(PALETTE['sky'])
        base_y = VH - 56
        # Two parallax layers
        for i in range(7):
            hx = int((-camx*0.3 + i*120) % (VW+160)) - 80
            pygame.draw.ellipse(surf, PALETTE['hill'], (hx, base_y, 160, 90))
        pygame.draw.rect(surf, PALETTE['grass'], (0, VH-32, VW, 10))

    def draw_tiles(self, surf, camx):
        gcol = PALETTE['ground']
        bcol = PALETTE['block']
        shad = PALETTE['shadow']
        for y in range(self.rows):
            for x in range(self.cols):
                ch = self.grid[y][x]
                if ch in SOLIDS or ch in (GOAL,):
                    rx = x*TILE - camx
                    ry = y*TILE
                    pygame.draw.rect(surf, gcol if ch=='X' else bcol, (rx, ry, TILE, TILE))
                    pygame.draw.line(surf, shad, (rx, ry+TILE-1), (rx+TILE, ry+TILE-1))
                    pygame.draw.line(surf, shad, (rx+TILE-1, ry), (rx+TILE-1, ry+TILE))
                if ch == 'E':
                    rx = x*TILE - camx
                    ry = y*TILE
                    pygame.draw.rect(surf, PALETTE['accent'], (rx+4, ry+4, TILE-8, TILE-8))
                    pygame.draw.line(surf, PALETTE['white'], (rx+4, ry+5), (rx+TILE-4, ry+5))

    def draw_stars(self, surf, camx):
        for r in self.stars:
            rx = r.x - camx
            if -TILE <= rx <= VW:
                cx, cy = rx + r.w//2, r.y + r.h//2
                pygame.draw.rect(surf, (255, 235, 100), (cx-2, cy-2, 4, 4))
                pygame.draw.line(surf, PALETTE['white'], (cx-3, cy), (cx+3, cy))
                pygame.draw.line(surf, PALETTE['white'], (cx, cy-3), (cx, cy+3))

# --------------------------------- Entities ---------------------------------
GRAVITY     = 0.25
JUMP_VEL    = -5.6
MOVE_ACC    = 0.35
FRICTION    = 0.85
MAX_RUN_SPD = 1.9
KNOCKBACK   = 2.0

class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 12, 14)
        self.x, self.y = float(x), float(y)
        self.vx, self.vy = 0.0, 0.0
        self.on_ground = False
        self.facing = 1
        self.stars = 0
        self.lives = 3
        self.invuln = 0

    def update(self, level, keys):
        ax = 0.0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:  ax -= MOVE_ACC
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: ax += MOVE_ACC
        if ax == 0:
            self.vx *= FRICTION
        else:
            self.vx = clamp(self.vx + ax, -MAX_RUN_SPD, MAX_RUN_SPD)
            self.facing = 1 if self.vx >= 0 else -1

        if (keys[pygame.K_z] or keys[pygame.K_SPACE]) and self.on_ground:
            self.vy = JUMP_VEL
            self.on_ground = False

        self.vy = min(self.vy + GRAVITY, 6)

        self._move(level, self.vx, 0)
        self.on_ground = False
        self._move(level, 0, self.vy)

        if self.invuln > 0:
            self.invuln -= 1

    def _move(self, level, dx, dy):
        self.x += dx; self.y += dy
        self.rect.x = int(self.x); self.rect.y = int(self.y)
        for s in level.solid_rects_near(self.rect):
            if self.rect.colliderect(s):
                if dx > 0:
                    self.rect.right = s.left;  self.x = self.rect.x; self.vx = 0
                elif dx < 0:
                    self.rect.left  = s.right; self.x = self.rect.x; self.vx = 0
                if dy > 0:
                    self.rect.bottom = s.top;  self.y = self.rect.y; self.vy = 0; self.on_ground = True
                elif dy < 0:
                    self.rect.top = s.bottom;  self.y = self.rect.y; self.vy = 0

    def draw(self, surf, camx):
        rx, ry = self.rect.x - camx, self.rect.y
        if self.invuln and (self.invuln // 3) % 2 == 0:
            return
        pygame.draw.rect(surf, PALETTE['player'], (rx, ry, self.rect.w, self.rect.h))
        if self.facing >= 0:
            pygame.draw.polygon(surf, PALETTE['dark'], [(rx+2, ry), (rx+6, ry), (rx+4, ry-3)])
            pygame.draw.polygon(surf, PALETTE['dark'], [(rx+8, ry), (rx+12, ry), (rx+10, ry-3)])
        else:
            pygame.draw.polygon(surf, PALETTE['dark'], [(rx+1, ry), (rx+5, ry), (rx+3, ry-3)])
            pygame.draw.polygon(surf, PALETTE['dark'], [(rx+7, ry), (rx+11, ry), (rx+9, ry-3)])

class Slime:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 12, 12)
        self.x, self.y = float(x), float(y)
        self.vx, self.vy = random.choice([-0.7, 0.7]), 0.0
        self.on_ground = False
        self.alive = True

    def update(self, level):
        if not self.alive: return
        self.vy = min(self.vy + GRAVITY, 6)
        self._move(level, self.vx, 0)
        self.on_ground = False
        self._move(level, 0, self.vy)

        ahead_x = self.rect.centerx + (8 if self.vx > 0 else -8)
        ahead_y = self.rect.bottom + 1
        tx = ahead_x // TILE; ty = ahead_y // TILE
        if 0 <= ty < level.rows and 0 <= tx < level.cols:
            if level.grid[ty][tx] not in SOLIDS:
                self.vx *= -1

    def _move(self, level, dx, dy):
        self.x += dx; self.y += dy
        self.rect.x = int(self.x); self.rect.y = int(self.y)
        for s in level.solid_rects_near(self.rect):
            if self.rect.colliderect(s):
                if dx > 0:
                    self.rect.right = s.left;  self.x = self.rect.x; self.vx *= -1
                elif dx < 0:
                    self.rect.left  = s.right; self.x = self.rect.x; self.vx *= -1
                if dy > 0:
                    self.rect.bottom = s.top;  self.y = self.rect.y; self.vy = 0; self.on_ground = True
                elif dy < 0:
                    self.rect.top = s.bottom;  self.y = self.rect.y; self.vy = 0

    def draw(self, surf, camx):
        if not self.alive: return
        rx, ry = self.rect.x - camx, self.rect.y
        pygame.draw.rect(surf, (60, 180, 60), (rx, ry, self.rect.w, self.rect.h))
        pygame.draw.line(surf, (0,0,0), (rx+3, ry+4), (rx+5, ry+4))
        pygame.draw.line(surf, (0,0,0), (rx+7, ry+4), (rx+9, ry+4))

# --------------------------------- Game State --------------------------------
STATE_MENU      = 0
STATE_PLAY      = 1
STATE_PAUSE     = 2
STATE_LEVEL_END = 3
STATE_LOSE      = 4
STATE_HELP      = 5
STATE_SELECT    = 6
STATE_GAMECLEAR = 7

class Game:
    def __init__(self):
        self.current_level = 1
        self.level = Level(self.current_level)
        sx, sy = self.level.spawn
        self.player = Player(sx, sy)
        self.enemies = self.level.enemies
        self.camx = 0
        self.state = STATE_MENU
        self.time_left = 300
        self._time_accum = 0.0

    def load_level(self, level_idx):
        self.current_level = int(clamp(level_idx, 1, TOTAL_LEVELS))
        self.level = Level(self.current_level)
        sx, sy = self.level.spawn
        self.player = Player(sx, sy)
        self.enemies = self.level.enemies
        self.camx = 0
        self.time_left = 300
        self._time_accum = 0.0

    def reset_game(self):
        self.load_level(1)
        self.player.lives = 3

    def update_camera(self):
        target = self.player.rect.centerx - VW//2
        self.camx = int(clamp(target, 0, self.level.cols*TILE - VW))

    def update_play(self, dt, keys):
        self._time_accum += dt
        if self._time_accum >= 1.0:
            self.time_left = max(0, self.time_left - 1)
            self._time_accum -= 1.0
            if self.time_left == 0:
                self.state = STATE_LOSE

        self.player.update(self.level, keys)

        # Stars pickup
        new_stars = []
        for r in self.level.stars:
            if self.player.rect.colliderect(r):
                self.player.stars += 1
            else:
                new_stars.append(r)
        self.level.stars = new_stars

        # Enemies
        for en in self.enemies:
            en.update(self.level)

        # Interactions
        for en in self.enemies:
            if not en.alive: continue
            if self.player.rect.colliderect(en.rect):
                if self.player.vy > 0 and self.player.rect.bottom - en.rect.top < 10:
                    en.alive = False
                    self.player.vy = JUMP_VEL * 0.6
                    self.player.on_ground = False
                else:
                    if self.player.invuln == 0:
                        self.player.lives -= 1
                        self.player.invuln = 90
                        self.player.vx = -KNOCKBACK if self.player.rect.centerx < en.rect.centerx else KNOCKBACK
                        self.player.vy = JUMP_VEL * 0.6
                        if self.player.lives < 0:
                            self.state = STATE_LOSE

        if self.level.goal_rect and self.player.rect.colliderect(self.level.goal_rect):
            if self.current_level >= TOTAL_LEVELS:
                self.state = STATE_GAMECLEAR
            else:
                self.state = STATE_LEVEL_END

        self.update_camera()

        if self.player.rect.top > VH + 40:
            self.player.lives -= 1
            if self.player.lives < 0:
                self.state = STATE_LOSE
            else:
                sx, sy = self.level.spawn
                self.player.x, self.player.y = sx, sy
                self.player.rect.topleft = (int(sx), int(sy))
                self.player.vx = self.player.vy = 0
                self.camx = 0

    # ---------------------------- Drawing routines ---------------------------
    def draw_hud(self, surf):
        w, s = world_stage(self.current_level)
        draw_text(surf, f"LIVES {max(0,self.player.lives)}", 8, 8, PALETTE['white'], FONT12)
        draw_text(surf, f"STARS {self.player.stars:03d}", 100, 8, PALETTE['white'], FONT12)
        draw_text(surf, f"W{w}-{s}", 200, 8, PALETTE['white'], FONT12)
        draw_text(surf, f"TIME {self.time_left:03d}", VW-90, 8, PALETTE['white'], FONT12)

    def draw_menu(self, surf, sel_idx):
        self.level.draw_bg(surf, 0)
        title = "ULTRA MARIO LEGACY 2D BROS"
        subtitle = "[fan‑mod‑style homage — original, not a ROM/mod]"
        draw_text(surf, title, VW//2, 56, PALETTE['dark'], FONT16, center=True)
        draw_text(surf, subtitle, VW//2, 74, PALETTE['dark'], FONT8, center=True)

        items = ["Start Game", "Level Select", "How to Play", "Quit"]
        for i, it in enumerate(items):
            col = PALETTE['accent'] if i == sel_idx else PALETTE['white']
            draw_text(surf, it, VW//2, 120 + i*18, col, FONT12, center=True)

        draw_text(surf, "Palette source: vibe_mario.py (if present)", VW//2, VH-20, PALETTE['dark'], FONT8, center=True)

        pygame.draw.rect(surf, PALETTE['ground'], (0, VH-16, VW, 16))
        pygame.draw.rect(surf, PALETTE['player'], (VW//2-6, VH-22, 12, 14))

    def draw_help(self, surf):
        self.level.draw_bg(surf, 0)
        lines = [
            "Left/Right (A/D): Move",
            "Z or Space: Jump",
            "P: Pause",
            "Goal: ring the bell at the far right.",
            "Collect stars, stomp slimes, avoid pits.",
            "All assets & layouts are original; no Nintendo IP."
        ]
        for i, ln in enumerate(lines):
            draw_text(surf, ln, VW//2, 90 + i*16, PALETTE['white'], FONT12, center=True)
        draw_text(surf, "Press Enter to return", VW//2, VH-26, PALETTE['accent'], FONT12, center=True)

    def draw_play(self, surf):
        self.level.draw_bg(surf, self.camx)
        self.level.draw_tiles(surf, self.camx)
        self.level.draw_stars(surf, self.camx)
        for en in self.enemies:
            en.draw(surf, self.camx)
        self.player.draw(surf, self.camx)
        self.draw_hud(surf)

    def draw_level_end(self, surf):
        w, s = world_stage(self.current_level)
        self.level.draw_bg(surf, 0)
        draw_text(surf, f"LEVEL W{w}-{s} CLEAR!", VW//2, 80, PALETTE['white'], FONT16, center=True)
        draw_text(surf, f"Stars: {self.player.stars}", VW//2, 110, PALETTE['white'], FONT12, center=True)
        draw_text(surf, f"Time:  {self.time_left}", VW//2, 126, PALETTE['white'], FONT12, center=True)
        draw_text(surf, "Press Enter for next level", VW//2, 160, PALETTE['accent'], FONT12, center=True)

    def draw_game_clear(self, surf):
        self.level.draw_bg(surf, 0)
        draw_text(surf, "ALL 32 LEVELS CLEARED!", VW//2, 90, PALETTE['white'], FONT16, center=True)
        draw_text(surf, "Thanks for playing!", VW//2, 116, PALETTE['white'], FONT12, center=True)
        draw_text(surf, "Press Enter for Menu", VW//2, 150, PALETTE['accent'], FONT12, center=True)

    def draw_lose(self, surf):
        self.level.draw_bg(surf, 0)
        draw_text(surf, "GAME OVER", VW//2, 100, PALETTE['white'], FONT16, center=True)
        draw_text(surf, "Press Enter for Menu", VW//2, 140, PALETTE['accent'], FONT12, center=True)

    def draw_level_select(self, surf, sel_level):
        # Grid: WORLDS columns, 4 rows (stages)
        self.level.draw_bg(surf, 0)
        draw_text(surf, "LEVEL SELECT", VW//2, 42, PALETTE['white'], FONT16, center=True)
        cell_w, cell_h = 24, 18
        margin_x, margin_y = 20, 70
        gap_x, gap_y = 6, 6
        for w in range(1, WORLDS+1):
            for s in range(1, LEVELS_PER_WORLD+1):
                idx = (w-1)*LEVELS_PER_WORLD + s
                cx = margin_x + (w-1)*(cell_w+gap_x)
                cy = margin_y + (s-1)*(cell_h+gap_y)
                rect = pygame.Rect(cx, cy, cell_w, cell_h)
                col = (80,80,100)
                pygame.draw.rect(surf, col, rect)
                if idx == sel_level:
                    pygame.draw.rect(surf, PALETTE['accent'], rect, 2)
                t = f"{w}-{s}"
                draw_text(surf, t, rect.centerx, rect.centery, PALETTE['white'], FONT12, center=True)
        draw_text(surf, "Arrows: move  •  Enter: play  •  Esc: back", VW//2, VH-22, PALETTE['white'], FONT12, center=True)

# --------------------------------- Main loop ---------------------------------
def main():
    game = Game()
    menu_idx = 0
    menu_items = ["Start Game", "Level Select", "How to Play", "Quit"]
    sel_level = 1

    paused = False
    running = True
    while running:
        dt = clock.tick(60) / 1000.0

        keys = pygame.key.get_pressed()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    if game.state == STATE_SELECT:
                        game.state = STATE_MENU
                    else:
                        running = False

                # Menu
                if game.state == STATE_MENU:
                    if e.key in (pygame.K_UP, pygame.K_w):
                        menu_idx = (menu_idx - 1) % len(menu_items)
                    elif e.key in (pygame.K_DOWN, pygame.K_s):
                        menu_idx = (menu_idx + 1) % len(menu_items)
                    elif e.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z):
                        choice = menu_items[menu_idx]
                        if choice == "Start Game":
                            game.reset_game()
                            game.state = STATE_PLAY
                        elif choice == "Level Select":
                            game.state = STATE_SELECT
                        elif choice == "How to Play":
                            game.state = STATE_HELP
                        else:
                            running = False

                elif game.state == STATE_HELP:
                    if e.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z):
                        game.state = STATE_MENU

                elif game.state == STATE_SELECT:
                    if e.key in (pygame.K_LEFT, pygame.K_a):
                        sel_level = max(1, sel_level - LEVELS_PER_WORLD)
                    elif e.key in (pygame.K_RIGHT, pygame.K_d):
                        sel_level = min(TOTAL_LEVELS, sel_level + LEVELS_PER_WORLD)
                    elif e.key in (pygame.K_UP, pygame.K_w):
                        if (sel_level-1) % LEVELS_PER_WORLD != 0:
                            sel_level -= 1
                    elif e.key in (pygame.K_DOWN, pygame.K_s):
                        if (sel_level-1) % LEVELS_PER_WORLD != LEVELS_PER_WORLD-1:
                            sel_level += 1
                    elif e.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z):
                        game.load_level(sel_level)
                        game.state = STATE_PLAY

                elif game.state == STATE_PLAY:
                    if e.key == pygame.K_p:
                        paused = not paused
                        game.state = STATE_PAUSE if paused else STATE_PLAY

                elif game.state == STATE_PAUSE:
                    if e.key == pygame.K_p:
                        paused = not paused
                        game.state = STATE_PLAY

                elif game.state == STATE_LEVEL_END:
                    if e.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z):
                        game.load_level(game.current_level + 1)
                        game.state = STATE_PLAY

                elif game.state == STATE_GAMECLEAR:
                    if e.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z):
                        game.state = STATE_MENU

                elif game.state == STATE_LOSE:
                    if e.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z):
                        game.state = STATE_MENU

        # Update
        if game.state == STATE_PLAY and not paused:
            game.update_play(dt, keys)

        # Draw
        if game.state == STATE_MENU:
            vpix.fill(PALETTE['sky']); game.draw_menu(vpix, menu_idx)
        elif game.state == STATE_SELECT:
            vpix.fill(PALETTE['sky']); game.draw_level_select(vpix, sel_level)
        elif game.state == STATE_HELP:
            vpix.fill(PALETTE['sky']); game.draw_help(vpix)
        elif game.state == STATE_PLAY:
            vpix.fill(PALETTE['sky']); game.draw_play(vpix)
        elif game.state == STATE_LEVEL_END:
            vpix.fill(PALETTE['sky']); game.draw_level_end(vpix)
        elif game.state == STATE_GAMECLEAR:
            vpix.fill(PALETTE['sky']); game.draw_game_clear(vpix)
        elif game.state == STATE_LOSE:
            vpix.fill(PALETTE['sky']); game.draw_lose(vpix)
        elif game.state == STATE_PAUSE:
            vpix.fill(PALETTE['sky'])
            game.draw_play(vpix)
            pygame.draw.rect(vpix, (0,0,0), (0,0,VW,VH), 0)
            draw_text(vpix, "PAUSED", VW//2, VH//2, PALETTE['white'], FONT16, center=True)

        pygame.transform.scale(vpix, (W, H), screen)
        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
