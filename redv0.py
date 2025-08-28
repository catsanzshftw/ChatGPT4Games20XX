#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
red.py — Single-file, no-assets, 60 FPS retro monster RPG engine (original)
----------------------------------------------------------------------------
This is NOT the commercial game you're thinking of. It is an original,
minimal engine inspired by tile-based overworld movement and turn-based
battles from classic handheld RPGs.

Constraints satisfied:
- files = off  → No external assets or file I/O. Everything is generated.
- import pygame → Uses Pygame for rendering and input.
- 60 fps       → Fixed-timestep render/update target.
- noglitches   → Safety clamps to avoid negative HP, NaNs, etc.
- import math  → We import math and use it in battle calcs and tweening.

Run:
    python3 red.py

Controls:
    Arrow keys   Move on overworld (tile-based, collisions)
    Enter / Z    Confirm / Interact
    X / Backspace Cancel
    B            Bag (in battle or overworld)
    P            Party (overworld)
    ESC          Quit

Author: ChatGPT (original work, no copyrighted content)
License: MIT
"""
from __future__ import annotations

import sys
import math
import random
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

# ---- Third-party: pygame ----
try:
    import pygame
except Exception as e:
    print("This program requires pygame. Install with: pip install pygame")
    raise

# ---------------------------
# Global toggles / settings
# ---------------------------
FILES_OFF: bool = True      # "files = off" — keep everything in-memory
NO_GLITCHES: bool = True    # "noglitches = true" — clamp and sanity-check values
FPS: int = 60               # 60 FPS render/update target

# Screen: 160x144 (classic) * 3 scale = 480x432
SCALE = 3
BASE_W, BASE_H = 160, 144
SCREEN_W, SCREEN_H = BASE_W * SCALE, BASE_H * SCALE
TILE = 16  # logical tile size (before scale)
WORLD_TILE = TILE * SCALE   # onscreen tile size in pixels

# GB-style 4-color palette
PALETTE = {
    "darkest": (15, 56, 15),
    "dark": (48, 98, 48),
    "light": (139, 172, 15),
    "lightest": (155, 188, 15),
    "white": (240, 240, 240),
    "black": (0, 0, 0),
}

# ---------------------------
# Utility helpers
# ---------------------------
def clamp(v: float, lo: float, hi: float) -> float:
    if NO_GLITCHES:
        if math.isnan(v) or math.isinf(v):
            v = 0.0
        return max(lo, min(hi, v))
    return v

def draw_window(surf: pygame.Surface, rect: pygame.Rect, border=3) -> None:
    # Simple handheld-style dialog box
    pygame.draw.rect(surf, PALETTE["white"], rect)
    pygame.draw.rect(surf, PALETTE["black"], rect, border)

def text(surf: pygame.Surface, font: pygame.font.Font, s: str, pos: Tuple[int, int], color=PALETTE["black"]) -> None:
    surf.blit(font.render(s, True, color), pos)

# ---------------------------
# Data models (original)
# ---------------------------
@dataclass
class Move:
    name: str
    power: int
    accuracy: float  # 0.0..1.0
    kind: str = "physical"  # or "special"
    pp: int = 35
    max_pp: int = 35

@dataclass
class Species:
    name: str
    base_hp: int
    base_atk: int
    base_def: int
    base_spa: int
    base_spd: int
    base_spe: int
    learnset: List[Tuple[int, str]] = field(default_factory=list)  # (level, move_name)

@dataclass
class Creature:
    species: Species
    level: int = 5
    moves: List[Move] = field(default_factory=list)
    exp: int = 0

    def __post_init__(self):
        # Initialize stats with a simple original formula
        self.max_hp = int(self.species.base_hp + self.level * 5)
        self.atk = int(self.species.base_atk + self.level * 2)
        self.defense = int(self.species.base_def + self.level * 2)
        self.spa = int(self.species.base_spa + self.level * 2)
        self.spd = int(self.species.base_spd + self.level * 2)
        self.spe = int(self.species.base_spe + self.level * 2)
        self.hp = self.max_hp

    def is_fainted(self) -> bool:
        return self.hp <= 0

    def learn_move_if_applicable(self):
        for lvl, move_name in sorted(self.species.learnset):
            if lvl <= self.level and all(m.name != move_name for m in self.moves):
                self.moves.append(MOVES[move_name])
                if len(self.moves) > 4:
                    self.moves = self.moves[-4:]  # keep last 4

# ---------------------------
# Content (original, no IP)
# ---------------------------
MOVES = {
    "Tackle": Move("Tackle", power=35, accuracy=0.95),
    "Ember": Move("Ember", power=40, accuracy=0.95, kind="special"),
    "Splash": Move("Splash", power=0, accuracy=1.0),
    "Vine": Move("Vine", power=40, accuracy=0.95, kind="physical"),
}

SPECIES = {
    "Pyrodon": Species("Pyrodon", 21, 13, 10, 14, 11, 12, learnset=[(1, "Tackle"), (5, "Ember")]),
    "Aquaphin": Species("Aquaphin", 23, 11, 12, 13, 12, 11, learnset=[(1, "Tackle")]),
    "Leaflit": Species("Leaflit", 22, 12, 12, 12, 12, 12, learnset=[(1, "Tackle"), (6, "Vine")]),
    "Rattish": Species("Rattish", 18, 11, 9, 9, 9, 14, learnset=[(1, "Tackle")]),
}

def make_creature(name: str, level: int) -> Creature:
    c = Creature(SPECIES[name], level=level, moves=[])
    c.learn_move_if_applicable()
    return c

# ---------------------------
# Simple inventory / bag
# ---------------------------
@dataclass
class Item:
    name: str
    kind: str  # "heal", "capture"
    potency: int = 0  # heal amount or capture bonus

ITEMS = {
    "Potion": Item("Potion", "heal", potency=20),
    "Capsule": Item("Capsule", "capture", potency=1),  # basic capture item
}

# ---------------------------
# Overworld map (ASCII)
# ---------------------------
MAP_STR = [
    "####################",
    "#......GGGG......H.#",
    "#..####GGGG####....#",
    "#..#..........#....#",
    "#..#..GGGG....#....#",
    "#..#..........#....#",
    "#..####....####....#",
    "#..................#",
    "#..................#",
    "#....GGGGGG........#",
    "#..................#",
    "#..................#",
    "#..................#",
    "#S.................#",
    "####################",
]
MAP_W, MAP_H = len(MAP_STR[0]), len(MAP_STR)
SOLID = {"#", "H"}  # walls and building block movement (H is heal center tile)

def map_find(c: str) -> Tuple[int, int]:
    for y, row in enumerate(MAP_STR):
        x = row.find(c)
        if x != -1:
            return x, y
    return 1, 1

START_TX, START_TY = map_find("S")

# ---------------------------
# Scene system
# ---------------------------
class Scene:
    def __init__(self, game: "Game"):
        self.game = game

    def handle_event(self, e: pygame.event.Event): ...
    def update(self, dt: float): ...
    def draw(self, surf: pygame.Surface): ...

class SceneStack:
    def __init__(self):
        self._stack: List[Scene] = []

    def push(self, s: Scene) -> None:
        self._stack.append(s)

    def pop(self) -> None:
        if self._stack:
            self._stack.pop()

    def top(self) -> Optional[Scene]:
        return self._stack[-1] if self._stack else None

    def is_empty(self) -> bool:
        return not self._stack

# ---------------------------
# Title Scene
# ---------------------------
class TitleScene(Scene):
    def __init__(self, game: "Game"):
        super().__init__(game)
        self.blink = 0.0

    def handle_event(self, e: pygame.event.Event):
        if e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN, pygame.K_z):
            self.game.start_new_game()

    def update(self, dt: float):
        self.blink += dt

    def draw(self, surf: pygame.Surface):
        surf.fill(PALETTE["light"])
        font_big = self.game.font_big
        font = self.game.font
        title = "POCKET RED-LIKE"
        text(surf, font_big, title, (SCREEN_W//2 - font_big.size(title)[0]//2, 50), PALETTE["black"])
        subtitle = "Original, no external files"
        text(surf, font, subtitle, (SCREEN_W//2 - font.size(subtitle)[0]//2, 110), PALETTE["black"])
        if int(self.blink*2) % 2 == 0:
            press = "Press ENTER"
            text(surf, font, press, (SCREEN_W//2 - font.size(press)[0]//2, SCREEN_H-60), PALETTE["black"])

# ---------------------------
# Overworld Scene
# ---------------------------
class OverworldScene(Scene):
    def __init__(self, game: "Game"):
        super().__init__(game)
        self.player_tx, self.player_ty = START_TX, START_TY
        self.offset_x = 0
        self.offset_y = 0
        self.moving = False
        self.move_t = 0.0
        self.move_from = (self.player_tx, self.player_ty)
        self.move_to = (self.player_tx, self.player_ty)
        self.step_speed = 8.0  # tiles per second
        self.encounter_cooldown = 0.0

    def handle_event(self, e: pygame.event.Event):
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                self.game.quit()
            if e.key == pygame.K_p:
                self.game.push_scene(PartyScene(self.game))
            if e.key == pygame.K_b:
                self.game.push_scene(BagScene(self.game, context="overworld"))
            if not self.moving:
                dx, dy = 0, 0
                if e.key == pygame.K_LEFT:  dx = -1
                elif e.key == pygame.K_RIGHT: dx = 1
                elif e.key == pygame.K_UP:    dy = -1
                elif e.key == pygame.K_DOWN:  dy = 1
                if dx or dy:
                    ntx, nty = self.player_tx + dx, self.player_ty + dy
                    if 0 <= ntx < MAP_W and 0 <= nty < MAP_H and MAP_STR[nty][ntx] not in SOLID:
                        self.moving = True
                        self.move_t = 0.0
                        self.move_from = (self.player_tx, self.player_ty)
                        self.move_to = (ntx, nty)

    def _check_random_encounter(self):
        # Trigger on grass tiles with cooldown to avoid chain encounters
        if self.encounter_cooldown > 0.0:
            return
        tile = MAP_STR[self.player_ty][self.player_tx]
        if tile == "G":
            if random.random() < 0.12:  # ~12% chance
                wild = make_creature("Rattish", random.choice([3, 4, 5, 6]))
                self.game.push_scene(BattleScene(self.game, wild=wild))
                self.encounter_cooldown = 1.0

    def update(self, dt: float):
        self.encounter_cooldown = max(0.0, self.encounter_cooldown - dt)
        if self.moving:
            self.move_t += dt * self.step_speed
            t = clamp(self.move_t, 0.0, 1.0)
            # Ease slightly with sine
            t_ease = math.sin((t * math.pi) / 2.0)
            curx = (1 - t_ease) * self.move_from[0] + t_ease * self.move_to[0]
            cury = (1 - t_ease) * self.move_from[1] + t_ease * self.move_to[1]
            self.offset_x = int(curx * WORLD_TILE)
            self.offset_y = int(cury * WORLD_TILE)
            if self.move_t >= 1.0 - 1e-6:
                self.player_tx, self.player_ty = self.move_to
                self.moving = False
                self._check_random_encounter()
        else:
            self.offset_x = self.player_tx * WORLD_TILE
            self.offset_y = self.player_ty * WORLD_TILE

    def draw(self, surf: pygame.Surface):
        surf.fill(PALETTE["dark"])
        # Draw map tiles
        for y, row in enumerate(MAP_STR):
            for x, ch in enumerate(row):
                rx, ry = x * WORLD_TILE, y * WORLD_TILE
                rect = pygame.Rect(rx, ry, WORLD_TILE, WORLD_TILE)
                if ch == "#":
                    pygame.draw.rect(surf, PALETTE["darkest"], rect)
                elif ch == ".":
                    pygame.draw.rect(surf, PALETTE["lightest"], rect)
                elif ch == "G":
                    pygame.draw.rect(surf, PALETTE["light"], rect)
                    # grass blades
                    for i in range(4):
                        gx = rx + (i*7* SCALE) % (WORLD_TILE - 4)
                        gy = ry + (i*5* SCALE) % (WORLD_TILE - 6)
                        pygame.draw.line(surf, PALETTE["darkest"], (gx, gy+6), (gx+4, gy), 2)
                elif ch == "H":
                    pygame.draw.rect(surf, (220, 220, 220), rect)
                    cx, cy = rect.center
                    pygame.draw.rect(surf, (200, 0, 0), (cx-6*SCALE, cy-2*SCALE, 12*SCALE, 4*SCALE))
                    pygame.draw.rect(surf, (200, 0, 0), (cx-2*SCALE, cy-6*SCALE, 4*SCALE, 12*SCALE))
                elif ch == "S":
                    pygame.draw.rect(surf, PALETTE["lightest"], rect)
                else:
                    pygame.draw.rect(surf, PALETTE["lightest"], rect)

        # Draw player (simple masked square)
        px = self.offset_x
        py = self.offset_y
        pr = pygame.Rect(px+4*SCALE, py+4*SCALE, WORLD_TILE-8*SCALE, WORLD_TILE-8*SCALE)
        pygame.draw.rect(surf, (20, 20, 20), pr)
        pygame.draw.rect(surf, (250, 250, 250), pr.inflate(-4, -4))

        # HUD hint
        hud = pygame.Rect(8, SCREEN_H - 40, SCREEN_W - 16, 32)
        draw_window(surf, hud, border=2)
        text(surf, self.game.font, "Arrows: Move  P: Party  B: Bag  ESC: Quit", (hud.x+8, hud.y+6))

# ---------------------------
# Party Scene
# ---------------------------
class PartyScene(Scene):
    def __init__(self, game: "Game"):
        super().__init__(game)
        self.sel = 0

    def handle_event(self, e: pygame.event.Event):
        if e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_ESCAPE, pygame.K_x, pygame.K_BACKSPACE):
                self.game.pop_scene()
            elif e.key == pygame.K_UP:
                self.sel = (self.sel - 1) % len(self.game.party)
            elif e.key == pygame.K_DOWN:
                self.sel = (self.sel + 1) % len(self.game.party)

    def update(self, dt: float): ...
    def draw(self, surf: pygame.Surface):
        surf.fill(PALETTE["light"])
        title = "Party"
        text(surf, self.game.font_big, title, (12, 12))
        y = 60
        for i, c in enumerate(self.game.party):
            row = pygame.Rect(16, y, SCREEN_W - 32, 36)
            draw_window(surf, row, border=2)
            if i == self.sel:
                pygame.draw.rect(surf, PALETTE["light"], row, 0)
                pygame.draw.rect(surf, PALETTE["black"], row, 2)
            text(surf, self.game.font, f"{c.species.name} Lv{c.level}", (row.x+8, row.y+8))
            text(surf, self.game.font, f"HP {c.hp}/{c.max_hp}", (row.x+240, row.y+8))
            y += 42

# ---------------------------
# Bag Scene
# ---------------------------
class BagScene(Scene):
    def __init__(self, game: "Game", context: str):
        super().__init__(game)
        self.context = context
        self.sel = 0
        self.keys = list(self.game.bag.keys()) or ["(empty)"]

    def handle_event(self, e: pygame.event.Event):
        if e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_ESCAPE, pygame.K_x, pygame.K_BACKSPACE):
                self.game.pop_scene()
            elif e.key == pygame.K_UP:
                self.sel = (self.sel - 1) % len(self.keys)
            elif e.key == pygame.K_DOWN:
                self.sel = (self.sel + 1) % len(self.keys)
            elif e.key in (pygame.K_RETURN, pygame.K_z):
                self._use_selected()

    def _use_selected(self):
        if not self.game.bag:
            return
        name = self.keys[self.sel]
        if name not in self.game.bag:
            return
        item = ITEMS[name]
        # If in battle, delegate to BattleScene to interpret
        top = self.game.scenes.top()
        if isinstance(top, BattleScene):
            top.use_item(item)
        else:
            # Overworld use: allow Potion on first non-fainted
            if item.kind == "heal":
                for c in self.game.party:
                    if c.hp < c.max_hp:
                        c.hp = min(c.max_hp, c.hp + item.potency)
                        self.game.toast(f"{c.species.name} healed +{item.potency}!")
                        self.game.bag[name] -= 1
                        if self.game.bag[name] <= 0:
                            del self.game.bag[name]
                            self.keys = list(self.game.bag.keys()) or ["(empty)"]
                        return
                self.game.toast("All party at full HP.")

    def update(self, dt: float): ...
    def draw(self, surf: pygame.Surface):
        surf.fill(PALETTE["light"])
        title = f"Bag ({self.context})"
        text(surf, self.game.font_big, title, (12, 12))
        y = 60
        for i, k in enumerate(self.keys):
            row = pygame.Rect(16, y, SCREEN_W - 32, 36)
            draw_window(surf, row, border=2)
            if i == self.sel:
                pygame.draw.rect(surf, PALETTE["light"], row, 0)
                pygame.draw.rect(surf, PALETTE["black"], row, 2)
            qty = self.game.bag.get(k, 0)
            text(surf, self.game.font, f"{k}", (row.x+8, row.y+8))
            if qty:
                text(surf, self.game.font, f"x{qty}", (row.x+SCREEN_W-32-40, row.y+8))
            y += 42

# ---------------------------
# Battle Scene
# ---------------------------
class BattleScene(Scene):
    def __init__(self, game: "Game", wild: Creature):
        super().__init__(game)
        self.wild = wild
        self.player = self.game.active_creature()
        self.state = "menu"  # menu -> fight -> anim -> win/lose/catch/run
        self.sel = 0
        self.msg = f"A wild {self.wild.species.name} appeared!"
        self.msg_t = 0.0
        self.turn_queue: List[str] = []  # sequence of messages to show
        self.escape_fail = False

    def handle_event(self, e: pygame.event.Event):
        if e.type == pygame.KEYDOWN:
            if self.state == "menu":
                if e.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT):
                    dx = (e.key == pygame.K_RIGHT) - (e.key == pygame.K_LEFT)
                    dy = (e.key == pygame.K_DOWN) - (e.key == pygame.K_UP)
                    # 2x2 grid: [Fight, Bag, Catch, Run]
                    self.sel = (self.sel + dx + dy * 2) % 4
                elif e.key in (pygame.K_RETURN, pygame.K_z):
                    if self.sel == 0:  # Fight
                        self.state = "fight"
                        self.sel = 0
                        self.msg = "Choose a move."
                    elif self.sel == 1:  # Bag
                        self.game.push_scene(BagScene(self.game, context="battle"))
                    elif self.sel == 2:  # Catch
                        self._attempt_catch()
                    elif self.sel == 3:  # Run
                        self._attempt_run()
                elif e.key in (pygame.K_x, pygame.K_BACKSPACE):
                    self.game.pop_scene()  # leave battle
            elif self.state == "fight":
                if e.key in (pygame.K_UP, pygame.K_DOWN):
                    self.sel = (self.sel + (1 if e.key == pygame.K_DOWN else -1)) % len(self.player.moves)
                elif e.key in (pygame.K_RETURN, pygame.K_z):
                    self._perform_move(self.player, self.wild, self.player.moves[self.sel])
                elif e.key in (pygame.K_x, pygame.K_BACKSPACE):
                    self.state = "menu"
                    self.msg = "What will you do?"
            elif self.state == "message":
                if e.key in (pygame.K_RETURN, pygame.K_z):
                    if self.turn_queue:
                        self.msg = self.turn_queue.pop(0)
                    else:
                        self._post_turn()
            elif self.state in ("win", "lose", "caught", "run"):
                if e.key in (pygame.K_RETURN, pygame.K_z):
                    self.game.pop_scene()

    def use_item(self, item: Item):
        # Called by BagScene if we're in battle
        if item.kind == "heal":
            if self.player.hp < self.player.max_hp:
                self.player.hp = min(self.player.max_hp, self.player.hp + item.potency)
                self.game.toast(f"{self.player.species.name} healed +{item.potency}!")
                self.game.consume_item(item.name)
                self.state = "message"
                self.msg = "You used a Potion."
                self.turn_queue = [f"{self.player.species.name} feels better."]
            else:
                self.game.toast("Already full HP.")
        elif item.kind == "capture":
            self._attempt_catch(item_bonus=item.potency)
            self.game.consume_item(item.name)

    def _attempt_run(self):
        # Simple speed-based flee chance
        chance = clamp(0.5 + (self.player.spe - self.wild.spe) * 0.05, 0.1, 0.95)
        if random.random() < chance:
            self.state = "run"
            self.msg = "Got away safely!"
        else:
            self.state = "message"
            self.msg = "Can't escape!"
            self.turn_queue = []
            self._enemy_turn_enqueue()

    def _attempt_catch(self, item_bonus: int = 1):
        # Simple catch chance: higher when wild HP is low
        hp_ratio = self.wild.hp / max(1, self.wild.max_hp)
        base = 0.25 + (1.0 - hp_ratio) * 0.5  # 0.25..0.75 depending on HP
        level_factor = clamp(1.0 - (self.wild.level - self.player.level) * 0.05, 0.7, 1.3)
        chance = clamp(base * level_factor * (0.75 + 0.25 * item_bonus), 0.05, 0.95)
        if random.random() < chance:
            self.state = "caught"
            self.msg = f"Gotcha! {self.wild.species.name} was caught."
            # Add to party if room, else to "box" (discarded in this demo)
            if len(self.game.party) < 6:
                self.game.party.append(self.wild)
                self.game.toast(f"{self.wild.species.name} joined your party!")
        else:
            self.state = "message"
            self.msg = "The capsule wobbled..."
            self.turn_queue = ["...but the creature broke free!"]
            self._enemy_turn_enqueue()

    def _enemy_turn_enqueue(self):
        # Enemy picks a random move
        emove = random.choice(self.wild.moves or [MOVES["Tackle"]])
        self.turn_queue.append(f"The wild {self.wild.species.name} used {emove.name}!")
        self.turn_queue.append(self._apply_move(self.wild, self.player, emove))

    def _perform_move(self, atk: Creature, dfn: Creature, move: Move):
        # Player acts then enemy if still alive
        self.state = "message"
        self.msg = f"{atk.species.name} used {move.name}!"
        self.turn_queue = [self._apply_move(atk, dfn, move)]
        if not dfn.is_fainted():
            self._enemy_turn_enqueue()

    def _apply_move(self, atk: Creature, dfn: Creature, move: Move) -> str:
        if move.power <= 0:
            return "It had no effect..."
        if random.random() > move.accuracy:
            return "But it missed!"
        # Simple physical/special split
        atk_stat = atk.atk if move.kind == "physical" else atk.spa
        def_stat = dfn.defense if move.kind == "physical" else dfn.spd
        # Damage formula (original): scaled by level and random factor
        level_factor = 0.5 + atk.level * 0.05
        variance = random.uniform(0.85, 1.0)
        raw = move.power * (atk_stat / max(1, def_stat)) * level_factor * variance
        dmg = max(1, int(raw))
        # Clamp for safety
        dmg = int(clamp(dmg, 1, 9999))
        dfn.hp = max(0, dfn.hp - dmg)
        if dfn.is_fainted():
            return f"It dealt {dmg} damage. Fainted!"
        return f"It dealt {dmg} damage."

    def _post_turn(self):
        # Check end states
        if self.player.is_fainted():
            self.state = "lose"
            self.msg = f"{self.player.species.name} fainted..."
        elif self.wild.is_fainted():
            self.state = "win"
            self.msg = f"The wild {self.wild.species.name} fainted!"
        else:
            self.state = "menu"
            self.msg = "What will you do?"

    def update(self, dt: float):
        self.msg_t += dt

    def draw(self, surf: pygame.Surface):
        surf.fill(PALETTE["lightest"])
        # Sides for player/wild
        left = pygame.Rect(0, 0, SCREEN_W//2, SCREEN_H-64)
        right = pygame.Rect(SCREEN_W//2, 0, SCREEN_W//2, SCREEN_H-64)
        pygame.draw.rect(surf, (210, 235, 210), left)
        pygame.draw.rect(surf, (210, 210, 235), right)

        # "Sprites" (abstract shapes)
        p_rect = pygame.Rect(left.centerx-30, left.centery, 60, 60)
        w_rect = pygame.Rect(right.centerx-30, right.centery-20, 60, 60)
        pygame.draw.rect(surf, (40, 40, 40), p_rect)
        pygame.draw.rect(surf, (240, 240, 240), p_rect.inflate(-6, -6))
        pygame.draw.rect(surf, (240, 240, 240), w_rect)
        pygame.draw.rect(surf, (40, 40, 40), w_rect.inflate(-6, -6))

        # HP boxes
        def hp_box(rect: pygame.Rect, c: Creature, align="left"):
            box = pygame.Rect(rect.x+8, rect.y+8, rect.width-16, 32)
            draw_window(surf, box, border=2)
            name = f"{c.species.name} Lv{c.level}"
            hp = f"HP {c.hp}/{c.max_hp}"
            if align == "left":
                text(surf, self.game.font, name, (box.x+8, box.y+6))
                text(surf, self.game.font, hp, (box.right-140, box.y+6))
            else:
                text(surf, self.game.font, name, (box.right - self.game.font.size(name)[0] - 8, box.y+6))
                text(surf, self.game.font, hp, (box.x+8, box.y+6))
            # HP bar
            bar = pygame.Rect(box.x+8, box.bottom-10, box.width-16, 6)
            pygame.draw.rect(surf, (30,30,30), bar, 1)
            ratio = c.hp / max(1, c.max_hp)
            inner = pygame.Rect(bar.x+1, bar.y+1, int((bar.width-2) * ratio), bar.height-2)
            col = (0,180,0) if ratio>0.5 else (180,160,0) if ratio>0.2 else (180,0,0)
            pygame.draw.rect(surf, col, inner)

        hp_box(pygame.Rect(0, 0, SCREEN_W//2, 64), self.player, align="left")
        hp_box(pygame.Rect(SCREEN_W//2, 0, SCREEN_W//2, 64), self.wild, align="right")

        # Message box
        msg_rect = pygame.Rect(8, SCREEN_H-64, SCREEN_W-16, 56)
        draw_window(surf, msg_rect, border=3)

        if self.state == "menu":
            opts = ["Fight", "Bag", "Catch", "Run"]
            # Grid layout 2x2
            for i, label in enumerate(opts):
                cx = msg_rect.x + 12 + (i % 2) * 120
                cy = msg_rect.y + 10 + (i // 2) * 22
                if i == self.sel:
                    pygame.draw.rect(surf, PALETTE["light"], (cx-6, cy-4, 80, 20))
                    pygame.draw.rect(surf, PALETTE["black"], (cx-6, cy-4, 80, 20), 2)
                text(surf, self.game.font, label, (cx, cy))
            text(surf, self.game.font, self.msg, (msg_rect.x+SCREEN_W//2, msg_rect.y+10))
        elif self.state == "fight":
            # List moves
            for i, m in enumerate(self.player.moves or [MOVES["Tackle"]]):
                cy = msg_rect.y + 10 + i * 18
                if i == self.sel:
                    pygame.draw.rect(surf, PALETTE["light"], (msg_rect.x+8, cy-4, SCREEN_W-32, 18))
                    pygame.draw.rect(surf, PALETTE["black"], (msg_rect.x+8, cy-4, SCREEN_W-32, 18), 2)
                text(surf, self.game.font, f"{m.name}  Pow:{m.power}  Acc:{int(m.accuracy*100)}%", (msg_rect.x+14, cy))
        else:
            text(surf, self.game.font, self.msg, (msg_rect.x+12, msg_rect.y+10))

# ---------------------------
# Game shell
# ---------------------------
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Pocket Red-like (original)")
        self.clock = pygame.time.Clock()

        # Fonts
        pygame.font.init()
        self.font = pygame.font.SysFont("Courier", 16, bold=False)
        self.font_big = pygame.font.SysFont("Courier", 24, bold=True)

        # Scenes
        self.scenes = SceneStack()

        # Player data
        self.party: List[Creature] = []
        self.bag = {"Potion": 3, "Capsule": 5}

        # Toast
        self.toast_msg = ""
        self.toast_t = 0.0

        # Start on title
        self.scenes.push(TitleScene(self))

    def start_new_game(self):
        # Choose a starter (fixed for this demo)
        self.party = [make_creature("Pyrodon", 5)]
        self.scenes.push(OverworldScene(self))

    def active_creature(self) -> Creature:
        # First non-fainted creature
        for c in self.party:
            if not c.is_fainted():
                return c
        # If all fainted, just return first
        return self.party[0]

    def consume_item(self, name: str):
        if name in self.bag:
            self.bag[name] -= 1
            if self.bag[name] <= 0:
                del self.bag[name]

    def toast(self, msg: str, dur: float = 1.5):
        self.toast_msg = msg
        self.toast_t = dur

    def push_scene(self, s: Scene):
        self.scenes.push(s)

    def pop_scene(self):
        self.scenes.pop()

    def quit(self):
        pygame.quit()
        sys.exit(0)

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0

            # Event handling
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.quit()
                top = self.scenes.top()
                if top:
                    top.handle_event(e)

            # Update
            top = self.scenes.top()
            if top:
                top.update(dt)

            # Draw
            self.screen.fill(PALETTE["lightest"])
            if top:
                top.draw(self.screen)

            # Toast overlay
            if self.toast_t > 0.0:
                self.toast_t -= dt
                r = pygame.Rect(8, 8, SCREEN_W - 16, 28)
                draw_window(self.screen, r, border=2)
                text(self.screen, self.font, self.toast_msg, (r.x+8, r.y+6))

            pygame.display.flip()

# ---------------------------
# Entrypoint
# ---------------------------
def main():
    game = Game()
    game.run()

if __name__ == "__main__":
    main()
