#!/usr/bin/env python3
"""
Breakout — PS5-ish vibes, no external assets.
- Mouse paddle control
- Main menu, game, and in-session leaderboard (no files)
- Simple synthesized SFX (beep/boop) generated in code
- Smooth glow, gradients, and subtle particles (still lightweight)

Requires: pygame (pip install pygame)
"""

import math
import random
import struct
import sys
from typing import List, Tuple

import pygame

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
WIN_W, WIN_H = 1280, 720
FPS = 120
PS5_MODE = True         # turn off to simplify visuals
SHOW_TRAILS = True
MOUSE_CAPTURE = False   # True hides the cursor
START_LIVES = 3

# Audio config: mixer initialized for 16-bit mono @ 44100Hz
pygame.mixer.pre_init(44100, -16, 1, 512)


# -----------------------------------------------------------------------------
# Utilities
# -----------------------------------------------------------------------------
def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def mix(a: Tuple[int, int, int], b: Tuple[int, int, int], t: float) -> Tuple[int, int, int]:
    """Linear color mix."""
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def draw_text(
    surf: pygame.Surface,
    text: str,
    size: int,
    pos: Tuple[int, int],
    color=(240, 245, 255),
    center=False,
    shadow=True,
    font_name=None,
):
    font = pygame.font.SysFont(font_name, size, bold=True)
    img = font.render(text, True, color)
    rect = img.get_rect()
    if center:
        rect.center = pos
    else:
        rect.topleft = pos
    if shadow:
        shadow_img = font.render(text, True, (0, 0, 0))
        shadow_rect = shadow_img.get_rect()
        shadow_rect.topleft = (rect.left + 2, rect.top + 2)
        surf.blit(shadow_img, shadow_rect)
    surf.blit(img, rect)


def draw_vertical_gradient(surf: pygame.Surface, top_color, bottom_color):
    """Fast vertical gradient fill."""
    h = surf.get_height()
    w = surf.get_width()
    for y in range(h):
        t = y / max(1, h - 1)
        pygame.draw.line(surf, mix(top_color, bottom_color, t), (0, y), (w, y))


def draw_glow_circle(surf: pygame.Surface, center, radius, color, layers=6):
    """Soft glow by layered circles."""
    x, y = center
    r = radius
    for i in range(layers, 0, -1):
        t = i / layers
        alpha = int(40 * t)
        glow = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
        pygame.draw.circle(
            glow,
            (*color, alpha),
            (glow.get_width() // 2, glow.get_height() // 2),
            int(r * (1 + 0.8 * (1 - t))),
            0,
        )
        surf.blit(glow, (x - glow.get_width() // 2, y - glow.get_height() // 2))
    pygame.draw.circle(surf, color, (int(x), int(y)), r)


def rounded_rect(surf: pygame.Surface, rect: pygame.Rect, color, radius=12, border=0, border_color=(0, 0, 0)):
    pygame.draw.rect(surf, color, rect, border_radius=radius)
    if border > 0:
        pygame.draw.rect(surf, border_color, rect, width=border, border_radius=radius)


# -----------------------------------------------------------------------------
# SFX: tiny tone synthesizer (no files)
# -----------------------------------------------------------------------------
class ToneSynth:
    """
    Generates short PCM tones into pygame.mixer.Sound without external files.
    """

    def __init__(self, sample_rate=44100):
        self.sample_rate = sample_rate
        # Cache generated tones to avoid re-allocations
        self.cache = {}

    def tone(self, freq=440, duration=0.06, volume=0.5, wave="sine"):
        key = (freq, duration, volume, wave)
        if key in self.cache:
            return self.cache[key]

        n_samples = int(self.sample_rate * duration)
        buf = bytearray()
        max_amp = int(32767 * volume)

        # Simple envelopes for nicer clickless blips
        a_len = max(1, int(0.002 * self.sample_rate))
        r_len = max(1, int(0.010 * self.sample_rate))

        for i in range(n_samples):
            t = i / self.sample_rate
            # Envelope
            if i < a_len:
                env = i / a_len
            elif i > n_samples - r_len:
                env = max(0.0, (n_samples - i) / r_len)
            else:
                env = 1.0

            if wave == "square":
                s = 1.0 if math.sin(2 * math.pi * freq * t) >= 0 else -1.0
            elif wave == "triangle":
                s = 2 / math.pi * math.asin(math.sin(2 * math.pi * freq * t))
            else:  # sine
                s = math.sin(2 * math.pi * freq * t)

            sample = int(max_amp * env * s)
            buf += struct.pack("<h", sample)

        snd = pygame.mixer.Sound(buffer=bytes(buf))
        self.cache[key] = snd
        return snd


# -----------------------------------------------------------------------------
# Game Objects
# -----------------------------------------------------------------------------
class Paddle:
    def __init__(self, y):
        self.w = 180
        self.h = 18
        self.x = WIN_W // 2 - self.w // 2
        self.y = y
        self.speed = 0.0  # derived from mouse delta (for spin)
        self.last_x = self.x

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def update(self):
        mx, _ = pygame.mouse.get_pos()
        self.last_x = self.x
        self.x = clamp(mx - self.w // 2, 16, WIN_W - self.w - 16)
        self.speed = self.x - self.last_x

    def draw(self, surf):
        color = (220, 235, 255) if PS5_MODE else (230, 230, 230)
        rounded_rect(surf, self.rect, color, radius=12)
        if PS5_MODE:
            # subtle top highlight
            hl = self.rect.copy()
            hl.height = 4
            rounded_rect(surf, hl, (255, 255, 255), radius=4)


class Ball:
    def __init__(self, x, y):
        self.r = 10
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.speed = 430.0  # base speed
        self.launched = False
        self.trail = []

    @property
    def rect(self):
        return pygame.Rect(int(self.x - self.r), int(self.y - self.r), self.r * 2, self.r * 2)

    def launch(self):
        if not self.launched:
            angle = random.uniform(-0.35, 0.35)  # slight variation
            self.vx = self.speed * math.sin(angle)
            self.vy = -self.speed * math.cos(angle)
            self.launched = True

    def update(self, dt, paddle: Paddle):
        if not self.launched:
            # stick to paddle until launch
            self.x = paddle.x + paddle.w / 2
            self.y = paddle.y - self.r - 2
            return

        # motion
        self.x += self.vx * dt
        self.y += self.vy * dt

        # Trails
        if SHOW_TRAILS and PS5_MODE:
            self.trail.append((self.x, self.y))
            if len(self.trail) > 10:
                self.trail.pop(0)

        # walls
        if self.x - self.r <= 8:
            self.x = 8 + self.r
            self.vx = -abs(self.vx)
        elif self.x + self.r >= WIN_W - 8:
            self.x = WIN_W - 8 - self.r
            self.vx = abs(self.vx) * -1

        if self.y - self.r <= 8:
            self.y = 8 + self.r
            self.vy = abs(self.vy)

    def bounce_on_paddle(self, paddle: Paddle, synth: ToneSynth):
        if self.rect.colliderect(paddle.rect) and self.vy > 0:
            # spin from where it hits on the paddle + paddle motion
            rel = ((self.x - paddle.rect.centerx) / (paddle.w * 0.5))
            rel = clamp(rel, -1.0, 1.0)
            speed = min(780.0, math.hypot(self.vx, self.vy) * 1.03 + 8)
            angle = -math.pi / 2 + rel * 0.5  # -90deg ± ~28deg
            self.vx = math.cos(angle + math.pi / 2) * speed
            self.vy = -abs(math.sin(angle + math.pi / 2)) * speed
            # add paddle motion
            self.vx += paddle.speed * 3.2

            # correct position to avoid sticking
            self.y = paddle.y - self.r - 2

            # SFX
            synth.tone(freq=880, duration=0.045, volume=0.35, wave="sine").play()

    def draw(self, surf):
        if PS5_MODE and SHOW_TRAILS and self.trail:
            for i, (tx, ty) in enumerate(self.trail):
                alpha = int(10 + 14 * (i / len(self.trail)))
                trail = pygame.Surface((self.r * 4, self.r * 4), pygame.SRCALPHA)
                pygame.draw.circle(trail, (180, 205, 255, alpha), (trail.get_width() // 2, trail.get_height() // 2), self.r)
                surf.blit(trail, (tx - trail.get_width() // 2, ty - trail.get_height() // 2))

        if PS5_MODE:
            draw_glow_circle(surf, (int(self.x), int(self.y)), self.r, (210, 230, 255))
        else:
            pygame.draw.circle(surf, (240, 240, 240), (int(self.x), int(self.y)), self.r)


class Brick:
    def __init__(self, x, y, w, h, color, hp=1, score=50):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = color
        self.hp = hp
        self.score = score

    def hit(self) -> bool:
        self.hp -= 1
        return self.hp <= 0

    def draw(self, surf):
        c = self.color
        rounded_rect(surf, self.rect, c, radius=10)
        if PS5_MODE:
            # top shine
            top = self.rect.copy()
            top.height = 6
            rounded_rect(surf, top, (255, 255, 255), radius=6)


class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        ang = random.uniform(0, math.tau)
        speed = random.uniform(80, 220)
        self.vx = math.cos(ang) * speed
        self.vy = math.sin(ang) * speed
        self.life = random.uniform(0.25, 0.55)
        self.color = color

    def update(self, dt):
        self.life -= dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 220 * dt  # gravity-ish

    def draw(self, surf):
        if self.life <= 0:
            return
        alpha = int(clamp(self.life / 0.55, 0, 1) * 160)
        s = pygame.Surface((6, 6), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, alpha), (3, 3), 3)
        surf.blit(s, (self.x - 3, self.y - 3))


# -----------------------------------------------------------------------------
# UI elements
# -----------------------------------------------------------------------------
class Button:
    def __init__(self, rect: pygame.Rect, label: str, hotkey=None):
        self.rect = rect
        self.label = label
        self.hotkey = hotkey

    def draw(self, surf, hovered=False):
        base = (34, 52, 90)
        hl = (64, 115, 210)
        col = mix(base, hl, 0.5 if hovered else 0.0)
        rounded_rect(surf, self.rect, col, radius=12)
        draw_text(surf, self.label, 28, self.rect.center, center=True)

    def is_hover(self):
        return self.rect.collidepoint(pygame.mouse.get_pos())


# -----------------------------------------------------------------------------
# Scenes
# -----------------------------------------------------------------------------
class Leaderboard:
    """In-session only (no files)."""
    def __init__(self):
        self.entries: List[Tuple[str, int]] = []  # (name, score)

    def add(self, name: str, score: int):
        if not name:
            name = "Player"
        self.entries.append((name[:12], int(score)))
        self.entries.sort(key=lambda e: e[1], reverse=True)
        self.entries = self.entries[:10]


class TextInput:
    """Simple text input overlay to capture player name."""
    def __init__(self, prompt="Your Name:"):
        self.prompt = prompt
        self.value = ""
        self.done = False
        self.cancelled = False

    def handle_event(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.done = True
            elif e.key == pygame.K_ESCAPE:
                self.cancelled = True
            elif e.key == pygame.K_BACKSPACE:
                self.value = self.value[:-1]
            else:
                ch = e.unicode
                if ch.isprintable() and len(self.value) < 16:
                    self.value += ch

    def draw(self, surf):
        overlay = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surf.blit(overlay, (0, 0))

        box = pygame.Rect(0, 0, 640, 160)
        box.center = (WIN_W // 2, WIN_H // 2)
        rounded_rect(surf, box, (30, 40, 70), radius=16)
        draw_text(surf, self.prompt, 32, (box.centerx, box.top + 30), center=True)
        draw_text(surf, self.value + "▌", 36, box.center, center=True, color=(255, 255, 255))


class GameScene:
    def __init__(self, game):
        self.game = game
        self.paddle = Paddle(y=WIN_H - 68)
        self.ball = Ball(self.paddle.x + self.paddle.w / 2, self.paddle.y - 20)
        self.bricks: List[Brick] = []
        self.particles: List[Particle] = []
        self.level = 1
        self.score = 0
        self.lives = START_LIVES
        self.paused = False
        self.enter_name: TextInput | None = None

        self.synth = ToneSynth()

        self._build_level(self.level)

    def _build_level(self, level):
        self.bricks.clear()
        cols = 10
        rows = 6
        margin_x = 64
        margin_y = 90
        area_w = WIN_W - margin_x * 2
        area_h = 320
        bw = area_w // cols - 10
        bh = area_h // rows - 8
        palette = [
            (74, 144, 226),
            (80, 200, 240),
            (147, 197, 253),
            (124, 168, 255),
            (106, 137, 247),
            (90, 108, 220),
        ]
        for r in range(rows):
            for c in range(cols):
                x = margin_x + c * (bw + 10)
                y = margin_y + r * (bh + 8)
                hp = 1 + (r // 2)  # tougher higher rows
                score = 60 + r * 15
                col = mix(palette[r % len(palette)], (240, 250, 255), 0.15)
                self.bricks.append(Brick(x, y, bw, bh, col, hp=hp, score=score))

    def reset_ball(self):
        self.ball = Ball(self.paddle.x + self.paddle.w / 2, self.paddle.y - 20)

    def handle_event(self, e):
        if self.enter_name:
            self.enter_name.handle_event(e)
            return

        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                self.paused = not self.paused
            elif e.key in (pygame.K_SPACE, pygame.K_RETURN):
                self.ball.launch()
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.ball.launch()

    def update(self, dt):
        if self.enter_name:
            if self.enter_name.done:
                self.game.leaderboard.add(self.enter_name.value.strip() or "Player", self.score)
                self.game.change_scene("menu")
            elif self.enter_name.cancelled:
                self.game.change_scene("menu")
            return

        if self.paused:
            return

        self.paddle.update()
        self.ball.update(dt, self.paddle)
        self.ball.bounce_on_paddle(self.paddle, self.synth)

        # Top & sides wall SFX
        if self.ball.y - self.ball.r <= 8 or self.ball.x - self.ball.r <= 8 or self.ball.x + self.ball.r >= WIN_W - 8:
            # quiet boop; we don't want to spam overly loud sounds
            pass  # the paddle/brick hits have more character

        # Bottom: life lost
        if self.ball.y - self.ball.r > WIN_H + 40:
            self.lives -= 1
            self.synth.tone(freq=160, duration=0.15, volume=0.4, wave="triangle").play()
            if self.lives <= 0:
                # enter name for leaderboard
                self.enter_name = TextInput("Game Over — enter name:")
            else:
                self.reset_ball()

        # Bricks
        ball_rect = self.ball.rect
        to_remove = []
        hit_any = False
        for i, b in enumerate(self.bricks):
            if ball_rect.colliderect(b.rect):
                hit_any = True
                # Determine side bounce using overlap
                dx_left = ball_rect.right - b.rect.left
                dx_right = b.rect.right - ball_rect.left
                dy_top = ball_rect.bottom - b.rect.top
                dy_bottom = b.rect.bottom - ball_rect.top
                min_x = min(dx_left, dx_right)
                min_y = min(dy_top, dy_bottom)
                if min_x < min_y:
                    self.ball.vx *= -1
                    if dx_left < dx_right:
                        self.ball.x -= dx_left
                    else:
                        self.ball.x += dx_right
                else:
                    self.ball.vy *= -1
                    if dy_top < dy_bottom:
                        self.ball.y -= dy_top
                    else:
                        self.ball.y += dy_bottom

                if b.hit():
                    to_remove.append(i)
                    self.score += b.score
                    # particle burst
                    for _ in range(10):
                        self.particles.append(Particle(b.rect.centerx, b.rect.centery, (200, 220, 255)))
                else:
                    self.score += max(10, b.score // 4)

                # SFX
                self.synth.tone(freq=random.choice([480, 520, 560]), duration=0.04, volume=0.35, wave="square").play()

        if hit_any:
            # keep ball speed under control
            sp = math.hypot(self.ball.vx, self.ball.vy)
            sp = clamp(sp, 320.0, 900.0)
            ang = math.atan2(self.ball.vy, self.ball.vx)
            self.ball.vx = math.cos(ang) * sp
            self.ball.vy = math.sin(ang) * sp

        # Remove destroyed bricks
        if to_remove:
            for idx in reversed(to_remove):
                self.bricks.pop(idx)

        # Level clear
        if not self.bricks and self.lives > 0:
            self.level += 1
            self.synth.tone(freq=880, duration=0.12, volume=0.45, wave="triangle").play()
            self._build_level(self.level)
            self.reset_ball()

        # Particles
        if self.particles:
            for p in self.particles:
                p.update(dt)
            self.particles = [p for p in self.particles if p.life > 0]

    def draw(self, surf):
        # background
        if PS5_MODE:
            draw_vertical_gradient(surf, (10, 20, 40), (18, 32, 68))
            # soft vignette
            vignette = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
            pygame.draw.rect(vignette, (0, 0, 0, 90), (0, 0, WIN_W, WIN_H), border_radius=40)
            surf.blit(vignette, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
        else:
            surf.fill((18, 22, 30))

        # boundaries
        pygame.draw.rect(surf, (60, 80, 110), (8, 8, WIN_W - 16, WIN_H - 16), width=2, border_radius=8)

        # HUD
        draw_text(surf, f"Score: {self.score}", 28, (24, 18), color=(230, 240, 255))
        draw_text(surf, f"Lives: {self.lives}", 28, (WIN_W - 180, 18), color=(230, 240, 255))

        # Bricks
        for b in self.bricks:
            b.draw(surf)

        # Paddle
        self.paddle.draw(surf)

        # Ball
        self.ball.draw(surf)

        # Particles
        for p in self.particles:
            p.draw(surf)

        # Paused
        if self.paused:
            draw_text(surf, "Paused", 64, (WIN_W // 2, WIN_H // 2 - 10), center=True)
            draw_text(surf, "Press Esc to resume", 28, (WIN_W // 2, WIN_H // 2 + 46), center=True, color=(210, 220, 235))

        # Name entry
        if self.enter_name:
            self.enter_name.draw(surf)


class MenuScene:
    def __init__(self, game):
        self.game = game
        cx, cy = WIN_W // 2, WIN_H // 2
        self.buttons = [
            Button(pygame.Rect(cx - 160, cy - 20, 320, 56), "Start Game  (Enter)", hotkey=pygame.K_RETURN),
            Button(pygame.Rect(cx - 160, cy + 50, 320, 56), "Leaderboard  (L)", hotkey=pygame.K_l),
            Button(pygame.Rect(cx - 160, cy + 120, 320, 56), "Quit  (Q)", hotkey=pygame.K_q),
        ]

    def handle_event(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.game.change_scene("game")
            elif e.key == pygame.K_l:
                self.game.change_scene("leaderboard")
            elif e.key == pygame.K_q or e.key == pygame.K_ESCAPE:
                pygame.event.post(pygame.event.Event(pygame.QUIT))
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for b in self.buttons:
                if b.is_hover():
                    if "Start" in b.label:
                        self.game.change_scene("game")
                    elif "Leader" in b.label:
                        self.game.change_scene("leaderboard")
                    else:
                        pygame.event.post(pygame.event.Event(pygame.QUIT))

    def draw(self, surf):
        # Fancy background
        draw_vertical_gradient(surf, (12, 18, 36), (24, 38, 84))
        # Title
        draw_text(surf, "BREAKOUT", 96, (WIN_W // 2, 150), center=True, color=(220, 235, 255))
        draw_text(surf, "PS5‑ish vibes • Mouse paddle • No asset files", 26, (WIN_W // 2, 210), center=True, color=(200, 215, 240))

        # Buttons
        for b in self.buttons:
            b.draw(surf, hovered=b.is_hover())

        draw_text(surf, "F11: Fullscreen   •   Esc: Pause in-game", 22, (WIN_W // 2, WIN_H - 40), center=True, color=(190, 205, 230))


class LeaderboardScene:
    def __init__(self, game):
        self.game = game

    def handle_event(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_q, pygame.K_m):
                self.game.change_scene("menu")
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.game.change_scene("menu")

    def draw(self, surf):
        draw_vertical_gradient(surf, (14, 22, 42), (26, 40, 90))
        draw_text(surf, "LEADERBOARD (session)", 56, (WIN_W // 2, 120), center=True)

        if not self.game.leaderboard.entries:
            draw_text(surf, "No scores yet — play a round!", 28, (WIN_W // 2, WIN_H // 2), center=True, color=(210, 220, 235))
        else:
            y = 220
            for i, (name, score) in enumerate(self.game.leaderboard.entries, start=1):
                rank = f"{i:>2}."
                draw_text(surf, rank, 36, (WIN_W // 2 - 220, y), center=False)
                draw_text(surf, name, 36, (WIN_W // 2 - 160, y), center=False, color=(230, 240, 255))
                draw_text(surf, f"{score}", 36, (WIN_W // 2 + 240, y), center=True, color=(230, 240, 255))
                y += 48

        draw_text(surf, "Click or press Esc/Enter to return", 22, (WIN_W // 2, WIN_H - 42), center=True, color=(190, 205, 230))


# -----------------------------------------------------------------------------
# Game wrapper
# -----------------------------------------------------------------------------
class Game:
    def __init__(self):
        pygame.init()
        if MOUSE_CAPTURE:
            pygame.mouse.set_visible(False)

        flags = pygame.SCALED | pygame.RESIZABLE
        self.screen = pygame.display.set_mode((WIN_W, WIN_H), flags, vsync=1)
        pygame.display.set_caption("Breakout — PS5-ish vibes")

        self.clock = pygame.time.Clock()
        self.scene_name = "menu"
        self.menu = MenuScene(self)
        self.game_scene = GameScene(self)
        self.lb_scene = LeaderboardScene(self)
        self.leaderboard = Leaderboard()

        self.fullscreen = False

    def change_scene(self, name: str):
        self.scene_name = name
        if name == "game":
            # reset fresh game
            self.game_scene = GameScene(self)

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.SCALED | pygame.HWSURFACE, vsync=1)
        else:
            pygame.display.set_mode((WIN_W, WIN_H), pygame.SCALED | pygame.RESIZABLE, vsync=1)

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    running = False
                    break
                if e.type == pygame.KEYDOWN and e.key == pygame.K_F11:
                    self.toggle_fullscreen()

                # delegate
                if self.scene_name == "menu":
                    self.menu.handle_event(e)
                elif self.scene_name == "game":
                    self.game_scene.handle_event(e)
                elif self.scene_name == "leaderboard":
                    self.lb_scene.handle_event(e)

            # update & draw
            if self.scene_name == "menu":
                self.menu.draw(self.screen)
            elif self.scene_name == "game":
                self.game_scene.update(dt)
                self.game_scene.draw(self.screen)
            elif self.scene_name == "leaderboard":
                self.lb_scene.draw(self.screen)

            pygame.display.flip()

        pygame.quit()


# -----------------------------------------------------------------------------
# Entrypoint
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    Game().run()
