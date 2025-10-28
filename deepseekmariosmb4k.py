import pygame  # pyright: ignore[reportMissingImports]
import sys
import random

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (80, 80, 255)
BROWN = (139, 69, 19)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)

class Player:
    def __init__(self):
        self.width = 30
        self.height = 50
        self.x = 100
        self.y = SCREEN_HEIGHT - 150
        self.vel_y = 0
        self.jump_power = -15
        self.gravity = 0.8
        self.is_jumping = False
        self.speed = 5
        self.color = RED
        self.lives = 3
        self.score = 0
        self.direction = 1  # 1 for right, -1 for left

    def jump(self):
        if not self.is_jumping:
            self.vel_y = self.jump_power
            self.is_jumping = True

    def update(self, platforms):
        # Apply gravity
        self.vel_y += self.gravity
        self.y += self.vel_y

        # Check platform collisions
        on_ground = False
        for platform in platforms:
            if (self.y + self.height >= platform.y and 
                self.y + self.height <= platform.y + 20 and
                self.x + self.width > platform.x and 
                self.x < platform.x + platform.width and
                self.vel_y > 0):
                self.y = platform.y - self.height
                self.vel_y = 0
                self.is_jumping = False
                on_ground = True

        # Floor collision
        if self.y >= SCREEN_HEIGHT - 50:
            self.y = SCREEN_HEIGHT - 50
            self.vel_y = 0
            self.is_jumping = False

    def draw(self, screen):
        # Draw Mario-like character
        pygame.draw.rect(screen, self.color, (self.x, self.y, self.width, self.height))
        # Face
        pygame.draw.rect(screen, WHITE, (self.x + 20 if self.direction == 1 else self.x + 5, 
                                        self.y + 10, 8, 8))
        # Hat
        pygame.draw.rect(screen, RED, (self.x - 5, self.y, self.width + 10, 10))

class Platform:
    def __init__(self, x, y, width, color=BROWN):
        self.x = x
        self.y = y
        self.width = width
        self.height = 20
        self.color = color

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, (self.x, self.y, self.width, self.height))

class Enemy:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 30
        self.height = 30
        self.speed = 2
        self.direction = 1
        self.color = GREEN

    def update(self, platforms):
        self.x += self.speed * self.direction
        
        # Change direction at platform edges
        on_platform = False
        for platform in platforms:
            if (self.y + self.height >= platform.y and 
                self.y + self.height <= platform.y + 5 and
                self.x + self.width > platform.x and 
                self.x < platform.x + platform.width):
                on_platform = True
                if (self.x <= platform.x and self.direction == -1) or \
                   (self.x + self.width >= platform.x + platform.width and self.direction == 1):
                    self.direction *= -1
                    break
        
        if not on_platform:
            self.direction *= -1

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, (self.x, self.y, self.width, self.height))
        # Eyes
        pygame.draw.rect(screen, WHITE, (self.x + 5, self.y + 5, 8, 8))
        pygame.draw.rect(screen, WHITE, (self.x + 17, self.y + 5, 8, 8))

class Coin:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 15
        self.height = 15
        self.collected = False

    def draw(self, screen):
        if not self.collected:
            pygame.draw.circle(screen, YELLOW, (self.x + self.width//2, self.y + self.height//2), self.width//2)

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Super Maro Bros - Famicom Style")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        
        self.state = "main_menu"  # "main_menu", "playing", "game_over"
        self.level = 1
        self.reset_game()

    def reset_game(self):
        self.player = Player()
        self.platforms = []
        self.enemies = []
        self.coins = []
        self.setup_level()

    def setup_level(self):
        # Clear existing objects
        self.platforms.clear()
        self.enemies.clear()
        self.coins.clear()

        # Ground platform
        self.platforms.append(Platform(0, SCREEN_HEIGHT - 50, SCREEN_WIDTH))

        # Level-specific platforms
        if self.level == 1:
            # Level 1 platforms
            self.platforms.append(Platform(200, 400, 200))
            self.platforms.append(Platform(500, 350, 150))
            self.platforms.append(Platform(300, 250, 100))
            self.platforms.append(Platform(600, 200, 200))
            
            # Enemies
            self.enemies.append(Enemy(250, 370))
            self.enemies.append(Enemy(550, 320))
            
            # Coins
            for i in range(5):
                self.coins.append(Coin(220 + i * 30, 370))
            self.coins.append(Coin(320, 220))
            self.coins.append(Coin(650, 170))

        elif self.level == 2:
            # Level 2 platforms
            self.platforms.append(Platform(150, 450, 100))
            self.platforms.append(Platform(350, 400, 150))
            self.platforms.append(Platform(200, 300, 200))
            self.platforms.append(Platform(500, 250, 100))
            self.platforms.append(Platform(350, 150, 150))
            
            # More enemies
            self.enemies.append(Enemy(180, 430))
            self.enemies.append(Enemy(380, 380))
            self.enemies.append(Enemy(230, 280))
            
            # More coins
            for i in range(3):
                self.coins.append(Coin(170 + i * 25, 430))
            for i in range(4):
                self.coins.append(Coin(220 + i * 25, 270))
            self.coins.append(Coin(530, 220))
            self.coins.append(Coin(380, 120))

    def check_collisions(self):
        # Enemy collisions
        for enemy in self.enemies[:]:
            if (self.player.x < enemy.x + enemy.width and
                self.player.x + self.player.width > enemy.x and
                self.player.y < enemy.y + enemy.height and
                self.player.y + self.player.height > enemy.y):
                
                # If player is falling and hits enemy from above
                if self.player.vel_y > 0 and self.player.y + self.player.height < enemy.y + enemy.height / 2:
                    self.enemies.remove(enemy)
                    self.player.score += 100
                    self.player.vel_y = self.player.jump_power / 1.5
                else:
                    self.player.lives -= 1
                    if self.player.lives <= 0:
                        self.state = "game_over"
                    else:
                        # Reset player position
                        self.player.x = 100
                        self.player.y = SCREEN_HEIGHT - 150
                        self.player.vel_y = 0

        # Coin collisions
        for coin in self.coins[:]:
            if not coin.collected and (self.player.x < coin.x + coin.width and
                self.player.x + self.player.width > coin.x and
                self.player.y < coin.y + coin.height and
                self.player.y + self.player.height > coin.y):
                coin.collected = True
                self.player.score += 50
                self.coins.remove(coin)

        # Check if all coins collected (level complete)
        if len(self.coins) == 0:
            self.level += 1
            if self.level > 2:  # Only 2 levels for this demo
                self.state = "game_over"
            else:
                self.setup_level()
                self.player.x = 100
                self.player.y = SCREEN_HEIGHT - 150

    def draw_main_menu(self):
        self.screen.fill(BLUE)
        
        # Title
        title_font = pygame.font.Font(None, 72)
        title_text = title_font.render("SUPER MARO BROS", True, RED)
        self.screen.blit(title_text, (SCREEN_WIDTH//2 - title_text.get_width()//2, 100))
        
        # Subtitle
        sub_text = self.font.render("FAMICOM STYLE", True, WHITE)
        self.screen.blit(sub_text, (SCREEN_WIDTH//2 - sub_text.get_width()//2, 180))
        
        # Menu options
        start_text = self.font.render("PRESS SPACE TO START", True, YELLOW)
        self.screen.blit(start_text, (SCREEN_WIDTH//2 - start_text.get_width()//2, 300))
        
        controls_text = self.small_font.render("CONTROLS: ARROWS TO MOVE, SPACE TO JUMP", True, WHITE)
        self.screen.blit(controls_text, (SCREEN_WIDTH//2 - controls_text.get_width()//2, 400))
        
        # FPS display
        fps_text = self.small_font.render(f"FPS: {FPS}", True, WHITE)
        self.screen.blit(fps_text, (10, 10))

    def draw_game_over(self):
        self.screen.fill(BLACK)
        
        game_over_text = self.font.render("GAME OVER", True, RED)
        self.screen.blit(game_over_text, (SCREEN_WIDTH//2 - game_over_text.get_width()//2, 200))
        
        score_text = self.font.render(f"FINAL SCORE: {self.player.score}", True, WHITE)
        self.screen.blit(score_text, (SCREEN_WIDTH//2 - score_text.get_width()//2, 280))
        
        restart_text = self.font.render("PRESS R TO RESTART", True, YELLOW)
        self.screen.blit(restart_text, (SCREEN_WIDTH//2 - restart_text.get_width()//2, 360))

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                if event.type == pygame.KEYDOWN:
                    if self.state == "main_menu" and event.key == pygame.K_SPACE:
                        self.state = "playing"
                        self.reset_game()
                    elif self.state == "game_over" and event.key == pygame.K_r:
                        self.state = "main_menu"
                        self.level = 1
                    elif self.state == "playing" and event.key == pygame.K_SPACE:
                        self.player.jump()

            if self.state == "main_menu":
                self.draw_main_menu()
                
            elif self.state == "playing":
                # Handle input
                keys = pygame.key.get_pressed()
                if keys[pygame.K_LEFT]:
                    self.player.x -= self.player.speed
                    self.player.direction = -1
                if keys[pygame.K_RIGHT]:
                    self.player.x += self.player.speed
                    self.player.direction = 1

                # Update game objects
                self.player.update(self.platforms)
                for enemy in self.enemies:
                    enemy.update(self.platforms)
                
                self.check_collisions()

                # Draw everything
                self.screen.fill(BLUE)  # Sky background
                
                # Draw platforms
                for platform in self.platforms:
                    platform.draw(self.screen)
                
                # Draw coins
                for coin in self.coins:
                    coin.draw(self.screen)
                
                # Draw enemies
                for enemy in self.enemies:
                    enemy.draw(self.screen)
                
                # Draw player
                self.player.draw(self.screen)
                
                # Draw HUD
                score_text = self.font.render(f"SCORE: {self.player.score}", True, WHITE)
                self.screen.blit(score_text, (10, 10))
                
                lives_text = self.font.render(f"LIVES: {self.player.lives}", True, WHITE)
                self.screen.blit(lives_text, (SCREEN_WIDTH - 120, 10))
                
                level_text = self.font.render(f"LEVEL: {self.level}", True, WHITE)
                self.screen.blit(level_text, (SCREEN_WIDTH//2 - 50, 10))
                
            elif self.state == "game_over":
                self.draw_game_over()

            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = Game()
    game.run()
