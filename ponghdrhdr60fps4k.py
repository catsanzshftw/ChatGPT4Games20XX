#!/usr/bin/env python3
"""
ULTRA ! PONG [C] SAMSOFT 1990–2025
-----------------------------------
HDR Edition with main menu & credits.
Mouse vs AI • Neon glow • Procedural audio
"""

import pygame, sys, random, math

# === Init ===
pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=256)
WIDTH, HEIGHT = 800, 480
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("ULTRA ! PONG — Samsoft 1990–2025")
clock = pygame.time.Clock()
FPS = 60

# === Colors ===
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
NEON_BLUE = (100, 180, 255)
NEON_PINK = (255, 120, 200)
NEON_PURPLE = (200, 160, 255)
GRAY = (120, 120, 120)

# === Gameplay ===
PADDLE_W, PADDLE_H = 12, 90
BALL_SIZE = 12
AI_SPEED = 5
BALL_SPEED = 5
WIN_SCORE = 5

# === Beep ===
def beep(freq=600, dur=100, vol=0.3):
    rate = 44100
    n = int(rate * dur / 1000)
    buf = bytearray()
    for i in range(n):
        s = int(math.sin(2 * math.pi * freq * i / rate) * 32767 * vol)
        buf += int.to_bytes(s, 2, "little", signed=True)
    pygame.mixer.Sound(buffer=buf).play()

# === Paddle ===
class Paddle:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.rect = pygame.Rect(x, y, PADDLE_W, PADDLE_H)

    def move_to(self, y):
        self.y = max(0, min(y - PADDLE_H // 2, HEIGHT - PADDLE_H))
        self.rect.y = self.y

    def move_ai(self, ball_y):
        c = self.y + PADDLE_H / 2
        if c < ball_y - 8: self.y += AI_SPEED
        elif c > ball_y + 8: self.y -= AI_SPEED
        self.y = max(0, min(self.y, HEIGHT - PADDLE_H))
        self.rect.y = self.y

    def draw(self, surf, color):
        glow = pygame.Surface((PADDLE_W * 3, PADDLE_H * 3), pygame.SRCALPHA)
        pygame.draw.rect(glow, (*color, 40), glow.get_rect(), border_radius=8)
        glow = pygame.transform.smoothscale(glow, (PADDLE_W * 2, PADDLE_H * 2))
        surf.blit(glow, (self.rect.x - PADDLE_W / 2, self.rect.y - PADDLE_H / 2))
        pygame.draw.rect(surf, color, self.rect, border_radius=3)

# === Ball ===
class Ball:
    def __init__(self):
        self.trail = []
        self.reset()

    def reset(self):
        self.x, self.y = WIDTH / 2, HEIGHT / 2
        ang = math.radians(random.choice([-30, -20, 20, 30]))
        self.dx = random.choice([-1, 1]) * BALL_SPEED * math.cos(ang)
        self.dy = BALL_SPEED * math.sin(ang)
        self.rect = pygame.Rect(self.x, self.y, BALL_SIZE, BALL_SIZE)
        self.trail.clear()

    def move(self):
        self.trail.append((self.x, self.y))
        if len(self.trail) > 12: self.trail.pop(0)
        self.x += self.dx; self.y += self.dy
        if self.y <= 0 or self.y >= HEIGHT - BALL_SIZE:
            self.dy *= -1; beep(880, 40, 0.25)
        self.rect.topleft = (self.x, self.y)

    def collide(self, paddle):
        if self.rect.colliderect(paddle.rect):
            offset = (self.y + BALL_SIZE / 2 - (paddle.y + PADDLE_H / 2)) / (PADDLE_H / 2)
            self.dx *= -1; self.dy = BALL_SPEED * offset
            beep(1320, 40, 0.4)

    def draw(self, surf):
        for i, (tx, ty) in enumerate(self.trail):
            a = int(255 * (i / len(self.trail)))
            pygame.draw.circle(surf, (*NEON_PINK, a), (int(tx), int(ty)), BALL_SIZE // 2)
        pygame.draw.circle(surf, NEON_PINK, (int(self.x), int(self.y)), BALL_SIZE // 2)

# === Visual Helpers ===
def draw_center_line(surf):
    for i in range(0, HEIGHT, 24):
        pygame.draw.rect(surf, GRAY, (WIDTH // 2 - 2, i, 4, 12))

def draw_score(surf, l, r):
    font = pygame.font.Font(None, 72)
    sl, sr = font.render(str(l), True, WHITE), font.render(str(r), True, WHITE)
    surf.blit(sl, (WIDTH // 4 - sl.get_width() // 2, 40))
    surf.blit(sr, (3 * WIDTH // 4 - sr.get_width() // 2, 40))

def glow_overlay(surf):
    blur = pygame.transform.smoothscale(surf, (WIDTH // 4, HEIGHT // 4))
    blur = pygame.transform.smoothscale(blur, (WIDTH, HEIGHT))
    blur.set_alpha(60)
    SCREEN.blit(blur, (0, 0))

# === Menu ===
def main_menu():
    t = 0
    font_title = pygame.font.Font(None, 120)
    font_sub = pygame.font.Font(None, 36)
    font_copy = pygame.font.Font(None, 20)

    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_SPACE, pygame.K_z):
                    beep(600, 120, 0.4)
                    return
                elif e.key == pygame.K_ESCAPE: pygame.quit(); sys.exit()

        t += 1
        SCREEN.fill((10, 10, 25))
        pulse = 180 + int(50 * math.sin(t * 0.05))
        title = font_title.render("ULTRA ! PONG", True, (pulse, 160, 255))
        SCREEN.blit(title, (WIDTH / 2 - title.get_width() / 2, HEIGHT / 3))

        if (t // 30) % 2 == 0:
            txt = font_sub.render("PRESS SPACE OR Z TO ENTER", True, NEON_BLUE)
            SCREEN.blit(txt, (WIDTH / 2 - txt.get_width() / 2, HEIGHT / 2 + 60))

        copy = font_copy.render("© SAMSOFT 1990 – 2025", True, (160, 160, 160))
        SCREEN.blit(copy, (WIDTH / 2 - copy.get_width() / 2, HEIGHT - 40))
        pygame.display.flip(); clock.tick(FPS)

# === Credits Screen ===
def credits_screen():
    font_big = pygame.font.Font(None, 80)
    font_mid = pygame.font.Font(None, 36)
    font_small = pygame.font.Font(None, 24)
    t = 0
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_SPACE, pygame.K_ESCAPE): return

        t += 1
        SCREEN.fill((0, 0, 20))
        title = font_big.render("CREDITS", True, (200, 160, 255))
        SCREEN.blit(title, (WIDTH / 2 - title.get_width() / 2, 80))

        y = 200
        lines = [
            "Developed by Samsoft Labs",
            "Inspired by Nintendo & Atari Classics",
            "AI Collaboration: ChatGPT (GPT-5 Kernel)",
            "Music & Sound: Procedural Beepsynth™",
            "© SAMSOFT 1990 – 2025  All Rights Reserved"
        ]
        for line in lines:
            glow = font_mid.render(line, True, (100 + int(80 * math.sin(t * 0.03)), 180, 255))
            SCREEN.blit(glow, (WIDTH / 2 - glow.get_width() / 2, y))
            y += 40

        press = font_small.render("Press SPACE or ESC to return", True, (180, 180, 200))
        SCREEN.blit(press, (WIDTH / 2 - press.get_width() / 2, HEIGHT - 60))

        pygame.display.flip(); clock.tick(FPS)

# === Game Over ===
def game_over(winner):
    font = pygame.font.Font(None, 90)
    sub = pygame.font.Font(None, 36)
    surf = pygame.Surface((WIDTH, HEIGHT))
    surf.fill((0, 0, 0))
    text = font.render(f"{winner.upper()} WINS", True, NEON_PURPLE)
    msg = sub.render("Press SPACE for credits or ESC to quit", True, WHITE)
    surf.blit(text, (WIDTH / 2 - text.get_width() / 2, HEIGHT / 2 - 50))
    surf.blit(msg, (WIDTH / 2 - msg.get_width() / 2, HEIGHT / 2 + 30))
    SCREEN.blit(surf, (0, 0))
    pygame.display.flip()

    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_SPACE:
                    beep(700, 150, 0.5)
                    credits_screen()
                    return True
                elif e.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()
        clock.tick(30)

# === Main Game ===
def main():
    left = Paddle(40, HEIGHT / 2 - PADDLE_H / 2)
    right = Paddle(WIDTH - 40 - PADDLE_W, HEIGHT / 2 - PADDLE_H / 2)
    ball = Ball()
    scoreL = scoreR = 0

    while True:
        clock.tick(FPS)
        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit()

        my = pygame.mouse.get_pos()[1]
        left.move_to(my)
        right.move_ai(ball.y)
        ball.move(); ball.collide(left); ball.collide(right)

        if ball.x < 0: scoreR += 1; beep(220, 200, 0.4); ball.reset()
        elif ball.x > WIDTH: scoreL += 1; beep(330, 200, 0.4); ball.reset()

        if scoreL >= WIN_SCORE or scoreR >= WIN_SCORE:
            winner = "Player" if scoreL > scoreR else "AI"
            if game_over(winner): return main()
            else: return

        frame = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        frame.fill((10, 10, 20))
        draw_center_line(frame)
        draw_score(frame, scoreL, scoreR)
        left.draw(frame, NEON_BLUE)
        right.draw(frame, NEON_PURPLE)
        ball.draw(frame)
        SCREEN.blit(frame, (0, 0))
        glow_overlay(frame)
        pygame.display.flip()

# === Run ===
if __name__ == "__main__":
    main_menu()
    main()
