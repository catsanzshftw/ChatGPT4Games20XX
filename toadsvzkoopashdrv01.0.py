# Toads vs Koopaz - Ultra HD XP Edition (Silent Base)
# 600x400, full bloom lighting, fixed 60FPS logic, XP Graphite UI
# All procedural, no assets required.

import pygame, random, math, time
from pygame.locals import *

# --------------------------------------------------------------------
# CONFIGURATION
# --------------------------------------------------------------------
pygame.init()
pygame.display.set_caption("Toads vs Koopaz — Ultra HD XP Deluxe")
SCREEN_WIDTH, SCREEN_HEIGHT = 600, 400
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
clock = pygame.time.Clock()

# Color palette (Graphite Silver XP aesthetic)
GRAY = (120, 120, 120)
GRAY_DARK = (60, 60, 60)
GRAY_LIGHT = (180, 180, 180)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (70, 130, 180)
GREEN = (0, 200, 0)
RED = (200, 50, 50)
YELLOW = (255, 215, 0)
PURPLE = (140, 50, 220)

# Game grid
ROWS, COLS = 5, 7
TILE_SIZE = 60
LAWN_LEFT, LAWN_TOP = 70, 80
LAWN_WIDTH, LAWN_HEIGHT = COLS * TILE_SIZE, ROWS * TILE_SIZE

font = pygame.font.SysFont("segoeui", 18)
bigfont = pygame.font.SysFont("segoeui", 28, bold=True)

# --------------------------------------------------------------------
# BACKGROUND RENDER (bloom + gradient)
# --------------------------------------------------------------------
def draw_xp_background(surf):
    for y in range(SCREEN_HEIGHT):
        c = int(100 + 60 * (y / SCREEN_HEIGHT))
        pygame.draw.line(surf, (c, c, c + 40), (0, y), (SCREEN_WIDTH, y))
    # Bloomed sun area
    cx, cy = SCREEN_WIDTH - 80, 60
    for r in range(50, 120, 10):
        alpha = max(10, 120 - (r - 50) * 2)
        s = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
        pygame.draw.circle(s, (255, 240, 180, alpha), (r, r), r)
        surf.blit(s, (cx - r, cy - r), special_flags=pygame.BLEND_PREMULTIPLIED)

# --------------------------------------------------------------------
# CLASSES
# --------------------------------------------------------------------
class Toad(pygame.sprite.Sprite):
    def __init__(self, row, col, color):
        super().__init__()
        self.row, self.col = row, col
        self.rect = pygame.Rect(LAWN_LEFT + col*TILE_SIZE, LAWN_TOP + row*TILE_SIZE, TILE_SIZE, TILE_SIZE)
        self.surf = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        self.hp = 10
        self.color = color
        self.timer = 0

    def update(self, dt):
        self.timer += dt
        self.draw()

    def draw(self):
        self.surf.fill((0,0,0,0))
        pygame.draw.ellipse(self.surf, self.color, (8, 10, TILE_SIZE-16, TILE_SIZE-16))
        pygame.draw.circle(self.surf, WHITE, (TILE_SIZE//2, 15), 10)
        pygame.draw.circle(self.surf, BLACK, (TILE_SIZE//2 - 4, 15), 2)
        pygame.draw.circle(self.surf, BLACK, (TILE_SIZE//2 + 4, 15), 2)

class Koopa(pygame.sprite.Sprite):
    def __init__(self, row):
        super().__init__()
        self.row = row
        self.rect = pygame.Rect(SCREEN_WIDTH, LAWN_TOP + row*TILE_SIZE, 40, 40)
        self.surf = pygame.Surface((40, 40), pygame.SRCALPHA)
        self.hp = 8
        self.speed = 25 + random.randint(-5, 5)

    def update(self, dt):
        self.rect.x -= int(self.speed * dt)
        self.draw()
        if self.rect.right < 0:
            self.kill()

    def draw(self):
        self.surf.fill((0,0,0,0))
        pygame.draw.ellipse(self.surf, (200,100,0), (0,5,38,28))
        pygame.draw.circle(self.surf, (250,200,100), (20,10), 8)

# --------------------------------------------------------------------
# GAME SETUP
# --------------------------------------------------------------------
all_sprites = pygame.sprite.Group()
toads = pygame.sprite.Group()
koopas = pygame.sprite.Group()

def spawn_koopa():
    k = Koopa(random.randint(0, ROWS-1))
    koopas.add(k)
    all_sprites.add(k)

def place_toad(row, col):
    if any(t.row == row and t.col == col for t in toads):
        return
    color = random.choice([GREEN, BLUE, YELLOW, PURPLE])
    t = Toad(row, col, color)
    toads.add(t)
    all_sprites.add(t)

# --------------------------------------------------------------------
# MAIN LOOP
# --------------------------------------------------------------------
def run():
    spawn_timer = 0
    last_time = time.perf_counter()
    running = True
    while running:
        now = time.perf_counter()
        dt = now - last_time
        last_time = now

        for e in pygame.event.get():
            if e.type == QUIT:
                running = False
            elif e.type == MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()
                if LAWN_LEFT <= pos[0] < LAWN_LEFT + LAWN_WIDTH and LAWN_TOP <= pos[1] < LAWN_TOP + LAWN_HEIGHT:
                    col = (pos[0]-LAWN_LEFT)//TILE_SIZE
                    row = (pos[1]-LAWN_TOP)//TILE_SIZE
                    place_toad(row,col)

        spawn_timer += dt
        if spawn_timer >= 2.5:
            spawn_koopa()
            spawn_timer = 0

        # update
        for s in list(all_sprites):
            s.update(dt)

        # collisions
        for k in list(koopas):
            for t in list(toads):
                if k.rect.colliderect(t.rect):
                    t.hp -= 5*dt
                    if t.hp <= 0:
                        t.kill()
                        toads.remove(t)
                    k.hp -= 5*dt
                    if k.hp <= 0:
                        k.kill()
                        koopas.remove(k)

        # render
        draw_xp_background(screen)
        # Lawn grid
        pygame.draw.rect(screen, (100,150,100), (LAWN_LEFT, LAWN_TOP, LAWN_WIDTH, LAWN_HEIGHT))
        for r in range(ROWS+1):
            pygame.draw.line(screen, (80,120,80), (LAWN_LEFT, LAWN_TOP + r*TILE_SIZE), (LAWN_LEFT+LAWN_WIDTH, LAWN_TOP + r*TILE_SIZE))
        for c in range(COLS+1):
            pygame.draw.line(screen, (80,120,80), (LAWN_LEFT + c*TILE_SIZE, LAWN_TOP), (LAWN_LEFT + c*TILE_SIZE, LAWN_TOP+LAWN_HEIGHT))

        # Sprites
        for s in all_sprites:
            screen.blit(s.surf, s.rect)

        # XP top bar
        pygame.draw.rect(screen, GRAY_LIGHT, (0,0,SCREEN_WIDTH,60))
        pygame.draw.rect(screen, GRAY_DARK, (0,59,SCREEN_WIDTH,1))
        title = bigfont.render("Toads vs Koopaz — XP Ultra HD", True, BLACK)
        screen.blit(title, (20,15))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == '__main__':
    run()
