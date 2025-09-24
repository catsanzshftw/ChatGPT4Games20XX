#!/usr/bin/env python3
"""
Super Mario Bros - 32 Levels + Deluxe Overworld
SMB1-style physics (Remastered, Mega Connector Edition)
Built with Pygame

Optimized for 60 FPS:
- Fixed-timestep physics (60 Hz) with busy-loop cap
- Spatial grid collision (tile hash)
- Float positions; integer rects for render/collide
- Converted surfaces for faster blits
"""

import pygame, sys, random
from collections import defaultdict

pygame.init()
W, H = 800, 600
TILE = 40
FPS = 60
FIXED_DT = 1.0 / FPS
USE_BUSY_LOOP = True  # set False to reduce CPU if needed

# -------------------------------------------------
# Display
# -------------------------------------------------
pygame.display.set_caption("Super Mario Bros 1 Physics Engine (Remastered)")
pygame.event.set_allowed([pygame.QUIT, pygame.KEYDOWN, pygame.KEYUP])

_flags = pygame.SCALED | pygame.DOUBLEBUF
try:
    screen = pygame.display.set_mode((W, H), _flags, vsync=1)
except TypeError:
    screen = pygame.display.set_mode((W, H), _flags)

clock = pygame.time.Clock()

# -------------------------------------------------
# Physics constants (SMB1 tuned)
# -------------------------------------------------
GRAVITY = 0.55
JUMP_VELOCITY = -11.5
WALK_ACCEL = 0.4
RUN_ACCEL = 0.6
FRICTION = 0.2
MAX_WALK = 4
MAX_RUN = 6

FONT = pygame.font.SysFont("Arial", 16, bold=True)

# -------------------------------------------------
# Mega Connector: Procedural assets (converted)
# -------------------------------------------------
def make_surface(size, color, shape="rect"):
    # Note: display is already created; safe to convert for fast blits.
    surf = pygame.Surface(size, pygame.SRCALPHA, 32)
    if shape == "rect":
        surf.fill(color)
    elif shape == "circle":
        pygame.draw.ellipse(surf, color, surf.get_rect())
    elif shape == "flag":
        pygame.draw.rect(surf, (200, 200, 200), (size[0]//2 - 2, 0, 4, size[1]))
        pygame.draw.rect(surf, color, (size[0]//2, 10, size[0]//2, 20))
    elif shape == "castle":
        surf.fill((128, 128, 128))
        pygame.draw.rect(surf, (60, 60, 60), (5, 5, size[0]-10, size[1]-10), 3)
    return surf.convert_alpha()

ASSETS = {
    "mario_small": make_surface((32, 32), (255, 0, 0)),
    "brick": make_surface((TILE, TILE), (139, 69, 19)),
    "flag": make_surface((20, 160), (0, 200, 0), shape="flag"),
    "node": make_surface((30, 30), (0, 100, 255), shape="circle"),
    "castle": make_surface((60, 60), (128, 128, 128), shape="castle"),
}
NODE_LOCKED = make_surface((30, 30), (200, 200, 200), shape="circle")

# -------------------------------------------------
# Spatial grid for collisions (tile-size hashing)
# -------------------------------------------------
class SpatialGrid:
    __slots__ = ("cell", "grid")
    def __init__(self, cell=TILE):
        self.cell = cell
        self.grid: dict[tuple[int, int], list[pygame.Rect]] = defaultdict(list)

    def _cells_for(self, rect: pygame.Rect):
        cs = self.cell
        x0 = rect.left // cs
        x1 = (rect.right - 1) // cs
        y0 = rect.top // cs
        y1 = (rect.bottom - 1) // cs
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                yield (x, y)

    def add(self, rect: pygame.Rect):
        for c in self._cells_for(rect):
            self.grid[c].append(rect)

    def query(self, rect: pygame.Rect):
        seen = set()
        out = []
        for c in self._cells_for(rect):
            lst = self.grid.get(c)
            if lst:
                for r in lst:
                    ir = id(r)
                    if ir not in seen:
                        seen.add(ir)
                        out.append(r)
        return out

# -------------------------------------------------
# Mario
# -------------------------------------------------
class Mario(pygame.sprite.Sprite):
    __slots__ = ("image","rect","pos_x","pos_y","vel_x","vel_y","on_ground")
    def __init__(self, x, y):
        super().__init__()
        self.image = ASSETS["mario_small"]
        self.rect = self.image.get_rect(topleft=(x, y))
        self.pos_x = float(self.rect.x)
        self.pos_y = float(self.rect.y)
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.on_ground = False

    def step(self, keys, level):
        shift = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        accel = RUN_ACCEL if shift else WALK_ACCEL

        left = keys[pygame.K_LEFT]
        right = keys[pygame.K_RIGHT]

        if left and not right:
            self.vel_x -= accel
        elif right and not left:
            self.vel_x += accel
        else:
            if self.vel_x > 0:
                self.vel_x = max(0.0, self.vel_x - FRICTION)
            elif self.vel_x < 0:
                self.vel_x = min(0.0, self.vel_x + FRICTION)

        max_speed = MAX_RUN if shift else MAX_WALK
        if self.vel_x > max_speed: self.vel_x = max_speed
        if self.vel_x < -max_speed: self.vel_x = -max_speed

        if keys[pygame.K_SPACE] and self.on_ground:
            self.vel_y = JUMP_VELOCITY
            self.on_ground = False

        # Gravity
        self.vel_y = min(self.vel_y + GRAVITY, 12)

        # --- Move X, resolve collisions
        self.pos_x += self.vel_x
        self.rect.x = int(self.pos_x)
        for p in level.get_colliders(self.rect):
            if self.rect.colliderect(p):
                if self.vel_x > 0:
                    self.rect.right = p.left
                elif self.vel_x < 0:
                    self.rect.left = p.right
                self.pos_x = float(self.rect.x)
                self.vel_x = 0.0

        # --- Move Y, resolve collisions
        self.pos_y += self.vel_y
        self.rect.y = int(self.pos_y)
        self.on_ground = False
        for p in level.get_colliders(self.rect):
            if self.rect.colliderect(p):
                if self.vel_y > 0:
                    self.rect.bottom = p.top
                    self.on_ground = True
                elif self.vel_y < 0:
                    self.rect.top = p.bottom
                self.pos_y = float(self.rect.y)
                self.vel_y = 0.0

# -------------------------------------------------
# Level
# -------------------------------------------------
class Level:
    __slots__ = ("number","width","platforms","blocks","flag","_view_margin","_grid")
    def __init__(self, number, width=2000):
        self.number = number
        self.platforms: list[pygame.Rect] = []
        self.blocks: list[tuple[str, pygame.Rect]] = []
        self.flag = pygame.Rect(width - 500, H - 200, 20, 160)
        self.width = width
        self._view_margin = 80
        self._grid = SpatialGrid(TILE)
        self.build()

    def _add_block(self, kind: str, rect: pygame.Rect):
        self.platforms.append(rect)
        self.blocks.append((kind, rect))
        self._grid.add(rect)

    def build(self):
        # Ground
        ground_y = H - TILE
        for x in range(0, self.width, TILE):
            self._add_block("brick", pygame.Rect(x, ground_y, TILE, TILE))
        # Platforms
        for _ in range(20):
            x = random.randint(200, self.width - 200)
            y = random.choice([H - 200, H - 300])
            self._add_block("brick", pygame.Rect(x, y, TILE, TILE))

    def get_colliders(self, rect: pygame.Rect):
        # Inflate slightly to catch edge-touch cases during movement
        query = rect.inflate(2, 2)
        return self._grid.query(query)

    def draw(self, surf, camera_x: int):
        view_rect = pygame.Rect(camera_x - self._view_margin, 0,
                                W + 2 * self._view_margin, H)
        blit = surf.blit
        brick = ASSETS["brick"]
        for kind, rect in self.blocks:
            if rect.colliderect(view_rect):
                # Only 'brick' kind used for tiles currently; keep switch for future assets
                img = brick if kind == "brick" else ASSETS[kind]
                blit(img, (rect.x - camera_x, rect.y))
        blit(ASSETS["flag"], (self.flag.x - camera_x, self.flag.y))

# -------------------------------------------------
# Overworld
# -------------------------------------------------
class Overworld:
    __slots__ = ("nodes","current_index","unlocked","_labels")
    def __init__(self, total_levels=32):
        self.nodes = []
        self.current_index = 0
        self.unlocked = 1
        spacing_x, spacing_y = 120, 70
        cols = 8
        for i in range(total_levels):
            row, col = divmod(i, cols)
            x, y = 80 + col * spacing_x, 120 + row * spacing_y
            self.nodes.append(pygame.Rect(x, y, 30, 30))
        self._labels = [FONT.render(str(i + 1), True, (0, 0, 0))
                        for i in range(total_levels)]

    def draw(self, surf):
        blit = surf.blit
        for i, node in enumerate(self.nodes):
            img = ASSETS["node"] if i < self.unlocked else NODE_LOCKED
            blit(img, node.topleft)
            label = self._labels[i]
            blit(label, label.get_rect(center=node.center))
        blit(ASSETS["castle"], (self.nodes[-1].x - 15, self.nodes[-1].y - 15))
        pygame.draw.rect(surf, (255, 255, 0), self.nodes[self.current_index], 3)

    def move(self, dx, dy):
        cols = 8
        new = self.current_index + dx + dy * cols
        if 0 <= new < self.unlocked:
            self.current_index = new

# -------------------------------------------------
# Gameplay with flag clear (fixed-step update)
# -------------------------------------------------
def play_level(level_num):
    mario = Mario(50, H - 100)
    level = Level(level_num)
    camera_x = 0
    clearing = False
    walking = False
    accumulator = 0.0

    while True:
        # --- Events
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if not clearing and e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                return False

        keys = pygame.key.get_pressed()

        # --- Timing
        dt_ms = clock.tick_busy_loop(FPS) if USE_BUSY_LOOP else clock.tick(FPS)
        accumulator += dt_ms / 1000.0

        # --- Fixed-step updates
        while accumulator >= FIXED_DT:
            if not clearing:
                mario.step(keys, level)
            else:
                # Flag animation and auto-walk (fixed-step)
                if not walking:
                    if mario.rect.bottom < H - TILE:
                        mario.pos_y += 4
                        mario.rect.y = int(mario.pos_y)
                    else:
                        walking = True
                else:
                    mario.pos_x += 2
                    mario.rect.x = int(mario.pos_x)
                    if mario.rect.x > level.width - 400:
                        return True

            # Freeze camera during clear
            if not clearing:
                max_scroll = max(0, level.width - W)
                camera_x = mario.rect.centerx - W // 2
                if camera_x < 0: camera_x = 0
                if camera_x > max_scroll: camera_x = max_scroll

            # Begin clear when touching flag
            if not clearing and mario.rect.colliderect(level.flag):
                clearing = True
                mario.vel_x = 0.0
                mario.vel_y = 0.0

            accumulator -= FIXED_DT

        # --- Render
        screen.fill((92, 148, 252))
        level.draw(screen, int(camera_x))
        screen.blit(mario.image, (mario.rect.x - int(camera_x), mario.rect.y))
        pygame.display.flip()

# -------------------------------------------------
# Main loop
# -------------------------------------------------
def main():
    overworld = Overworld()
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_LEFT:  overworld.move(-1, 0)
                if e.key == pygame.K_RIGHT: overworld.move(1, 0)
                if e.key == pygame.K_UP:    overworld.move(0, -1)
                if e.key == pygame.K_DOWN:  overworld.move(0, 1)
                if e.key == pygame.K_RETURN:
                    if overworld.current_index < overworld.unlocked:
                        cleared = play_level(overworld.current_index + 1)
                        if cleared:
                            overworld.unlocked = min(overworld.unlocked + 1, len(overworld.nodes))

        screen.fill((0, 0, 0))
        overworld.draw(screen)
        pygame.display.flip()
        clock.tick(FPS)  # run overworld at 60 as well

if __name__ == "__main__":
    main()
