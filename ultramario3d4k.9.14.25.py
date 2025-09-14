#!/usr/bin/env python3
"""
Super Mario Bros 3: Mario Forever - 3D Ursina Edition
With Photonic Gaussian Splatting and Mario 64 Controls
CatOS 0.4 IndyCat-Evolve Compatible
"""

from ursina import *
from ursina.shaders import lit_with_shadows_shader
import random, math, time
from enum import Enum


# ============= GAME STATE ENUMS =============
class GameState(Enum):
    WORLD_MAP = 1
    LEVEL = 2
    GAME_OVER = 3


class PowerUp(Enum):
    SMALL = 0
    SUPER = 1
    FIRE = 2
    RACCOON = 3


# ============= PHOTONIC SYSTEM =============
class PhotonicGaussian3D(Entity):
    def __init__(self):
        super().__init__()
        self.particles = []

    def emit_photon_burst_3d(self, position, count, color, spread=5):
        for _ in range(count):
            vel = Vec3(random.uniform(-1,1), random.uniform(0.2,1), random.uniform(-1,1)) * spread
            particle = Entity(model='sphere', color=color, scale=0.2, position=position)
            self.particles.append({'entity': particle, 'vel': vel, 'life': 1})

    def update(self):
        for p in self.particles[:]:
            p['entity'].position += p['vel'] * time.dt
            p['life'] -= time.dt
            if p['life'] <= 0:
                destroy(p['entity'])
                self.particles.remove(p)


# ============= MARIO 3D =============
class Mario3D(Entity):
    def __init__(self, pos=(0,2,0)):
        super().__init__(model='cube', color=color.red, position=pos, collider='box')
        self.velocity = Vec3(0,0,0)
        self.grounded = False
        self.jump_height = 8
        self.walk_speed = 5
        self.run_speed = 10
        self.power_up = PowerUp.SMALL
        self.lives = 3
        self.coins = 0

        # Camera
        self.camera_pivot = Entity(parent=self, y=2)
        camera.parent = self.camera_pivot
        camera.position = (0,5,-15)
        camera.rotation_x = 20

    def update(self):
        self.handle_movement()
        self.apply_physics()

    def handle_movement(self):
        move = Vec3(held_keys['d']-held_keys['a'], 0, held_keys['w']-held_keys['s']).normalized()
        if move.length() > 0:
            speed = self.run_speed if held_keys['shift'] else self.walk_speed
            self.velocity.x = move.x * speed
            self.velocity.z = move.z * speed
            self.rotation_y = math.degrees(math.atan2(move.x, move.z))
        else:
            self.velocity.x *= 0.8
            self.velocity.z *= 0.8

        if held_keys['space'] and self.grounded:
            self.velocity.y = self.jump_height
            self.grounded = False

    def apply_physics(self):
        self.velocity.y -= 20 * time.dt
        self.position += self.velocity * time.dt
        if self.y <= 0:
            self.y = 0
            self.velocity.y = 0
            self.grounded = True


# ============= LEVEL GENERATOR =============
class Level3D:
    def __init__(self):
        self.platforms = []
        self.generate()

    def generate(self):
        for x in range(-20, 40, 5):
            for z in range(-20, 40, 5):
                ground = Entity(model='cube', color=color.green, position=(x,-1,z), scale=(5,1,5), collider='box')
                self.platforms.append(ground)

    def clear(self):
        for e in self.platforms: destroy(e)
        self.platforms.clear()


# ============= HUD =============
class HUD3D:
    def __init__(self, mario):
        self.coins_text = Text(text=f"Coins: {mario.coins}", position=(-0.85,0.45), scale=2, color=color.gold)
        self.lives_text = Text(text=f"Lives: {mario.lives}", position=(-0.85,0.4), scale=2)

    def update(self, mario):
        self.coins_text.text = f"Coins: {mario.coins}"
        self.lives_text.text = f"Lives: {mario.lives}"


# ============= GAME CLASS =============
class SMB3Game3D:
    def __init__(self):
        global mario, photonic
        mario = Mario3D()
        self.level = Level3D()
        photonic = PhotonicGaussian3D()
        self.hud = HUD3D(mario)

    def update(self):
        photonic.update()
        self.hud.update(mario)


# ============= MAIN =============
app = Ursina()
window.title = "SMB3 3D Ursina Edition"

game = SMB3Game3D()

def update():
    game.update()

app.run()
