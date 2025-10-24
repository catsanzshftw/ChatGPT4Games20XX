import pygame
import sys
import math
import random
import requests
import json
from socketio import Client as SocketIOClient
from threading import Thread

# Constants
SCREEN_WIDTH = 1024  # Scaled DS (2x 256x192 top + bottom + borders)
SCREEN_HEIGHT = 500
DS_WIDTH = 256
DS_HEIGHT = 192
SCALE = 2  # Pixel-perfect upscale
GRAVITY = 0.5
FRICTION = 0.8
GROUND_Y = 150  # Scaled ground

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 100, 0)
SKY_BLUE = (135, 206, 235)
GRASS_GREEN = (34, 139, 34)
DESERT = (210, 180, 140)
RED = (200, 0, 0)

# Server config (update to your backend URL)
SERVER_URL = "http://localhost:3000"
SOCKET_URL = "http://localhost:3000"

# Global state
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Mario & Luigi LIVE - Pygame DS MMORPG")
clock = pygame.time.Clock()
font_small = pygame.font.Font(None, 24)
font_tiny = pygame.font.Font(None, 16)
socket = SocketIOClient()
my_player = None
players = {}  # {id: player_dict}
state = "menu"  # menu, game, battle
battle_state = {"active": False, "enemy": None, "turn": "player", "messages": []}
patches = []
currency = 1000
host_code = ""
connections = {}  # Simulated local, but uses socket

# Socket integration
def socket_thread():
    socket.connect(SOCKET_URL)
    socket.on("player-moved", on_player_moved)
    socket.on("session-code", on_session_code)
    socket.on("joined-session", on_joined_session)
    socket.on("player-joined-session", on_player_joined)
    socket.on("battle-started", on_battle_started)
    socket.on("special-synced", on_special_synced)
    socket.wait()

def on_player_moved(data):
    if data["id"] != my_player["id"]:
        players[data["id"]] = {**players.get(data["id"], {}), "x": data["pos"]["x"], "y": data["pos"]["y"]}

def on_session_code(code):
    global host_code
    host_code = code
    print(f"Hosted session: {code}")

def on_joined_session(data):
    print(f"Joined {data['code']}! Players: {data['players']}")

def on_player_joined(data):
    print(f"Player joined: {data['id']}")

def on_battle_started(data):
    # Sync battle with peers
    global battle_state
    battle_state = {"active": True, "enemy": data["enemy"], "turn": "player", "messages": []}
    state = "battle"

def on_special_synced(data):
    # Apply synced special effects
    if data["success"]:
        my_player["hp"] = min(my_player["maxHp"], my_player["hp"] + 20)
        global currency
        currency += 10
    print(f"Special synced from {data['playerId']}: Power {data['power']}")

# HTTP helpers
def create_character(name, species, gender, age, color):
    global my_player
    resp = requests.post(f"{SERVER_URL}/create-character", json={"name": name, "species": species, "gender": gender, "age": age, "color": color})
    if resp.status_code == 200:
        data = resp.json()
        my_player = {"id": data["playerId"], "name": name, "species": species, "gender": gender, "age": age,
                     "color": color, "x": 100, "y": 300, "vx": 0, "vy": 0, "level": 1, "hp": 100, "maxHp": 100,
                     "items": ["Mushroom", "Maple Syrup"], "attacks": ["Jump", "Hammer"], "brosAttacks": ["Luigi Dunk"]}
        socket.emit("auth", data["playerId"])
        return True
    return False

def buy_patch(patch, cost):
    global currency
    resp = requests.post(f"{SERVER_URL}/buy-patch/{my_player['id']}/{patch}", json={"cost": cost})
    if resp.status_code == 200:
        currency -= cost
        if patch not in patches:
            patches.append(patch)
        return True
    return False

def get_player_data():
    resp = requests.get(f"{SERVER_URL}/player/{my_player['id']}")
    if resp.status_code == 200:
        data = resp.json()
        my_player.update({k: v for k, v in data.items() if k not in ["id", "name"]})

# Draw functions (species sprites, M&L style)
def draw_human(player, surface, x, y):
    color = player["color"] if isinstance(player["color"], tuple) else eval(player["color"])  # Handle str/tuple
    pygame.draw.rect(surface, color, (x-8*SCALE, y, 16*SCALE, 25*SCALE))  # Body
    pygame.draw.circle(surface, WHITE, (x, y-8*SCALE), 8*SCALE)  # Head
    pygame.draw.polygon(surface, RED, [(x-6*SCALE, y-16*SCALE), (x+6*SCALE, y-16*SCALE), (x, y-24*SCALE)])  # Hat
    pygame.draw.rect(surface, (0, 0, 255), (x-8*SCALE, y+10*SCALE, 16*SCALE, 15*SCALE))  # Overalls
    # Arms/legs
    pygame.draw.rect(surface, color, (x-12*SCALE, y+5*SCALE, 4*SCALE, 12*SCALE))
    pygame.draw.rect(surface, color, (x+8*SCALE, y+5*SCALE, 4*SCALE, 12*SCALE))
    pygame.draw.rect(surface, color, (x-6*SCALE, y+20*SCALE, 4*SCALE, 8*SCALE))
    pygame.draw.rect(surface, color, (x+2*SCALE, y+20*SCALE, 4*SCALE, 8*SCALE))

def draw_koopa(player, surface, x, y):
    color = player["color"] if isinstance(player["color"], tuple) else eval(player["color"])
    pygame.draw.ellipse(surface, (139, 69, 19), (x-10*SCALE, y+8*SCALE, 20*SCALE, 12*SCALE))  # Shell
    pygame.draw.rect(surface, color, (x-6*SCALE, y-2*SCALE, 12*SCALE, 18*SCALE))  # Body
    pygame.draw.circle(surface, WHITE, (x, y-6*SCALE), 5*SCALE)  # Head
    pygame.draw.circle(surface, BLACK, (x-2*SCALE, y-4*SCALE), 1*SCALE)  # Eyes
    pygame.draw.circle(surface, BLACK, (x+2*SCALE, y-4*SCALE), 1*SCALE)

# Add other draw functions similarly: draw_goomba, draw_toad, draw_yoshi, draw_boo
draw_functions = {
    "human": draw_human,
    "koopa": draw_koopa,
    # "goomba": draw_goomba,
    # etc. - Implement as needed
}

def draw_player(player, surface, x, y):
    draw_fn = draw_functions.get(player["species"], draw_human)
    draw_fn(player, surface, x, y)
    # Name/Level text
    name_surf = font_tiny.render(player["name"], True, BLACK)
    level_surf = font_tiny.render(f"Lv{player['level']}", True, BLACK)
    surface.blit(name_surf, (x - 20, y - 60))
    surface.blit(level_surf, (x - 10, y - 75))

def draw_top_screen():
    top_surf = pygame.Surface((DS_WIDTH * SCALE, DS_HEIGHT * SCALE))
    top_surf.fill(GREEN)  # Overworld map
    pygame.draw.rect(top_surf, WHITE, (10, 10, DS_WIDTH*SCALE-20, DS_HEIGHT*SCALE-20), 2)  # Border
    if state == "game":
        pygame.draw.circle(top_surf, (255, 0, 0, 100), (int(my_player["x"]/3), int(my_player["y"]/3)), 5)  # Player dot
        if "mlss" in patches:
            pygame.draw.rect(top_surf, (255, 200, 100, 50), (100, 50, 50, 30))  # Desert area
        text = font_small.render("Overworld Map", True, WHITE)
        top_surf.blit(text, (DS_WIDTH*SCALE//2 - 50, 20))
        players_count = len(players) + 1
        text = font_small.render(f"Players: {players_count}", True, WHITE)
        top_surf.blit(text, (DS_WIDTH*SCALE//2 - 40, DS_HEIGHT*SCALE - 20))
    elif state == "battle":
        top_surf.fill((200, 0, 0))
        text = font_small.render("Battle Mode Active", True, WHITE)
        top_surf.blit(text, (DS_WIDTH*SCALE//2 - 70, DS_HEIGHT*SCALE//2))
    return top_surf

def draw_bottom_screen():
    bottom_surf = pygame.Surface((DS_WIDTH * SCALE, DS_HEIGHT * SCALE))
    if state == "menu":
        # Character creation menu
        text = font_small.render("Character Creation", True, BLACK)
        bottom_surf.blit(text, (50, 50))
        # Inputs simulated via console for simplicity; in full, use text input
        prompt = "Enter name, species (human/koopa/...), gender (m/f), age (baby/child/adult), color (r,g,b): "
        print(prompt)  # Console input for demo
        # Parse input here in loop
    elif state == "game":
        bottom_surf.fill(SKY_BLUE)  # Sky
        pygame.draw.rect(bottom_surf, GRASS_GREEN, (0, GROUND_Y * SCALE, DS_WIDTH * SCALE, DS_HEIGHT * SCALE - GROUND_Y * SCALE))  # Grass
        if "mlss" in patches:
            pygame.draw.rect(bottom_surf, DESERT, (DS_WIDTH * SCALE // 2, GROUND_Y * SCALE, DS_WIDTH * SCALE // 2, DS_HEIGHT * SCALE - GROUND_Y * SCALE))
            pygame.draw.circle(bottom_surf, (255, 255, 0), (int(DS_WIDTH * SCALE * 0.75), int(GROUND_Y * SCALE - 10)), 10)  # Cactus
        # Draw enemies (simple)
        enemy_x = (pygame.time.get_ticks() * 0.5 / 1000) % (DS_WIDTH * SCALE)
        pygame.draw.circle(bottom_surf, (139, 69, 19), (int(enemy_x), int(GROUND_Y * SCALE - 15)), 8)  # Goomba
        # Update & draw my_player
        update_player(my_player)
        draw_player(my_player, bottom_surf, my_player["x"] * SCALE % (DS_WIDTH * SCALE), my_player["y"] * SCALE)
        # Draw other players
        for pid, pl in players.items():
            draw_player(pl, bottom_surf, pl["x"] * SCALE % (DS_WIDTH * SCALE), pl["y"] * SCALE)
        # Random battle chance
        if random.random() < 0.01:
            start_battle({"name": "Goomba", "hp": 50, "maxHp": 50, "attacks": ["Headbonk"]})
    elif state == "battle":
        bottom_surf.fill((150, 0, 150))  # Battle bg
        text = font_small.render("BATTLE!", True, WHITE)
        bottom_surf.blit(text, (DS_WIDTH*SCALE//2 - 30, 20))
        # Player & enemy
        draw_player(my_player, bottom_surf, 50, 50)
        # Enemy placeholder
        pygame.draw.circle(bottom_surf, (139, 69, 19), (DS_WIDTH*SCALE - 50, 50), 10)
        # HP bars
        pygame.draw.rect(bottom_surf, (0, 255, 0), (10, 30, int((my_player["hp"] / my_player["maxHp"]) * 100), 10))
        pygame.draw.rect(bottom_surf, (0, 255, 0), (DS_WIDTH*SCALE - 110, 60, int((battle_state["enemy"]["hp"] / battle_state["enemy"]["maxHp"]) * 100), 10))
        if battle_state["turn"] == "player":
            text = font_tiny.render("Jump (SPACE) | Hammer (E) | Item (I)", True, (255, 255, 0))
            bottom_surf.blit(text, (DS_WIDTH*SCALE//2 - 80, DS_HEIGHT*SCALE - 20))
        # Messages
        for i, msg in enumerate(battle_state["messages"]):
            text = font_tiny.render(msg, True, WHITE)
            bottom_surf.blit(text, (DS_WIDTH*SCALE//2 - 100, 100 + i * 15))
    # HUD overlay
    hud_surf = font_tiny.render(f"HP: {my_player['hp']} | Lv: {my_player['level']} | Coins: {currency}", True, WHITE)
    bottom_surf.blit(hud_surf, (10, 10))
    items_text = font_tiny.render(f"Items: {', '.join(my_player['items'][:2])}", True, WHITE)
    bottom_surf.blit(items_text, (10, 30))
    dl_status = font_tiny.render(f"Download Play: {len(connections) + 1} players | Code: {host_code}", True, WHITE)
    bottom_surf.blit(dl_status, (10, DS_HEIGHT*SCALE - 20))
    return bottom_surf

def update_player(player):
    keys = pygame.key.get_pressed()
    if keys[pygame.K_a] or keys[pygame.K_LEFT]:
        player["vx"] -= 0.5
    if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
        player["vx"] += 0.5
    if (keys[pygame.K_w] or keys[pygame.K_UP] or keys[pygame.K_SPACE]) and player["y"] >= GROUND_Y - 20:
        player["vy"] = -12  # Jump
    if keys[pygame.K_e]:  # Special attack
        check_special_attack()
    player["vx"] *= FRICTION
    player["vy"] += GRAVITY
    player["x"] += player["vx"]
    player["y"] += player["vy"]
    # Boundaries wrap
    if player["x"] < 0: player["x"] = DS_WIDTH
    if player["x"] > DS_WIDTH: player["x"] = 0
    if player["y"] > GROUND_Y - 20:
        player["y"] = GROUND_Y - 20
        player["vy"] = 0
    # Modifiers
    if player["age"] == "baby": player["vx"] *= 0.7
    if player["species"] == "yoshi": player["vy"] -= 0.2
    # Emit position to server
    socket.emit("update-position", {"pos": {"x": player["x"], "y": player["y"]}})

def check_special_attack():
    # Simplified rhythm: random success
    success = random.random() > 0.5
    socket.emit("special-attack", {"power": 50, "success": success})
    if success:
        my_player["hp"] = min(my_player["maxHp"], my_player["hp"] + 20)
        global currency
        currency += 10

def start_battle(enemy):
    global battle_state, state
    battle_state = {"active": True, "enemy": enemy, "turn": "player", "messages": []}
    state = "battle"
    socket.emit("start-battle", enemy)

def perform_turn(action):
    global battle_state
    damage = random.randint(10, 30)
    battle_state["enemy"]["hp"] -= damage
    battle_state["messages"].append(f"{my_player['name']} used {action}! Dealt {damage} damage!")
    if battle_state["enemy"]["hp"] <= 0:
        end_battle(True)
        return
    # Enemy turn (delayed)
    pygame.time.wait(1000)
    enemy_dmg = random.randint(5, 20)
    my_player["hp"] -= enemy_dmg
    battle_state["messages"].append(f"{battle_state['enemy']['name']} attacked! Took {enemy_dmg} damage!")
    if my_player["hp"] <= 0:
        end_battle(False)
    battle_state["turn"] = "player"

def end_battle(victory):
    global state, battle_state
    battle_state["active"] = False
    state = "game"
    if victory:
        my_player["level"] += 1
        my_player["maxHp"] += 20
        my_player["hp"] = my_player["maxHp"]
        global currency
        currency += 50
        battle_state["messages"] = ["Victory! +1 Lv & 50 coins!"]

def handle_input():
    global state
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type == pygame.KEYDOWN:
            if state == "menu":
                # Simulate input: In full game, use pygame_textinput
                pass  # Create char via console
            elif state == "battle" and battle_state["turn"] == "player":
                if event.key == pygame.K_SPACE:  # Jump
                    perform_turn("Jump")
                elif event.key == pygame.K_e:  # Hammer
                    perform_turn("Hammer")
                elif event.key == pygame.K_i:  # Item
                    perform_turn("Item")
            elif event.key == pygame.K_p:  # Patches menu
                buy_patch("mlbis", 750)  # Example
            elif event.key == pygame.K_h:  # Host session
                socket.emit("host-session")
            elif event.key == pygame.K_j:  # Join (prompt code)
                code = input("Enter code: ")
                socket.emit("join-session", code)

def main():
    global state, my_player
    Thread(target=socket_thread, daemon=True).start()
    running = True
    # Initial menu: Console input for char creation
    print("Welcome! Enter character details (name species gender age color_r,g,b): ")
    inputs = input().split()
    if len(inputs) >= 5:
        name, species, gender, age = inputs[:4]
        color = tuple(map(int, inputs[4].split(',')))
        if create_character(name, species, gender, age, color):
            state = "game"
        else:
            print("Failed to create char")
            return
    else:
        print("Invalid input")
        return

    while running:
        handle_input()
        # Draw
        top = draw_top_screen()
        bottom = draw_bottom_screen()
        # DS frame
        screen.fill((51, 51, 51))  # Gray DS body
        screen.blit(top, (20, 20))  # Top screen
        screen.blit(bottom, (20, 250))  # Bottom screen
        pygame.draw.rect(screen, WHITE, (18, 18, DS_WIDTH*SCALE+4, DS_HEIGHT*SCALE+4), 2)  # Top border
        pygame.draw.rect(screen, WHITE, (18, 248, DS_WIDTH*SCALE+4, DS_HEIGHT*SCALE+4), 2)  # Bottom border
        pygame.display.flip()
        clock.tick(60)
    socket.disconnect()

if __name__ == "__main__":
    main()
