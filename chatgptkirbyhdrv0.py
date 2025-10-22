# Ultra Kirby — M4 Pro Port v1.1
# NES-accurate 60.0988 FPS (Kirby's Adventure 1-1 style)
# by FlamesCo / Samsoft 2025

import pygame, time, math
from pygame.locals import *

pygame.init()
pygame.display.set_caption("Ultra Kirby — M4 Pro Port v1.1 (Vegetable Valley Scroll)")

# -------------------------
# Display / Timing
# -------------------------
WIDTH, HEIGHT = 600, 400
screen = pygame.display.set_mode((WIDTH, HEIGHT))
NES_FPS = 60.0988
FRAME_TIME = 1.0 / NES_FPS
clock = pygame.time.Clock()

# -------------------------
# Colors / Palette
# -------------------------
SKY = (172, 210, 255)
GROUND = (239, 215, 183)
HILL = (190, 240, 200)
STAR = (255, 247, 173)
KIRBY = (255, 182, 193)
DOOR_GLOW = (255, 220, 128)

# -------------------------
# Level data (8 screens wide)
# 0 = air, 1 = ground, 2 = door
# -------------------------
TILE = 40
ROWS = HEIGHT // TILE
COLS = 52  # ~8.5 screens wide (2048 px)
level = [[0 for _ in range(COLS)] for _ in range(ROWS)]

# Ground pattern (gentle slopes)
heights = [6,6,6,6,5,5,5,6,6,7,7,7,6,6,5,5,5,6,6,6,7,7,7,6,6,5,5,5,6,6,6,7,7,7,6,6,5,5,5,6,6,6,6,7,7,7,7,6,6,6,6,6]
for x in range(COLS):
    ground_row = heights[x]
    for y in range(ROWS - ground_row, ROWS):
        level[y][x] = 1
# Door at the far right
level[ROWS-7][COLS-2] = 2

# -------------------------
# Kirby State
# -------------------------
kirby_x, kirby_y = 100.0, HEIGHT - 120
kirby_vx = kirby_vy = 0.0
on_ground = False
camera_x = 0.0

# -------------------------
# Helpers
# -------------------------
def draw_background(scroll):
    screen.fill(SKY)
    # clouds / parallax
    for i in range(8):
        cx = (i * 120 - scroll * 0.3) % (WIDTH + 120)
        pygame.draw.circle(screen, HILL, (int(cx), 80 + (i*15)%40), 40)
    # far hills
    for i in range(10):
        hx = (i * 180 - scroll * 0.2) % (WIDTH + 180)
        pygame.draw.circle(screen, (150,230,180), (int(hx), 300), 90)

def draw_level(scroll):
    start_col = int(scroll // TILE)
    offset_x = -(scroll % TILE)
    for x in range(start_col, min(start_col + WIDTH//TILE + 3, COLS)):
        for y in range(ROWS):
            tile = level[y][x]
            if tile == 1:
                pygame.draw.rect(screen, GROUND,
                    (offset_x + (x-start_col)*TILE, y*TILE, TILE, TILE))
            elif tile == 2:
                rect = pygame.Rect(offset_x + (x-start_col)*TILE, y*TILE, TILE, TILE)
                pygame.draw.rect(screen, DOOR_GLOW, rect)
                pygame.draw.rect(screen, (139,69,19), rect, 3)

def rect_collide(kx, ky, radius):
    # simple tile collision
    k_rect = pygame.Rect(kx-radius, ky-radius, radius*2, radius*2)
    startx = int((kx-radius)//TILE)
    endx = int((kx+radius)//TILE)+1
    starty = int((ky-radius)//TILE)
    endy = int((ky+radius)//TILE)+1
    for y in range(starty, min(endy, ROWS)):
        for x in range(startx, min(endx, COLS)):
            if 0 <= x < COLS and 0 <= y < ROWS:
                tile = level[y][x]
                if tile == 1:
                    rect = pygame.Rect(x*TILE, y*TILE, TILE, TILE)
                    if k_rect.colliderect(rect):
                        return True, rect
                if tile == 2 and k_rect.colliderect(pygame.Rect(x*TILE,y*TILE,TILE,TILE)):
                    return "door", None
    return False, None

def fade_out():
    for a in range(0,255,8):
        s = pygame.Surface((WIDTH,HEIGHT))
        s.fill((0,0,0))
        s.set_alpha(a)
        screen.blit(s,(0,0))
        pygame.display.flip()
        time.sleep(0.01)

# -------------------------
# Main loop
# -------------------------
running = True
stage_clear = False
while running:
    frame_start = time.perf_counter()

    for e in pygame.event.get():
        if e.type == QUIT:
            running = False

    keys = pygame.key.get_pressed()
    kirby_vx = 0
    if keys[K_RIGHT]: kirby_vx = 2.0
    if keys[K_LEFT]:  kirby_vx = -2.0
    if keys[K_SPACE] and on_ground:
        kirby_vy = -6.0
        on_ground = False

    # physics
    kirby_vy += 0.3
    kirby_y += kirby_vy
    kirby_x += kirby_vx

    # collisions
    collided, rect = rect_collide(kirby_x, kirby_y, 16)
    if collided == "door":
        fade_out()
        stage_clear = True
        running = False
    elif collided:
        # snap to top of block
        if kirby_vy > 0:
            kirby_y = rect.top - 16
            kirby_vy = 0
            on_ground = True
    else:
        on_ground = False

    # scrolling camera
    camera_x = max(0, min(kirby_x - WIDTH/2, COLS*TILE - WIDTH))

    # wrap Kirby horizontally (just safety)
    kirby_x = max(0, min(kirby_x, COLS*TILE-1))

    # --- draw ---
    draw_background(camera_x)
    draw_level(camera_x)
    pygame.draw.circle(screen, KIRBY,
        (int(kirby_x - camera_x), int(kirby_y)), 16)
    pygame.display.flip()

    # --- frame pacing ---
    elapsed = time.perf_counter() - frame_start
    delay = FRAME_TIME - elapsed
    if delay > 0: time.sleep(delay)
    else: time.sleep(0.001)
    clock.tick()

# --- Stage Clear ---
if stage_clear:
    screen.fill((0,0,0))
    font = pygame.font.SysFont("Arial", 36, bold=True)
    txt = font.render("STAGE CLEAR!", True, (255,255,255))
    screen.blit(txt,(WIDTH//2 - txt.get_width()//2, HEIGHT//2 - 20))
    pygame.display.flip()
    time.sleep(3)

pygame.quit()
