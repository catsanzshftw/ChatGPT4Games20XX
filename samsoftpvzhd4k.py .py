#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PVZ: Rebooted HDR v0.1.0 (single-file, Pygame)
License: GPL-3.0-or-later
Author: FlamesCo Labs (homage build, not affiliated with PopCap)
Resolution: 600 x 400

This is an original tower-defense game inspired by lane-based defenders.
It does not include or reproduce PopCap assets, levels, names, or code.
All art is primitive, drawn at runtime (rectangles, circles, text).

Controls
--------
  - 1 : Select Shooter (cost 100, fires peas)
  - 2 : Select Generator (cost 50, produces sun/energy)
  - 3 : Select Blocker (cost 50, absorbs damage)
  - Mouse Left: Place selected plant on an empty tile (if you can afford it)
  - Mouse Right: Remove a plant (refund 25%)
  - H : Toggle fake "HDR glow" (additive light effects; not true HDR)
  - P : Pause / Unpause
  - N : Skip to next demo level (when available)
  - ESC : Cancel selection

Win/Lose
--------
  - Win when all scheduled zombies are defeated.
  - Lose if a zombie crosses the left edge and the lane’s mower is already spent.
    (Each lane has a single-use mower that auto-triggers to clear that lane once.)

Notes
-----
  - Pygame doesn’t provide true HDR. The "HDR glow" here is a simple additive glow
    pass using blurred circles drawn under bright objects (peas, suns). Consider it
    purely cosmetic.
  - This is a lean, study-friendly codebase designed for extension rather than
    feature parity with any commercial title.
"""

import os
import sys
import math
import random
import time
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict

import pygame

# --------------------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------------------
WIDTH, HEIGHT = 600, 400
UI_HEIGHT = 80                    # top bar
GRID_ROWS, GRID_COLS = 5, 9
FPS = 60
SEED_COOLDOWN_TINT = (0, 0, 0, 90)
GLOW_ENABLED_DEFAULT = True       # can be toggled with 'H'

# Derived grid sizing
GRID_H = HEIGHT - UI_HEIGHT
CELL_H = GRID_H // GRID_ROWS      # integer size
GRID_W = CELL_H * GRID_COLS       # keep square-ish cells
LEFT_MARGIN = (WIDTH - GRID_W) // 2
CELL_W = GRID_W // GRID_COLS

# Gameplay tuning
START_ENERGY = 100
REFUND_RATIO = 0.25
PROJECTILE_RADIUS = 5
PROJECTILE_SPEED_PX_S = 180
ZOMBIE_W = 32
ZOMBIE_H = CELL_H - 12

# Colors
COL_BG = (18, 22, 28)
COL_GRID = (46, 56, 66)
COL_UI = (28, 34, 40)
COL_TEXT = (230, 235, 240)
COL_ACCENT = (90, 200, 120)
COL_DANGER = (220, 80, 70)
COL_YELLOW = (255, 230, 90)
COL_BLUE = (90, 160, 230)
COL_GREEN = (90, 200, 120)
COL_ORANGE = (255, 140, 50)
COL_CARD = (56, 66, 76)
COL_CARD_SEL = (86, 106, 126)
COL_SHADOW = (0, 0, 0, 70)

# --------------------------------------------------------------------------------------
# Data Classes
# --------------------------------------------------------------------------------------

@dataclass
class PlantType:
    name: str
    cost: int
    cooldown: float
    max_hp: int
    # combat
    shoot_interval: float = 0.0
    bullet_damage: int = 0
    # economy
    generate_interval: float = 0.0
    generate_amount: int = 0
    # visuals
    color: Tuple[int, int, int] = (120, 180, 120)
    glow_color: Tuple[int, int, int, int] = (255, 255, 180, 80)
    hotkey: int = 0


@dataclass
class Plant:
    ptype: PlantType
    row: int
    col: int
    hp: int
    next_shoot_t: float = 0.0
    next_gen_t: float = 0.0

    def rect(self) -> pygame.Rect:
        x = LEFT_MARGIN + self.col * CELL_W
        y = UI_HEIGHT + self.row * CELL_H
        return pygame.Rect(x+6, y+6, CELL_W-12, CELL_H-12)


@dataclass
class ZombieType:
    name: str
    max_hp: int
    speed: float      # px/s while walking
    dps: float        # damage per second to plants
    color: Tuple[int, int, int] = (140, 120, 120)


@dataclass
class Zombie:
    ztype: ZombieType
    row: int
    x: float
    hp: int
    chewing: bool = False

    @property
    def y(self) -> float:
        return UI_HEIGHT + self.row * CELL_H + (CELL_H - ZOMBIE_H) / 2

    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x - ZOMBIE_W), int(self.y), ZOMBIE_W, ZOMBIE_H)


@dataclass
class Projectile:
    row: int
    x: float
    y: float
    vx: float
    damage: int
    alive: bool = True

    def rect(self) -> pygame.Rect:
        r = PROJECTILE_RADIUS
        return pygame.Rect(int(self.x - r), int(self.y - r), 2*r, 2*r)


@dataclass
class LawnMower:
    row: int
    x: float
    active: bool = False
    spent: bool = False

    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), UI_HEIGHT + self.row * CELL_H + CELL_H//4, CELL_W//2, CELL_H//2)


@dataclass
class SpawnEvent:
    t: float                     # time since level start to spawn (seconds)
    ztype: ZombieType
    row: Optional[int] = None    # if None, random row


@dataclass
class Level:
    name: str
    env: str                    # "day" | "evening" | "night"
    schedule: List[SpawnEvent]
    prize: int = 0              # bonus energy after victory


# --------------------------------------------------------------------------------------
# Core Types
# --------------------------------------------------------------------------------------

def make_default_plant_types() -> List[PlantType]:
    return [
        PlantType(
            name="Shooter", cost=100, cooldown=5.0, max_hp=100,
            shoot_interval=1.4, bullet_damage=20,
            color=(100, 200, 140), glow_color=(255, 255, 200, 80), hotkey=1
        ),
        PlantType(
            name="Generator", cost=50, cooldown=5.0, max_hp=60,
            generate_interval=6.0, generate_amount=25,
            color=(240, 210, 80), glow_color=(255, 240, 120, 80), hotkey=2
        ),
        PlantType(
            name="Blocker", cost=50, cooldown=7.5, max_hp=260,
            color=(160, 140, 100), glow_color=(255, 180, 120, 60), hotkey=3
        ),
    ]


def make_default_zombie_types() -> Dict[str, ZombieType]:
    return {
        "Walker": ZombieType("Walker", max_hp=120, speed=22.0, dps=8.0, color=(140, 120, 120)),
        "Tough":  ZombieType("Tough",  max_hp=240, speed=16.0, dps=8.0, color=(120, 100, 100)),
        "Fast":   ZombieType("Fast",   max_hp=90,  speed=34.0, dps=6.0, color=(150, 120, 120)),
    }


def make_demo_levels(ztypes: Dict[str, ZombieType]) -> List[Level]:
    lvls = []

    # Level 1: mellow day
    schedule1 = []
    t = 3.0
    for i in range(8):
        schedule1.append(SpawnEvent(t=t, ztype=ztypes["Walker"], row=None))
        t += random.uniform(3.5, 6.0)
    lvls.append(Level(name="1-1 Day", env="day", schedule=schedule1, prize=25))

    # Level 2: evening with mixed zombies
    schedule2 = []
    t = 3.0
    for i in range(10):
        zt = ztypes["Walker"] if i % 3 else ztypes["Tough"]
        schedule2.append(SpawnEvent(t=t, ztype=zt, row=None))
        t += random.uniform(2.8, 5.5)
    lvls.append(Level(name="1-2 Evening", env="evening", schedule=schedule2, prize=35))

    # Level 3: night-ish with faster adds
    schedule3 = []
    t = 2.5
    for i in range(14):
        zt = ztypes["Fast"] if i % 2 else ztypes["Walker"]
        schedule3.append(SpawnEvent(t=t, ztype=zt, row=None))
        t += random.uniform(2.2, 4.2)
    lvls.append(Level(name="1-3 Night", env="night", schedule=schedule3, prize=50))

    return lvls


# --------------------------------------------------------------------------------------
# Utilities
# --------------------------------------------------------------------------------------

def clamp(x, a, b):
    return a if x < a else b if x > b else x


def now_ms():
    return int(time.time() * 1000)


def world_to_cell(mx, my) -> Optional[Tuple[int, int]]:
    """Convert mouse pos into (row, col) if inside grid; else None."""
    if my < UI_HEIGHT or my >= HEIGHT:
        return None
    if mx < LEFT_MARGIN or mx >= LEFT_MARGIN + GRID_W:
        return None
    col = (mx - LEFT_MARGIN) // CELL_W
    row = (my - UI_HEIGHT) // CELL_H
    if 0 <= row < GRID_ROWS and 0 <= col < GRID_COLS:
        return int(row), int(col)
    return None


def draw_shadowed_rect(surface, rect: pygame.Rect, color: Tuple[int, int, int], radius=6):
    # simple rounded rect substitute
    pygame.draw.rect(surface, (0, 0, 0), rect.inflate(4, 4), border_radius=radius)
    pygame.draw.rect(surface, color, rect, border_radius=radius)


def draw_text(surface, text, font, color, pos, center=False):
    img = font.render(text, True, color)
    r = img.get_rect()
    if center:
        r.center = pos
    else:
        r.topleft = pos
    surface.blit(img, r)


# --------------------------------------------------------------------------------------
# Game
# --------------------------------------------------------------------------------------

class Game:
    def __init__(self, screen):
        pygame.display.set_caption("PVZ: Rebooted HDR v0.1.0 — FlamesCo Labs")
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.running = True
        self.paused = False
        self.hdr = GLOW_ENABLED_DEFAULT

        # Fonts
        self.font = pygame.font.SysFont("arial", 16)
        self.font_small = pygame.font.SysFont("arial", 14)
        self.font_big = pygame.font.SysFont("arial", 20, bold=True)

        # Content
        self.plant_types = make_default_plant_types()
        self.zombie_types = make_default_zombie_types()
        self.levels = make_demo_levels(self.zombie_types)
        self.level_i = 0

        # State
        self.energy = START_ENERGY
        self.grid: List[List[Optional[Plant]]] = [[None for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
        self.plants: List[Plant] = []
        self.zombies: List[Zombie] = []
        self.projectiles: List[Projectile] = []
        self.mowers: List[LawnMower] = [LawnMower(row=r, x=LEFT_MARGIN - CELL_W//2) for r in range(GRID_ROWS)]
        self.cooldowns: Dict[str, float] = {pt.name: 0.0 for pt in self.plant_types}
        self.selected: Optional[PlantType] = None

        # Level scheduling
        self.level_elapsed = 0.0
        self.next_spawn_index = 0
        self.victory = False
        self.defeat = False

        # Build card rects for UI selection
        self.card_rects: Dict[str, pygame.Rect] = {}
        self._layout_cards()

        # background gradient
        self.bg_surface = pygame.Surface((WIDTH, HEIGHT))
        self._regenerate_background()

    # ------------------------- Layout ----------------------------------

    def _layout_cards(self):
        pad = 8
        w = 120
        h = UI_HEIGHT - pad*2
        x = LEFT_MARGIN
        for pt in self.plant_types:
            r = pygame.Rect(x, pad, w, h)
            self.card_rects[pt.name] = r
            x += w + 8

    def _regenerate_background(self):
        # Draw a simple vertical gradient to bg_surface depending on env
        self.bg_surface.fill(COL_BG)
        env = self.levels[self.level_i].env if self.levels else "day"
        top_col = (24, 28, 34)
        if env == "day":
            top_col = (34, 90, 140)
        elif env == "evening":
            top_col = (80, 50, 90)
        elif env == "night":
            top_col = (12, 16, 28)

        for y in range(HEIGHT):
            t = y / max(1, HEIGHT-1)
            r = int(top_col[0] * (1 - t) + COL_BG[0] * t)
            g = int(top_col[1] * (1 - t) + COL_BG[1] * t)
            b = int(top_col[2] * (1 - t) + COL_BG[2] * t)
            pygame.draw.line(self.bg_surface, (r, g, b), (0, y), (WIDTH, y))

        # UI bar
        pygame.draw.rect(self.bg_surface, COL_UI, pygame.Rect(0, 0, WIDTH, UI_HEIGHT))

        # Grid cells
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                x = LEFT_MARGIN + c * CELL_W
                y = UI_HEIGHT + r * CELL_H
                pygame.draw.rect(self.bg_surface, COL_GRID, pygame.Rect(x, y, CELL_W-1, CELL_H-1))

    # ------------------------- Level control ----------------------------

    def reset_level(self, idx: int):
        self.level_i = idx % len(self.levels)
        self.energy = START_ENERGY
        self.grid = [[None for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
        self.plants.clear()
        self.zombies.clear()
        self.projectiles.clear()
        self.mowers = [LawnMower(row=r, x=LEFT_MARGIN - CELL_W//2) for r in range(GRID_ROWS)]
        self.cooldowns = {pt.name: 0.0 for pt in self.plant_types}
        self.selected = None

        self.level_elapsed = 0.0
        self.next_spawn_index = 0
        self.victory = False
        self.defeat = False
        self._regenerate_background()

    # ------------------------- Input -----------------------------------

    def handle_event(self, e: pygame.event.Event):
        if e.type == pygame.QUIT:
            self.running = False
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                self.selected = None
            elif e.key == pygame.K_h:
                self.hdr = not self.hdr
            elif e.key == pygame.K_p:
                self.paused = not self.paused
            elif e.key == pygame.K_n:
                if self.victory and self.level_i + 1 < len(self.levels):
                    self.reset_level(self.level_i + 1)
            elif e.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                hk = {pygame.K_1: 1, pygame.K_2: 2, pygame.K_3: 3}[e.key]
                for pt in self.plant_types:
                    if pt.hotkey == hk:
                        self.selected = pt
                        break
        elif e.type == pygame.MOUSEBUTTONDOWN:
            mx, my = e.pos
            if e.button == 1:  # left click
                # Check cards first
                for pt in self.plant_types:
                    r = self.card_rects[pt.name]
                    if r.collidepoint(mx, my):
                        self.selected = pt
                        return
                # Place plant
                cell = world_to_cell(mx, my)
                if cell and self.selected and not self.defeat and not self.victory:
                    row, col = cell
                    if not self.grid[row][col] and self.energy >= self.selected.cost:
                        # seed cooldown?
                        if self.level_elapsed >= self.cooldowns[self.selected.name]:
                            p = Plant(ptype=self.selected, row=row, col=col, hp=self.selected.max_hp)
                            self.plants.append(p)
                            self.grid[row][col] = p
                            self.energy -= self.selected.cost
                            self.cooldowns[self.selected.name] = self.level_elapsed + self.selected.cooldown
                    # else: not enough energy or occupied
            elif e.button == 3:  # right click -> remove plant
                cell = world_to_cell(mx, my)
                if cell:
                    row, col = cell
                    p = self.grid[row][col]
                    if p:
                        self.grid[row][col] = None
                        self.plants.remove(p)
                        refund = int(p.ptype.cost * REFUND_RATIO)
                        self.energy += refund

    # ------------------------- Update ----------------------------------

    def _spawn_scheduled(self, dt: float):
        lvl = self.levels[self.level_i]
        while self.next_spawn_index < len(lvl.schedule) and self.level_elapsed >= lvl.schedule[self.next_spawn_index].t:
            ev = lvl.schedule[self.next_spawn_index]
            self.next_spawn_index += 1
            row = ev.row if ev.row is not None else random.randint(0, GRID_ROWS-1)
            z = Zombie(ztype=ev.ztype, row=row, x=WIDTH + ZOMBIE_W + random.uniform(2, 10), hp=ev.ztype.max_hp)
            self.zombies.append(z)

    def _update_plants(self, dt: float):
        for p in self.plants[:]:
            # Shooting
            if p.ptype.shoot_interval > 0:
                if self.level_elapsed >= p.next_shoot_t:
                    # Check if any zombie is ahead in the same row
                    ahead = any((z.row == p.row and z.x > LEFT_MARGIN + p.col * CELL_W) for z in self.zombies)
                    if ahead:
                        # fire
                        cx = LEFT_MARGIN + p.col * CELL_W + CELL_W - 12
                        cy = UI_HEIGHT + p.row * CELL_H + CELL_H // 2
                        self.projectiles.append(Projectile(row=p.row, x=cx, y=cy, vx=PROJECTILE_SPEED_PX_S, damage=p.ptype.bullet_damage))
                        p.next_shoot_t = self.level_elapsed + p.ptype.shoot_interval
                    else:
                        # wait a bit and re-check soon
                        p.next_shoot_t = self.level_elapsed + 0.3

            # Generation (energy)
            if p.ptype.generate_interval > 0:
                if self.level_elapsed >= p.next_gen_t:
                    self.energy += p.ptype.generate_amount
                    p.next_gen_t = self.level_elapsed + p.ptype.generate_interval

            # Death cleanup
            if p.hp <= 0:
                self.grid[p.row][p.col] = None
                self.plants.remove(p)

    def _update_projectiles(self, dt: float):
        for pr in self.projectiles[:]:
            pr.x += pr.vx * dt
            if pr.x > WIDTH + 20:
                self.projectiles.remove(pr)
                continue
            # Collision with first zombie in row (leftmost)
            hit: Optional[Zombie] = None
            min_front = float('inf')
            for z in self.zombies:
                if z.row != pr.row:
                    continue
                zr = z.rect()
                if pr.rect().colliderect(zr):
                    # keep nearest to projectile
                    if zr.right < min_front:
                        min_front = zr.right
                        hit = z
            if hit:
                hit.hp -= pr.damage
                pr.alive = False
                if pr in self.projectiles:
                    self.projectiles.remove(pr)

    def _update_zombies(self, dt: float):
        for z in self.zombies[:]:
            # Check plant collision in its row (same column area)
            z.chewing = False
            zr = z.rect()
            # Identify plant directly overlapping
            target_plant: Optional[Plant] = None
            # plant columns whose rect x-range overlaps with zombie rect
            c_start = max(0, int((zr.left - LEFT_MARGIN) // CELL_W) - 1)
            c_end = min(GRID_COLS-1, int((zr.right - LEFT_MARGIN) // CELL_W) + 1)
            for c in range(c_start, c_end+1):
                p = self.grid[z.row][c]
                if p and zr.colliderect(p.rect()):
                    target_plant = p
                    break

            if target_plant:
                z.chewing = True
                # damage over time
                target_plant.hp -= int(z.ztype.dps * dt)
                if target_plant.hp <= 0:
                    # plant removed in _update_plants
                    pass
            else:
                # walk
                z.x -= z.ztype.speed * dt

            # Lawn mowers (trigger when z reaches left edge of lane)
            if z.x - ZOMBIE_W <= LEFT_MARGIN - 6:
                mower = self.mowers[z.row]
                if not mower.spent and not mower.active:
                    mower.active = True
                else:
                    # If mower already spent/active and a zombie reaches the end, player loses
                    self.defeat = True

            # Death
            if z.hp <= 0:
                self.zombies.remove(z)

        # Update mowers
        for m in self.mowers:
            if m.active:
                m.x += 300 * dt
                # kill zombies in its path
                mr = m.rect()
                for z in self.zombies[:]:
                    if z.row == m.row and mr.colliderect(z.rect()):
                        self.zombies.remove(z)
                if m.x > WIDTH + 60:
                    m.active = False
                    m.spent = True

    def _check_victory(self):
        lvl = self.levels[self.level_i]
        done_spawning = self.next_spawn_index >= len(lvl.schedule)
        if done_spawning and not self.zombies and not self.defeat:
            if not self.victory:
                self.energy += lvl.prize
            self.victory = True

    def update(self, dt: float):
        if self.paused or self.defeat or self.victory:
            return
        self.level_elapsed += dt
        self._spawn_scheduled(dt)
        self._update_plants(dt)
        self._update_projectiles(dt)
        self._update_zombies(dt)
        self._check_victory()

    # ------------------------- Render ----------------------------------

    def _draw_ui_cards(self, surf: pygame.Surface):
        for pt in self.plant_types:
            r = self.card_rects[pt.name]
            # Background
            base = COL_CARD_SEL if self.selected == pt else COL_CARD
            pygame.draw.rect(surf, base, r, border_radius=6)

            # Name & cost
            draw_text(surf, f"{pt.name}", self.font_big, COL_TEXT, (r.x+8, r.y+6))
            draw_text(surf, f"{pt.cost} ⚡", self.font, COL_YELLOW, (r.x+8, r.y+28))
            draw_text(surf, f"[{pt.hotkey}]", self.font_small, COL_TEXT, (r.right-28, r.y+8))

            # Cooldown mask
            ready_in = max(0.0, self.cooldowns[pt.name] - self.level_elapsed)
            if ready_in > 0.0:
                frac = clamp(ready_in / pt.cooldown, 0.0, 1.0)
                h = int(r.h * frac)
                cd_rect = pygame.Rect(r.x, r.bottom - h, r.w, h)
                cd = pygame.Surface((r.w, h), pygame.SRCALPHA)
                cd.fill(SEED_COOLDOWN_TINT)
                surf.blit(cd, cd_rect)

    def _draw_grid_contents(self, surf: pygame.Surface, glow_points: List[Tuple[int, int, int]]):
        # Plants
        for p in self.plants:
            pr = p.rect()
            pygame.draw.rect(surf, p.ptype.color, pr, border_radius=8)
            # HP bar
            hp_frac = clamp(p.hp / p.ptype.max_hp, 0.0, 1.0)
            hp_w = int(pr.w * hp_frac)
            pygame.draw.rect(surf, (40,40,40), pygame.Rect(pr.x, pr.bottom-6, pr.w, 6), border_radius=3)
            pygame.draw.rect(surf, COL_GREEN, pygame.Rect(pr.x, pr.bottom-6, hp_w, 6), border_radius=3)

            # Add glow point (for generator and shooter as emissive)
            if self.hdr and (p.ptype.generate_interval > 0 or p.ptype.shoot_interval > 0):
                cx = pr.centerx
                cy = pr.centery
                glow_points.append((cx, cy, 26))

        # Projectiles
        for pr in self.projectiles:
            pygame.draw.circle(surf, COL_GREEN, (int(pr.x), int(pr.y)), PROJECTILE_RADIUS)
            if self.hdr:
                glow_points.append((int(pr.x), int(pr.y), 24))

        # Zombies
        for z in self.zombies:
            zr = z.rect()
            color = z.ztype.color
            pygame.draw.rect(surf, color, zr, border_radius=6)
            # HP bar
            hp_frac = clamp(z.hp / z.ztype.max_hp, 0.0, 1.0)
            pygame.draw.rect(surf, (40,40,40), pygame.Rect(zr.x, zr.y-6, zr.w, 5), border_radius=2)
            pygame.draw.rect(surf, COL_DANGER, pygame.Rect(zr.x, zr.y-6, int(zr.w*hp_frac), 5), border_radius=2)
            # chewing indicator
            if z.chewing:
                pygame.draw.rect(surf, COL_ORANGE, zr.inflate(-8, -8), width=2, border_radius=6)

        # Mowers
        for m in self.mowers:
            color = (180, 180, 180) if not m.spent else (90, 90, 90)
            pygame.draw.rect(surf, color, m.rect(), border_radius=8)
            pygame.draw.circle(surf, (50,50,50), (m.rect().x + 10, m.rect().bottom), 6)
            pygame.draw.circle(surf, (50,50,50), (m.rect().x + m.rect().w - 10, m.rect().bottom), 6)

    def _draw_hdr_glow(self, surf: pygame.Surface, glow_points: List[Tuple[int,int,int]]):
        if not self.hdr or not glow_points:
            return
        glow = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        for (x, y, r) in glow_points:
            pygame.draw.circle(glow, (255, 255, 200, 40), (x, y), r)
        # cheap blur: downscale then upscale
        small = pygame.transform.smoothscale(glow, (max(1, surf.get_width()//4), max(1, surf.get_height()//4)))
        blurred = pygame.transform.smoothscale(small, surf.get_size())
        surf.blit(blurred, (0, 0), special_flags=pygame.BLEND_ADD)

    def draw(self):
        # Base layers
        self.screen.blit(self.bg_surface, (0, 0))

        # UI cards
        self._draw_ui_cards(self.screen)

        # Grid contents
        glow_points: List[Tuple[int,int,int]] = []
        self._draw_grid_contents(self.screen, glow_points)

        # Post FX
        self._draw_hdr_glow(self.screen, glow_points)

        # Top-right HUD info
        lvl = self.levels[self.level_i]
        draw_text(self.screen, f"Level: {lvl.name}", self.font_big, COL_TEXT, (WIDTH-190, 10))
        draw_text(self.screen, f"Energy: {self.energy}", self.font_big, COL_YELLOW, (WIDTH-190, 34))
        draw_text(self.screen, f"HDR: {'ON' if self.hdr else 'OFF'}  FPS: {int(self.clock.get_fps())}", self.font_small, COL_TEXT, (WIDTH-190, 58))

        # Selection hint
        if self.selected:
            draw_text(self.screen, f"Selected: {self.selected.name} — cost {self.selected.cost}", self.font, COL_TEXT, (10, HEIGHT-22))

        # Victory/Defeat banners
        banner = None
        if self.victory:
            banner = ("VICTORY! Press N for next level", COL_GREEN)
        elif self.defeat:
            banner = ("DEFEAT! Press R to retry level", COL_DANGER)

        if banner:
            text, color = banner
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 120))
            self.screen.blit(overlay, (0, 0))
            draw_text(self.screen, text, self.font_big, color, (WIDTH//2, HEIGHT//2), center=True)

    # ------------------------- Main Loop --------------------------------

    def run(self):
        # Immediately reset level 0
        self.reset_level(0)
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            for e in pygame.event.get():
                # Quick retry
                if e.type == pygame.KEYDOWN and e.key == pygame.K_r and (self.defeat or self.victory):
                    self.reset_level(self.level_i)
                self.handle_event(e)

            self.update(dt)
            self.draw()
            pygame.display.flip()


def main():
    pygame.init()
    try:
        screen = pygame.display.set_mode((WIDTH, HEIGHT))
    except pygame.error as ex:
        print("Failed to create Pygame window:", ex)
        print("If running in a headless environment, run locally on your machine.")
        return
    game = Game(screen)
    game.run()
    pygame.quit()


if __name__ == "__main__":
    main()
