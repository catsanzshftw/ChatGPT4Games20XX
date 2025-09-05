# ps1_pong.py
# Single-file Pygame Pong
# - Right paddle = AI
# - 60 FPS, no external assets (all sounds generated in code)
# - PS1-ish vibes: low-res render, jitter, scanlines, slight dither
# - Game Over when each side has 5+ points (configurable), Y/N to restart/quit

import sys, math, random
from array import array

import pygame

# --------------------------- Config --------------------------- #
BASE_W, BASE_H = 320, 240          # render resolution (low-res, then scaled)
SCALE = 3                          # upscale factor for the display window
FPS = 60
WIN_W, WIN_H = BASE_W * SCALE, BASE_H * SCALE

PADDLE_W, PADDLE_H = 6, 34
BALL_SIZE = 4

PADDLE_SPEED = 145.0               # px/s at base resolution
BALL_SPEED_START = 105.0
BALL_SPEED_MAX = 260.0
BALL_SPEED_GAIN = 1.06             # speed-up after paddle hit

SCORE_TO_END = 5
END_REQUIRE_BOTH_SIDES = True      # True => require BOTH sides >=5; False => game over when EITHER reaches 5

# CRT / PS1-ish presentation
WOBBLE_AMT = 2                     # horizontal per-scanline wobble (pixels)
WOBBLE_SPEED = 2.2                 # wobble speed multiplier
SCANLINE_ALPHA = 46                # 0..255 opacity of scanlines overlay
DITHER_ALPHA = 18                  # 0..255 opacity of dither overlay

# Audio
MIXER_SAMPLE_RATE = 22050
MIXER_SIZE = -16                   # 16-bit signed
MIXER_CHANNELS = 1                 # mono
MIXER_BUFFER = 512

# ------------------------- Audio Synth ------------------------ #
def init_audio():
    pygame.mixer.pre_init(MIXER_SAMPLE_RATE, MIXER_SIZE, MIXER_CHANNELS, MIXER_BUFFER)
    # Important: call pygame.init() AFTER pre_init so mixer picks up settings.

def _env(i, n, sr, attack=0.005, release=0.020):
    if n <= 0:
        return 1.0
    a = max(1, int(sr * attack))
    r = max(1, int(sr * release))
    if i < a:
        return i / a
    if i > n - r:
        return max(0.0, (n - i) / r)
    return 1.0

def synth_tone(freq=440.0, duration=0.12, volume=0.5, wave='sine', sr=MIXER_SAMPLE_RATE):
    """Generate a one-shot tone (no files needed)."""
    n = int(duration * sr)
    buf = array('h')
    twopi = 2.0 * math.pi
    for i in range(n):
        t = i / sr
        if wave == 'sine':
            v = math.sin(twopi * freq * t)
        elif wave == 'square':
            v = 1.0 if math.sin(twopi * freq * t) >= 0 else -1.0
        elif wave == 'saw':
            v = 2.0 * ((freq * t) % 1.0) - 1.0
        elif wave == 'tri':
            v = 2.0 * abs(2.0 * ((freq * t) % 1.0) - 1.0) - 1.0
        else:
            v = 0.0
        v *= _env(i, n, sr)
        s = max(-1.0, min(1.0, v)) * volume
        buf.append(int(s * 32767))
    return pygame.mixer.Sound(buffer=buf.tobytes())

def synth_engine_loop(duration=2.0, volume=0.22, sr=MIXER_SAMPLE_RATE):
    """Looping low-fi 'engine' hum: saw + octave + a bit of noise + faint whine."""
    n = int(duration * sr)
    buf = array('h')
    base = 55.0
    twopi = 2.0 * math.pi
    rnd = random.Random(1337)  # deterministic small-noise to avoid clicks
    for i in range(n):
        t = i / sr
        # crude saws
        saw1 = 2.0 * ((base * t) % 1.0) - 1.0
        saw2 = 2.0 * (((base * 2.0) * t) % 1.0) - 1.0
        whine = 0.20 * math.sin(twopi * 1200.0 * t)
        noise = 0.07 * (rnd.random() * 2.0 - 1.0)
        flutter = 1.0 + 0.04 * math.sin(twopi * 0.9 * t)
        v = (0.55 * saw1 + 0.35 * saw2 + whine + noise) * flutter
        v = max(-1.0, min(1.0, v)) * volume
        buf.append(int(v * 32767))
    snd = pygame.mixer.Sound(buffer=buf.tobytes())
    snd.set_volume(volume)
    return snd

# --------------------------- Entities ------------------------- #
class Paddle:
    def __init__(self, x, y):
        self.x = x
        self.y = y  # center y in base-resolution coordinates

    def rect(self):
        return pygame.Rect(int(self.x - PADDLE_W / 2),
                           int(self.y - PADDLE_H / 2),
                           PADDLE_W, PADDLE_H)

    def move(self, dy, dt):
        self.y += dy * dt
        self.y = max(PADDLE_H / 2, min(BASE_H - PADDLE_H / 2, self.y))

class Ball:
    def __init__(self):
        self.reset()

    def reset(self, to_right=None):
        self.x = BASE_W / 2
        self.y = BASE_H / 2
        angle = random.uniform(-0.35 * math.pi, 0.35 * math.pi)
        if to_right is None:
            to_right = random.choice([True, False])
        self.vx = math.cos(angle) * BALL_SPEED_START * (1 if to_right else -1)
        self.vy = math.sin(angle) * BALL_SPEED_START

    def rect(self):
        return pygame.Rect(int(self.x - BALL_SIZE/2),
                           int(self.y - BALL_SIZE/2),
                           BALL_SIZE, BALL_SIZE)

# --------------------------- Drawing -------------------------- #
def make_scanlines_surface():
    surf = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
    surf.set_alpha(SCANLINE_ALPHA)
    for y in range(0, WIN_H, 2):
        pygame.draw.line(surf, (0, 0, 0, SCANLINE_ALPHA), (0, y), (WIN_W, y))
    return surf

def make_dither_surface():
    # Tiny 2x2 tile filled across a full-size overlay to hint at 1990s dithering.
    tile = pygame.Surface((2, 2), pygame.SRCALPHA)
    tile.fill((0, 0, 0, 0))
    tile.set_at((0, 0), (0, 0, 0, DITHER_ALPHA))
    overlay = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
    for y in range(0, WIN_H, 2):
        for x in range(0, WIN_W, 2):
            overlay.blit(tile, (x, y))
    return overlay

def draw_center_dotted_line(surface, color):
    seg_h = 6
    gap = 3
    x = BASE_W // 2
    for y in range(0, BASE_H, seg_h + gap):
        pygame.draw.rect(surface, color, (x - 1, y, 2, seg_h))

# ---------------------------- AI ------------------------------ #
class RightAI:
    def __init__(self):
        self.reaction = 0.12       # sec of predictive lead time
        self.max_speed = 150.0     # move speed
        self.jitter = 4.0          # target fuzz (px)

    def update(self, paddle: Paddle, ball: Ball, dt: float):
        # Only track when ball moving towards the AI
        if ball.vx > 0:
            target_y = ball.y + ball.vy * self.reaction
            # a little imperfection
            target_y += random.uniform(-self.jitter, self.jitter)
        else:
            target_y = BASE_H / 2

        dy = target_y - paddle.y
        if abs(dy) < 1.0:
            return
        move = self.max_speed if dy > 0 else -self.max_speed
        # ease down when close
        if abs(dy) < 20:
            move *= 0.45
        paddle.move(move, dt)

# --------------------------- Game Loop ------------------------ #
def main():
    init_audio()
    pygame.init()
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption("PS1-ish Pong (files=off, 60fps, AI Right)")

    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 24)
    big_font = pygame.font.SysFont(None, 32)

    # Low-res render target
    game_surf = pygame.Surface((BASE_W, BASE_H))
    scanlines = make_scanlines_surface()
    dither = make_dither_surface()

    # Colors chosen from a muted PS1-flavored palette
    BG = (12, 14, 20)
    FG = (220, 220, 220)
    DIM = (60, 70, 96)

    left = Paddle(12 + PADDLE_W // 2, BASE_H / 2)
    right = Paddle(BASE_W - (12 + PADDLE_W // 2), BASE_H / 2)
    ball = Ball()
    ai = RightAI()

    # Sounds (procedural)
    engine = synth_engine_loop(duration=2.2, volume=0.20)
    engine.play(loops=-1)
    snd_bounce = synth_tone(620, 0.07, 0.55, 'square')
    snd_boop = synth_tone(180, 0.12, 0.6, 'tri')
    snd_boop2 = synth_tone(240, 0.09, 0.5, 'saw')

    left_score = 0
    right_score = 0
    pause_timer = 0.0  # brief pause after scoring
    wobble_phase = 0.0
    state = "play"     # 'play' | 'gameover'

    def reset_round(scored_right: bool):
        nonlocal pause_timer
        ball.reset(to_right=not scored_right)
        pause_timer = 0.6

    def check_game_over():
        if END_REQUIRE_BOTH_SIDES:
            return (left_score >= SCORE_TO_END) and (right_score >= SCORE_TO_END)
        else:
            return (left_score >= SCORE_TO_END) or (right_score >= SCORE_TO_END)

    while True:
        dt = clock.tick(FPS) / 1000.0
        wobble_phase += dt * WOBBLE_SPEED

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if state == "gameover" and e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_y, pygame.K_RETURN):
                    # restart
                    left_score = 0
                    right_score = 0
                    left.y = BASE_H / 2
                    right.y = BASE_H / 2
                    ball.reset()
                    state = "play"
                elif e.key in (pygame.K_n, pygame.K_ESCAPE):
                    pygame.quit()
                    sys.exit()

        # Input (left paddle)
        keys = pygame.key.get_pressed()
        move_dir = 0.0
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            move_dir -= 1.0
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            move_dir += 1.0

        if state == "play":
            if pause_timer > 0.0:
                pause_timer -= dt
            else:
                # Update player paddle
                left.move(move_dir * PADDLE_SPEED, dt)
                # Update AI paddle
                ai.update(right, ball, dt)

                # Move ball
                ball.x += ball.vx * dt
                ball.y += ball.vy * dt

                # Wall bounce
                if ball.y <= BALL_SIZE / 2:
                    ball.y = BALL_SIZE / 2
                    ball.vy *= -1
                    snd_bounce.play()
                elif ball.y >= BASE_H - BALL_SIZE / 2:
                    ball.y = BASE_H - BALL_SIZE / 2
                    ball.vy *= -1
                    snd_bounce.play()

                # Paddle collisions
                brect = ball.rect()
                if brect.colliderect(left.rect()) and ball.vx < 0:
                    # position fix
                    ball.x = left.rect().right + BALL_SIZE / 2 + 0.1
                    # angle based on hit position
                    offset = (ball.y - left.y) / (PADDLE_H / 2)
                    ball.vx = abs(ball.vx) * BALL_SPEED_GAIN
                    ball.vy = (abs(ball.vx) * 0.25) * offset
                    # clamp speed
                    spd = (ball.vx ** 2 + ball.vy ** 2) ** 0.5
                    if spd > BALL_SPEED_MAX:
                        scale = BALL_SPEED_MAX / spd
                        ball.vx *= scale
                        ball.vy *= scale
                    snd_bounce.play()

                if brect.colliderect(right.rect()) and ball.vx > 0:
                    ball.x = right.rect().left - BALL_SIZE / 2 - 0.1
                    offset = (ball.y - right.y) / (PADDLE_H / 2)
                    ball.vx = -abs(ball.vx) * BALL_SPEED_GAIN
                    ball.vy = (abs(ball.vx) * 0.25) * offset
                    spd = (ball.vx ** 2 + ball.vy ** 2) ** 0.5
                    if spd > BALL_SPEED_MAX:
                        scale = BALL_SPEED_MAX / spd
                        ball.vx *= scale
                        ball.vy *= scale
                    snd_bounce.play()

                # Scoring
                if ball.x < -BALL_SIZE:
                    right_score += 1
                    snd_boop.play()
                    snd_boop2.play()
                    reset_round(scored_right=True)
                    if check_game_over():
                        state = "gameover"
                elif ball.x > BASE_W + BALL_SIZE:
                    left_score += 1
                    snd_boop.play()
                    snd_boop2.play()
                    reset_round(scored_right=False)
                    if check_game_over():
                        state = "gameover"

        # ------------------ Draw to low-res surface ------------------ #
        game_surf.fill(BG)

        # center dotted line
        draw_center_dotted_line(game_surf, DIM)

        # paddles & ball
        pygame.draw.rect(game_surf, FG, left.rect())
        pygame.draw.rect(game_surf, FG, right.rect())
        pygame.draw.rect(game_surf, FG, ball.rect())

        # scores
        ls = font.render(str(left_score), True, FG)
        rs = font.render(str(right_score), True, FG)
        game_surf.blit(ls, (BASE_W * 0.25 - ls.get_width() // 2, 8))
        game_surf.blit(rs, (BASE_W * 0.75 - rs.get_width() // 2, 8))

        if pause_timer > 0 and state == "play":
            hint = font.render("Get ready...", True, DIM)
            game_surf.blit(hint, (BASE_W // 2 - hint.get_width() // 2, BASE_H // 2 - 24))

        if state == "gameover":
            overlay = pygame.Surface((BASE_W, BASE_H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 140))
            game_surf.blit(overlay, (0, 0))
            title = big_font.render("GAME OVER", True, FG)
            cond = font.render(f"Condition: each side >= {SCORE_TO_END}", True, DIM)
            prompt = font.render("Restart? Y = yes  N = quit", True, FG)
            game_surf.blit(title, (BASE_W // 2 - title.get_width() // 2, BASE_H // 2 - 30))
            game_surf.blit(cond, (BASE_W // 2 - cond.get_width() // 2, BASE_H // 2 - 6))
            game_surf.blit(prompt, (BASE_W // 2 - prompt.get_width() // 2, BASE_H // 2 + 16))

        # ----------------- Scale & PS1-ish presentation ---------------- #
        scaled = pygame.transform.scale(game_surf, (WIN_W, WIN_H))

        # "Affine wobble" + scanlines pass (line-by-line blit with horizontal offset)
        screen.fill((0, 0, 0))
        # Copy each scanline with a slight X offset for a wobbly texture feel
        # (still very cheap at 60 fps for this window size).
        for y in range(WIN_H):
            # gentle sine wobble with a hint of randomness
            offset = int(WOBBLE_AMT * math.sin(0.035 * y + wobble_phase)) + (y % 3 == 0)
            # Clip rows to avoid wrapping artifacts
            src = pygame.Rect(0, y, WIN_W - abs(offset), 1)
            dstx = max(0, offset)
            screen.blit(scaled, (dstx, y), src)

        # Overlays: scanlines + light dither
        screen.blit(scanlines, (0, 0))
        screen.blit(dither, (0, 0))

        # Present
        pygame.display.flip()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pygame.quit()
        sys.exit()
