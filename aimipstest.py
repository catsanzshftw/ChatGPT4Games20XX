#!/usr/bin/env python3
# SPACEWORLD 95 BETA ROOM - Mario 64 Physics Test (Ursina PC Prototype)
from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController

app = Ursina()
window.title = "SpaceWorld 95 Beta Room - Mario 64 Physics Test"
window.size = (1280, 720)
window.borderless = False
window.fullscreen = False

# ------------------------
# Player (Mario test proxy)
# ------------------------
class MarioController(Entity):
    def __init__(self, **kwargs):
        super().__init__()
        self.model = "cube"
        self.color = color.azure
        self.scale = (1, 2, 1)
        self.collider = "box"
        self.y = 1
        self.speed = 5
        self.jump_height = 6
        self.gravity = 9.8
        self.velocity_y = 0
        self.grounded = False
        self.camera_pivot = Entity(parent=self, y=1.5)
        camera.parent = self.camera_pivot
        camera.position = (0, 2, -10)
        camera.rotation = (10, 0, 0)

    def update(self):
        # Horizontal movement
        move = Vec3(
            held_keys["d"] - held_keys["a"],
            0,
            held_keys["w"] - held_keys["s"]
        ).normalized() * time.dt * self.speed
        self.position += self.forward * move.z + self.right * move.x

        # Gravity
        ray = raycast(self.world_position, Vec3(0, -1, 0), distance=1.1, ignore=[self, ])
        self.grounded = ray.hit

        if self.grounded:
            self.velocity_y = 0
            if held_keys["space"]:
                self.velocity_y = self.jump_height
        else:
            self.velocity_y -= self.gravity * time.dt

        self.y += self.velocity_y * time.dt

        # Rotate camera with mouse
        self.rotation_y += held_keys["right arrow"] * 100 * time.dt
        self.rotation_y -= held_keys["left arrow"] * 100 * time.dt

# ------------------------
# Beta Test Room
# ------------------------
Entity(model="plane", collider="box", scale=(40,1,40), color=color.gray)
walls = [
    Entity(model="cube", collider="box", scale=(40,10,1), position=(0,5,20), color=color.light_gray),
    Entity(model="cube", collider="box", scale=(40,10,1), position=(0,5,-20), color=color.light_gray),
    Entity(model="cube", collider="box", scale=(1,10,40), position=(20,5,0), color=color.light_gray),
    Entity(model="cube", collider="box", scale=(1,10,40), position=(-20,5,0), color=color.light_gray),
]

# Add beta-style blocks to test collisions
for x in range(-8, 9, 4):
    for z in range(-8, 9, 4):
        Entity(model="cube", collider="box", scale=2, position=(x,1,z), color=color.yellow)

# Sloped ramp for testing SM64 jumps
Entity(model="cube", collider="box", scale=(6,2,6), position=(0,1,-10), rotation=(20,0,0), color=color.orange)

# Spawn player
mario = MarioController()

# Light
DirectionalLight().look_at(Vec3(1,-1,-1))

app.run()
