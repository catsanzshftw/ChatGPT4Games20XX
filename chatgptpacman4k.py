#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pac‑Man Remaster — Stereo‑Safe Full Edition (Event‑Based Audio Only)
Author: FlamesCo-ChatGPT-OS (GPT-5 Pro)
License: MIT

Highlights
----------
• Event-based sounds only (waka, power pellet, ghost eaten) — no continuous siren.
• Stereo-safe sound synthesis; degrades gracefully to silence when audio device is unavailable.
• Clean state machine (MENU → INTRO → ROLL_CALL → READY → PLAY → WIN/GAME_OVER).
• Lives system, pause (P), restart (R), escape quits.
• Scatter/Chase timing schedule inspired by the arcade (simplified).
• Frightened mode with end-of-timer blink; eaten ghosts return as “eyes” and exit house automatically.
• Consistent, frame-rate–independent movement measured in tiles/sec.
• Single-file program.py (drop-in).

Requires
--------
Python 3.9+, pygame, numpy

Run
---
pip install pygame numpy
python program.py
"""

from __future__ import annotations

import math
import os
import random
import sys
from dataclasses import dataclass
from typing import List, Tuple

# Third-party at runtime
try:
    import pygame
    import numpy as np
except Exception as e:  # pragma: no cover
    print("This game needs pygame and numpy. Install them with: pip install pygame numpy")
    raise

# ----------------------------- Config & Constants -----------------------------

CELL_SIZE       = 20
TOP_OFFSET      = 40
FPS             = 60

BLACK=(0,0,0); WHITE=(255,255,255); BLUE=(0,0,255); YELLOW=(255,255,0)
RED=(255,0,0); PINK=(255,192,203); CYAN=(0,255,255); ORANGE=(255,165,0)
FRIGHT_BLUE=(0,0,139)

# Speeds are expressed in tiles per second
PACMAN_SPEED_TPS = 10.0
GHOST_SPEED_TPS  = 9.0
GHOST_FRIGHT_SPEED_TPS = 6.0

LIVES_START = 3
FRIGHT_MS   = 6000
FRIGHT_BLINK_LAST_MS = 2000  # The last N ms of frightened time blink between blue/white

DIRS    = ['UP','LEFT','DOWN','RIGHT']
DIR_VEC = {'LEFT':(-1,0),'RIGHT':(1,0),'UP':(0,-1),'DOWN':(0,1)}
OPPOSITE= {'LEFT':'RIGHT','RIGHT':'LEFT','UP':'DOWN','DOWN':'UP'}
SCATTER_CORNERS={'blinky':(26,1),'pinky':(1,1),'inky':(26,29),'clyde':(1,29)}

# Mode schedule inspired by the original: (mode, seconds)
MODE_SCHEDULE = [('scatter',7), ('chase',20), ('scatter',7), ('chase',20), ('scatter',5), ('chase',9999)]

# Allow muting by environment variable
SOUND_MUTE = os.environ.get("PACMAN_MUTE", "0") == "1"


# --------------------------------- Utilities ----------------------------------

def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v

def tile_center_px(x: float, y: float) -> Tuple[int,int]:
    cx = int(x*CELL_SIZE + CELL_SIZE/2)
    cy = int(TOP_OFFSET + y*CELL_SIZE + CELL_SIZE/2)
    return (cx, cy)

# --------------------------------- Audio --------------------------------------

class _SilentSound:
    def play(self, *_, **__): pass
    def stop(self, *_, **__): pass

def _make_square_wave(freq: float, duration: float, volume: float=0.5, sr: int=22050):
    """Return a pygame Sound object; returns silent sound if mixer unavailable.
    Stereo-safe: duplicates mono buffer when mixer channels == 2.
    """
    if SOUND_MUTE:
        return _SilentSound()
    try:
        mixer_init = pygame.mixer.get_init()
        if not mixer_init:
            return _SilentSound()
        channels = mixer_init[2]
        n = max(1, int(duration * sr))
        # Use numpy to build a simple square wave (avoid DC offset bias by sign of sine)
        t = np.arange(n, dtype=np.float32)
        wave = (volume * np.sign(np.sin(2*np.pi*freq * t / sr))).astype(np.float32)
        wave_i16 = np.array(wave * 32767, dtype=np.int16)
        if channels == 2:
            wave_i16 = np.column_stack((wave_i16, wave_i16))
        wave_i16 = np.ascontiguousarray(wave_i16)
        return pygame.sndarray.make_sound(wave_i16)
    except Exception:
        return _SilentSound()

def init_mixer():
    if SOUND_MUTE:
        return
    try:
        pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
    except Exception:
        # No audio device — we will use silent sounds.
        pass


# -------------------------------- Maze Layout ---------------------------------

MAZE_LAYOUT = [list("############################"),
               list("#............##............#"),
               list("#.####.#####.##.#####.####.#"),
               list("#o####.#####.##.#####.####o#"),
               list("#.####.#####.##.#####.####.#"),
               list("#..........................#"),
               list("#.####.##.########.##.####.#"),
               list("#.####.##.########.##.####.#"),
               list("#......##....##....##......#"),
               list("######.##### ## #####.######"),
               list("######.##### ## #####.######"),
               list("######.##          ##.######"),
               list("######.## ###--### ##.######"),
               list("######.## #      # ##.######"),
               list("       ## #      # ##       "),
               list("######.## #      # ##.######"),
               list("######.## ######## ##.######"),
               list("######.##          ##.######"),
               list("######.## ######## ##.######"),
               list("######.## ######## ##.######"),
               list("#............##............#"),
               list("#.####.#####.##.#####.####.#"),
               list("#.####.#####.##.#####.####.#"),
               list("#o..##................##..o#"),
               list("###.##.##.########.##.##.###"),
               list("###.##.##.########.##.##.###"),
               list("#......##....##....##......#"),
               list("#.##########.##.##########.#"),
               list("#.##########.##.##########.#"),
               list("#..........................#"),
               list("############################")]

ROWS = len(MAZE_LAYOUT)
COLS = len(MAZE_LAYOUT[0])
SCREEN_WIDTH  = COLS * CELL_SIZE
SCREEN_HEIGHT = TOP_OFFSET + ROWS * CELL_SIZE


def is_passable_for(entity, board, x: int, y: int) -> bool:
    if not (0<=y<len(board) and 0<=x<len(board[0])):
        return False
    ch = board[y][x]
    if ch == '#':
        return False
    if ch == '-':
        # Only eaten ghosts can pass the house door (Pac-Man cannot, live ghosts cannot re-enter)
        return isinstance(entity, Ghost) and getattr(entity, "eaten", False)
    return True

def draw_board(surf, board):
    for y,row in enumerate(board):
        for x,ch in enumerate(row):
            if ch=='#':
                pygame.draw.rect(surf, BLUE, (x*CELL_SIZE, TOP_OFFSET+y*CELL_SIZE, CELL_SIZE, CELL_SIZE))
            elif ch=='.':
                pygame.draw.circle(surf, WHITE, tile_center_px(x,y), 3)
            elif ch=='o':
                pygame.draw.circle(surf, WHITE, tile_center_px(x,y), 6)

def count_dots(board) -> int:
    # board rows are lists of chars; list.count works for single characters
    total = 0
    for r in board:
        total += r.count('.') + r.count('o')
    return total


# ------------------------------- Game State -----------------------------------

class GameState:
    frightened_until_ms: int = 0
    ghost_eat_streak: int = 0

    @staticmethod
    def trigger_frightened(now_ms: int):
        GameState.frightened_until_ms = now_ms + FRIGHT_MS
        GameState.ghost_eat_streak = 0

    @staticmethod
    def frightened_active(now_ms: int) -> bool:
        return now_ms < GameState.frightened_until_ms

    @staticmethod
    def frightened_blink(now_ms: int) -> bool:
        """Return True when frightened is active and we are in blink window; blinks ~4Hz."""
        remain = GameState.frightened_until_ms - now_ms
        if remain <= 0:
            return False
        if remain > FRIGHT_BLINK_LAST_MS:
            return False
        # Blink state toggles every ~125ms
        return ((now_ms // 125) % 2) == 0


# --------------------------------- Entities -----------------------------------

@dataclass
class Pacman:
    x: float
    y: float
    dir: str = 'LEFT'
    next_dir: str = 'LEFT'
    progress: float = 0.0
    alive: bool = True
    _waka_toggle: bool = False
    mouth_angle: int = 30

    def try_set_dir(self, board, new_dir: str):
        dx,dy = DIR_VEC[new_dir]
        nx,ny = int(self.x+dx), int(self.y+dy)
        # Allow choosing a turn before reaching the center of the tile;
        # also allow tunnel wrap decisions.
        if 0 <= ny < len(board) and ((0 <= nx < len(board[0]) and is_passable_for(self,board,nx,ny)) or nx < 0 or nx >= len(board[0])):
            self.next_dir = new_dir

    def move(self, board, tiles_per_sec: float, dt_sec: float, sounds) -> int:
        if not self.alive:
            return 0
        # Try to commit the queued turn if possible
        dxn,dyn = DIR_VEC[self.next_dir]
        nxp, nyp = int(self.x+dxn), int(self.y+dyn)
        if ((0 <= nxp < len(board[0]) and is_passable_for(self,board,nxp,nyp))
            or (nxp < 0 or nxp >= len(board[0]))):
            self.dir = self.next_dir

        # Move
        dx,dy = DIR_VEC[self.dir]
        nx,ny = int(self.x+dx), int(self.y+dy)

        points = 0
        self.progress += tiles_per_sec * dt_sec
        while self.progress >= 1.0:
            self.x += dx; self.y += dy; self.progress -= 1.0
            # Wrap in tunnels
            if self.x < 0: self.x = len(board[0]) - 1
            if self.x >= len(board[0]): self.x = 0
            # Eat pellets
            gx, gy = int(self.x), int(self.y)
            if 0 <= gy < len(board) and 0 <= gx < len(board[0]):
                if board[gy][gx]=='.':
                    board[gy][gx]=' '; points += 10
                    (sounds['waka1'] if self._waka_toggle else sounds['waka2']).play()
                    self._waka_toggle = not self._waka_toggle
                elif board[gy][gx]=='o':
                    board[gy][gx]=' '; points += 50
                    GameState.trigger_frightened(pygame.time.get_ticks())
                    sounds['powerup'].play()

        # Animate mouth with time
        self.mouth_angle = int(30 * (0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.02)))
        return points

    def draw(self, surf):
        cx,cy = tile_center_px(self.x,self.y)
        if self.alive:
            radius = CELL_SIZE//2
            heading = {'RIGHT':0,'DOWN':90,'LEFT':180,'UP':270}[self.dir]
            pygame.draw.circle(surf, YELLOW, (cx,cy), radius)
            a1 = math.radians(heading + self.mouth_angle)
            a2 = math.radians(heading - self.mouth_angle)
            p1=(cx,cy)
            p2=(cx + int(radius*math.cos(a1)), cy + int(radius*math.sin(a1)))
            p3=(cx + int(radius*math.cos(a2)), cy + int(radius*math.sin(a2)))
            pygame.draw.polygon(surf, BLACK, [p1,p2,p3])
        else:
            pygame.draw.circle(surf, YELLOW, (cx,cy), CELL_SIZE//2)

    def die(self):
        self.alive = False


@dataclass
class Ghost:
    name: str
    color: Tuple[int,int,int]
    spawn: Tuple[int,int]
    x: float = 0.0
    y: float = 0.0
    dir: str = 'LEFT'
    progress: float = 0.0
    eaten: bool = False

    def __post_init__(self):
        self.reset()

    def reset(self):
        self.x, self.y = float(self.spawn[0]), float(self.spawn[1])
        self.dir = random.choice(DIRS)
        self.progress = 0.0
        self.eaten = False

    def target_tile(self, board, pac: Pacman, blinky_tile: Tuple[int,int], mode: str, now_ms: int) -> Tuple[int,int]:
        if self.eaten:
            # Go to house center to regenerate
            return (13,14)
        if GameState.frightened_active(now_ms) and not self.eaten:
            return (random.randint(0,len(board[0])-1), random.randint(0,len(board)-1))
        return (int(pac.x), int(pac.y)) if mode == 'chase' else SCATTER_CORNERS[self.name]

    def move(self, board, pac: Pacman, blinky_tile: Tuple[int,int], mode: str, tiles_per_sec: float, dt_sec: float):
        self.progress += tiles_per_sec * dt_sec
        if self.progress < 1.0:
            return
        # Decide direction greedily to minimize squared distance to target (simple & fast)
        target = self.target_tile(board, pac, blinky_tile, mode, pygame.time.get_ticks())
        best = None; bestdist = 1e18
        for d in DIRS:
            if d == OPPOSITE[self.dir]:
                continue
            dx,dy = DIR_VEC[d]
            nx,ny = int(self.x+dx), int(self.y+dy)
            if 0 <= nx < len(board[0]) and is_passable_for(self, board, nx, ny):
                dist = (nx - target[0])**2 + (ny - target[1])**2
                if dist < bestdist:
                    bestdist = dist; best = d
        if best:
            self.dir = best
        dx,dy = DIR_VEC[self.dir]
        self.x += dx; self.y += dy; self.progress -= 1.0
        # Wrap in tunnels
        if self.x < 0: self.x = len(board[0]) - 1
        if self.x > len(board[0]) - 1: self.x = 0
        # Regenerate when reaching house
        if self.eaten and (int(self.x), int(self.y)) == (13,14):
            self.eaten = False

    def draw(self, surf, now_ms: int):
        cx,cy = tile_center_px(self.x,self.y)
        if self.eaten:
            # Eyes only
            pygame.draw.circle(surf, WHITE, (cx-4,cy-2), 4)
            pygame.draw.circle(surf, WHITE, (cx+4,cy-2), 4)
            pygame.draw.circle(surf, BLACK, (cx-4,cy-2), 2)
            pygame.draw.circle(surf, BLACK, (cx+4,cy-2), 2)
            return

        col = self.color
        if GameState.frightened_active(now_ms):
            col = WHITE if GameState.frightened_blink(now_ms) else FRIGHT_BLUE

        pygame.draw.circle(surf, col, (cx,cy), CELL_SIZE//2)
        # Eyes
        pygame.draw.circle(surf, WHITE,(cx-4,cy-3),4)
        pygame.draw.circle(surf, WHITE,(cx+4,cy-3),4)
        pygame.draw.circle(surf, BLACK,(cx-4,cy-3),2)
        pygame.draw.circle(surf, BLACK,(cx+4,cy-3),2)


# ------------------------------- Mode Schedule --------------------------------

def global_mode(level_time_ms: int) -> str:
    """Return 'scatter' or 'chase' based on MODE_SCHEDULE and time since level start."""
    t = level_time_ms / 1000.0
    acc = 0.0
    for mode, seconds in MODE_SCHEDULE:
        acc += seconds
        if t < acc:
            return mode
    return 'chase'


# ------------------------------- UI Helpers -----------------------------------

def draw_center_text(screen, lines: List[str], font, color=WHITE, y_offset=0):
    for i,l in enumerate(lines):
        surf = font.render(l, True, color)
        rect = surf.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + y_offset + i*40))
        screen.blit(surf, rect)

def draw_hud(screen, font, score: int, lives: int):
    hud = font.render(f"Score: {score}", True, WHITE)
    screen.blit(hud,(10,10))
    # Lives as mini Pac‑Men
    for i in range(lives):
        cx = SCREEN_WIDTH - 20 - i*20
        cy = 20
        pygame.draw.circle(screen, YELLOW, (cx,cy), 8)
        pygame.draw.polygon(screen, BLACK, [(cx,cy),(cx+8,cy-3),(cx+8,cy+3)])


# --------------------------------- Main Game ----------------------------------

def main():
    pygame.init()
    init_mixer()

    # Window — created after maze so dimensions are correct
    screen = pygame.display.set_mode((SCREEN_WIDTH,SCREEN_HEIGHT))
    pygame.display.set_caption("Pac‑Man Remaster — FlamesCo Edition")
    clock = pygame.time.Clock()

    font       = pygame.font.SysFont('Arial',18)
    large_font = pygame.font.SysFont('Arial',36,bold=True)
    title_font = pygame.font.SysFont('Arial',64,bold=True)

    # Sounds (event-based only)
    sounds = {
        'waka1': _make_square_wave(440, 0.10, volume=0.5),
        'waka2': _make_square_wave(554, 0.10, volume=0.5),
        'powerup': _make_square_wave(200, 0.30, volume=0.5),
        'ghost_eaten': _make_square_wave(600, 0.20, volume=0.5),
    }

    rng = random.Random()  # deterministic seed optional: rng.seed(0)

    def show_menu():
        start_time = pygame.time.get_ticks()
        waiting=True
        while waiting:
            screen.fill(BLACK)
            t = title_font.render("PAC‑MAN", True, YELLOW)
            screen.blit(t, t.get_rect(center=(SCREEN_WIDTH//2, 200)))
            draw_center_text(screen, ["Press SPACE to Start"], large_font, WHITE)
            c = font.render("© Bandai Namco — Team Flames", True, WHITE)
            screen.blit(c,(SCREEN_WIDTH//2-140, 500))

            for e in pygame.event.get():
                if e.type==pygame.QUIT: pygame.quit(); sys.exit(0)
                if e.type==pygame.KEYDOWN and e.key==pygame.K_SPACE: waiting=False
            # Auto-start after 3 seconds
            if pygame.time.get_ticks() - start_time > 3000:
                waiting=False

            pygame.display.flip(); clock.tick(FPS)

    def show_intro():
        screen.fill(BLACK)
        draw_center_text(screen, ["Get Ready!"], large_font, YELLOW)
        pygame.display.flip(); pygame.time.delay(1200)

    def show_roll_call():
        screen.fill(BLACK)
        draw_center_text(screen, ["Blinky - Red","Pinky - Pink","Inky - Cyan","Clyde - Orange"], large_font, WHITE)
        pygame.display.flip(); pygame.time.delay(1500)

    def reset_level(state):
        # Deep copy maze
        state['maze'] = [row[:] for row in MAZE_LAYOUT]
        state['pac']  = Pacman(13,23)
        state['blinky']=Ghost('blinky',RED,(13,11))
        state['pinky'] =Ghost('pinky',PINK,(12,11))
        state['inky']  =Ghost('inky',CYAN,(13,10))
        state['clyde'] =Ghost('clyde',ORANGE,(14,11))
        state['ghosts']= [state['blinky'], state['pinky'], state['inky'], state['clyde']]
        state['level_start_ms'] = pygame.time.get_ticks()
        GameState.frightened_until_ms = 0
        GameState.ghost_eat_streak = 0

    # ---- Game loop state
    show_menu(); show_intro(); show_roll_call()
    state = {}
    reset_level(state)
    score = 0
    lives = LIVES_START
    run = True
    phase = 'READY'
    phase_until = pygame.time.get_ticks() + 1200
    paused = False

    while run:
        now = pygame.time.get_ticks()
        dt_sec = clock.get_time() / 1000.0 or (1.0/FPS)

        for e in pygame.event.get():
            if e.type==pygame.QUIT:
                run = False
            elif e.type==pygame.KEYDOWN:
                if e.key==pygame.K_ESCAPE:
                    run = False
                elif e.key==pygame.K_p:
                    paused = not paused
                elif e.key==pygame.K_r:
                    # Full restart
                    score = 0; lives = LIVES_START; phase='READY'; phase_until=now+1200; reset_level(state)
                elif e.key==pygame.K_LEFT:  state['pac'].try_set_dir(state['maze'],'LEFT')
                elif e.key==pygame.K_RIGHT: state['pac'].try_set_dir(state['maze'],'RIGHT')
                elif e.key==pygame.K_UP:    state['pac'].try_set_dir(state['maze'],'UP')
                elif e.key==pygame.K_DOWN:  state['pac'].try_set_dir(state['maze'],'DOWN')

        screen.fill(BLACK)
        draw_board(screen, state['maze'])

        if paused:
            # Draw paused overlay on top of current frame
            for g in state['ghosts']: g.draw(screen, now)
            state['pac'].draw(screen)
            draw_center_text(screen, ["PAUSED"], large_font, YELLOW)
            draw_hud(screen, font, score, lives)
            pygame.display.flip(); clock.tick(FPS)
            continue

        if phase == 'READY':
            for g in state['ghosts']: g.draw(screen, now)
            state['pac'].draw(screen)
            draw_center_text(screen, ["READY!"], large_font, YELLOW)
            if now >= phase_until:
                phase = 'PLAY'

        elif phase == 'PLAY':
            # Move Pac-Man
            score += state['pac'].move(state['maze'], PACMAN_SPEED_TPS, dt_sec, sounds)

            # Mode
            level_elapsed = now - state['level_start_ms']
            gmode = 'scatter' if GameState.frightened_active(now) else global_mode(level_elapsed)

            # Move & draw ghosts
            blinky_tile=(int(state['blinky'].x), int(state['blinky'].y))
            for g in state['ghosts']:
                g_speed = GHOST_FRIGHT_SPEED_TPS if GameState.frightened_active(now) and not g.eaten else GHOST_SPEED_TPS
                g.move(state['maze'], state['pac'], blinky_tile, gmode, g_speed, dt_sec)
                g.draw(screen, now)

            # Draw Pac-Man
            state['pac'].draw(screen)

            # Collisions
            for g in state['ghosts']:
                if abs(state['pac'].x - g.x) <= 0.5 and abs(state['pac'].y - g.y) <= 0.5:
                    if GameState.frightened_active(now) and not g.eaten:
                        pts = 200 * (2 ** GameState.ghost_eat_streak)
                        # Cap at 1600 like the arcade
                        pts = int(min(1600, pts))
                        score += pts
                        GameState.ghost_eat_streak += 1
                        g.eaten = True
                        sounds['ghost_eaten'].play()
                    elif not g.eaten:
                        state['pac'].die()
                        lives -= 1
                        if lives > 0:
                            phase = 'READY'; phase_until = now + 1500
                            # Reset positions only (keep score & dots)
                            pac_spawn = Pacman(13,23)
                            state['pac'].x, state['pac'].y = pac_spawn.x, pac_spawn.y
                            state['pac'].dir = 'LEFT'; state['pac'].next_dir='LEFT'; state['pac'].progress=0.0; state['pac'].alive=True
                            for gh, sp in zip(state['ghosts'], [(13,11),(12,11),(13,10),(14,11)]):
                                gh.x, gh.y = float(sp[0]), float(sp[1])
                                gh.dir = random.choice(DIRS)
                                gh.progress = 0.0
                                gh.eaten = False
                            GameState.frightened_until_ms = 0
                            GameState.ghost_eat_streak = 0
                        else:
                            phase = 'GAME_OVER'; phase_until = now + 1800

            # Win condition
            if count_dots(state['maze']) == 0 and phase == 'PLAY':
                phase = 'WIN'; phase_until = now + 1800

        elif phase == 'WIN':
            for g in state['ghosts']: g.draw(screen, now)
            state['pac'].draw(screen)
            draw_center_text(screen, ["YOU WIN!", "BOARD CLEARED"], large_font, WHITE)
            if now >= phase_until:
                # Next level (simple replay)
                reset_level(state)
                phase = 'READY'; phase_until = now + 1200

        elif phase == 'GAME_OVER':
            for g in state['ghosts']: g.draw(screen, now)
            state['pac'].draw(screen)
            draw_center_text(screen, ["GAME OVER"], large_font, RED)
            if now >= phase_until:
                run = False

        draw_hud(screen, font, score, lives)
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
