import pygame
import sys
import random

# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
GRAVITY = 0.8
JUMP_STRENGTH = -15
PLAYER_SPEED = 5
FIREBALL_SPEED = 8

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BROWN = (139, 69, 19)
BLUE = (0, 100, 255)
PURPLE = (128, 0, 128)
ORANGE = (255, 165, 0)

THEME_COLORS = {
    'plains': GREEN,
    'dunes': BROWN,
    'peaks': BLUE,
    'grove': PURPLE,
    'inferno': ORANGE
}

class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface((32, 32))
        self.image.fill(RED)
        self.rect = self.image.get_rect()
        self.rect.x = 50
        self.rect.y = 400
        self.vel_x = 0
        self.vel_y = 0
        self.on_ground = False
        self.power_up = 'small'  # small, big, fire
        self.size = 32
        self.hurt_timer = 0

    def update(self, platforms):
        if self.hurt_timer > 0:
            self.hurt_timer -= 1
            return

        self.vel_y += GRAVITY
        self.rect.y += self.vel_y
        self.on_ground = False

        # Vertical collisions
        for plat in platforms:
            if self.rect.colliderect(plat.rect):
                if self.vel_y > 0:
                    self.rect.bottom = plat.rect.top
                    self.vel_y = 0
                    self.on_ground = True
                elif self.vel_y < 0:
                    self.rect.top = plat.rect.bottom
                    self.vel_y = 0

        self.rect.x += self.vel_x
        # Horizontal collisions
        for plat in platforms:
            if self.rect.colliderect(plat.rect):
                if self.vel_x > 0:
                    self.rect.right = plat.rect.left
                elif self.vel_x < 0:
                    self.rect.left = plat.rect.right
                self.vel_x = 0

    def jump(self):
        if self.on_ground:
            self.vel_y = JUMP_STRENGTH

    def shoot(self):
        if self.power_up == 'fire':
            return Fireball(self.rect.right, self.rect.centery, 1)
        return None

    def power_up_collect(self, type):
        if type == 'mushroom' and self.power_up == 'small':
            self.power_up = 'big'
            self.size = 48
            self.image = pygame.Surface((32, 48))
            self.image.fill(RED)
        elif type == 'fireflower' and self.power_up == 'big':
            self.power_up = 'fire'

    def hurt(self):
        if self.power_up != 'small':
            self.power_up = 'small' if self.power_up == 'big' else 'big'
            self.size = 32
            self.image = pygame.Surface((32, 32))
            self.image.fill(RED)
        else:
            # Die: reset position
            self.rect.x = 50
            self.rect.y = 400
            self.vel_y = 0
        self.hurt_timer = 60

class Platform(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, color=GREEN):
        super().__init__()
        self.image = pygame.Surface((width, height))
        self.image.fill(color)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, type='goomba', color=BLACK):
        super().__init__()
        self.image = pygame.Surface((32, 32))
        self.image.fill(color)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.type = type
        self.vel_x = -2 if type == 'goomba' else random.choice([-2, 2])
        self.on_ground = False

    def update(self, platforms):
        self.vel_x += random.uniform(-0.1, 0.1)
        self.rect.x += self.vel_x
        # Simple ground check/wall bounce
        for plat in platforms:
            if self.rect.colliderect(plat.rect):
                if self.vel_x > 0:
                    self.rect.right = plat.rect.left
                else:
                    self.rect.left = plat.rect.right
                self.vel_x *= -1

class Boss(pygame.sprite.Sprite):
    def __init__(self, x, y, color=RED):
        super().__init__()
        self.image = pygame.Surface((64, 64))
        self.image.fill(color)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.health = 5
        self.phase = 0
        self.vel_x = 0
        self.vel_y = 0
        self.spin_timer = 0

    def update(self, player, platforms):
        self.phase = max(0, 2 - (self.health // 2))
        if self.phase == 0:  # Chase
            self.vel_x = (player.rect.centerx - self.rect.centerx) / 100
            self.rect.x += self.vel_x
        elif self.phase == 1:  # Dive
            if random.random() < 0.02:
                self.vel_y = -10
            self.vel_y += GRAVITY
            self.rect.y += self.vel_y
            self.rect.x += self.vel_x
        elif self.phase == 2:  # Spin
            self.spin_timer += 1
            self.vel_x = 3 * random.choice([-1, 1])
            self.rect.x += self.vel_x
            if self.spin_timer > 120:
                self.spin_timer = 0
        # Ground collision
        for plat in platforms:
            if self.rect.colliderect(plat.rect) and self.vel_y > 0:
                self.rect.bottom = plat.rect.top
                self.vel_y = 0

    def hit(self):
        self.health -= 1
        if self.health <= 0:
            self.kill()

class PowerUp(pygame.sprite.Sprite):
    def __init__(self, x, y, type):
        super().__init__()
        self.type = type
        self.image = pygame.Surface((24, 24))
        color = (255, 215, 0) if type == 'mushroom' else (255, 0, 255)
        self.image.fill(color)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.vel_y = -2

    def update(self):
        self.rect.y += self.vel_y
        self.vel_y += 0.2
        if self.rect.y > 500:
            self.kill()

class Fireball(pygame.sprite.Sprite):
    def __init__(self, x, y, direction):
        super().__init__()
        self.image = pygame.Surface((16, 16))
        self.image.fill(ORANGE)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.vel_x = FIREBALL_SPEED * direction
        self.vel_y = 0

    def update(self, platforms, enemies, boss):
        self.rect.x += self.vel_x
        self.rect.y += self.vel_y
        self.vel_y += GRAVITY / 2

        # Wall collision
        for plat in platforms:
            if self.rect.colliderect(plat.rect):
                self.kill()
                return

        # Hit enemies
        hits = pygame.sprite.spritecollide(self, enemies, True)
        for hit in hits:
            hit.kill()

        # Hit boss
        if boss and self.rect.colliderect(boss.rect):
            boss.hit()
            self.kill()

        if self.rect.x < 0 or self.rect.x > SCREEN_WIDTH or self.rect.y > SCREEN_HEIGHT:
            self.kill()

class Level:
    def __init__(self, world_num, level_num):
        self.platforms = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.powerups = pygame.sprite.Group()
        self.boss = None
        self.theme = self.get_theme(world_num)
        self.color = THEME_COLORS[self.theme]
        self.enemy_color = self.color if self.theme != 'inferno' else BLACK
        self.setup_level(world_num, level_num)

    def get_theme(self, world_num):
        themes = ['plains', 'dunes', 'peaks', 'grove', 'inferno']
        return themes[world_num - 1]

    def setup_level(self, world_num, level_num):
        # Ground
        self.platforms.add(Platform(0, 550, SCREEN_WIDTH, 50, self.color))
        
        # Varied platforms based on level
        plat_positions = [
            (150, 450, 100, 20), (300, 350, 80, 20), (500, 250, 120, 20),
            (600, 400, 60, 20), (200, 200, 100, 20), (400, 150, 80, 20)
        ]
        for i in range(min(3 + level_num, len(plat_positions))):
            x, y, w, h = plat_positions[i]
            self.platforms.add(Platform(x + random.randint(-50, 50), y, w, h, self.color))

        # Enemies: more per level/world
        enemy_types = ['goomba', 'koopa', 'pokey']
        for i in range(2 + level_num + (world_num - 1)):
            x = random.randint(100, 700)
            y = 500
            etype = random.choice(enemy_types)
            self.enemies.add(Enemy(x, y, etype, self.enemy_color))

        # Power-ups
        if level_num % 2 == 0:
            self.powerups.add(PowerUp(250, 300, 'mushroom'))
            if level_num > 1:
                self.powerups.add(PowerUp(450, 200, 'fireflower'))

        # Add boss on level 3 of each world
        if level_num == 3:
            self.platforms.add(Platform(700, 500, 100, 20, RED))
            self.boss = Boss(650, 400, RED)

class World:
    def __init__(self, num):
        self.num = num
        self.levels = [Level(num, i+1) for i in range(3)]  # Exactly 3 levels per world

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption('Ultra Mario 2D Bros - 5 Worlds x 3 Levels')
        self.clock = pygame.time.Clock()
        self.player = Player()
        self.all_sprites = pygame.sprite.Group(self.player)
        self.fireballs = pygame.sprite.Group()
        self.current_world = 1
        self.current_level = 1
        self.worlds = {i: World(i) for i in range(1, 6)}  # 5 worlds
        self.load_level()
        self.font = pygame.font.Font(None, 36)

    def load_level(self):
        # Clear old level sprites
        for sprite in self.all_sprites:
            if not isinstance(sprite, Player):
                sprite.kill()
        self.fireballs.empty()

        world = self.worlds[self.current_world]
        self.level = world.levels[self.current_level - 1]

        self.all_sprites.add(self.level.platforms, self.level.enemies, self.level.powerups)
        if self.level.boss:
            self.all_sprites.add(self.level.boss)

    def run(self):
        running = True
        while running:
            self.clock.tick(60)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        self.player.jump()
                    if event.key == pygame.K_f:
                        fireball = self.player.shoot()
                        if fireball:
                            self.all_sprites.add(fireball)
                            self.fireballs.add(fireball)

            keys = pygame.key.get_pressed()
            self.player.vel_x = (keys[pygame.K_d] - keys[pygame.K_a]) * PLAYER_SPEED

            # Updates
            self.player.update(self.level.platforms)
            self.level.enemies.update(self.level.platforms)
            if self.level.powerups:
                self.level.powerups.update()
            if self.level.boss:
                self.level.boss.update(self.player, self.level.platforms)
            self.fireballs.update(self.level.platforms, self.level.enemies, self.level.boss)

            # Player - Enemy collisions
            if self.player.hurt_timer == 0:
                hits = pygame.sprite.spritecollide(self.player, self.level.enemies, False)
                for hit in hits:
                    if self.player.vel_y > 3 and self.player.rect.bottom < hit.rect.centery + 10:
                        hit.kill()
                        self.player.vel_y = -8
                    else:
                        self.player.hurt()

            # Player - Boss collisions
            if self.level.boss and self.player.hurt_timer == 0:
                if self.player.rect.colliderect(self.level.boss.rect):
                    if self.player.vel_y > 3 and self.player.rect.bottom < self.level.boss.rect.centery + 20:
                        self.level.boss.hit()
                        self.player.vel_y = -10
                    else:
                        self.player.hurt()

            # Power-up collection
            pu_hits = pygame.sprite.spritecollide(self.player, self.level.powerups, True)
            for pu in pu_hits:
                self.player.power_up_collect(pu.type)

            # Boss defeated or level complete
            if (self.level.boss and not self.level.boss.alive()) or (self.current_level == 3 and not self.level.enemies):
                pygame.time.wait(1000)
                self.progress()

            # Fall death
            if self.player.rect.y > SCREEN_HEIGHT + 100:
                self.player.hurt()

            # Draw
            self.screen.fill(WHITE)
            self.all_sprites.draw(self.screen)
            self.fireballs.draw(self.screen)

            # UI
            world_name = self.level.theme.capitalize()
            boss_hp = self.level.boss.health if self.level.boss else 'N/A'
            text = self.font.render(f"{world_name} {self.current_world}-{self.current_level} | Power: {self.player.power_up} | Boss HP: {boss_hp}", True, BLACK)
            self.screen.blit(text, (10, 10))

            pygame.display.flip()

        pygame.quit()
        sys.exit()

    def progress(self):
        self.current_level += 1
        if self.current_level > 3:  # Only 3 levels per world
            self.current_world += 1
            self.current_level = 1
            if self.current_world > 5:  # 5 worlds total
                print("🎮 GAME COMPLETE! You saved the Mushroom Kingdom!")
                print("Total: 5 Worlds x 3 Levels = 15 Levels Completed!")
                pygame.time.wait(3000)
                pygame.quit()
                sys.exit()
        self.load_level()
        print(f"➡️ Progressed to {self.worlds[self.current_world].levels[self.current_level-1].theme.capitalize()} World {self.current_world}-{self.current_level}")

if __name__ == "__main__":
    game = Game()
    game.run()
