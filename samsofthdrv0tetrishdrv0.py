#!/usr/bin/env python3
# ULTRA TETRIS 0.X — Samsoft 199X Nintendo (fan recreation)
# ----------------------------------------------------------
# • Full NES pacing (levels 1→29)
# • Korobeiniki theme + square-wave SFX
# • Retro boot menu [ PRESS SPACE TO START TO PLAY TETRIS ]
# • No external assets — pure Python + Pygame + NumPy
# ----------------------------------------------------------

import os, sys, math, time, random, threading
import pygame, numpy as np

# === INIT ===
pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()
pygame.mixer.init()
pygame.font.init()

WIDTH, HEIGHT = 700, 600
GAME_W, GAME_H = 200, 400
BLOCK = 20
TOPX, TOPY = (WIDTH - GAME_W)//2, HEIGHT - GAME_H - 50

SHAPES = [
    [[1,5,9,13],[4,5,6,7]], [[4,5,9,10],[2,6,5,9]], [[6,7,9,10],[1,5,6,10]],
    [[1,2,5,9],[0,4,5,6],[1,5,9,8],[4,5,6,10]],
    [[1,2,6,10],[5,6,7,9],[2,6,10,11],[3,5,6,7]],
    [[1,4,5,6],[1,4,5,9],[4,5,6,9],[1,5,6,9]],
    [[1,2,5,6]]
]
COLORS = [
    (0,255,0),(255,0,0),(0,255,255),
    (255,255,0),(255,165,0),(0,0,255),(128,0,128)
]

# === SOUND ===
class GameBoySound:
    def __init__(self):
        self.sr = 44100
        self.music = pygame.mixer.Channel(0)
        self.sfx   = pygame.mixer.Channel(1)

    def beep(self,f,d):
        t = np.linspace(0,d,int(self.sr*d),False)
        phase = 2 * np.pi * f * t
        square = np.where(np.sin(phase) > 0, 1.0, -1.0)
        duty_mask = (np.mod(phase, 2*np.pi) < 0.25*np.pi)  # 12.5% duty cycle
        wave = np.where(duty_mask, square, -1.0)
        s = np.int16(wave*32767 * 0.5)  # Adjusted volume
        return pygame.mixer.Sound(buffer=np.column_stack((s,s)).ravel().tobytes())

    def seq(self,notes,ch=None,delay=.02):
        c = ch or self.music
        for f,d in notes:
            if f > 0:  # Skip rests if any
                c.play(self.beep(f,d))
            time.sleep(d+delay)

    def play_async(self,notes,ch=None,delay=.02):
        threading.Thread(target=self.seq,
                         args=(notes,ch,delay),
                         daemon=True).start()

    def clear(self): self.play_async([(880,.05),(988,.05),(1175,.05),(1397,.1)],self.sfx)
    def drop (self): self.sfx.play(self.beep(440,.08))
    def rot  (self): self.sfx.play(self.beep(660,.04))
    def over (self): self.play_async([(523,.15),(494,.15),(440,.15),(392,.15),(349,.15)],self.sfx)
    def theme(self):
        korobeiniki = [
            (659, 0.406), (494, 0.203), (523, 0.203), (587, 0.406), (523, 0.203), (494, 0.203), (440, 0.406), (440, 0.203),
            (523, 0.203), (659, 0.406), (587, 0.203), (523, 0.203), (494, 0.609), (523, 0.203), (587, 0.406), (659, 0.406),
            (523, 0.406), (440, 0.406), (440, 0.203), (440, 0.203), (494, 0.203), (523, 0.203), (587, 0.609), (698, 0.203),
            (880, 0.406), (784, 0.203), (698, 0.203), (659, 0.609), (523, 0.203), (659, 0.406), (587, 0.203), (523, 0.203),
            (494, 0.406), (494, 0.203), (523, 0.203), (587, 0.406), (659, 0.406), (523, 0.406), (440, 0.406), (440, 0.406)
        ] * 2  # Full loop played twice for continuous feel
        self.play_async(korobeiniki, self.music, delay=0.0)  # No gap for seamless playback

sound = GameBoySound()

# === GAME CORE ===
class Block:
    def __init__(self,x,y,t):
        self.x,self.y,self.t=x,y,t
        self.c=random.randrange(len(COLORS))
        self.r=0
    def img(self): return SHAPES[self.t][self.r]
    def rot(self): self.r=(self.r+1)%len(SHAPES[self.t])

class Tetris:
    def __init__(self,w,h):
        self.w,self.h=w,h
        self.f=[[0]*w for _ in range(h)]
        self.sc=self.lv=self.li=0
        self.state="start"
        self.b=self.nb=None
        self.x,self.y,self.z=TOPX,TOPY,BLOCK

    def interval(self): return max(1,48-self.lv*2)
    def newb(self):
        self.b=self.nb or Block(3,0,random.randrange(len(SHAPES)))
        self.nb=Block(3,0,random.randrange(len(SHAPES)))
        if self.coll(): self.state="gameover"; sound.over()
    def coll(self):
        for i in range(4):
            for j in range(4):
                if i*4+j in self.b.img():
                    if (i+self.b.y>=self.h or j+self.b.x>=self.w
                        or j+self.b.x<0 or self.f[i+self.b.y][j+self.b.x]):
                        return True
        return False
    def lines(self):
        c=0
        for i in range(self.h-1,-1,-1):
            if 0 not in self.f[i]:
                del self.f[i]; self.f.insert(0,[0]*self.w); c+=1
        if c: self.sc+=c**2; self.li+=c; self.lv=self.li//10; sound.clear()
    def freeze(self):
        for i in range(4):
            for j in range(4):
                if i*4+j in self.b.img():
                    self.f[i+self.b.y][j+self.b.x]=self.b.c+1
        self.lines(); self.newb()
    def down(self):
        self.b.y+=1
        if self.coll(): self.b.y-=1; self.freeze()
    def space(self):
        while not self.coll(): self.b.y+=1
        self.b.y-=1; self.freeze(); sound.drop()
    def side(self,d):
        o=self.b.x; self.b.x+=d
        if self.coll(): self.b.x=o
    def rotate(self):
        o=self.b.r; self.b.rot()
        if self.coll(): self.b.r=o
        else: sound.rot()

# === DRAW ===
def draw(scr,g):
    scr.fill((255,255,255))
    for i in range(g.h):
        for j in range(g.w):
            pygame.draw.rect(scr,(178,190,181),
                [g.x+g.z*j,g.y+g.z*i,g.z,g.z],1)
            if g.f[i][j]:
                pygame.draw.rect(scr,COLORS[(g.f[i][j]-1)%len(COLORS)],
                    [g.x+g.z*j+1,g.y+g.z*i+1,g.z-2,g.z-2])
    if g.b:
        for i in range(4):
            for j in range(4):
                if i*4+j in g.b.img():
                    pygame.draw.rect(scr,COLORS[g.b.c%len(COLORS)],
                        [g.x+g.z*(j+g.b.x)+1,g.y+g.z*(i+g.b.y)+1,g.z-2,g.z-2])

# === GAME LOOP ===
def startGame(scr):
    pygame.display.set_caption("ULTRA TETRIS 0.X © Samsoft 199X Nintendo")
    g=Tetris(10,20); g.newb()
    clock=pygame.time.Clock(); c=0; down=False
    while g.state!="gameover":
        c+=1; interval=g.interval()
        if down or c%interval==0:g.down()
        for e in pygame.event.get():
            if e.type==pygame.QUIT:return
            if e.type==pygame.KEYDOWN:
                if e.key==pygame.K_UP:g.rotate()
                elif e.key==pygame.K_DOWN:down=True
                elif e.key==pygame.K_LEFT:g.side(-1)
                elif e.key==pygame.K_RIGHT:g.side(1)
                elif e.key==pygame.K_SPACE:g.space()
                elif e.key==pygame.K_ESCAPE:return
            elif e.type==pygame.KEYUP and e.key==pygame.K_DOWN:down=False
        draw(scr,g)
        f=pygame.font.SysFont('Courier',28,True)
        scr.blit(f.render(f"Score:{g.sc}",True,(0,0,0)),(10,0))
        scr.blit(f.render(f"Level:{g.lv}",True,(0,0,0)),(10,35))
        pygame.display.flip(); clock.tick(60)
        if g.lv>=29:g.state="gameover"
    for i in range(8):
        scr.fill((255,0,0) if i%2 else (0,0,0)); pygame.display.flip(); time.sleep(.25)
    sound.over()

# === MENU ===
def menu():
    scr=pygame.display.set_mode((WIDTH,HEIGHT))
    clock=pygame.time.Clock(); t=0; run=True
    while run:
        t+=1; scr.fill((0,48,32))
        glow=abs(int(127*math.sin(t*.05)))+128
        title=pygame.font.SysFont("Courier",56,True)
        sub=pygame.font.SysFont("Courier",26,True)
        press=pygame.font.SysFont("Courier",22,True)
        scr.blit(title.render("ULTRA TETRIS 0.X",True,(0,glow,80)),(120,180))
        scr.blit(sub.render("© Samsoft 199X Nintendo",True,(0,255,153)),(180,250))
        msg="[ PRESS SPACE TO PLAY TETRIS ]"
        if math.sin(t*.15)>0:scr.blit(press.render(msg,True,(204,255,204)),(160,340))
        pygame.display.flip(); clock.tick(60)
        for e in pygame.event.get():
            if e.type==pygame.QUIT:run=False
            elif e.type==pygame.KEYDOWN:
                if e.key==pygame.K_SPACE:
                    sound.theme()        # plays asynchronously
                    startGame(scr)
                elif e.key==pygame.K_ESCAPE:run=False
    pygame.quit()

if __name__=="__main__":
    menu()
