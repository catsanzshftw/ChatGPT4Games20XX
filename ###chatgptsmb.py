#!/usr/bin/env python3
"""
NSMB-Style PC Port — 5 Worlds x 3 Levels (Single-File Prototype)
No external assets ("DS graphics" vibe with drawn tiles), flag -> overworld -> next level

Controls
- Overworld: ←/→ move selection, ENTER to play, ESC quits program
- In Level: ←/→ move, Z/SPACE jump, X run (slightly faster), ESC return to overworld, R restart level

Notes
- This is an original fan-style engine. No Nintendo assets or code are used.
- Procedural, deterministic levels (seeded by world/level) with safe terrain and a goal flagpole.
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

SOLID_TILES = {T_GROUND, T_BLOCK, T_QBLOCK, T_PIPE}

# Colors (simple DS-ish palette)
COLORS = {
    'sky'        : (120, 190, 255),
    'cloud'      : (240, 250, 255),
    'soil'       : (166, 110, 68),
    'grass'      : (100, 200, 80),
    'block'      : (170, 120, 70),
    'qblock'     : (245, 200, 70),
    'outline'    : (50, 35, 20),
    'pipe'       : (56, 176, 64),
    'pipe_dark'  : (32, 112, 40),
    'ui'         : (10, 10, 10),
    'ui2'        : (255, 255, 255),
    'path'       : (255, 238, 180),
    'node_locked': (110, 110, 110),
    'node_open'  : (255, 255, 255),
    'node_clear' : (255, 225, 90),
    'water'      : (90, 150, 230),
    'land'       : (140, 210, 90),
}

# Worlds meta
WORLD_INFO = [
    ("World 1 — Grassland", (140, 210, 90)),
    ("World 2 — Desert",    (220, 200, 90)),
    ("World 3 — Beach",     (140, 200, 210)),
    ("World 4 — Forest",    (110, 180, 110)),
    ("World 5 — Volcano",   (200, 90, 60)),
]

# -------------------------------------------------
# Init Pygame
# -------------------------------------------------
pygame.init()
pygame.display.set_caption("NSMB-Style PC Port — 5x3 (Prototype)")
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
# Level generation
# -------------------------------------------------
class Level:
    def __init__(self, world_idx: int, level_idx: int):
        self.world_idx = world_idx
        self.level_idx = level_idx
        self.title = f"W{world_idx+1}-{level_idx+1}"
        seed = (world_idx+1) * 1000 + (level_idx+1) * 13
        self.rng = random.Random(seed)

        # Size scaling per world/level (longer later)
        base_w = 96
        self.w_tiles = base_w + world_idx * 10 + level_idx * 6
        self.h_tiles = 17
        self.pixel_w = self.w_tiles * TILE
        self.pixel_h = self.h_tiles * TILE

        self.grid = [[T_EMPTY for _ in range(self.w_tiles)] for __ in range(self.h_tiles)]
        self.spawn_px = (TILE*2, TILE*8)
        self.flag_rect = pygame.Rect(0, 0, TILE//2, int(TILE*4.5))
        self._gen()

    # ---- generation routines ----
    def _add_ground(self, g_y:int):
        # Two-layer ground for nicer profile
        for x in range(self.w_tiles):
            for y in range(g_y, self.h_tiles):
                self.grid[y][x] = T_GROUND

    def _add_plateau(self, x:int, top_y:int, length:int):
        # Solid top row with ground beneath
        for i in range(length):
            xx = clamp(x+i, 0, self.w_tiles-1)
            for y in range(top_y, self.h_tiles):
                self.grid[y][xx] = T_GROUND

    def _add_blocks(self, x0:int, x1:int, base_y:int, density:float=0.18):
        for x in range(x0, x1):
            if self.rng.random() < density:
                t = T_QBLOCK if self.rng.random() < 0.35 else T_BLOCK
                y = base_y - self.rng.choice([3,4])
                if 1 <= y < self.h_tiles-2:
                    self.grid[y][x] = t

    def _add_pipes(self, x_start:int, x_end:int, g_y:int, step:int=22):
        for x in range(x_start, x_end, step):
            height = self.rng.randint(2, 4)
            for yy in range(g_y - height, g_y):
                if 0 <= x < self.w_tiles:
                    self.grid[yy][x] = T_PIPE

    def _gen(self):
        g = self.h_tiles - 3  # ground y index
        self._add_ground(g)

        # Gentle elevation changes via plateaus
        x = TILE
        pos = 4
        while x < self.w_tiles-32:
            length = self.rng.randint(6, 14)
            delta  = self.rng.choice([-1, 0, 0, 1])
            pos = clamp(pos + delta, 3, 8)
            top_y = g - pos
            self._add_plateau(x, top_y, length)
            self._add_blocks(x+2, x+length-2, top_y, density=0.25)
            if self.rng.random() < 0.5:
                self._add_pipes(x+2, x+length-2, g, step=self.rng.randint(18, 26))
            x += length

        # Flag near end
        flag_x_tile = self.w_tiles - 6
        self.flag_rect.topleft = (flag_x_tile*TILE + TILE//2, (g-5)*TILE)
        # Clear a little plaza before the flag
        for xx in range(flag_x_tile-2, self.w_tiles):
            for yy in range(g-1, self.h_tiles):
                self.grid[yy][xx] = T_GROUND

    # ---- collision queries ----
    def solid_rects_around(self, rect: pygame.Rect):
        # Query tiles around a rect for collision
        x0 = clamp(rect.left // TILE - 2, 0, self.w_tiles-1)
        x1 = clamp(rect.right // TILE + 2, 0, self.w_tiles-1)
        y0 = clamp(rect.top // TILE - 2, 0, self.h_tiles-1)
        y1 = clamp(rect.bottom // TILE + 2, 0, self.h_tiles-1)
        rects = []
        for y in range(y0, y1+1):
            row = self.grid[y]
            for x in range(x0, x1+1):
                t = row[x]
                if t in SOLID_TILES:
                    rects.append(pygame.Rect(x*TILE, y*TILE, TILE, TILE))
        return rects

    # ---- drawing ----
    def draw_bg(self, surf, camera_x):
        surf.fill(COLORS['sky'])
        # Simple parallax clouds
        rng = self.rng
        for i in range(14):
            cx = (i*220 - (camera_x*0.4) + (i*37 % 2000)) % (self.pixel_w + 400) - 200
            cy = 60 + (i*23 % 140)
            pygame.draw.ellipse(surf, COLORS['cloud'], (cx, cy, 140, 40))

    def draw_tiles(self, surf, camera_x):
        # Compute visible tile range
        x0 = clamp(int(camera_x // TILE) - 2, 0, self.w_tiles-1)
        x1 = clamp(int((camera_x + W) // TILE) + 2, 0, self.w_tiles-1)
        for y in range(self.h_tiles):
            ry = y*TILE
            for x in range(x0, x1+1):
                t = self.grid[y][x]
                if t == T_EMPTY: continue
                rx = x*TILE - camera_x

                if t == T_GROUND:
                    r = pygame.Rect(rx, ry, TILE, TILE)
                    pygame.draw.rect(surf, COLORS['soil'], r)
                    # grassy top edge
                    if y == 0 or self.grid[y-1][x] != T_GROUND:
                        pygame.draw.rect(surf, COLORS['grass'], (rx, ry, TILE, 6))
                        pygame.draw.line(surf, COLORS['outline'], (rx, ry+6), (rx+TILE, ry+6))
                elif t == T_BLOCK:
                    r = pygame.Rect(rx, ry, TILE, TILE)
                    pygame.draw.rect(surf, COLORS['block'], r)
                    pygame.draw.rect(surf, COLORS['outline'], r, 2)
                elif t == T_QBLOCK:
                    r = pygame.Rect(rx, ry, TILE, TILE)
                    pygame.draw.rect(surf, COLORS['qblock'], r)
                    pygame.draw.rect(surf, COLORS['outline'], r, 2)
                    # small dot pattern
                    pygame.draw.circle(surf, COLORS['outline'], (rx+TILE//2, ry+TILE//2), 3)
                elif t == T_PIPE:
                    r = pygame.Rect(rx, ry, TILE, TILE)
                    pygame.draw.rect(surf, COLORS['pipe'], r)
                    pygame.draw.rect(surf, COLORS['pipe_dark'], r, 3)

        # Flag pole & banner
        fx = self.flag_rect.x - camera_x
        fy = self.flag_rect.y
        pygame.draw.rect(surf, (220, 220, 220), (fx, fy, 6, self.flag_rect.height))
        # simple flag triangle
        pygame.draw.polygon(surf, (255, 90, 90), [(fx+6, fy+12), (fx+6+24, fy+24), (fx+6, fy+36)])


# -------------------------------------------------
# Player
# -------------------------------------------------
class Player:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = False
        self.facing = 1
        self.width = 20
        self.height = 28

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    def move_and_collide(self, level: Level, dt: float, hold_run: bool, input_x: int, jump_pressed: bool):
        max_speed = MAX_RUN if hold_run else MAX_WALK
        accel     = MOVE_ACCEL * (AIR_CONTROL if not self.on_ground else 1.0)

        # Horizontal control
        if input_x:
            self.vx += input_x * accel * dt
            self.facing = input_x
        else:
            # friction
            self.vx *= (FRICTION_GND if self.on_ground else FRICTION_AIR)
            if abs(self.vx) < 3: self.vx = 0

        self.vx = clamp(self.vx, -max_speed, max_speed)

        # Jump
        if jump_pressed and self.on_ground:
            self.vy = JUMP_VEL
            self.on_ground = False

        # Gravity
        self.vy += GRAVITY * dt
        if self.vy > 1400: self.vy = 1400

        # Integrate X
        new_rect = self.rect.move(self.vx*dt, 0)
        for s in level.solid_rects_around(new_rect):
            if new_rect.colliderect(s):
                if self.vx > 0:
                    new_rect.right = s.left
                elif self.vx < 0:
                    new_rect.left = s.right
                self.vx = 0
        self.x, self.y = new_rect.x, new_rect.y

        # Integrate Y
        new_rect = self.rect.move(0, self.vy*dt)
        collided = False
        for s in level.solid_rects_around(new_rect):
            if new_rect.colliderect(s):
                collided = True
                if self.vy > 0:
                    new_rect.bottom = s.top
                    self.on_ground = True
                elif self.vy < 0:
                    new_rect.top = s.bottom
                self.vy = 0
        if not collided:
            self.on_ground = False
        self.x, self.y = new_rect.x, new_rect.y

    def draw(self, surf, camera_x):
        r = self.rect
        rx = r.x - camera_x
        body = pygame.Rect(rx, r.y, r.w, r.h)
        pygame.draw.rect(surf, (240, 64, 64), body)      # body (red)
        pygame.draw.rect(surf, (250, 220, 180), (rx+4, r.y+2, 12, 10))  # face
        # simple eye
        ex = rx+ (10 if self.facing>=0 else 6)
        pygame.draw.rect(surf, (20,20,20), (ex, r.y+6, 3, 3))


# -------------------------------------------------
# Overworld
# -------------------------------------------------
class Node:
    def __init__(self, index:int, world:int, level:int, pos):
        self.index = index
        self.world = world
        self.level = level
        self.pos   = pos  # (x, y) pixels
        self.clear = False

class Overworld:
    def __init__(self):
        # Linear path of 5 worlds x 3 nodes -> 15 nodes
        self.nodes = []
        self.current_index = 0
        self.unlocked_max = 0
        self._build_layout()

    def _build_layout(self):
        self.nodes.clear()
        margin_x = 110
        gap_x    = 150
        base_y   = 220
        gap_y    = 68
        idx = 0
        for w in range(5):
            x = margin_x + w * gap_x
            for l in range(3):
                y = base_y + l*gap_y + (w%2)*16
                self.nodes.append(Node(idx, w, l, (x, y)))
                idx += 1

    def move_sel(self, dir:int):
        # Move along unlocked range
        new_i = clamp(self.current_index + dir, 0, min(self.unlocked_max, len(self.nodes)-1))
        self.current_index = new_i

    def set_cleared(self, idx:int):
        self.nodes[idx].clear = True
        if idx == self.unlocked_max and self.unlocked_max < len(self.nodes)-1:
            self.unlocked_max += 1
        # auto-select next node if any
        self.current_index = min(self.unlocked_max, len(self.nodes)-1)

    def is_all_cleared(self):
        return self.unlocked_max >= len(self.nodes)-1 and self.nodes[-1].clear

    def draw(self, surf):
        surf.fill(COLORS['water'])
        # Land stripe
        pygame.draw.rect(surf, COLORS['land'], (0, H//3, W, H))

        # Path lines
        for i in range(0, min(self.unlocked_max, len(self.nodes)-1)):
            a = self.nodes[i].pos
            b = self.nodes[i+1].pos
            pygame.draw.line(surf, COLORS['path'], a, b, 6)
            pygame.draw.line(surf, (180, 150, 90), a, b, 2)

        # Nodes
        for i, n in enumerate(self.nodes):
            x,y = n.pos
            unlocked = (i <= self.unlocked_max)
            c = COLORS['node_clear'] if n.clear else (COLORS['node_open'] if unlocked else COLORS['node_locked'])
            pygame.draw.circle(surf, (30,30,30), (x,y), 18)
            pygame.draw.circle(surf, c, (x,y), 15)

        # Selector
        sx, sy = self.nodes[self.current_index].pos
        pygame.draw.circle(surf, (255, 80, 80), (sx, sy), 22, 3)

        # Labels
        cur = self.nodes[self.current_index]
        title = f"Overworld — {WORLD_INFO[cur.world][0]} — Select W{cur.world+1}-{cur.level+1}"
        draw_text(surf, title, (24, 16))
        draw_text(surf, "ENTER: play  |  ←/→: move  |  ESC: quit", (24, 44), COLORS['ui'])


# -------------------------------------------------
# Game State
# -------------------------------------------------
class Game:
    def __init__(self):
        self.state = 'OVERWORLD'  # or 'LEVEL'
        self.overworld = Overworld()
        self.level = None
        self.player = None
        self.camera_x = 0
        self.level_index_linear = 0  # 0..14
        self._flash_timer = 0.0

    def start_level(self, index:int):
        node = self.overworld.nodes[index]
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

    def all_clear_screen(self, surf):
        surf.fill((10,10,10))
        draw_text(surf, "ALL WORLDS CLEARED!", (W//2-160, H//2-40), COLORS['ui2'])
        draw_text(surf, "Thanks for playing this prototype.", (W//2-210, H//2), COLORS['ui2'])

    # ---- Update/Draw per-state ----
    def update_overworld(self, dt, events):
        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_LEFT, pygame.K_a):
                    self.overworld.move_sel(-1)
                elif e.key in (pygame.K_RIGHT, pygame.K_d):
                    self.overworld.move_sel(1)
                elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    idx = self.overworld.current_index
                    if idx <= self.overworld.unlocked_max:
                        self.start_level(idx)
                elif e.key == pygame.K_ESCAPE:
                    pygame.event.post(pygame.event.Event(pygame.QUIT))

        self.overworld.draw(screen)
        if self._flash_timer > 0:
            self._flash_timer = max(0.0, self._flash_timer - dt)
            if int(self._flash_timer*10) % 2 == 0:
                # highlight the newly unlocked node
                i = self.overworld.current_index
                if i < len(self.overworld.nodes):
                    x, y = self.overworld.nodes[i].pos
                    pygame.draw.circle(screen, (255,255,255), (x,y), 28, 4)

        if self.overworld.is_all_cleared():
            self.all_clear_screen(screen)

    def update_level(self, dt, events):
        assert self.level and self.player
        # Input
        keys = pygame.key.get_pressed()
        input_x = (1 if (keys[pygame.K_RIGHT] or keys[pygame.K_d]) else 0) + (-1 if (keys[pygame.K_LEFT] or keys[pygame.K_a]) else 0)
        hold_run = keys[pygame.K_x]
        jump_pressed = keys[pygame.K_SPACE] or keys[pygame.K_z]

        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    self.return_to_overworld(False)
                elif e.key == pygame.K_r:
                    # restart
                    self.start_level(self.level_index_linear)

        # Step player
        self.player.move_and_collide(self.level, dt, hold_run, input_x, jump_pressed)

        # Camera follow
        target = self.player.x - (W//2 - self.player.width//2)
        self.camera_x = clamp(target, 0, max(0, self.level.pixel_w - W))

        # Goal check
        if self.player.rect.colliderect(self.level.flag_rect):
            self.return_to_overworld(True)
            return

        # Drawing
        self.level.draw_bg(screen, self.camera_x)
        self.level.draw_tiles(screen, self.camera_x)
        self.player.draw(screen, self.camera_x)

        # HUD
        draw_text(screen, f"{self.level.title}", (12, 10))
        draw_text(screen, "ESC: overworld  |  R: restart  |  ←/→ move  |  Z/SPACE jump  |  X run", (12, 34), COLORS['ui'])

    def tick(self, dt, events):
        if self.state == 'OVERWORLD':
            self.update_overworld(dt, events)
        else:
            self.update_level(dt, events)


# -------------------------------------------------
# Main loop
# -------------------------------------------------

def main():
    game = Game()
    running = True
    accumulator = 0.0

    while running:
        dt = min(clock.tick(FPS) / 1000.0, 0.05)
        accumulator += dt

        # Gather events once per frame
        events = []
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            else:
                events.append(e)

        # Fixed-step update for consistent physics
        while accumulator >= FIXED_DT:
            game.tick(FIXED_DT, events)
            accumulator -= FIXED_DT

        # Present (already drawn inside game.tick)
        pygame.display.flip()

    pygame.quit()
    sys.exit(0)


if __name__ == '__main__':
    main()
