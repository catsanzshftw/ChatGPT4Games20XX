#!/usr/bin/env python3
# ---------------------------------------------------------------------------
# Five Nights at James's — Luigi's Mansion Edition v1.1
# by Catsan + ChatGPT (FlamesCo build)
# ---------------------------------------------------------------------------
# 600×400 • 60 FPS • All-code fallback (no assets required)
# ---------------------------------------------------------------------------

import pygame, sys, random, time, os
pygame.init()
pygame.mixer.init()

# Window ---------------------------------------------------------------
W, H = 600, 400
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Five Nights at James’s — Luigi’s Mansion Edition")
clock = pygame.time.Clock()
FONT = pygame.font.Font(None, 36)
SMALL = pygame.font.Font(None, 24)

# Colors ---------------------------------------------------------------
BLACK=(0,0,0); WHITE=(255,255,255); GRAY=(128,128,128)
RED=(255,0,0); GREEN=(0,255,0); BLUE=(0,0,255)
YELLOW=(255,255,0); DARK=(50,50,50)

OFFICE, CAMERA = 0, 1

# Try to load optional ambience
try:
    hum = pygame.mixer.Sound("hum.wav")
    hum.set_volume(0.2)
    hum.play(loops=-1)
except: hum=None

class Animatronic:
    def __init__(self,name,img,start,speed):
        self.name=name
        self.path=img
        self.image=self.load_image()
        self.position=start
        self.max_pos=5
        self.base_speed=speed
        self.speed=speed
        self.at_door=False

    def load_image(self):
        if os.path.exists(self.path):
            return pygame.image.load(self.path).convert_alpha()
        surf=pygame.Surface((30,50),pygame.SRCALPHA)
        c=BLUE if "Blue" in self.name else GREEN if "Boo" in self.name else RED
        surf.fill(c)
        return surf

    def scaled(self,size=(30,50)): return pygame.transform.scale(self.image,size)
    def reset(self): self.position=0; self.at_door=False
    def move(self):
        if random.random()<self.speed:
            self.position+=1
            if self.position>=self.max_pos:
                self.position=self.max_pos; self.at_door=True

class Game:
    def __init__(self):
        self.state=OFFICE
        self.night=1
        self.power=100
        self.power_drain=1
        self.time_left=300
        self.hour=12
        self.game_over=False
        self.jumpscare=False
        self.jumpscare_timer=0

        self.left_door=self.right_door=False
        self.left_light=self.right_light=False

        self.anim=[
            Animatronic("Gold Bat","goldbat.png",0,0.01),
            Animatronic("Boilike","boilike.png",0,0.015),
            Animatronic("Blue Twirler","bluetwirler.png",0,0.02)
        ]

    # -------------------------------------------------------------------
    def draw_office(self):
        screen.fill(DARK)
        pygame.draw.rect(screen,GRAY,(0,0,200,H))
        pygame.draw.rect(screen,GRAY,(400,0,200,H))
        pygame.draw.rect(screen,BLACK,(200,0,200,H))
        # doors
        pygame.draw.rect(screen,YELLOW if self.left_door else GRAY,(0,0,50,H))
        pygame.draw.rect(screen,YELLOW if self.right_door else GRAY,(550,0,50,H))
        # lights
        if self.left_light:  pygame.draw.circle(screen,WHITE,(25,H//2),10)
        if self.right_light: pygame.draw.circle(screen,WHITE,(575,H//2),10)

        for a in self.anim:
            if a.at_door:
                side=random.choice(["l","r"])
                img=a.scaled((40,60))
                x=5 if side=="l" else 555
                screen.blit(img,(x,120))

        # UI
        screen.blit(SMALL.render(f"Power: {int(self.power)}%",1,WHITE),(10,10))
        screen.blit(SMALL.render(f"Time: {self.hour}:00 AM",1,WHITE),(500,10))
        screen.blit(SMALL.render(f"Night {self.night}",1,WHITE),(260,10))

        btns=[]
        labels=["Left Light","Right Light","Left Door","Right Door"]
        for i,txt in enumerate(labels):
            rect=pygame.Rect(100+i*100,350,80,30)
            color=GREEN if i%2==0 and not getattr(self,["left_light","right_light","left_door","right_door"][i]) \
                   or i%2==1 and not getattr(self,["left_light","right_light","left_door","right_door"][i]) else RED
            pygame.draw.rect(screen,color,rect)
            screen.blit(SMALL.render(txt,1,BLACK),(rect.x+4,rect.y+6))
            btns.append(rect)

        cam_btn=pygame.Rect(250,300,100,40)
        pygame.draw.rect(screen,BLUE,cam_btn)
        screen.blit(FONT.render("CAMERA",1,WHITE),(255,305))
        btns.append(cam_btn)
        return btns

    def draw_camera(self):
        screen.fill((0,40,0))
        for i in range(6):
            x=50+i*90
            pygame.draw.rect(screen,GRAY,(x,50,80,60))
            screen.blit(SMALL.render(f"Cam{i}",1,WHITE),(x+25,115))
            for a in self.anim:
                if a.position==i:
                    screen.blit(a.scaled((20,20)),(x+35,70))
        # static overlay
        s=pygame.Surface((W,H)); val=random.randint(90,150)
        s.fill((val,val,val)); s.set_alpha(random.randint(15,30))
        screen.blit(s,(0,0))

        back=pygame.Rect(250,300,100,40)
        pygame.draw.rect(screen,RED,back)
        screen.blit(FONT.render("OFFICE",1,WHITE),(260,305))
        screen.blit(SMALL.render(f"Power: {int(self.power)}%",1,WHITE),(10,10))
        return [back]

    # -------------------------------------------------------------------
    def handle(self,buttons):
        for e in pygame.event.get():
            if e.type==pygame.QUIT: return False
            if e.type==pygame.MOUSEBUTTONDOWN:
                m=pygame.mouse.get_pos()
                for i,b in enumerate(buttons):
                    if b.collidepoint(m):
                        if self.state==OFFICE:
                            if i==0: self.left_light=not self.left_light; self.power_drain+=1 if self.left_light else -1
                            if i==1: self.right_light=not self.right_light; self.power_drain+=1 if self.right_light else -1
                            if i==2: self.left_door=not self.left_door; self.power_drain+=2 if self.left_door else -2
                            if i==3: self.right_door=not self.right_door; self.power_drain+=2 if self.right_door else -2
                            if i==4: self.state=CAMERA; self.power_drain+=1
                        else:
                            self.state=OFFICE; self.power_drain-=1
                self.power_drain=max(0.5,self.power_drain)
        return True

    # -------------------------------------------------------------------
    def update(self,dt):
        if self.game_over or self.jumpscare: return
        self.power-=self.power_drain*dt/1000
        if self.power<=0: self.game_over=True; return
        self.time_left-=dt/1000
        if self.time_left<=0:
            self.night+=1
            if self.night>3: self.game_over=True; return
            self.reset()
        self.hour=12+int((300-self.time_left)//60)

        mult=0.8+(self.night*0.1)
        for a in self.anim:
            a.speed=max(0.005,a.base_speed*mult)
            a.move()

        for a in self.anim:
            if a.at_door:
                door=(a.name=="Gold Bat" and self.left_door) or (a.name!="Gold Bat" and self.right_door)
                light=(a.name=="Gold Bat" and self.left_light) or (a.name!="Gold Bat" and self.right_light)
                if not door and not light:
                    self.jumpscare_timer+=dt
                    if self.jumpscare_timer>1000:
                        self.jumpscare=True
                        try: s=pygame.mixer.Sound("jumpscare.wav"); s.play()
                        except: pass
                        break
                else: self.jumpscare_timer=0
            else: self.jumpscare_timer=0

    # -------------------------------------------------------------------
    def reset(self):
        self.power=100; self.time_left=300; self.hour=12
        self.power_drain=1
        self.left_door=self.right_door=self.left_light=self.right_light=False
        for a in self.anim: a.reset()

    def draw_end(self):
        if self.night>3:
            screen.fill(GREEN)
            screen.blit(FONT.render("YOU SURVIVED 3 NIGHTS!",1,BLACK),(50,180))
        else:
            screen.fill(RED)
            screen.blit(FONT.render("POWER OUT! GAME OVER",1,WHITE),(70,180))

    def draw_jumpscare(self):
        screen.fill(RED)
        screen.blit(FONT.render("JUMPSCARE!",1,WHITE),(200,180))

    # -------------------------------------------------------------------
    def run(self):
        running=True
        while running:
            dt=clock.tick(60)
            running=self.handle([])
            self.update(dt)
            if self.jumpscare: self.draw_jumpscare()
            elif self.game_over: self.draw_end()
            else:
                if self.state==OFFICE: btns=self.draw_office()
                else: btns=self.draw_camera()
                running=self.handle(btns)
            pygame.display.flip()
            if self.game_over or self.jumpscare:
                time.sleep(3); pygame.quit(); sys.exit()

# -----------------------------------------------------------------------
if __name__=="__main__":
    Game().run()
