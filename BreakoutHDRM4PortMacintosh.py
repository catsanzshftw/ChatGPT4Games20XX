#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cat's Breakout — PS5-Boop Edition (Python 3.14-Safe)
====================================================
• Fully procedural sound (NumPy + sounddevice, no mixer)
• Mouse = paddle, SPACE / click = serve
• 6 colored rows, Atari-style scoring
• 5 lives, clear two walls to win
• Works everywhere — even where pygame.mixer is missing
"""

import os, sys, math, random, numpy as np, sounddevice as sd, pygame

# ----------------------------------------------------------------------
# Audio engine (sounddevice + NumPy)
# ----------------------------------------------------------------------
SAMPLE_RATE = 44100

def _play_wave(wave):
    """Non-blocking playback."""
    sd.play(wave.astype(np.float32), SAMPLE_RATE, blocking=False)

def make_square(freq=440, dur_ms=80, vol=0.5):
    t = np.linspace(0, dur_ms/1000, int(SAMPLE_RATE*dur_ms/1000), endpoint=False)
    return np.sign(np.sin(2*np.pi*freq*t))*vol

def make_tone(freq=440, dur_ms=100, vol=0.6, bend=0.0):
    """Pulse-like tone with slight bend."""
    t = np.linspace(0, dur_ms/1000, int(SAMPLE_RATE*dur_ms/1000))
    f2 = freq*(1.0+bend)
    f_inst = np.linspace(freq, f2, len(t))
    y = np.sign(np.sin(2*np.pi*np.cumsum(f_inst)/SAMPLE_RATE))*vol
    return y.astype(np.float32)

def beep(segment=2, speed=0):
    base = [540, 620, 700, 780][max(0,min(3,speed))]
    seg_ratio = [0.85,0.93,1.00,1.07,1.15][max(0,min(4,segment))]
    _play_wave(make_tone(base*seg_ratio, 70-6*speed, 0.6, 0.02))

def boop(row):
    f = [196,220,247,262,294,330][max(0,min(5,row))]
    bend = 0.05 if row>=3 else -0.03
    _play_wave(make_tone(f, 90, 0.7, bend))

def jingle(kind):
    seq = {
        "wall_clear":[(660,0.05),(880,0.06),(990,0.07)],
        "win":[(660,0.05),(880,0.05),(1320,0.08),(1760,0.1)],
        "game_over":[(523,-0.05),(392,-0.06),(330,-0.07)],
    }.get(kind,[ (660,0.05),(880,0.06) ])
    waves=[]
    for f,b in seq:
        waves.append(make_tone(f,100,0.7,b))
    _play_wave(np.concatenate(waves))

# ----------------------------------------------------------------------
# Pygame setup
# ----------------------------------------------------------------------
pygame.display.init()
pygame.event.set_allowed([pygame.QUIT,pygame.KEYDOWN,pygame.MOUSEBUTTONDOWN,pygame.MOUSEMOTION])

LOGIC_W,LOGIC_H=148,244
SCALE=3.5
WIDTH,HEIGHT=int(LOGIC_W*SCALE),int(LOGIC_H*SCALE)
FPS=60
screen=pygame.display.set_mode((WIDTH,HEIGHT))
pygame.display.set_caption("Cat's Breakout — PS5-Boop Edition")
clock=pygame.time.Clock()

# Colors
BLACK=(0,0,0); WHITE=(245,245,245)
GRAY=(180,180,180)
BLUE=(60,60,255); AQUA=(60,210,255); GREEN=(60,200,60)
YELLOW=(235,235,60); ORANGE=(255,160,50); RED=(255,60,60)

# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def scale_rect(r):
    return pygame.Rect(int(r.x*SCALE),int(r.y*SCALE),int(r.w*SCALE),int(r.h*SCALE))

def draw_pixel_text(surf,text,x,y,color=WHITE):
    px=2
    font={
        '0':["1111","1001","1001","1001","1001","1111"],
        '1':["0010","0010","0010","0010","0010","0010"],
        '2':["1111","0001","1111","1000","1000","1111"],
        '3':["1111","0001","0111","0001","0001","1111"],
        '4':["1001","1001","1111","0001","0001","0001"],
        '5':["1111","1000","1111","0001","0001","1111"],
        '6':["1111","1000","1111","1001","1001","1111"],
        '7':["1111","0001","0010","0010","0100","0100"],
        '8':["1111","1001","1111","1001","1001","1111"],
        '9':["1111","1001","1111","0001","0001","1111"],
        'S':["1110","1000","1110","0001","0001","1110"],
        'C':["1111","1000","1000","1000","1000","1111"],
        'O':["1111","1001","1001","1001","1001","1111"],
        'R':["1110","1001","1110","1010","1001","1001"],
        'E':["1111","1000","1110","1000","1000","1111"],
        'L':["1000","1000","1000","1000","1000","1111"],
        'I':["111","010","010","010","010","111"],
        'V':["1001","1001","1001","1001","0110","0110"],
        ':':["0","1","0","1","0","0"],' ':["0","0","0","0","0","0"]
    }
    for ch in text:
        g=font.get(ch.upper())
        if not g:
            x+=6*px;continue
        for ry,row in enumerate(g):
            for rx,b in enumerate(row):
                if b=='1':
                    surf.fill(color,pygame.Rect(int((x+rx*px)*SCALE),
                                                int((y+ry*px)*SCALE),
                                                int(px*SCALE),int(px*SCALE)))
        x+=(len(g[0])+2)*px

# ----------------------------------------------------------------------
# Bricks
# ----------------------------------------------------------------------
ROW_COLORS=[BLUE,AQUA,GREEN,YELLOW,ORANGE,RED]
ROW_SCORES=[1,1,4,4,7,7]
BRICK_ROWS,BRICK_COLS=6,18
GAP_X,GAP_Y=1,2
Y_START=40; BRICK_H=6
BRICK_W=(LOGIC_W-(BRICK_COLS-1)*GAP_X)//BRICK_COLS
total_w=BRICK_COLS*BRICK_W+(BRICK_COLS-1)*GAP_X
X_START=(LOGIC_W-total_w)//2

def make_bricks():
    out=[]
    for r in range(BRICK_ROWS):
        for c in range(BRICK_COLS):
            x=X_START+c*(BRICK_W+GAP_X)
            y=Y_START+r*(BRICK_H+GAP_Y)
            out.append({"rect":pygame.Rect(x,y,BRICK_W,BRICK_H),
                        "color":ROW_COLORS[r],"score":ROW_SCORES[r],"row":r})
    return out

# ----------------------------------------------------------------------
# Entities
# ----------------------------------------------------------------------
class Paddle:
    def __init__(self):
        self.rect=pygame.Rect(LOGIC_W//2-16,LOGIC_H-22,32,5)
    def update(self):
        mx,_=pygame.mouse.get_pos()
        self.rect.centerx=mx/SCALE
        self.rect.clamp_ip(pygame.Rect(0,0,LOGIC_W,LOGIC_H))
    def draw(self,s): pygame.draw.rect(s,GRAY,scale_rect(self.rect))

class Ball:
    def __init__(self):
        self.rect=pygame.Rect(LOGIC_W//2,LOGIC_H//2,5,5)
        self.x,self.y=float(self.rect.x),float(self.rect.y)
        self.vx,self.vy=1.5,-2
        self.active=False
        self.level_speed=0
        self.paddle_hits=0
        self.speeds=[2.0,2.4,2.9,3.4]
    def current_speed(self): return self.speeds[self.level_speed]
    def aim(self,paddle,seg):
        ang=math.radians([150,120,88,60,30][seg])
        s=self.current_speed()
        self.vx=s*math.cos(ang); self.vy=-abs(s*math.sin(ang))
    def update(self,paddle,bricks):
        if not self.active:
            self.rect.centerx=paddle.rect.centerx
            self.rect.bottom=paddle.rect.top-1
            self.x,self.y=float(self.rect.x),float(self.rect.y)
            return 0
        self.x+=self.vx; self.y+=self.vy
        self.rect.x, self.rect.y=int(self.x),int(self.y)
        if self.rect.left<=0: self.rect.left=0; self.x=self.rect.x; self.vx=abs(self.vx); beep(0,self.level_speed)
        if self.rect.right>=LOGIC_W: self.rect.right=LOGIC_W; self.x=self.rect.x; self.vx=-abs(self.vx); beep(4,self.level_speed)
        if self.rect.top<=0: self.rect.top=0; self.y=self.rect.y; self.vy=abs(self.vy); beep(2,self.level_speed)
        if self.rect.colliderect(paddle.rect) and self.vy>0:
            seg=int((self.rect.centerx-paddle.rect.left)/(paddle.rect.w/5))
            self.paddle_hits+=1
            if self.paddle_hits in (4,8,12):
                self.level_speed=min(3,self.level_speed+1); beep(2,self.level_speed)
            self.aim(paddle,max(0,min(4,seg))); beep(seg,self.level_speed)
        hit=None
        for i,b in enumerate(bricks):
            if self.rect.colliderect(b["rect"]): hit=i;break
        if hit is not None:
            br=bricks.pop(hit)
            self.vy=-self.vy; boop(br["row"])
            if br["row"]>=3:self.level_speed=3
            return br["score"]
        return 0
    def draw(self,s): pygame.draw.rect(s,RED,scale_rect(self.rect))

# ----------------------------------------------------------------------
# Game
# ----------------------------------------------------------------------
class Game:
    def __init__(self):
        self.paddle=Paddle(); self.ball=Ball()
        self.bricks=make_bricks()
        self.score=0; self.lives=5; self.level=1
        self.over=False; self.win=False
    def serve(self):
        if not self.ball.active and not self.over and not self.win:
            self.ball.active=True
    def reset_ball(self): self.ball=Ball()
    def update(self):
        self.paddle.update()
        self.score+=self.ball.update(self.paddle,self.bricks)
        if self.ball.active and self.ball.rect.top>LOGIC_H:
            self.lives-=1; self.reset_ball()
            if self.lives<=0: self.over=True; jingle("game_over")
        if not self.bricks and not self.over:
            if self.level==1:
                self.level=2; self.bricks=make_bricks(); self.reset_ball(); jingle("wall_clear")
            else:
                self.win=True; jingle("win")
    def draw_hud(self,s):
        draw_pixel_text(s,"SCORE:",4,4); draw_pixel_text(s,f"{self.score:03}",52,4)
        draw_pixel_text(s,"LIVES:",LOGIC_W-60,4); draw_pixel_text(s,str(self.lives),LOGIC_W-16,4)
        draw_pixel_text(s,f"LEVEL:{self.level}",LOGIC_W//2-28,4)
    def draw(self,s):
        s.fill(BLACK)
        for b in self.bricks: pygame.draw.rect(s,b["color"],scale_rect(b["rect"]))
        self.paddle.draw(s); self.ball.draw(s); self.draw_hud(s)
        if not self.ball.active and not self.over and not self.win:
            draw_pixel_text(s,"SPACE/CLICK TO SERVE",LOGIC_W//2-60,LOGIC_H//2-4)
        if self.over:
            draw_pixel_text(s,"GAME OVER",LOGIC_W//2-32,LOGIC_H//2-4)
        if self.win:
            draw_pixel_text(s,"YOU WIN!",LOGIC_W//2-28,LOGIC_H//2-4)

# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main():
    game=Game()
    while True:
        for e in pygame.event.get():
            if e.type==pygame.QUIT: pygame.quit(); sys.exit()
            if e.type==pygame.KEYDOWN:
                if e.key==pygame.K_ESCAPE: pygame.quit(); sys.exit()
                if e.key==pygame.K_r: game=Game()
                if e.key==pygame.K_SPACE: game.serve()
            if e.type==pygame.MOUSEBUTTONDOWN: game.serve()
        if not (game.over or game.win): game.update()
        game.draw(screen)
        pygame.display.flip()
        clock.tick(FPS)

if __name__=="__main__":
    main()
