"""Paper Mario 64 inspired pseudo-3D scene built with Pygame.
Run with: python program_paper_m4k1.0x9.15.251.0x.py
"""
from __future__ import annotations

import math
import random
import sys
from dataclasses import dataclass

import pygame

WIDTH, HEIGHT = 1024, 576
HORIZON = int(HEIGHT * 0.42)
FOV = 900.0
CAMERA_BASE_Y = 140.0
CAMERA_BASE_Z = -260.0
NEAR_Z = 60.0
FAR_Z = 1200.0
GROUND_Y = 0.0

MARIO_SPEED_X = 260.0
MARIO_SPEED_Z = 180.0
JUMP_VELOCITY = 880.0
GRAVITY = 2200.0


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


@dataclass
class Camera:
    x: float = 0.0
    y: float = CAMERA_BASE_Y
    z: float = CAMERA_BASE_Z

    def follow(self, target_x: float, dt: float) -> None:
        blend = clamp(dt * 4.0, 0.0, 1.0)
        self.x += (target_x - self.x) * blend


def project_point(x: float, y: float, z: float, camera: Camera) -> tuple[float, float, float, float]:
    dx = x - camera.x
    dy = y - camera.y
    dz = max(10.0, z - camera.z)
    scale = FOV / dz
    sx = WIDTH * 0.5 + dx * scale
    sy = HORIZON + dy * scale
    return sx, sy, scale, dz


def make_mario_surface() -> pygame.Surface:
    surf = pygame.Surface((64, 96), pygame.SRCALPHA)
    pygame.draw.rect(surf, (215, 0, 0), pygame.Rect(6, 14, 52, 28), border_radius=6)
    pygame.draw.rect(surf, (240, 205, 170), pygame.Rect(14, 24, 36, 34), border_radius=12)
    pygame.draw.rect(surf, (210, 0, 0), pygame.Rect(8, 0, 48, 22), border_radius=8)
    pygame.draw.rect(surf, (250, 230, 20), pygame.Rect(10, 58, 20, 26), border_radius=6)
    pygame.draw.rect(surf, (80, 60, 40), pygame.Rect(12, 70, 18, 18), border_radius=6)
    pygame.draw.rect(surf, (250, 230, 20), pygame.Rect(34, 58, 20, 26), border_radius=6)
    pygame.draw.rect(surf, (80, 60, 40), pygame.Rect(36, 70, 18, 18), border_radius=6)
    pygame.draw.rect(surf, (150, 40, 30), pygame.Rect(16, 42, 32, 6), border_radius=3)
    pygame.draw.circle(surf, (255, 255, 255), (28, 30), 6)
    pygame.draw.circle(surf, (255, 255, 255), (38, 30), 6)
    pygame.draw.circle(surf, (0, 70, 170), (28, 31), 2)
    pygame.draw.circle(surf, (0, 70, 170), (38, 31), 2)
    pygame.draw.rect(surf, (180, 30, 30), pygame.Rect(18, 10, 28, 12))
    pygame.draw.rect(surf, (245, 130, 70), pygame.Rect(24, 40, 16, 10))
    return surf


def make_goomba_surface() -> pygame.Surface:
    surf = pygame.Surface((56, 56), pygame.SRCALPHA)
    pygame.draw.ellipse(surf, (170, 110, 60), pygame.Rect(4, 8, 48, 40))
    pygame.draw.rect(surf, (120, 80, 40), pygame.Rect(10, 40, 36, 10))
    pygame.draw.rect(surf, (70, 50, 25), pygame.Rect(14, 46, 12, 8), border_radius=4)
    pygame.draw.rect(surf, (70, 50, 25), pygame.Rect(30, 46, 12, 8), border_radius=4)
    pygame.draw.circle(surf, (255, 255, 255), (22, 26), 6)
    pygame.draw.circle(surf, (255, 255, 255), (34, 26), 6)
    pygame.draw.circle(surf, (40, 40, 40), (22, 28), 2)
    pygame.draw.circle(surf, (40, 40, 40), (34, 28), 2)
    pygame.draw.arc(surf, (40, 25, 15), pygame.Rect(16, 30, 22, 12), math.pi, 2.2 * math.pi, 2)
    return surf


def make_tree_surface() -> pygame.Surface:
    surf = pygame.Surface((80, 120), pygame.SRCALPHA)
    pygame.draw.rect(surf, (110, 70, 30), pygame.Rect(32, 70, 16, 36))
    pygame.draw.ellipse(surf, (40, 130, 40), pygame.Rect(10, 10, 60, 60))
    pygame.draw.ellipse(surf, (50, 160, 50), pygame.Rect(0, 36, 80, 56))
    return surf


def make_block_surface() -> pygame.Surface:
    surf = pygame.Surface((64, 64), pygame.SRCALPHA)
    base = (205, 150, 40)
    pygame.draw.rect(surf, base, pygame.Rect(0, 0, 64, 64), border_radius=10)
    pygame.draw.rect(surf, (230, 190, 90), pygame.Rect(8, 8, 48, 48), border_radius=8)
    pygame.draw.rect(surf, (120, 80, 20), pygame.Rect(22, 20, 20, 24), border_radius=6)
    pygame.draw.rect(surf, (80, 50, 10), pygame.Rect(26, 24, 12, 16), border_radius=4)
    return surf


class PaperSprite:
    def __init__(self, surface: pygame.Surface, x: float, y: float, z: float) -> None:
        self.surface = surface
        self.x = x
        self.y = y
        self.z = z
        self.bob_phase = random.uniform(0.0, math.tau)
        self.bob_height = 0.0

    def update(self, dt: float) -> None:
        self.bob_phase += dt
        self.bob_height = math.sin(self.bob_phase * 1.2) * 6.0

    def build_draw_call(self, camera: Camera) -> tuple[float, pygame.Surface, pygame.Rect, tuple[float, float] | None]:
        sx, sy, scale, depth = project_point(self.x, self.y - self.bob_height, self.z, camera)
        width = max(2, int(self.surface.get_width() * scale))
        height = max(2, int(self.surface.get_height() * scale))
        sprite = pygame.transform.smoothscale(self.surface, (width, height))
        rect = sprite.get_rect(center=(sx, sy - height * 0.2))
        shadow_pos = (sx, sy + 4)
        return depth, sprite, rect, shadow_pos


class PaperPlayer(PaperSprite):
    def __init__(self, surface: pygame.Surface, x: float, y: float, z: float) -> None:
        super().__init__(surface, x, y, z)
        self.bob_height = 0.0
        self.jump_velocity = 0.0
        self.height_offset = 0.0
        self.bob_phase = 0.0

    def update(self, dt: float, keys: pygame.key.ScancodeWrapper) -> None:
        move_x = 0.0
        move_z = 0.0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            move_x -= 1.0
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            move_x += 1.0
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            move_z -= 1.0
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            move_z += 1.0

        length = math.hypot(move_x, move_z)
        if length > 0:
            move_x /= length
            move_z /= length

        self.x += move_x * MARIO_SPEED_X * dt
        self.z += move_z * MARIO_SPEED_Z * dt
        self.x = clamp(self.x, -320.0, 320.0)
        self.z = clamp(self.z, NEAR_Z + 20.0, FAR_Z - 80.0)

        if self.jump_velocity != 0.0 or self.height_offset > 0.0:
            self.jump_velocity -= GRAVITY * dt
            self.height_offset += self.jump_velocity * dt
            if self.height_offset <= 0.0:
                self.height_offset = 0.0
                self.jump_velocity = 0.0
        self.bob_phase += dt * 2.8
        self.bob_height = math.sin(self.bob_phase) * (4.0 + self.height_offset * 0.08)

    def jump(self) -> None:
        if self.height_offset == 0.0:
            self.jump_velocity = JUMP_VELOCITY

    def build_draw_call(self, camera: Camera) -> tuple[float, pygame.Surface, pygame.Rect, tuple[float, float] | None]:
        sx, sy, scale, depth = project_point(self.x, self.y - self.height_offset - self.bob_height, self.z, camera)
        width = max(2, int(self.surface.get_width() * scale))
        height = max(2, int(self.surface.get_height() * scale))
        sprite = pygame.transform.smoothscale(self.surface, (width, height))
        rect = sprite.get_rect(center=(sx, sy - height * 0.15))
        shadow_pos = (sx, sy + 6)
        return depth, sprite, rect, shadow_pos


class Stage:
    def __init__(self) -> None:
        self.near_half = 320.0
        self.far_half = 520.0
        self.floor_color = (198, 190, 150)
        self.floor_edge = (110, 90, 70)
        self.ring_color = (230, 210, 120)

    def draw_backdrop(self, surface: pygame.Surface) -> None:
        for y in range(HORIZON):
            t = y / max(1, HORIZON - 1)
            r = int(70 + 110 * t)
            g = int(110 + 90 * t)
            b = int(200 + 40 * t)
            pygame.draw.line(surface, (r, g, b), (0, y), (WIDTH, y))

        mountain_points = [
            [(80, HORIZON + 30), (220, HORIZON - 120), (360, HORIZON + 40)],
            [(420, HORIZON + 60), (580, HORIZON - 130), (740, HORIZON + 50)],
            [(620, HORIZON + 60), (820, HORIZON - 90), (980, HORIZON + 60)],
        ]
        shades = [(100, 150, 200), (90, 130, 180), (80, 120, 170)]
        for points, color in zip(mountain_points, shades):
            pygame.draw.polygon(surface, color, points)

        band_color = (235, 200, 120)
        pygame.draw.rect(surface, band_color, pygame.Rect(0, HORIZON, WIDTH, 12))

    def draw_floor(self, surface: pygame.Surface, camera: Camera) -> None:
        corners = [
            (-self.near_half, GROUND_Y, NEAR_Z),
            (self.near_half, GROUND_Y, NEAR_Z),
            (self.far_half, GROUND_Y, FAR_Z),
            (-self.far_half, GROUND_Y, FAR_Z),
        ]
        projected = [project_point(x, y, z, camera)[:2] for x, y, z in corners]
        pygame.draw.polygon(surface, self.floor_color, projected)
        pygame.draw.lines(surface, self.floor_edge, True, projected, 3)

        line_color = (170, 150, 110)
        for i in range(1, 9):
            z = NEAR_Z + (FAR_Z - NEAR_Z) * (i / 9.0)
            half = self.near_half + (self.far_half - self.near_half) * (i / 9.0)
            left = project_point(-half, GROUND_Y, z, camera)
            right = project_point(half, GROUND_Y, z, camera)
            pygame.draw.line(surface, line_color, (left[0], left[1]), (right[0], right[1]), 2)

        for side in (-1, 1):
            near = project_point(side * self.near_half, GROUND_Y, NEAR_Z, camera)
            far = project_point(side * self.far_half, GROUND_Y, FAR_Z, camera)
            pygame.draw.line(surface, self.floor_edge, (near[0], near[1]), (far[0], far[1]), 4)

        for z in (320.0, 720.0):
            half = self.near_half + (self.far_half - self.near_half) * ((z - NEAR_Z) / (FAR_Z - NEAR_Z))
            left = project_point(-half * 0.6, GROUND_Y, z, camera)
            right = project_point(half * 0.6, GROUND_Y, z, camera)
            pygame.draw.line(surface, self.ring_color, (left[0], left[1]), (right[0], right[1]), 6)


class AmbientSparkle:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.x = random.uniform(-400.0, 400.0)
        self.z = random.uniform(NEAR_Z + 40.0, FAR_Z - 60.0)
        self.y = random.uniform(-40.0, -10.0)
        self.timer = random.uniform(0.0, math.tau)

    def update(self, dt: float) -> None:
        self.timer += dt * 3.0
        if self.timer > math.tau:
            self.timer -= math.tau
            if random.random() < 0.2:
                self.reset()

    def build_draw_call(self, camera: Camera) -> tuple[float, pygame.Surface, pygame.Rect, tuple[float, float] | None]:
        sx, sy, scale, depth = project_point(self.x, self.y, self.z, camera)
        blink = (math.sin(self.timer) + 1.0) * 0.5
        size = max(1, int(28 * scale * (0.4 + blink * 0.6)))
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.line(surf, (255, 255, 240, 200), (0, size // 2), (size, size // 2), 2)
        pygame.draw.line(surf, (255, 255, 240, 200), (size // 2, 0), (size // 2, size), 2)
        pygame.draw.circle(surf, (255, 255, 240, 180), (size // 2, size // 2), size // 3)
        rect = surf.get_rect(center=(sx, sy))
        return depth, surf, rect, None


def build_draw_calls(camera: Camera, sprites: list[PaperSprite], sparkles: list[AmbientSparkle]) -> list[tuple[float, pygame.Surface, pygame.Rect, tuple[float, float] | None]]:
    calls: list[tuple[float, pygame.Surface, pygame.Rect, tuple[float, float] | None]] = []
    for sparkle in sparkles:
        calls.append(sparkle.build_draw_call(camera))
    for sprite in sprites:
        calls.append(sprite.build_draw_call(camera))
    return calls


def draw_shadows(surface: pygame.Surface, calls: list[tuple[float, pygame.Surface, pygame.Rect, tuple[float, float] | None]]) -> None:
    for depth, _, _, shadow in sorted(calls, key=lambda item: item[0], reverse=True):
        if shadow is None:
            continue
        size = clamp(1200.0 / depth, 6.0, 60.0)
        shadow_surf = pygame.Surface((int(size * 2), int(size)), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (0, 0, 0, 110), shadow_surf.get_rect())
        rect = shadow_surf.get_rect(center=(shadow[0], shadow[1]))
        surface.blit(shadow_surf, rect)


def create_world() -> tuple[Stage, PaperPlayer, list[PaperSprite], list[AmbientSparkle]]:
    mario_surface = make_mario_surface()
    goomba_surface = make_goomba_surface()
    tree_surface = make_tree_surface()
    block_surface = make_block_surface()

    player = PaperPlayer(mario_surface, 0.0, GROUND_Y, 220.0)

    sprites: list[PaperSprite] = []
    goomba_positions = [(-160.0, GROUND_Y, 360.0), (120.0, GROUND_Y, 520.0), (60.0, GROUND_Y, 780.0)]
    for gx, gy, gz in goomba_positions:
        goomba = PaperSprite(goomba_surface, gx, gy, gz)
        goomba.bob_phase = random.uniform(0.0, math.tau)
        sprites.append(goomba)

    tree_positions = [(-320.0, -30.0, 520.0), (340.0, -26.0, 640.0), (-280.0, -28.0, 900.0), (300.0, -28.0, 1040.0)]
    for tx, ty, tz in tree_positions:
        tree = PaperSprite(tree_surface, tx, ty, tz)
        tree.bob_height = 0.0
        sprites.append(tree)

    block_positions = [(-70.0, -4.0, 430.0), (40.0, -4.0, 650.0)]
    for bx, by, bz in block_positions:
        block = PaperSprite(block_surface, bx, by, bz)
        block.bob_height = 0.0
        sprites.append(block)

    sparkles = [AmbientSparkle() for _ in range(18)]
    stage = Stage()
    return stage, player, sprites, sparkles


def draw_ui(surface: pygame.Surface, font: pygame.font.Font, distance: float) -> None:
    panel = pygame.Surface((320, 84), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 90))
    surface.blit(panel, (20, 20))
    label = font.render("Shiver Patrol", True, (255, 255, 255))
    surface.blit(label, (36, 30))
    dist_text = font.render(f"Stage Depth: {int(distance):04d}m", True, (240, 220, 200))
    surface.blit(dist_text, (36, 60))

    help_panel = pygame.Surface((360, 80), pygame.SRCALPHA)
    help_panel.fill((0, 0, 0, 70))
    surface.blit(help_panel, (WIDTH - 380, 24))
    controls = [
        "Arrows / WASD: Move",
        "Space: Jump",
        "Esc: Quit",
    ]
    for i, text in enumerate(controls):
        hint = font.render(text, True, (245, 240, 235))
        surface.blit(hint, (WIDTH - 360, 34 + i * 24))


def main() -> None:
    pygame.init()
    pygame.display.set_caption("Paper Mario 64 - Pygame Diorama")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 24, bold=True)

    stage, player, world_sprites, sparkles = create_world()
    camera = Camera()

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_SPACE:
                    player.jump()

        keys = pygame.key.get_pressed()
        player.update(dt, keys)
        for sprite in world_sprites:
            sprite.update(dt)
        for sparkle in sparkles:
            sparkle.update(dt)

        camera.follow(player.x, dt)

        stage.draw_backdrop(screen)
        stage.draw_floor(screen, camera)

        draw_calls = build_draw_calls(camera, [player] + world_sprites, sparkles)
        draw_calls.sort(key=lambda item: item[0], reverse=True)
        draw_shadows(screen, draw_calls)
        for _, sprite, rect, _ in draw_calls:
            screen.blit(sprite, rect)

        draw_ui(screen, font, player.z)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
