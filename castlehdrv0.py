# ===============================
# Peach's Castle 3D (Ursina demo)
# ===============================
# Requires: pip install ursina
#
# Controls:
#   WASD  - move
#   Space - jump
#   Mouse - look around
#   Esc   - quit
# ===============================

from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController


app = Ursina()

# -------------------------------
# Environment setup
# -------------------------------
Sky()

# Ground
ground = Entity(model='plane', scale=200, texture='white_cube', texture_scale=(200,200), color=color.green, collider='box')

# Moat
moat = Entity(model='cube', scale=(80, 2, 80), color=color.azure, position=(0, -1, 0))

# Bridge
bridge = Entity(model='cube', scale=(10, 1, 20), color=color.brown, position=(0,0,40))


# -------------------------------
# Castle exterior
# -------------------------------
# Base walls
castle_base = Entity(model='cube', scale=(40, 20, 40), position=(0,10,60), color=color.light_gray, collider='box')

# Towers (4 corners)
tower_positions = [(18, 15, 42), (-18, 15, 42), (18, 15, 78), (-18, 15, 78)]
for pos in tower_positions:
    Entity(model='cylinder', scale=(10,30,10), position=pos, color=color.gray)

# Roof
roof = Entity(model='cone', scale=(45,20,45), position=(0,30,60), color=color.red)


# -------------------------------
# Player
# -------------------------------
player = FirstPersonController(y=5, z=-20)
player.speed = 6


# -------------------------------
# Lighting
# -------------------------------
DirectionalLight(y=3, z=3, shadows=True)
AmbientLight(color=color.rgba(100,100,100,0.3))


# -------------------------------
# Run
# -------------------------------
app.run()
