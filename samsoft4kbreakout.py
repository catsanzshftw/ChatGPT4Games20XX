import pygame, sys, numpy as np

# === INIT ===
pygame.init()
pygame.mixer.init()
WIDTH, HEIGHT = 640, 480
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Samsoft Breakout")

BLACK, WHITE = (0,0,0), (255,255,255)
clock = pygame.time.Clock()

# === NES-style sound ===
def make_beep(freq=440, dur_ms=150, vol=0.5):
    sr = 44100
    n_samples = int(sr * dur_ms / 1000)
    buf = (np.sign(np.sin(2*np.pi*np.arange(n_samples)*freq/sr)) * 32767).astype(np.int16)
    s = pygame.mixer.Sound(buffer=buf)
    s.set_volume(vol)
    return s

boot_chime = [make_beep(440,200,0.5), make_beep(554,200,0.5), make_beep(659,200,0.5)]
sfx_paddle = make_beep(800, 80, 0.5)
sfx_brick  = make_beep(500, 120, 0.5)
sfx_wall   = make_beep(300, 100, 0.5)

# === Fonts ===
big_font = pygame.font.SysFont("Arial", 48, bold=True)
mid_font = pygame.font.SysFont("Arial", 32)
small_font = pygame.font.SysFont("Arial", 20)

# === NES Hardware Boot Simulation ===
def nes_boot_sequence():
    messages = [
        "Initializing Samsoft NES Hardware...",
        "Checking CPU... OK",
        "Checking PPU... OK",
        "Checking APU... OK",
        "Loading Seal of Quality..."
    ]
    for msg in messages:
        screen.fill(BLACK)
        t = mid_font.render(msg, True, WHITE)
        screen.blit(t, (WIDTH//2 - t.get_width()//2, HEIGHT//2))
        pygame.display.flip()
        make_beep(300, 80, 0.5).play()
        pygame.time.delay(600)

# === Seal of Quality Screen ===
def seal_of_quality():
    timer = 0
    while timer < 180:  # ~3 seconds
        for e in pygame.event.get():
            if e.type == pygame.QUIT: sys.exit()

        screen.fill(BLACK)
        # Circle seal
        pygame.draw.circle(screen, WHITE, (WIDTH//2, HEIGHT//2-40), 100, 6)
        text1 = small_font.render("SAMSOFT", True, WHITE)
        text2 = small_font.render("SEAL OF", True, WHITE)
        text3 = small_font.render("QUALITY", True, WHITE)
        screen.blit(text1, (WIDTH//2 - text1.get_width()//2, HEIGHT//2-70))
        screen.blit(text2, (WIDTH//2 - text2.get_width()//2, HEIGHT//2-40))
        screen.blit(text3, (WIDTH//2 - text3.get_width()//2, HEIGHT//2-10))

        sub = small_font.render("Official Samsoft Software Product", True, WHITE)
        screen.blit(sub, (WIDTH//2 - sub.get_width()//2, HEIGHT//2+80))

        pygame.display.flip()
        clock.tick(60); timer += 1

# === Intro Stamp ===
def play_boot_chime():
    for s in boot_chime:
        s.play()
        pygame.time.delay(200)

def intro_stamp():
    play_boot_chime()
    timer = 0
    while timer < 180:  # ~3 sec
        for e in pygame.event.get():
            if e.type == pygame.QUIT: sys.exit()
        screen.fill(BLACK)
        rect = pygame.Rect(100, 150, 440, 180)
        pygame.draw.rect(screen, WHITE, rect, width=6)
        t1 = big_font.render("SAMSOFT SOFTWARE", True, WHITE)
        t2 = mid_font.render("PRESENTS", True, WHITE)
        screen.blit(t1, (WIDTH//2 - t1.get_width()//2, 190))
        screen.blit(t2, (WIDTH//2 - t2.get_width()//2, 250))
        pygame.display.flip()
        clock.tick(60); timer += 1

# === Main Menu ===
def main_menu():
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT: sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key in [pygame.K_RETURN, pygame.K_z]:
                    return  # start game

        screen.fill(BLACK)
        title = big_font.render("SAMSOFT BREAKOUT", True, WHITE)
        prompt = mid_font.render("Press Z or Enter to Play", True, WHITE)
        footer = small_font.render("[C] Team Flames   [C] Nintendo ###", True, WHITE)

        screen.blit(title, (WIDTH//2 - title.get_width()//2, 150))
        screen.blit(prompt, (WIDTH//2 - prompt.get_width()//2, 260))
        screen.blit(footer, (WIDTH//2 - footer.get_width()//2, HEIGHT-40))

        pygame.display.flip()
        clock.tick(60)

# === Breakout Game ===
PADDLE_W, PADDLE_H, BALL_SIZE = 80, 10, 10
BRICK_ROWS, BRICK_COLS = 6, 10
BRICK_W, BRICK_H = WIDTH//BRICK_COLS, 20
brick_colors = [(200,0,0),(255,140,0),(200,200,0),(0,200,0),(0,0,200),(255,255,255)]

def reset_bricks():
    bricks=[]
    for r in range(BRICK_ROWS):
        for c in range(BRICK_COLS):
            bricks.append((pygame.Rect(c*BRICK_W, r*BRICK_H+50, BRICK_W, BRICK_H),
                          brick_colors[r%len(brick_colors)]))
    return bricks

def breakout():
    paddle = pygame.Rect(WIDTH//2-PADDLE_W//2, HEIGHT-30, PADDLE_W, PADDLE_H)
    ball = pygame.Rect(WIDTH//2, HEIGHT//2, BALL_SIZE, BALL_SIZE)
    speed=[4,-4]; bricks=reset_bricks()
    score,lives=0,3
    font=pygame.font.SysFont("Arial",24)

    while True:
        for e in pygame.event.get():
            if e.type==pygame.QUIT: sys.exit()

        # Paddle
        mx,_=pygame.mouse.get_pos()
        paddle.x=max(0,min(WIDTH-PADDLE_W,mx-PADDLE_W//2))

        # Ball
        ball.x+=speed[0]; ball.y+=speed[1]
        if ball.left<=0 or ball.right>=WIDTH:
            speed[0]*=-1; sfx_wall.play()
        if ball.top<=0:
            speed[1]*=-1; sfx_wall.play()
        if ball.bottom>=HEIGHT:
            lives-=1
            if lives<=0: return  # back to menu
            ball.x,ball.y=WIDTH//2,HEIGHT//2; speed=[4,-4]

        if ball.colliderect(paddle):
            speed[1]=-abs(speed[1]); sfx_paddle.play()

        hit=ball.collidelist([b[0] for b in bricks])
        if hit!=-1:
            brick,color=bricks.pop(hit)
            speed[1]*=-1; score+=10; sfx_brick.play()

        # Draw
        screen.fill(BLACK)
        pygame.draw.rect(screen,WHITE,paddle)
        pygame.draw.ellipse(screen,WHITE,ball)
        for brick,color in bricks: pygame.draw.rect(screen,color,brick)
        screen.blit(font.render(f"Score: {score}",True,WHITE),(10,10))
        screen.blit(font.render(f"Lives: {lives}",True,WHITE),(WIDTH-100,10))
        pygame.display.flip(); clock.tick(60)

# === RUN ===
if __name__=="__main__":
    nes_boot_sequence()
    seal_of_quality()
    intro_stamp()
    while True:
        main_menu()
        breakout()
import pygame, sys, numpy as np

# === INIT ===
pygame.init()
pygame.mixer.init()
WIDTH, HEIGHT = 640, 480
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Samsoft Breakout")

BLACK, WHITE = (0,0,0), (255,255,255)
clock = pygame.time.Clock()

# === NES-style sound ===
def make_beep(freq=440, dur_ms=150, vol=0.5):
    sr = 44100
    n_samples = int(sr * dur_ms / 1000)
    buf = (np.sign(np.sin(2*np.pi*np.arange(n_samples)*freq/sr)) * 32767).astype(np.int16)
    s = pygame.mixer.Sound(buffer=buf)
    s.set_volume(vol)
    return s

boot_chime = [make_beep(440,200,0.5), make_beep(554,200,0.5), make_beep(659,200,0.5)]
sfx_paddle = make_beep(800, 80, 0.5)
sfx_brick  = make_beep(500, 120, 0.5)
sfx_wall   = make_beep(300, 100, 0.5)

# === Fonts ===
big_font = pygame.font.SysFont("Arial", 48, bold=True)
mid_font = pygame.font.SysFont("Arial", 32)
small_font = pygame.font.SysFont("Arial", 20)

# === NES Hardware Boot Simulation ===
def nes_boot_sequence():
    messages = [
        "Initializing Samsoft NES Hardware...",
        "Checking CPU... OK",
        "Checking PPU... OK",
        "Checking APU... OK",
        "Loading Seal of Quality..."
    ]
    for msg in messages:
        screen.fill(BLACK)
        t = mid_font.render(msg, True, WHITE)
        screen.blit(t, (WIDTH//2 - t.get_width()//2, HEIGHT//2))
        pygame.display.flip()
        make_beep(300, 80, 0.5).play()
        pygame.time.delay(600)

# === Seal of Quality Screen ===
def seal_of_quality():
    timer = 0
    while timer < 180:  # ~3 seconds
        for e in pygame.event.get():
            if e.type == pygame.QUIT: sys.exit()

        screen.fill(BLACK)
        # Circle seal
        pygame.draw.circle(screen, WHITE, (WIDTH//2, HEIGHT//2-40), 100, 6)
        text1 = small_font.render("SAMSOFT", True, WHITE)
        text2 = small_font.render("SEAL OF", True, WHITE)
        text3 = small_font.render("QUALITY", True, WHITE)
        screen.blit(text1, (WIDTH//2 - text1.get_width()//2, HEIGHT//2-70))
        screen.blit(text2, (WIDTH//2 - text2.get_width()//2, HEIGHT//2-40))
        screen.blit(text3, (WIDTH//2 - text3.get_width()//2, HEIGHT//2-10))

        sub = small_font.render("Official Samsoft Software Product", True, WHITE)
        screen.blit(sub, (WIDTH//2 - sub.get_width()//2, HEIGHT//2+80))

        pygame.display.flip()
        clock.tick(60); timer += 1

# === Intro Stamp ===
def play_boot_chime():
    for s in boot_chime:
        s.play()
        pygame.time.delay(200)

def intro_stamp():
    play_boot_chime()
    timer = 0
    while timer < 180:  # ~3 sec
        for e in pygame.event.get():
            if e.type == pygame.QUIT: sys.exit()
        screen.fill(BLACK)
        rect = pygame.Rect(100, 150, 440, 180)
        pygame.draw.rect(screen, WHITE, rect, width=6)
        t1 = big_font.render("SAMSOFT SOFTWARE", True, WHITE)
        t2 = mid_font.render("PRESENTS", True, WHITE)
        screen.blit(t1, (WIDTH//2 - t1.get_width()//2, 190))
        screen.blit(t2, (WIDTH//2 - t2.get_width()//2, 250))
        pygame.display.flip()
        clock.tick(60); timer += 1

# === Main Menu ===
def main_menu():
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT: sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key in [pygame.K_RETURN, pygame.K_z]:
                    return  # start game

        screen.fill(BLACK)
        title = big_font.render("SAMSOFT BREAKOUT", True, WHITE)
        prompt = mid_font.render("Press Z or Enter to Play", True, WHITE)
        footer = small_font.render("[C] Team Flames   [C] Nintendo ###", True, WHITE)

        screen.blit(title, (WIDTH//2 - title.get_width()//2, 150))
        screen.blit(prompt, (WIDTH//2 - prompt.get_width()//2, 260))
        screen.blit(footer, (WIDTH//2 - footer.get_width()//2, HEIGHT-40))

        pygame.display.flip()
        clock.tick(60)

# === Breakout Game ===
PADDLE_W, PADDLE_H, BALL_SIZE = 80, 10, 10
BRICK_ROWS, BRICK_COLS = 6, 10
BRICK_W, BRICK_H = WIDTH//BRICK_COLS, 20
brick_colors = [(200,0,0),(255,140,0),(200,200,0),(0,200,0),(0,0,200),(255,255,255)]

def reset_bricks():
    bricks=[]
    for r in range(BRICK_ROWS):
        for c in range(BRICK_COLS):
            bricks.append((pygame.Rect(c*BRICK_W, r*BRICK_H+50, BRICK_W, BRICK_H),
                          brick_colors[r%len(brick_colors)]))
    return bricks

def breakout():
    paddle = pygame.Rect(WIDTH//2-PADDLE_W//2, HEIGHT-30, PADDLE_W, PADDLE_H)
    ball = pygame.Rect(WIDTH//2, HEIGHT//2, BALL_SIZE, BALL_SIZE)
    speed=[4,-4]; bricks=reset_bricks()
    score,lives=0,3
    font=pygame.font.SysFont("Arial",24)

    while True:
        for e in pygame.event.get():
            if e.type==pygame.QUIT: sys.exit()

        # Paddle
        mx,_=pygame.mouse.get_pos()
        paddle.x=max(0,min(WIDTH-PADDLE_W,mx-PADDLE_W//2))

        # Ball
        ball.x+=speed[0]; ball.y+=speed[1]
        if ball.left<=0 or ball.right>=WIDTH:
            speed[0]*=-1; sfx_wall.play()
        if ball.top<=0:
            speed[1]*=-1; sfx_wall.play()
        if ball.bottom>=HEIGHT:
            lives-=1
            if lives<=0: return  # back to menu
            ball.x,ball.y=WIDTH//2,HEIGHT//2; speed=[4,-4]

        if ball.colliderect(paddle):
            speed[1]=-abs(speed[1]); sfx_paddle.play()

        hit=ball.collidelist([b[0] for b in bricks])
        if hit!=-1:
            brick,color=bricks.pop(hit)
            speed[1]*=-1; score+=10; sfx_brick.play()

        # Draw
        screen.fill(BLACK)
        pygame.draw.rect(screen,WHITE,paddle)
        pygame.draw.ellipse(screen,WHITE,ball)
        for brick,color in bricks: pygame.draw.rect(screen,color,brick)
        screen.blit(font.render(f"Score: {score}",True,WHITE),(10,10))
        screen.blit(font.render(f"Lives: {lives}",True,WHITE),(WIDTH-100,10))
        pygame.display.flip(); clock.tick(60)

# === RUN ===
if __name__=="__main__":
    nes_boot_sequence()
    seal_of_quality()
    intro_stamp()
    while True:
        main_menu()
        breakout()
