#!/usr/bin/env python3
import pygame, sys, random, array

pygame.init()
WIDTH, HEIGHT = 600, 400
FPS = 60
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Ultra Soft Pong")
clock = pygame.time.Clock()

# --- COLORS ---
CREAM = (255, 240, 210)
BLACK = (0, 0, 0)

font_title = pygame.font.SysFont("Courier", 60, bold=True)
font_small = pygame.font.SysFont("Courier", 26, bold=True)
font_fps = pygame.font.SysFont("Courier", 18, bold=False)

# --- SOUND SYSTEM ---
SAMPLE_RATE = 44100

def make_square_wave(freq=440, duration=0.1, volume=0.5):
    length = int(SAMPLE_RATE * duration)
    arr = array.array("h")
    half_period = int(SAMPLE_RATE / (2 * freq))
    amp = int(32767 * volume)
    for i in range(length):
        arr.append(amp if (i // half_period) % 2 == 0 else -amp)
    return pygame.mixer.Sound(buffer=arr)

def boop(): make_square_wave(880, 0.05, 0.3).play()
def beep(): make_square_wave(440, 0.1, 0.3).play()
def menu_jingle():
    for f in [523, 659, 784]:
        make_square_wave(f, 0.1, 0.3).play()
        pygame.time.delay(100)
def win_jingle():
    for f in [784, 659, 523, 392]:
        make_square_wave(f, 0.1, 0.4).play()
        pygame.time.delay(100)

# --- GAME OBJECTS ---
ball = pygame.Rect(WIDTH//2 - 10, HEIGHT//2 - 10, 20, 20)
paddle_w, paddle_h = 10, 80
ai = pygame.Rect(20, HEIGHT//2 - paddle_h//2, paddle_w, paddle_h)
player = pygame.Rect(WIDTH - 30, HEIGHT//2 - paddle_h//2, paddle_w, paddle_h)

ball_speed = [4 * random.choice((1, -1)), 4 * random.choice((1, -1))]
ai_speed = 4
ai_score = player_score = 0
game_over = False
in_menu = True
in_howto = False
in_credits = False

# --- Leaderboard ---
high_player = 0
high_ai = 0

def reset_ball():
    global ball_speed
    ball.center = (WIDTH//2, HEIGHT//2)
    ball_speed = [4 * random.choice((1, -1)), 4 * random.choice((1, -1))]

def footer():
    text = font_small.render("© Samsoft • UltraSoft Series • Powered by OpenAI", True, CREAM)
    screen.blit(text, (WIDTH//2 - text.get_width()//2, HEIGHT - 40))

def draw_fps(current_fps):
    fps_text = font_fps.render(f"{current_fps:.0f} FPS", True, CREAM)
    screen.blit(fps_text, (WIDTH - fps_text.get_width() - 10, 10))

def draw_menu():
    screen.fill(BLACK)
    title = font_title.render("Ultra Soft Pong", True, CREAM)
    start = font_small.render("Press ENTER to Start", True, CREAM)
    howto = font_small.render("Press H for How to Play", True, CREAM)
    credits = font_small.render("Press C for Credits", True, CREAM)
    lb = font_small.render(f"Leaderboard: Player {high_player} | AI {high_ai}", True, CREAM)
    screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//2 - 120))
    screen.blit(start, (WIDTH//2 - start.get_width()//2, HEIGHT//2 + 10))
    screen.blit(howto, (WIDTH//2 - howto.get_width()//2, HEIGHT//2 + 50))
    screen.blit(credits, (WIDTH//2 - credits.get_width()//2, HEIGHT//2 + 90))
    screen.blit(lb, (WIDTH//2 - lb.get_width()//2, HEIGHT//2 + 140))
    footer()
    draw_fps(clock.get_fps())
    pygame.display.flip()

def draw_howto():
    screen.fill(BLACK)
    title = font_title.render("HOW TO PLAY", True, CREAM)
    lines = [
        "Move your paddle with the mouse.",
        "Deflect the ball past the AI to score!",
        "First to 5 points wins the match.",
        "",
        "Press ENTER to return to Menu."
    ]
    screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//2 - 120))
    for i, line in enumerate(lines):
        text = font_small.render(line, True, CREAM)
        screen.blit(text, (WIDTH//2 - text.get_width()//2, HEIGHT//2 - 20 + i*30))
    footer()
    draw_fps(clock.get_fps())
    pygame.display.flip()

def draw_credits():
    screen.fill(BLACK)
    title = font_title.render("CREDITS", True, CREAM)
    names = [
        "[C] Samsoft",
        "[C] Atari",
        "[C] OpenAI",
        "[C] 2025 Ultra Soft Pong",
        "",
        "Press ENTER to return to Menu."
    ]
    screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//2 - 120))
    for i, name in enumerate(names):
        text = font_small.render(name, True, CREAM)
        screen.blit(text, (WIDTH//2 - text.get_width()//2, HEIGHT//2 - 20 + i*30))
    footer()
    draw_fps(clock.get_fps())
    pygame.display.flip()

def draw_game():
    screen.fill(BLACK)
    pygame.draw.rect(screen, CREAM, ai)
    pygame.draw.rect(screen, CREAM, player)
    pygame.draw.ellipse(screen, CREAM, ball)
    pygame.draw.aaline(screen, CREAM, (WIDTH//2, 0), (WIDTH//2, HEIGHT))
    score = font_small.render(f"{ai_score}  -  {player_score}", True, CREAM)
    screen.blit(score, (WIDTH//2 - 40, 10))
    footer()
    draw_fps(clock.get_fps())
    pygame.display.flip()

def draw_gameover():
    screen.fill(BLACK)
    over = font_title.render("GAME OVER!", True, CREAM)
    restart = font_small.render("Y = Restart   N = Quit", True, CREAM)
    screen.blit(over, (WIDTH//2 - over.get_width()//2, HEIGHT//2 - 80))
    screen.blit(restart, (WIDTH//2 - restart.get_width()//2, HEIGHT//2 + 20))
    footer()
    draw_fps(clock.get_fps())
    pygame.display.flip()

# --- Splash Screen ---
screen.fill(BLACK)
splash = font_title.render("Samsoft Presents…", True, CREAM)
screen.blit(splash, (WIDTH//2 - splash.get_width()//2, HEIGHT//2 - 40))
pygame.display.flip()
pygame.time.delay(2000)

# === MAIN LOOP ===
running = True
menu_jingle()

while running:
    if in_menu:
        draw_menu()
        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_RETURN:
                    in_menu = False
                    menu_jingle()
                elif e.key == pygame.K_h:
                    in_menu = False
                    in_howto = True
                    beep()
                elif e.key == pygame.K_c:
                    in_menu = False
                    in_credits = True
                    beep()

    elif in_howto:
        draw_howto()
        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_RETURN:
                in_howto = False
                in_menu = True
                beep()

    elif in_credits:
        draw_credits()
        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_RETURN:
                in_credits = False
                in_menu = True
                beep()

    elif not game_over:
        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit()

        mouse_y = pygame.mouse.get_pos()[1]
        player.centery = mouse_y
        player.y = max(0, min(HEIGHT - paddle_h, player.y))

        if ai.centery < ball.centery: ai.y += ai_speed
        if ai.centery > ball.centery: ai.y -= ai_speed
        ai.y = max(0, min(HEIGHT - paddle_h, ai.y))

        ball.x += ball_speed[0]
        ball.y += ball_speed[1]

        if ball.top <= 0 or ball.bottom >= HEIGHT:
            ball_speed[1] *= -1
            boop()
        if ball.colliderect(ai) or ball.colliderect(player):
            ball_speed[0] *= -1
            boop()

        if ball.left <= 0:
            player_score += 1
            beep()
            reset_ball()
        if ball.right >= WIDTH:
            ai_score += 1
            beep()
            reset_ball()

        if ai_score == 5 or player_score == 5:
            game_over = True
            win_jingle()
            if player_score > high_player: high_player = player_score
            if ai_score > high_ai: high_ai = ai_score

        draw_game()

    else:
        draw_gameover()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_y:
                    ai_score = player_score = 0
                    game_over = False
                    reset_ball()
                    beep()
                elif e.key == pygame.K_n:
                    pygame.quit(); sys.exit()

    clock.tick(FPS)
