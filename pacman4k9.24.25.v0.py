import pygame
import random
import sys

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH = 560
SCREEN_HEIGHT = 620
CELL_SIZE = 20
FPS = 10

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
RED = (255, 0, 0)
PINK = (255, 192, 203)
CYAN = (0, 255, 255)
ORANGE = (255, 165, 0)
DARK_BLUE = (0, 0, 139)  # For kill screen ghosts

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Pac-Man - Full 256 Levels + Kill Screen")
clock = pygame.time.Clock()
font = pygame.font.SysFont('Arial', 18)

# Maze (only 1 defined here for demo)
maze1 = [
    list("############################"),
    list("#............##............#"),
    list("#.####.#####.##.#####.####.#"),
    list("#o####.#####.##.#####.####o#"),
    list("#.####.#####.##.#####.####.#"),
    list("#..........................#"),
    list("#.####.##.########.##.####.#"),
    list("#.####.##.########.##.####.#"),
    list("#......##....##....##......#"),
    list("######.##### ## #####.######"),
    list("######.##### ## #####.######"),
    list("######.##          ##.######"),
    list("######.## ###--### ##.######"),
    list("######.## #      # ##.######"),
    list("       ## #      # ##       "),
    list("######.## #      # ##.######"),
    list("######.## ######## ##.######"),
    list("######.##          ##.######"),
    list("######.## ######## ##.######"),
    list("######.## ######## ##.######"),
    list("#............##............#"),
    list("#.####.#####.##.#####.####.#"),
    list("#.####.#####.##.#####.####.#"),
    list("#o..##................##..o#"),
    list("###.##.##.########.##.##.###"),
    list("###.##.##.########.##.##.###"),
    list("#......##....##....##......#"),
    list("#.##########.##.##########.#"),
    list("#.##########.##.##########.#"),
    list("#..........................#"),
    list("############################")
]

mazes = [maze1, [row[:] for row in maze1], [row[:] for row in maze1], [row[:] for row in maze1]]

def get_maze(level):
    if level >= 21:
        return maze1
    maze_index = (level - 1) // 2 % 4
    return mazes[maze_index]

def count_dots(maze):
    return sum(row.count('.') + row.count('o') for row in maze)

class Pacman:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.direction = 'RIGHT'
        self.next_direction = 'RIGHT'
        self.speed = 1.0

    def move(self, board):
        dx, dy = {'LEFT': (-1, 0), 'RIGHT': (1, 0), 'UP': (0, -1), 'DOWN': (0, 1)}[self.next_direction]
        nx, ny = self.x + dx, self.y + dy
        if 0 <= ny < len(board) and 0 <= nx < len(board[0]) and board[ny][nx] != '#':
            self.direction = self.next_direction

        dx, dy = {'LEFT': (-1, 0), 'RIGHT': (1, 0), 'UP': (0, -1), 'DOWN': (0, 1)}[self.direction]
        nx, ny = self.x + dx, self.y + dy
        if 0 <= ny < len(board) and 0 <= nx < len(board[0]) and board[ny][nx] != '#':
            self.x = nx
            self.y = ny
            if board[ny][nx] == '.':
                board[ny][nx] = ' '
                return 10
            elif board[ny][nx] == 'o':
                board[ny][nx] = ' '
                return 50
        return 0

    def draw(self):
        pygame.draw.circle(screen, YELLOW,
                           (self.x * CELL_SIZE + CELL_SIZE // 2,
                            self.y * CELL_SIZE + CELL_SIZE // 2 + 40),
                           CELL_SIZE // 2)

class Ghost:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = color
        self.direction = 'UP'
        self.speed = 0.8
        self.frightened = False
        self.dead = False

    def move(self, board, pacman_x, pacman_y, frightened=False):
        if self.dead:
            return
        directions = ['LEFT', 'RIGHT', 'UP', 'DOWN']
        random.shuffle(directions)
        for dir in directions:
            dx, dy = {'LEFT': (-1, 0), 'RIGHT': (1, 0), 'UP': (0, -1), 'DOWN': (0, 1)}[dir]
            nx, ny = self.x + dx, self.y + dy
            if 0 <= ny < len(board) and 0 <= nx < len(board[0]) and board[ny][nx] != '#':
                self.direction = dir
                self.x = nx
                self.y = ny
                break

    def draw(self):
        color = DARK_BLUE if self.frightened else self.color
        pygame.draw.circle(screen, color,
                           (self.x * CELL_SIZE + CELL_SIZE // 2,
                            self.y * CELL_SIZE + CELL_SIZE // 2 + 40),
                           CELL_SIZE // 2)
        pygame.draw.circle(screen, BLACK,
                           (self.x * CELL_SIZE + CELL_SIZE // 2,
                            self.y * CELL_SIZE + CELL_SIZE // 2 + 40),
                           CELL_SIZE // 2, 2)

def draw_board(board):
    for y, row in enumerate(board):
        for x, cell in enumerate(row):
            draw_x = x * CELL_SIZE
            draw_y = y * CELL_SIZE + 40
            if cell == '#':
                pygame.draw.rect(screen, BLUE, (draw_x, draw_y, CELL_SIZE, CELL_SIZE))
            elif cell == '.':
                pygame.draw.circle(screen, WHITE, (draw_x + CELL_SIZE // 2, draw_y + CELL_SIZE // 2), 2)
            elif cell == 'o':
                pygame.draw.circle(screen, WHITE, (draw_x + CELL_SIZE // 2, draw_y + CELL_SIZE // 2), 5)

def draw_ui(score, lives, level):
    screen.blit(font.render(f"Score: {score}", True, WHITE), (10, 10))
    screen.blit(font.render(f"Lives: {lives}", True, WHITE), (150, 10))
    screen.blit(font.render(f"Level: {level % 256 or 0}", True, WHITE), (250, 10))

def reset_level(level):
    maze = [row[:] for row in get_maze(level)]
    pac_start_x, pac_start_y = 13, 23
    ghost_starts = [(13, 11), (12, 11), (13, 10), (14, 11)]
    pacman = Pacman(pac_start_x, pac_start_y)
    ghosts = [Ghost(x, y, [RED, PINK, CYAN, ORANGE][i]) for i, (x, y) in enumerate(ghost_starts)]
    total_dots = count_dots(maze)
    return maze, pacman, ghosts, total_dots

def main():
    level = 1
    score = 0
    lives = 3
    maze, pacman, ghosts, total_dots = reset_level(level)
    eaten_dots = 0
    frightened_timer = 0
    running = True
    power_mode = False

    while running:
        screen.fill(BLACK)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT: pacman.next_direction = 'LEFT'
                elif event.key == pygame.K_RIGHT: pacman.next_direction = 'RIGHT'
                elif event.key == pygame.K_UP: pacman.next_direction = 'UP'
                elif event.key == pygame.K_DOWN: pacman.next_direction = 'DOWN'

        pacman.speed = 1 + (level - 1) * 0.02
        for g in ghosts:
            g.speed = 0.8 + (level - 1) * 0.01

        if power_mode:
            frightened_timer -= 1
            if frightened_timer <= 0:
                power_mode = False
                for g in ghosts: g.frightened = False

        points = pacman.move(maze)
        if points > 0:
            score += points
            eaten_dots += 1 if points == 10 else 0
            if points == 50:
                power_mode = True
                frightened_timer = 300
                for g in ghosts: g.frightened = True

        if eaten_dots >= total_dots:
            level += 1
            if level > 256:
                print("Congratulations! You beat all 256 levels!")
                running = False
            else:
                maze, pacman, ghosts, total_dots = reset_level(level)
                eaten_dots = 0

        for ghost in ghosts:
            ghost.move(maze, pacman.x, pacman.y, power_mode)
            if abs(ghost.x - pacman.x) < 1 and abs(ghost.y - pacman.y) < 1:
                if power_mode:
                    score += 200
                    ghost.dead = True
                else:
                    lives -= 1
                    if lives <= 0:
                        print("Game Over!")
                        running = False
                    else:
                        maze, pacman, ghosts, total_dots = reset_level(level)
                        eaten_dots = 0

        if level == 256:
            for g in ghosts:
                g.color = DARK_BLUE
                g.speed = random.uniform(0.5, 1.5)

        draw_board(maze)
        pacman.draw()
        for ghost in ghosts: ghost.draw()
        draw_ui(score, lives, level)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
