# Pac-Man Remaster — Stereo-Safe Full Edition
# Features: Menu, Intro, Roll-Call, Sounds, Pac-Man animation, Ghost eyes/eaten states
# Requires: pygame, numpy
import pygame, random, sys, math, numpy as np

pygame.init()
pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)

# --- Sound helpers ---
def make_square_wave(freq, duration, volume=0.5, sr=22050):
    n_samples = int(duration * sr)
    t = np.arange(n_samples)
    wave = (volume * np.sign(np.sin(2 * np.pi * freq * t / sr))).astype(np.float32)

    # Convert to int16
    wave_int16 = (wave * 32767).astype(np.int16)

    # Check mixer config
    channels = pygame.mixer.get_init()[2]
    if channels == 2:  # Stereo → duplicate mono data to 2 channels
        wave_int16 = np.column_stack((wave_int16, wave_int16))
    return pygame.sndarray.make_sound(wave_int16)

waka1 = make_square_wave(440, 0.1)
waka2 = make_square_wave(554, 0.1)
powerup = make_square_wave(200, 0.3)
siren   = make_square_wave(300, 0.4, 0.3)

# --- Constants ---
SCREEN_WIDTH, SCREEN_HEIGHT = 560, 620
CELL_SIZE, TOP_OFFSET, FPS = 20, 40, 60
BLACK=(0,0,0); WHITE=(255,255,255); BLUE=(0,0,255); YELLOW=(255,255,0)
RED=(255,0,0); PINK=(255,192,203); CYAN=(0,255,255); ORANGE=(255,165,0)
FRIGHT_BLUE=(0,0,139)

PACMAN_SPEED=1/6.0; GHOST_SPEED=1/6.0
DIRS=['UP','LEFT','DOWN','RIGHT']
DIR_VEC={'LEFT':(-1,0),'RIGHT':(1,0),'UP':(0,-1),'DOWN':(0,1)}
OPPOSITE={'LEFT':'RIGHT','RIGHT':'LEFT','UP':'DOWN','DOWN':'UP'}
SCATTER_CORNERS={'blinky':(26,1),'pinky':(1,1),'inky':(26,29),'clyde':(1,29)}

screen=pygame.display.set_mode((SCREEN_WIDTH,SCREEN_HEIGHT))
pygame.display.set_caption("Pac-Man Remaster")
clock=pygame.time.Clock()
font=pygame.font.SysFont('Arial',18)
large_font=pygame.font.SysFont('Arial',36,bold=True)
title_font=pygame.font.SysFont('Arial',64,bold=True)

# --- Maze ---
maze1=[list("############################"),
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

# --- Helpers ---
def tile_center_px(x,y): return (int(x*CELL_SIZE+CELL_SIZE/2),int(TOP_OFFSET+y*CELL_SIZE+CELL_SIZE/2))
def is_passable(board,x,y): return 0<=y<len(board) and 0<=x<len(board[0]) and board[y][x] not in '#-'
def draw_center_text(lines,color=WHITE):
    for i,l in enumerate(lines):
        surf=large_font.render(l,True,color)
        rect=surf.get_rect(center=(SCREEN_WIDTH//2,SCREEN_HEIGHT//2+i*40))
        screen.blit(surf,rect)
def draw_board(surf,board):
    for y,row in enumerate(board):
        for x,ch in enumerate(row):
            if ch=='#': pygame.draw.rect(surf,BLUE,(x*CELL_SIZE,TOP_OFFSET+y*CELL_SIZE,CELL_SIZE,CELL_SIZE))
            elif ch=='.': pygame.draw.circle(surf,WHITE,tile_center_px(x,y),3)
            elif ch=='o': pygame.draw.circle(surf,WHITE,tile_center_px(x,y),6)

def count_dots(board): return sum(r.count('.')+r.count('o') for r in board)

# --- Game State ---
class GameState:
    frightened_until=0; ghost_eat_streak=0
    @staticmethod
    def trigger_frightened():
        GameState.frightened_until=pygame.time.get_ticks()+6000
        GameState.ghost_eat_streak=0
    @staticmethod
    def frightened_active(): return pygame.time.get_ticks()<GameState.frightened_until

# --- Entities ---
class Pacman:
    def __init__(self,x,y):
        self.x,self.y=float(x),float(y)
        self.dir='LEFT'; self.next_dir='LEFT'
        self.progress=0.0; self._waka_toggle=False
        self.mouth_angle=30
        self.alive=True
    def try_set_dir(self,board,new_dir):
        dx,dy=DIR_VEC[new_dir]
        if is_passable(board,int(self.x+dx),int(self.y+dy)): self.next_dir=new_dir
    def move(self,board):
        if not self.alive: return 0
        dxn,dyn=DIR_VEC[self.next_dir]
        if is_passable(board,int(self.x+dxn),int(self.y+dyn)): self.dir=self.next_dir
        dx,dy=DIR_VEC[self.dir]; nx,ny=int(self.x+dx),int(self.y+dy)
        points=0
        if is_passable(board,nx,ny):
            self.progress+=PACMAN_SPEED
            if self.progress>=1.0:
                self.x+=dx; self.y+=dy; self.progress=0.0
                if board[ny][nx]=='.':
                    board[ny][nx]=' '; points+=10
                    (waka1 if self._waka_toggle else waka2).play()
                    self._waka_toggle=not self._waka_toggle
                elif board[ny][nx]=='o':
                    board[ny][nx]=' '; points+=50
                    GameState.trigger_frightened(); powerup.play()
        return points
    def draw(self,surf):
        cx,cy=tile_center_px(self.x,self.y)
        if self.alive:
            # Animated mouth
            start_angle,end_angle=0,360
            if self.dir=='RIGHT': start_angle,end_angle=self.mouth_angle,360-self.mouth_angle
            if self.dir=='LEFT':  start_angle,end_angle=180+self.mouth_angle,180-self.mouth_angle
            if self.dir=='UP':    start_angle,end_angle=90+self.mouth_angle,90-self.mouth_angle
            if self.dir=='DOWN':  start_angle,end_angle=270+self.mouth_angle,270-self.mouth_angle
            pygame.draw.arc(surf,YELLOW,(cx-10,cy-10,20,20),math.radians(start_angle),math.radians(end_angle),CELL_SIZE)
        else:
            pygame.draw.circle(surf,YELLOW,(cx,cy),CELL_SIZE//2)
    def die(self): self.alive=False

class Ghost:
    def __init__(self,name,color,x,y):
        self.name=name; self.color=color
        self.spawn=(x,y); self.reset()
    def reset(self):
        self.x,self.y=self.spawn; self.dir=random.choice(DIRS)
        self.progress=0.0; self.eaten=False
    def move(self,board,pac,blinky_tile,mode):
        if self.progress<1.0: self.progress+=GHOST_SPEED; return
        if self.eaten: target=(13,14)
        else:
            if GameState.frightened_active() and not self.eaten:
                target=(random.randint(0,27),random.randint(0,30))
            else:
                target=(int(pac.x),int(pac.y)) if mode=='chase' else SCATTER_CORNERS[self.name]
        best=None; bestdist=1e9
        for d in DIRS:
            if d==OPPOSITE[self.dir]: continue
            dx,dy=DIR_VEC[d]; nx,ny=int(self.x+dx),int(self.y+dy)
            if is_passable(board,nx,ny):
                dist=(nx-target[0])**2+(ny-target[1])**2
                if dist<bestdist: bestdist=dist; best=d
        if best: self.dir=best
        dx,dy=DIR_VEC[self.dir]; self.x+=dx; self.y+=dy; self.progress=0.0
        if self.x<0: self.x=27
        if self.x>27: self.x=0
        if self.eaten and (int(self.x),int(self.y))==(13,14): self.eaten=False
    def draw(self,surf):
        cx,cy=tile_center_px(self.x,self.y)
        if self.eaten:
            pygame.draw.circle(surf,WHITE,(cx-4,cy-2),4)
            pygame.draw.circle(surf,WHITE,(cx+4,cy-2),4)
            pygame.draw.circle(surf,BLACK,(cx-4,cy-2),2)
            pygame.draw.circle(surf,BLACK,(cx+4,cy-2),2)
        else:
            col=FRIGHT_BLUE if GameState.frightened_active() else self.color
            pygame.draw.circle(surf,col,(cx,cy),CELL_SIZE//2)
            # Eyes
            pygame.draw.circle(surf,WHITE,(cx-4,cy-3),4)
            pygame.draw.circle(surf,WHITE,(cx+4,cy-3),4)
            pygame.draw.circle(surf,BLACK,(cx-4,cy-3),2)
            pygame.draw.circle(surf,BLACK,(cx+4,cy-3),2)

# --- Modes ---
def global_mode(now): return 'chase' if (now//7000)%2 else 'scatter'

# --- Menu/Intro ---
def show_menu():
    waiting=True
    while waiting:
        screen.fill(BLACK)
        t=title_font.render("PAC-MAN",True,YELLOW)
        screen.blit(t,t.get_rect(center=(SCREEN_WIDTH//2,200)))
        draw_center_text(["Press SPACE to Start"],WHITE)
        c=font.render("© Nintendo © Team Flames",True,WHITE)
        screen.blit(c,(SCREEN_WIDTH//2-120,500))
        for e in pygame.event.get():
            if e.type==pygame.QUIT: pygame.quit(); sys.exit()
            if e.type==pygame.KEYDOWN and e.key==pygame.K_SPACE: waiting=False
        pygame.display.flip(); clock.tick(FPS)

def show_intro():
    screen.fill(BLACK); draw_center_text(["Get Ready!"],YELLOW)
    pygame.display.flip(); pygame.time.delay(1500)
def show_roll_call():
    screen.fill(BLACK)
    draw_center_text(["Blinky - Red","Pinky - Pink","Inky - Cyan","Clyde - Orange"],WHITE)
    pygame.display.flip(); pygame.time.delay(2000)

# --- Main ---
def main():
    show_menu(); show_intro(); show_roll_call()
    maze=[row[:] for row in maze1]
    pacman=Pacman(13,23)
    blinky=Ghost('blinky',RED,13,11)
    pinky=Ghost('pinky',PINK,12,11)
    inky=Ghost('inky',CYAN,13,10)
    clyde=Ghost('clyde',ORANGE,14,11)
    ghosts=[blinky,pinky,inky,clyde]

    score=0; state='READY'; ready_until=pygame.time.get_ticks()+1500; running=True
    game_over_until=0; win_until=0
    siren.play(loops=-1)

    while running:
        now=pygame.time.get_ticks()
        for e in pygame.event.get():
            if e.type==pygame.QUIT: running=False
            elif e.type==pygame.KEYDOWN:
                if e.key==pygame.K_ESCAPE: running=False
                elif e.key==pygame.K_LEFT: pacman.try_set_dir(maze,'LEFT')
                elif e.key==pygame.K_RIGHT: pacman.try_set_dir(maze,'RIGHT')
                elif e.key==pygame.K_UP: pacman.try_set_dir(maze,'UP')
                elif e.key==pygame.K_DOWN: pacman.try_set_dir(maze,'DOWN')

        screen.fill(BLACK); draw_board(screen,maze)

        if state=='READY':
            for g in ghosts: g.draw(screen); pacman.draw(screen)
            draw_center_text(["READY!"],YELLOW)
            if now>=ready_until: state='PLAY'

        elif state=='PLAY':
            score+=pacman.move(maze)
            gmode='scatter' if GameState.frightened_active() else global_mode(now)
            blinky_tile=(int(blinky.x),int(blinky.y))
            for g in ghosts: g.move(maze,pacman,blinky_tile,gmode); g.draw(screen)
            pacman.draw(screen)
            for g in ghosts:
                if abs(pacman.x-g.x)<=0.5 and abs(pacman.y-g.y)<=0.5:
                    if GameState.frightened_active() and not g.eaten:
                        pts=200*(2**GameState.ghost_eat_streak)
                        score+=pts; GameState.ghost_eat_streak+=1
                        g.eaten=True
                    elif not g.eaten:
                        pacman.die(); state='GAME_OVER'; game_over_until=now+1600; siren.stop()
            if count_dots(maze)==0:
                state='WIN'; win_until=now+2000; siren.stop()

        elif state=='WIN':
            for g in ghosts: g.draw(screen); pacman.draw(screen)
            draw_center_text(["YOU WIN!","BOARD CLEARED"])
            if now>=win_until: running=False

        elif state=='GAME_OVER':
            for g in ghosts: g.draw(screen); pacman.draw(screen)
            draw_center_text(["GAME OVER"],RED)
            if now>=game_over_until: running=False

        hud=font.render(f"Score: {score}",True,WHITE)
        screen.blit(hud,(10,10))
        pygame.display.flip(); clock.tick(FPS)

    siren.stop(); pygame.quit(); sys.exit()

if __name__=="__main__": main()
