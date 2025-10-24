import pygame
import sys
import random
import time
import os  # For checking if images exist

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH = 600
SCREEN_HEIGHT = 400
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (128, 128, 128)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
DARK_GRAY = (64, 64, 64)

# Game states
OFFICE = 0
CAMERA = 1

# Night states
NIGHT_1 = 1
NIGHT_2 = 2
NIGHT_3 = 3

class Animatronic:
    def __init__(self, name, image_path, start_pos, speed):
        self.name = name
        self.image_path = image_path
        self.image = self.load_image()  # Load once
        self.position = start_pos  # Position on a simple map (0-5 stages)
        self.max_pos = 5
        self.speed = speed
        self.at_door = False

    def load_image(self):
        if os.path.exists(self.image_path):
            return pygame.image.load(self.image_path).convert_alpha()
        else:
            # Fallback to colored rect if no image (for testing)
            surf = pygame.Surface((30, 50), pygame.SRCALPHA)
            color = BLUE if "Blue" in self.name else GREEN if "Boo" in self.name else RED
            surf.fill(color)
            return surf

    def get_scaled_image(self, size=(30, 50)):
        return pygame.transform.scale(self.image, size)

    def move(self):
        if random.random() < self.speed:
            self.position += 1
            if self.position >= self.max_pos:
                self.position = self.max_pos
                self.at_door = True

    def reset(self):
        self.position = 0
        self.at_door = False

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Five Nights at James's - Luigi's Mansion Edition")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        
        # Game variables
        self.state = OFFICE
        self.night = 1
        self.power = 100
        self.power_drain = 1  # Base drain
        self.time_left = 300  # 5 minutes in seconds
        self.hour = 12
        self.game_over = False
        self.jumpscare = False
        
        # Animatronics (Luigi's Mansion inspired: Gold Bat, Boilike, Blue Twirler)
        self.animatronics = [
            Animatronic("Gold Bat", "goldbat.png", 0, 0.01),  # Slow, download: https://www.vhv.rs/dpng/d/446-4462381_ghosts-luigi-s-manison-hd-png-download.png (crop/resize as needed)
            Animatronic("Boilike", "boilike.png", 0, 0.015),  # Medium, download: https://www.vhv.rs/dpng/d/451-4510294_luigis-mansion-ghost-png-ghost-luigis-mansion-characters.png
            Animatronic("Blue Twirler", "bluetwirler.png", 0, 0.02)  # Fast, download: https://www.vhv.rs/dpng/d/451-4513866_luigis-mansion-portrait-ghosts-png-png-download-luigis.png (crop portrait)
        ]
        
        # Doors and lights
        self.left_door = False
        self.right_door = False
        self.left_light = False
        self.right_light = False
        
        # Camera positions (simple map)
        self.camera_pos = 0  # 0: Office, 1-4: Hallways, 5: Stage
        
    def draw_office(self):
        self.screen.fill(DARK_GRAY)
        # Draw office walls (mansion vibe: add some eerie green tint if you want)
        pygame.draw.rect(self.screen, GRAY, (0, 0, 200, SCREEN_HEIGHT))  # Left wall
        pygame.draw.rect(self.screen, GRAY, (400, 0, 200, SCREEN_HEIGHT))  # Right wall
        pygame.draw.rect(self.screen, BLACK, (200, 0, 200, SCREEN_HEIGHT))  # Desk area
        
        # Draw doors
        if not self.left_door:
            pygame.draw.rect(self.screen, GRAY, (0, 0, 50, SCREEN_HEIGHT))  # Open left
        else:
            pygame.draw.rect(self.screen, YELLOW, (0, 0, 50, SCREEN_HEIGHT))  # Closed left
        
        if not self.right_door:
            pygame.draw.rect(self.screen, GRAY, (550, 0, 50, SCREEN_HEIGHT))  # Open right
        else:
            pygame.draw.rect(self.screen, YELLOW, (550, 0, 50, SCREEN_HEIGHT))  # Closed right
        
        # Draw lights (simple indicators)
        if self.left_light:
            pygame.draw.circle(self.screen, WHITE, (25, SCREEN_HEIGHT // 2), 10)
        if self.right_light:
            pygame.draw.circle(self.screen, WHITE, (575, SCREEN_HEIGHT // 2), 10)
        
        # Draw animatronics at doors if present (now with images!)
        for anim in self.animatronics:
            if anim.at_door:
                side = random.choice(["left", "right"])
                if side == "left":
                    # Left door anim
                    img = anim.get_scaled_image((40, 60))
                    self.screen.blit(img, (5, 120))
                else:
                    # Right door anim
                    img = anim.get_scaled_image((40, 60))
                    self.screen.blit(img, (555, 120))
        
        # UI
        power_text = self.small_font.render(f"Power: {self.power}%", True, WHITE)
        self.screen.blit(power_text, (10, 10))
        
        time_text = self.small_font.render(f"Time: {self.hour}:00 AM", True, WHITE)
        self.screen.blit(time_text, (500, 10))
        
        night_text = self.small_font.render(f"Night {self.night}", True, WHITE)
        self.screen.blit(night_text, (250, 10))
        
        # Buttons
        left_light_btn = pygame.Rect(100, 350, 80, 30)
        pygame.draw.rect(self.screen, GREEN if not self.left_light else RED, left_light_btn)
        self.screen.blit(self.small_font.render("Left Light", True, BLACK), (102, 355))
        
        right_light_btn = pygame.Rect(200, 350, 80, 30)
        pygame.draw.rect(self.screen, GREEN if not self.right_light else RED, right_light_btn)
        self.screen.blit(self.small_font.render("Right Light", True, BLACK), (202, 355))
        
        left_door_btn = pygame.Rect(300, 350, 80, 30)
        pygame.draw.rect(self.screen, GREEN if not self.left_door else RED, left_door_btn)
        self.screen.blit(self.small_font.render("Left Door", True, BLACK), (302, 355))
        
        right_door_btn = pygame.Rect(400, 350, 80, 30)
        pygame.draw.rect(self.screen, GREEN if not self.right_door else RED, right_door_btn)
        self.screen.blit(self.small_font.render("Right Door", True, BLACK), (402, 355))
        
        camera_btn = pygame.Rect(250, 300, 100, 40)
        pygame.draw.rect(self.screen, BLUE, camera_btn)
        self.screen.blit(self.font.render("CAMERA", True, WHITE), (255, 305))
        
        return [left_light_btn, right_light_btn, left_door_btn, right_door_btn, camera_btn]
    
    def draw_camera(self):
        self.screen.fill(BLACK)
        # Simple camera feed (monochrome for FNAF vibe, but ghostly green tint?)
        for i in range(6):
            x = 50 + i * 90
            # Draw static cam view
            pygame.draw.rect(self.screen, GRAY, (x, 50, 80, 60))
            cam_text = self.small_font.render(f"Cam {i}", True, WHITE)
            self.screen.blit(cam_text, (x + 30, 115))
            
            # Show animatronics on map (blit scaled images)
            for anim in self.animatronics:
                if anim.position == i:
                    img = anim.get_scaled_image((20, 20))
                    self.screen.blit(img, (x + 35, 70))
        
        back_btn = pygame.Rect(250, 300, 100, 40)
        pygame.draw.rect(self.screen, RED, back_btn)
        self.screen.blit(self.font.render("OFFICE", True, WHITE), (260, 305))
        
        power_text = self.small_font.render(f"Power: {self.power}%", True, WHITE)
        self.screen.blit(power_text, (10, 10))
        
        return [back_btn]
    
    def handle_events(self, buttons):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                for btn in buttons:
                    if btn.collidepoint(mouse_pos):
                        idx = buttons.index(btn)
                        if self.state == OFFICE:
                            if idx == 0:  # Left light
                                self.left_light = not self.left_light
                                if self.left_light:
                                    self.power_drain += 1
                                else:
                                    self.power_drain -= 1
                            elif idx == 1:  # Right light
                                self.right_light = not self.right_light
                                if self.right_light:
                                    self.power_drain += 1
                                else:
                                    self.power_drain -= 1
                            elif idx == 2:  # Left door
                                self.left_door = not self.left_door
                                if self.left_door:
                                    self.power_drain += 2
                                else:
                                    self.power_drain -= 2
                            elif idx == 3:  # Right door
                                self.right_door = not self.right_door
                                if self.right_door:
                                    self.power_drain += 2
                                else:
                                    self.power_drain -= 2
                            elif idx == 4:  # Camera
                                self.state = CAMERA
                                self.power_drain += 1  # Camera drain
                        else:  # CAMERA
                            if idx == 0:  # Back to office
                                self.state = OFFICE
                                self.power_drain -= 1  # Stop camera drain
        return True
    
    def update(self, dt):
        if self.game_over or self.jumpscare:
            return
        
        # Drain power
        self.power -= self.power_drain * dt / 1000  # Per second
        if self.power <= 0:
            self.game_over = True
        
        # Update time
        self.time_left -= dt / 1000
        if self.time_left <= 0:
            self.night += 1
            if self.night > 3:
                self.game_over = True  # Win!
                return
            self.reset_night()
        
        # Update hour display
        self.hour = 12 + int((300 - self.time_left) / 60)
        
        # Move animatronics (speeds increase per night)
        base_speed_mult = 0.8 + (self.night * 0.1)
        for anim in self.animatronics:
            anim.speed = anim.base_speed * base_speed_mult if hasattr(anim, 'base_speed') else anim.speed
            anim.move()
        
        # Check jumpscare
        for anim in self.animatronics:
            if anim.at_door:
                door_closed = (anim.name == "Gold Bat" and self.left_door) or (anim.name != "Gold Bat" and self.right_door)
                light_on = (anim.name == "Gold Bat" and self.left_light) or (anim.name != "Gold Bat" and self.right_light)
                if not door_closed and not light_on:
                    self.jumpscare = True
    
    def reset_night(self):
        self.power = 100
        self.time_left = 300
        self.hour = 12
        self.power_drain = 1
        self.left_door = False
        self.right_door = False
        self.left_light = False
        self.right_light = False
        for anim in self.animatronics:
            anim.reset()
            if not hasattr(anim, 'base_speed'):
                anim.base_speed = anim.speed  # Store base for scaling
    
    def draw_jumpscare(self):
        self.screen.fill(RED)
        text = self.font.render("JUMPSCARE! GAME OVER", True, WHITE)
        self.screen.blit(text, (100, 180))
    
    def draw_win_lose(self):
        if self.night > 3:
            self.screen.fill(GREEN)
            text = self.font.render("YOU SURVIVED 3 NIGHTS!", True, BLACK)
            self.screen.blit(text, (50, 180))
        else:
            self.screen.fill(RED)
            text = self.font.render("POWER OUT! GAME OVER", True, WHITE)
            self.screen.blit(text, (50, 180))
    
    def run(self):
        running = True
        while running:
            dt = self.clock.tick(60)
            
            running = self.handle_events([])
            self.update(dt)
            
            if self.jumpscare:
                self.draw_jumpscare()
            elif self.game_over:
                self.draw_win_lose()
            else:
                if self.state == OFFICE:
                    buttons = self.draw_office()
                    self.handle_events(buttons)
                else:
                    buttons = self.draw_camera()
                    self.handle_events(buttons)
            
            pygame.display.flip()
            
            if self.game_over or self.jumpscare:
                time.sleep(3)
                pygame.quit()
                sys.exit()
        
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = Game()
    # Set base speeds for animatronics
    game.animatronics[0].base_speed = 0.01
    game.animatronics[1].base_speed = 0.015
    game.animatronics[2].base_speed = 0.02
    game.run()