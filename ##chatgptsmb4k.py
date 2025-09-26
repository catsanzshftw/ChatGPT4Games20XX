import pygame
import sys

# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
TILE_SIZE = 32
FPS = 60

# World feel (NES-ish; hold Shift/X to run which is > NES walk speed)
WALK_MAX_SPEED = 160.0      # px/s  (~5 tiles/s)
RUN_MAX_SPEED  = 240.0      # px/s  (~7.5 tiles/s)
ACCEL          = 3200.0     # px/s²
FRICTION       = 3600.0     # px/s²
GRAVITY        = 3000.0     # px/s²
JUMP_SPEED     = 900.0      # px/s   (initial jump velocity)
MAX_FALL_SPEED = 1400.0     # px/s
COYOTE_TIME    = 0.08       # s after leaving a ledge where jump still works
JUMP_BUFFER    = 0.12       # s before landing we can queue a jump

# Colors
SKY = (172, 206, 255)
GROUND = (139, 76, 39)
FLAG_GREEN = (34, 177, 76)
COIN_YELLOW = (255, 236, 134)
PLAYER_RED = (206, 52, 52)
WHITE = (255, 255, 255)
UI_SHADOW = (16, 22, 48)

# ──────────────────────────────────────────────────────────────────────────────
# Level Data (World 1-1)
# Legend: P = ground, C = coin, (empty = air)
# ──────────────────────────────────────────────────────────────────────────────
LEVEL_1_1 = [
    "                                                                                ",
    "                                                                                ",
    "                                                                                ",
    "                                                                                ",
    "                                                                                ",
    "                                                                                ",
    "                                                                                ",
    "                                                                                ",
    "                                                                                ",
    "                                                                                ",
    "                                                                                ",
    "                                                                                ",
    "                                                                                ",
    "                                                                                ",
    "                                                                                ",
    "                       C   C                                                    ",
    "                                                                                ",
    "PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP",
    "PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP",
]

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────
def sign(x: float) -> int:
    return (x > 0) - (x < 0)

# ──────────────────────────────────────────────────────────────────────────────
# Player
# ──────────────────────────────────────────────────────────────────────────────
class Player(pygame.sprite.Sprite):
    def __init__(self, frames):
        super().__init__()
        if not frames:
            raise ValueError("Frames list cannot be empty")
        self.frames = frames
        self.image = frames[0]
        self.rect = self.image.get_rect()

        # spawn is set later after level build; defaults keep original behavior
        self.spawn_x = TILE_SIZE
        self.spawn_y = SCREEN_HEIGHT - 6 * TILE_SIZE

        # Physics
        self.vx = 0.0
        self.vy = 0.0
        self.facing = 1
        self.on_ground = False

        # Timers
        self.coyote = 0.0
        self.jump_buf = 0.0

        # Meta
        self.anim = 0
        self.coins = 0
        self.world = 1
        self.level = 1

        self._reset_to_spawn()

    def set_spawn(self, x, y):
        self.spawn_x = x
        self.spawn_y = y
        self._reset_to_spawn()

    def _reset_to_spawn(self):
        self.rect.x = int(self.spawn_x)
        self.rect.y = int(self.spawn_y)
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = False
        self.coyote = 0.0
        self.jump_buf = 0.0

    def reset(self):
        self._reset_to_spawn()
        self.image = self.frames[0]

    def respawn(self):
        self._reset_to_spawn()
        self.image = self.frames[0]

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_z, pygame.K_UP):
            self.jump_buf = JUMP_BUFFER

    def update(self, keys, tiles, dt):
        # ── Input/desired speed
        left  = keys[pygame.K_LEFT] or keys[pygame.K_a]
        right = keys[pygame.K_RIGHT] or keys[pygame.K_d]
        running = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT] or keys[pygame.K_x]
        max_speed = RUN_MAX_SPEED if running else WALK_MAX_SPEED

        # ── Horizontal accel/friction
        if left ^ right:
            ax = -ACCEL if left else ACCEL
            self.vx += ax * dt
            self.facing = -1 if left else 1
        else:
            if self.vx != 0.0:
                decel = FRICTION * dt * sign(self.vx)
                if abs(decel) > abs(self.vx):
                    self.vx = 0.0
                else:
                    self.vx -= decel

        # clamp to target max (but allow friction to bring it down if running released)
        if abs(self.vx) > max_speed:
            self.vx = max_speed * sign(self.vx)

        # ── Timers (coyote + jump buffer)
        if self.on_ground:
            self.coyote = COYOTE_TIME
        else:
            self.coyote = max(0.0, self.coyote - dt)
        if self.jump_buf > 0.0:
            self.jump_buf = max(0.0, self.jump_buf - dt)

        # ── Jump resolve (uses buffer/coyote)
        if self.jump_buf > 0.0 and (self.on_ground or self.coyote > 0.0):
            self.vy = -JUMP_SPEED
            self.on_ground = False
            self.coyote = 0.0
            self.jump_buf = 0.0

        # ── Gravity
        self.vy = min(self.vy + GRAVITY * dt, MAX_FALL_SPEED)

        # ── Axis-separated movement & collision
        # Horizontal
        self.rect.x += int(round(self.vx * dt))
        for tile in tiles:
            if self.rect.colliderect(tile):
                if self.vx > 0:
                    self.rect.right = tile.left
                elif self.vx < 0:
                    self.rect.left = tile.right
                self.vx = 0.0

        # Vertical
        self.rect.y += int(round(self.vy * dt))
        self.on_ground = False
        for tile in tiles:
            if self.rect.colliderect(tile):
                if self.vy > 0:
                    self.rect.bottom = tile.top
                    self.vy = 0.0
                    self.on_ground = True
                elif self.vy < 0:
                    self.rect.top = tile.bottom
                    self.vy = 0.0

# ──────────────────────────────────────────────────────────────────────────────
# Build Level
# ──────────────────────────────────────────────────────────────────────────────
def build_level(layout):
    tiles = []
    coins = []
    rows = len(layout)
    cols = len(layout[0]) if rows else 0

    for y, row in enumerate(layout):
        for x, cell in enumerate(row):
            if cell == "P":
                tiles.append(pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE))
            elif cell == "C":
                # smaller pickup rect looks nicer
                coins.append(pygame.Rect(x * TILE_SIZE + 8, y * TILE_SIZE + 8, 16, 16))

    # Estimate ground top (first 'P' from bottom)
    ground_row = rows - 1
    for r in range(rows - 1, -1, -1):
        if "P" in layout[r]:
            ground_row = r
            break
    ground_top_y = ground_row * TILE_SIZE

    world_width_px = cols * TILE_SIZE
    world_height_px = rows * TILE_SIZE

    # Flag near the far right, sitting on ground
    flag_x = world_width_px - TILE_SIZE * 5
    flag_height = TILE_SIZE * 6
    flag_rect = pygame.Rect(flag_x, ground_top_y - flag_height, 4, flag_height)  # pole
    flag_trigger = pygame.Rect(flag_x - TILE_SIZE//2, 0, TILE_SIZE, world_height_px)  # wide trigger

    # Suggested spawn: just above ground near the start
    spawn_x = TILE_SIZE * 2
    spawn_y = ground_top_y - TILE_SIZE

    return tiles, coins, flag_rect, flag_trigger, (world_width_px, world_height_px), (spawn_x, spawn_y)

# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SCALED | pygame.DOUBLEBUF)
    pygame.display.set_caption("World 1-1 — 60 FPS NES+ Feel")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 20, bold=True)

    # Player sprite (simple red square)
    frame = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    frame.fill(PLAYER_RED)
    player = Player([frame])

    tiles, coins, flag_rect, flag_trigger, (world_w, world_h), (spawn_x, spawn_y) = build_level(LEVEL_1_1)
    player.set_spawn(spawn_x, spawn_y)

    cam_x = 0
    running = True
    level_cleared = False
    clear_timer = 0.0

    while running:
        dt_ms = clock.tick(FPS)  # lock to 60 FPS
        dt = min(dt_ms / 1000.0, 1.0 / 30.0)  # guard if a frame hiccups

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            else:
                player.handle_event(event)

        if not level_cleared:
            keys = pygame.key.get_pressed()
            player.update(keys, tiles, dt)

            # Coin pickups
            i = 0
            while i < len(coins):
                if player.rect.colliderect(coins[i]):
                    del coins[i]
                    player.coins += 1
                else:
                    i += 1

            # Flag trigger -> level clear
            if player.rect.colliderect(flag_trigger):
                level_cleared = True
                clear_timer = 1.2  # short pause

            # Respawn if falling out of world
            if player.rect.top > world_h + TILE_SIZE * 4:
                player.respawn()

            # Camera: keep player ~1/3 from left
            target = player.rect.centerx - SCREEN_WIDTH // 3
            cam_x = max(0, min(int(target), world_w - SCREEN_WIDTH))

        else:
            clear_timer -= dt
            if clear_timer <= 0:
                running = False  # demo ends after clear

        # ── Draw
        screen.fill(SKY)

        # Tiles
        for tile in tiles:
            r = tile.move(-cam_x, 0)
            pygame.draw.rect(screen, GROUND, r)

        # Flag pole
        pygame.draw.rect(screen, (220, 220, 220), flag_rect.move(-cam_x, 0))  # pole
        # little flag
        flag_tip = (flag_rect.right - cam_x, flag_rect.top + TILE_SIZE)
        pygame.draw.polygon(screen, FLAG_GREEN, [
            flag_tip,
            (flag_tip[0] + TILE_SIZE, flag_tip[1] + TILE_SIZE // 2),
            (flag_tip[0], flag_tip[1] + TILE_SIZE),
        ])

        # Coins
        for c in coins:
            c2 = c.move(-cam_x, 0)
            pygame.draw.circle(screen, COIN_YELLOW, c2.center, 8)

        # Player
        screen.blit(player.image, player.rect.move(-cam_x, 0))

        # UI
        fps_txt = font.render(f"{int(clock.get_fps()):02d} FPS", True, WHITE)
        coin_txt = font.render(f"× {player.coins}", True, WHITE)
        world_txt = font.render(f"WORLD {player.world}-{player.level}", True, WHITE)

        # shadows
        screen.blit(font.render(f"{int(clock.get_fps()):02d} FPS", True, UI_SHADOW), (11, 11))
        screen.blit(font.render(f"× {player.coins}", True, UI_SHADOW), (11, 39))
        screen.blit(font.render(f"WORLD {player.world}-{player.level}", True, UI_SHADOW), (SCREEN_WIDTH - 200 + 1, 11))

        screen.blit(fps_txt, (10, 10))
        screen.blit(coin_txt, (10, 38))
        screen.blit(world_txt, (SCREEN_WIDTH - 200, 10))

        if level_cleared:
            msg = "COURSE CLEAR!"
            t = pygame.font.SysFont("Arial", 48, bold=True).render(msg, True, WHITE)
            t_shadow = pygame.font.SysFont("Arial", 48, bold=True).render(msg, True, UI_SHADOW)
            rect = t.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3))
            screen.blit(t_shadow, rect.move(2, 2))
            screen.blit(t, rect)

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
