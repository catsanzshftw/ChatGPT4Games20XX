"""Simple Mario-style auto-runner built with Pygame.
Run with: python smm_1.0vmario9.15.25build.py
"""
import math
import random
import sys

import pygame

WIDTH, HEIGHT = 960, 540
GROUND_Y = HEIGHT - 80
FPS = 60
GRAVITY = 2800
JUMP_VELOCITY = -1100
WORLD_SPEED_START = 320
WORLD_SPEED_MAX = 720
SPAWN_INTERVAL = (0.9, 1.75)
COIN_INTERVAL = (0.6, 1.2)


class Player:
    COLOR = (255, 80, 66)

    def __init__(self) -> None:
        self.rect = pygame.Rect(150, GROUND_Y - 64, 48, 64)
        self.vel_y = 0.0
        self.jump_ready = True
        self.double_jump = True
        self.invincible_timer = 0.0

    def update(self, dt: float) -> None:
        self.invincible_timer = max(0.0, self.invincible_timer - dt)
        self.vel_y += GRAVITY * dt
        self.rect.y += int(self.vel_y * dt)
        if self.rect.bottom >= GROUND_Y:
            self.rect.bottom = GROUND_Y
            self.vel_y = 0.0
            self.jump_ready = True
            self.double_jump = True

    def jump(self) -> None:
        if self.jump_ready:
            self.vel_y = JUMP_VELOCITY
            self.jump_ready = False
        elif self.double_jump:
            self.vel_y = JUMP_VELOCITY
            self.double_jump = False

    @property
    def flashing(self) -> bool:
        return self.invincible_timer > 0 and int(self.invincible_timer * 20) % 2 == 0

    def draw(self, surface: pygame.Surface) -> None:
        color = (255, 200, 200) if self.flashing else self.COLOR
        pygame.draw.rect(surface, color, self.rect)
        hat = pygame.Rect(self.rect.x + 6, self.rect.y - 10, self.rect.width - 12, 12)
        pygame.draw.rect(surface, (240, 240, 20), hat)


class Obstacle:
    COLORS = {
        "goomba": (150, 96, 48),
        "koopa": (25, 160, 60),
        "thwomp": (120, 120, 140),
    }

    def __init__(self, kind: str, x: int) -> None:
        self.kind = kind
        if kind == "goomba":
            self.rect = pygame.Rect(x, GROUND_Y - 40, 44, 40)
        elif kind == "koopa":
            self.rect = pygame.Rect(x, GROUND_Y - 60, 46, 60)
        else:
            height = random.randint(80, 120)
            self.rect = pygame.Rect(x, GROUND_Y - height, 52, height)

    def update(self, speed: float, dt: float) -> None:
        self.rect.x -= int(speed * dt)

    def draw(self, surface: pygame.Surface) -> None:
        color = self.COLORS.get(self.kind, (200, 200, 200))
        pygame.draw.rect(surface, color, self.rect)
        if self.kind == "thwomp":
            for i in range(4):
                spike = pygame.Rect(self.rect.x - 6, self.rect.y + i * (self.rect.height // 4), 6, 16)
                pygame.draw.rect(surface, (180, 180, 180), spike)


class Coin:
    COLOR = (255, 210, 60)

    def __init__(self, x: int, y: int) -> None:
        self.x = float(x)
        self.y = float(y)
        self.radius = 12

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x - self.radius), int(self.y - self.radius), self.radius * 2, self.radius * 2)

    def update(self, speed: float, dt: float) -> None:
        self.x -= speed * dt

    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.circle(surface, self.COLOR, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surface, (250, 250, 180), (int(self.x), int(self.y)), self.radius - 5, 2)


def spawn_obstacle(distance: float) -> str:
    if distance < 300:
        return "goomba"
    pool = ["goomba", "goomba", "koopa", "thwomp"]
    return random.choice(pool)


def draw_background(surface: pygame.Surface, offset: float) -> None:
    sky_top = (48, 120, 255)
    sky_bottom = (140, 200, 255)
    for y in range(HEIGHT):
        t = y / HEIGHT
        color = (
            int(sky_top[0] * (1 - t) + sky_bottom[0] * t),
            int(sky_top[1] * (1 - t) + sky_bottom[1] * t),
            int(sky_top[2] * (1 - t) + sky_bottom[2] * t),
        )
        surface.fill(color, rect=pygame.Rect(0, y, WIDTH, 1))
    hill_color = (80, 200, 120)
    for i in range(-1, 6):
        base_x = (i * 220 - offset * 0.4) % (WIDTH + 220) - 220
        pygame.draw.ellipse(surface, hill_color, (base_x, GROUND_Y - 80, 260, 140))
    surface.fill((94, 181, 72), (0, GROUND_Y, WIDTH, HEIGHT - GROUND_Y))
    tile_w = 40
    ground_offset = offset % tile_w
    for x in range(-tile_w, WIDTH + tile_w, tile_w):
        pygame.draw.rect(
            surface,
            (210, 180, 80),
            (x - ground_offset, GROUND_Y, tile_w - 6, 16),
        )
        pygame.draw.rect(
            surface,
            (180, 140, 60),
            (x - ground_offset + 6, GROUND_Y + 12, tile_w - 12, 20),
        )


def draw_ui(surface: pygame.Surface, font: pygame.font.Font, big_font: pygame.font.Font, score: int, coins: int, best: int) -> None:
    score_text = font.render(f"Distance: {score:05d}", True, (20, 20, 20))
    coin_text = font.render(f"Coins: {coins:02d}", True, (20, 20, 20))
    best_text = font.render(f"Best: {best:05d}", True, (20, 20, 20))
    surface.blit(score_text, (24, 20))
    surface.blit(coin_text, (24, 54))
    surface.blit(best_text, (24, 88))
    title = big_font.render("Super Midnight Marathon", True, (255, 255, 255))
    surface.blit(title, (WIDTH - title.get_width() - 24, 20))


def main() -> None:
    pygame.init()
    pygame.display.set_caption("Super Midnight Marathon")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 28, bold=True)
    big_font = pygame.font.SysFont("Arial", 42, bold=True)

    player = Player()
    obstacles: list[Obstacle] = []
    coins: list[Coin] = []
    world_speed = WORLD_SPEED_START
    distance = 0.0
    best_distance = 0
    coins_collected = 0
    spawn_timer = random.uniform(*SPAWN_INTERVAL)
    coin_timer = random.uniform(*COIN_INTERVAL)
    bg_offset = 0.0
    game_over = False

    while True:
        dt = clock.tick(FPS) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_SPACE, pygame.K_UP):
                    if game_over:
                        player = Player()
                        obstacles.clear()
                        coins.clear()
                        distance = 0.0
                        coins_collected = 0
                        world_speed = WORLD_SPEED_START
                        spawn_timer = random.uniform(*SPAWN_INTERVAL)
                        coin_timer = random.uniform(*COIN_INTERVAL)
                        bg_offset = 0.0
                        game_over = False
                    else:
                        player.jump()
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

        if not game_over:
            player.update(dt)
            bg_offset += world_speed * dt
            distance += world_speed * dt * 0.5
            world_speed = min(WORLD_SPEED_MAX, WORLD_SPEED_START + distance / 280)

            spawn_timer -= dt
            if spawn_timer <= 0:
                kind = spawn_obstacle(distance)
                obstacles.append(Obstacle(kind, WIDTH + 60))
                spawn_timer = random.uniform(*SPAWN_INTERVAL)

            coin_timer -= dt
            if coin_timer <= 0:
                y = random.randint(GROUND_Y - 140, GROUND_Y - 60)
                coins.append(Coin(WIDTH + 40, y))
                coin_timer = random.uniform(*COIN_INTERVAL)

            for obstacle in obstacles:
                obstacle.update(world_speed, dt)
            for coin in coins:
                coin.update(world_speed, dt)

            obstacles = [ob for ob in obstacles if ob.rect.right > -40]
            coins = [c for c in coins if c.rect.right > -40]

            player_rect = player.rect
            for obstacle in obstacles:
                if player_rect.colliderect(obstacle.rect) and player.invincible_timer <= 0:
                    game_over = True
                    best_distance = max(best_distance, int(distance))
                    break

            for coin in coins[:]:
                if player_rect.colliderect(coin.rect):
                    coins_collected += 1
                    player.invincible_timer = 0.25
                    coins.remove(coin)

        draw_background(screen, bg_offset)
        for coin in coins:
            coin.draw(screen)
        for obstacle in obstacles:
            obstacle.draw(screen)
        player.draw(screen)

        draw_ui(screen, font, big_font, int(distance), coins_collected, max(best_distance, int(distance)))

        if game_over:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 140))
            screen.blit(overlay, (0, 0))
            msg = big_font.render("Game Over!", True, (255, 255, 255))
            tip = font.render("Press SPACE to try again", True, (255, 255, 0))
            screen.blit(msg, (WIDTH // 2 - msg.get_width() // 2, HEIGHT // 2 - 60))
            screen.blit(tip, (WIDTH // 2 - tip.get_width() // 2, HEIGHT // 2))

        pygame.display.flip()


if __name__ == "__main__":
    main()
