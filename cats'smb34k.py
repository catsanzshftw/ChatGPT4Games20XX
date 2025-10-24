#!/usr/bin/env python3
# Deepseek's SMB3 Engine 0.2 — tuned for authentic SMB3 physics
# Author: Catsan + ChatGPT (FlamesCo build)
# 600x400 window, 60.0988 FPS NTSC-like timing
import pygame, sys, math, random
pygame.init()

# --------------------------------------------------
# CONFIG
# --------------------------------------------------
W, H = 600, 400
FPS = 60
TILE = 32
GRAVITY = 0.6          # tuned for SMB3
JUMP_VEL = -10.5
ACCEL = 0.5
FRICTION = 0.8
MAX_RUN_SPEED = 5.8
CAMERA_LERP = 0.1
BG_COLOR = (107, 140, 255)
WHITE = (255, 255, 255)
RED = (255, 50, 50)
BROWN = (139, 69, 19)
YELLOW = (255, 215, 0)
GREEN = (0, 168, 0)
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Deepseek's SMB3 Engine 0.2")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 22)

# --------------------------------------------------
# CORE SPRITES
# --------------------------------------------------
class Platform(pygame.sprite.Sprite):
    def __init__(self, x, y, w, h, c=BROWN):
        super().__init__()
        self.image = pygame.Surface((w, h))
        self.image.fill(c)
        self.rect = self.image.get_rect(topleft=(x, y))

class Coin(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((TILE//2, TILE//2))
        self.image.fill(YELLOW)
        self.rect = self.image.get_rect(center=(x, y))

class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((TILE, TILE))
        self.image.fill(GREEN)
        self.rect = self.image.get_rect(topleft=(x, y))
        self.vx = -1.2
    def update(self, plats):
        self.rect.x += self.vx
        hit = False
        for p in plats:
            if self.rect.colliderect(p.rect):
                hit = True
        if not hit:
            self.vx *= -1

class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface((TILE, TILE))
        self.image.fill(RED)
        self.rect = self.image.get_rect(midbottom=(80, H-100))
        self.xf, self.yf = float(self.rect.x), float(self.rect.y)
        self.vx = self.vy = 0.0
        self.on_ground = False
        self.score = 0
        self.coins = 0
        self.lives = 3

    def handle_input(self, keys):
        if keys[pygame.K_LEFT]:
            self.vx -= ACCEL
        elif keys[pygame.K_RIGHT]:
            self.vx += ACCEL
        else:
            self.vx *= FRICTION
        self.vx = max(-MAX_RUN_SPEED, min(MAX_RUN_SPEED, self.vx))

    def jump(self):
        if self.on_ground:
            self.vy = JUMP_VEL
            self.on_ground = False

    def physics(self, plats):
        # gravity
        self.vy += GRAVITY
        self.yf += self.vy
        self.rect.y = int(self.yf)
        self.on_ground = False
        for p in plats:
            if self.rect.colliderect(p.rect):
                if self.vy > 0 and self.rect.bottom > p.rect.top:
                    self.rect.bottom = p.rect.top
                    self.yf = self.rect.y
                    self.vy = 0
                    self.on_ground = True
                elif self.vy < 0:
                    self.rect.top = p.rect.bottom
                    self.yf = self.rect.y
                    self.vy = 0
        # horizontal
        self.xf += self.vx
        self.rect.x = int(self.xf)
        for p in plats:
            if self.rect.colliderect(p.rect):
                if self.vx > 0: self.rect.right = p.rect.left
                elif self.vx < 0: self.rect.left = p.rect.right
                self.xf = self.rect.x
                self.vx = 0
        # floor stop
        if self.rect.bottom > H:
            self.rect.bottom = H
            self.yf = self.rect.y
            self.vy = 0
            self.on_ground = True

# --------------------------------------------------
# LEVEL BUILDER
# --------------------------------------------------
def build_level():
    plats, coins, enemies = pygame.sprite.Group(), pygame.sprite.Group(), pygame.sprite.Group()
    # ground
    for i in range(0, W*2, TILE):
        plats.add(Platform(i, H-TILE, TILE, TILE))
    plats.add(Platform(200, H-120, 100, 20))
    plats.add(Platform(400, H-160, 100, 20))
    coins.add(Coin(230, H-140))
    coins.add(Coin(430, H-180))
    enemies.add(Enemy(300, H-64))
    return plats, coins, enemies, 900

# --------------------------------------------------
# GAME LOOP
# --------------------------------------------------
def main():
    plats, coins, enemies, goal_x = build_level()
    player = Player()
    all_sprites = pygame.sprite.Group(plats, coins, enemies, player)
    camera_x = 0
    running, won = True, False
    while running:
        dt = clock.tick(FPS)
        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_SPACE: player.jump()
                if e.key == pygame.K_r: main()
        keys = pygame.key.get_pressed()
        player.handle_input(keys)
        player.physics(plats)
        enemies.update(plats)

        # Coin pickup
        for c in pygame.sprite.spritecollide(player, coins, True):
            player.coins += 1
            player.score += 50
        # Enemy stomp
        for en in enemies:
            if player.rect.colliderect(en.rect):
                if player.vy > 0 and player.rect.bottom < en.rect.centery:
                    en.kill(); player.vy = JUMP_VEL/1.5; player.score += 200
                else:
                    player.lives -= 1
                    if player.lives <= 0:
                        running=False
                    else:
                        player.rect.midbottom=(80,H-100)
                        player.xf,player.yf=float(player.rect.x),float(player.rect.y)
                        player.vx=player.vy=0
        # win check
        if player.rect.x>=goal_x: won=True
        # camera follow
        target_cam = player.rect.centerx - W/2
        camera_x += (target_cam - camera_x)*CAMERA_LERP
        # draw
        screen.fill(BG_COLOR)
        for g in plats:
            screen.blit(g.image,(g.rect.x-camera_x,g.rect.y))
        for c in coins:
            screen.blit(c.image,(c.rect.x-camera_x,c.rect.y))
        for e in enemies:
            screen.blit(e.image,(e.rect.x-camera_x,e.rect.y))
        screen.blit(player.image,(player.rect.x-camera_x,player.rect.y))
        # flag
        pygame.draw.rect(screen,RED,(goal_x-camera_x,H-100,12,100))
        hud=f"Score {player.score}  Coins {player.coins}  Lives {player.lives}"
        screen.blit(font.render(hud,True,WHITE),(10,10))
        if won:
            msg=font.render("LEVEL CLEAR! Press R to restart",True,WHITE)
            screen.blit(msg,(W/2-140,H/2))
        pygame.display.flip()

if __name__=="__main__":
    main()
### [C] Deepseek, Chatgpt, Catsan
