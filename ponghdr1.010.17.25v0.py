#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Retro Pong — Famicom CRT Edition (v1.1)
---------------------------------------
• Ends game when score reaches 5
• Y/N prompt for restart or quit
• Classic Pong-style AI (slightly imperfect)
© 2025 FlamesCo / Samsoft
"""

from __future__ import annotations
import math, random
from array import array
import pygame

WINDOW_SIZE = (600, 400)
FPS = 120
PADDLE_SIZE = (12, 64)
BALL_SIZE = 12
BALL_SPEED = 280
PADDLE_SPEED = 320
SCORE_LIMIT = 5

COLORS = {
    "background": (15, 56, 15),
    "mid": (48, 98, 48),
    "bright": (139, 172, 15),
    "accent": (180, 220, 120),
    "scanline": (0, 0, 0, 50),
}

def make_square_wave(freq: float, duration_ms: int, volume: float = 0.5) -> pygame.mixer.Sound:
    sr = 44100
    amp = int(32767 * volume)
    step = 2 * math.pi * freq / sr
    wave = array("h")
    phase = 0.0
    for _ in range(int(sr * duration_ms / 1000)):
        wave.append(amp if math.sin(phase) >= 0 else -amp)
        phase += step
    return pygame.mixer.Sound(buffer=wave.tobytes())

class Paddle:
    def __init__(self, x: int, y: int):
        self.rect = pygame.Rect(x, y, *PADDLE_SIZE)
        self.speed = PADDLE_SPEED
    def draw(self, surf): pygame.draw.rect(surf, COLORS["accent"], self.rect, border_radius=4)

class Ball:
    def __init__(self):
        self.rect = pygame.Rect(0, 0, BALL_SIZE, BALL_SIZE)
        self.reset(random.choice((-1, 1)))
    def reset(self, dir: int):
        angle = random.uniform(-0.35, 0.35)
        self.rect.center = (WINDOW_SIZE[0]//2, WINDOW_SIZE[1]//2)
        self.vel = pygame.Vector2(dir * BALL_SPEED, 0).rotate_rad(angle)
    def update(self, dt: float): self.rect.move_ip(self.vel.x*dt, self.vel.y*dt)
    def draw(self, surf): pygame.draw.rect(surf, COLORS["bright"], self.rect, border_radius=2)

def clamp(v, lo, hi): return max(lo, min(v, hi))

def ai_move(ai: Paddle, ball: Ball, dt: float):
    # Classic Pong AI: has reaction lag & limited precision
    target = ball.rect.centery + random.uniform(-16, 16)
    diff = target - ai.rect.centery
    if abs(diff) > 8:
        ai.rect.y += int(math.copysign(ai.speed * 0.6 * dt, diff))
    ai.rect.y = clamp(ai.rect.y, 0, WINDOW_SIZE[1] - ai.rect.height)

def draw_scanlines(surf):
    s = pygame.Surface((WINDOW_SIZE[0], 2), pygame.SRCALPHA)
    s.fill(COLORS["scanline"])
    for y in range(0, WINDOW_SIZE[1], 4):
        surf.blit(s, (0, y))

def draw_court(surf):
    surf.fill(COLORS["background"])
    pygame.draw.rect(surf, COLORS["mid"], surf.get_rect(), width=10, border_radius=10)
    for y in range(0, WINDOW_SIZE[1], 28):
        seg = pygame.Rect(WINDOW_SIZE[0]//2 - 4, y + 6, 8, 16)
        pygame.draw.rect(surf, COLORS["bright"], seg, border_radius=3)

def play_game():
    pygame.mixer.pre_init(44100, -16, 1, 512)
    pygame.init()
    screen = pygame.display.set_mode(WINDOW_SIZE)
    pygame.display.set_caption("Pong HDR 10.17.25 @v1.1")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 48)
    small_font = pygame.font.Font(None, 24)

    hit_s = make_square_wave(880, 70, 0.4)
    wall_s = make_square_wave(196, 90, 0.35)
    score_s = make_square_wave(120, 200, 0.45)

    player = Paddle(24, WINDOW_SIZE[1]//2 - PADDLE_SIZE[1]//2)
    ai = Paddle(WINDOW_SIZE[0]-24-PADDLE_SIZE[0], WINDOW_SIZE[1]//2 - PADDLE_SIZE[1]//2)
    ball = Ball()
    player_score = ai_score = 0
    info_timer = 2.0
    running, game_over = True, False

    while running:
        dt = clock.tick(FPS) / 1000.0
        for e in pygame.event.get():
            if e.type == pygame.QUIT: return False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE: return False
                if game_over:
                    if e.key == pygame.K_y: return True
                    if e.key == pygame.K_n: return False

        if not game_over:
            # Player control
            my = pygame.mouse.get_pos()[1]
            player.rect.centery = clamp(my, player.rect.height//2, WINDOW_SIZE[1]-player.rect.height//2)
            ai_move(ai, ball, dt)
            ball.update(dt)

            # Top/bottom collision
            if ball.rect.top <= 0 or ball.rect.bottom >= WINDOW_SIZE[1]:
                ball.vel.y *= -1
                wall_s.play()

            # Paddle collisions
            if ball.rect.colliderect(player.rect) and ball.vel.x < 0:
                offset = (ball.rect.centery - player.rect.centery) / (player.rect.height / 2)
                ball.vel.x *= -1
                ball.vel.y = clamp(ball.vel.y + offset * 180, -420, 420)
                hit_s.play()
            elif ball.rect.colliderect(ai.rect) and ball.vel.x > 0:
                offset = (ball.rect.centery - ai.rect.centery) / (ai.rect.height / 2)
                ball.vel.x *= -1
                ball.vel.y = clamp(ball.vel.y + offset * 160, -420, 420)
                hit_s.play()

            # Scoring
            if ball.rect.right < 0:
                ai_score += 1; score_s.play(); ball.reset(1)
            elif ball.rect.left > WINDOW_SIZE[0]:
                player_score += 1; score_s.play(); ball.reset(-1)

            if player_score >= SCORE_LIMIT or ai_score >= SCORE_LIMIT:
                game_over = True

        # Draw
        draw_court(screen)
        player.draw(screen); ai.draw(screen); ball.draw(screen)
        draw_scanlines(screen)

        score_text = font.render(f"{player_score:02}  {ai_score:02}", True, COLORS["accent"])
        screen.blit(score_text, score_text.get_rect(center=(WINDOW_SIZE[0]//2, 40)))

        if not game_over and info_timer > 0:
            info_timer -= dt
            msg = small_font.render("Mouse to move • ESC to quit", True, COLORS["bright"])
            screen.blit(msg, msg.get_rect(center=(WINDOW_SIZE[0]//2, WINDOW_SIZE[1]-30)))

        if game_over:
            win = player_score > ai_score
            msg = font.render("GAME OVER", True, COLORS["bright"])
            sub = small_font.render(f"You {'WIN' if win else 'LOSE'}! Press Y to restart / N to quit", True, COLORS["accent"])
            screen.blit(msg, msg.get_rect(center=(WINDOW_SIZE[0]//2, WINDOW_SIZE[1]//2 - 20)))
            screen.blit(sub, sub.get_rect(center=(WINDOW_SIZE[0]//2, WINDOW_SIZE[1]//2 + 20)))

        pygame.display.flip()

def main():
    while play_game():
        pass
    pygame.quit()

if __name__ == "__main__":
    main()
