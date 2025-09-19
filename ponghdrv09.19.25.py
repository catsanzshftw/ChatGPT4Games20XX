"""Pygame Pong game with mouse-controlled player and AI opponent.

The left paddle follows the player's mouse cursor, while the right paddle is
controlled by a simple AI that tracks the ball. The first side to reach five
points triggers a game over prompt where the player can choose to restart or
quit.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Tuple

import pygame


# Screen configuration
WIDTH, HEIGHT = 800, 600
BACKGROUND_COLOR = (15, 15, 25)
LINE_COLOR = (230, 230, 230)
SCORE_COLOR = (240, 240, 240)

# Paddle configuration
PADDLE_WIDTH, PADDLE_HEIGHT = 14, 110
PADDLE_SPEED = 7

# Ball configuration
BALL_SIZE = 16
BALL_SPEED = 6
BALL_SPEED_INCREMENT = 0.3
MAX_BALL_SPEED = 12

# Game configuration
WINNING_SCORE = 5
FONT_NAME = "arial"
FPS = 60


@dataclass
class Paddle:
    """Simple paddle representation."""

    x: int
    y: int
    width: int
    height: int

    def rect(self) -> pygame.Rect:
        return pygame.Rect(self.x, self.y, self.width, self.height)

    def move_to(self, center_y: float) -> None:
        """Update the paddle's vertical position to center around center_y."""
        top = int(center_y - self.height / 2)
        top = max(0, min(HEIGHT - self.height, top))
        self.y = top

    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, LINE_COLOR, self.rect())


@dataclass
class Ball:
    """Ping-pong ball representation with velocity."""

    x: float
    y: float
    size: int
    velocity: Tuple[float, float]

    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), int(self.y), self.size, self.size)

    def reset(self, direction: int) -> None:
        """Center the ball and assign a horizontal direction (-1 or 1)."""
        self.x = WIDTH / 2 - self.size / 2
        self.y = HEIGHT / 2 - self.size / 2
        speed = min(BALL_SPEED, MAX_BALL_SPEED)
        self.velocity = (speed * direction, speed * 0.5)

    def increase_speed(self) -> None:
        vx, vy = self.velocity
        speed = math.hypot(vx, vy)
        speed = min(speed + BALL_SPEED_INCREMENT, MAX_BALL_SPEED)
        angle = math.atan2(vy, vx)
        self.velocity = (math.cos(angle) * speed, math.sin(angle) * speed)

    def update(self) -> None:
        self.x += self.velocity[0]
        self.y += self.velocity[1]

        # Bounce off top/bottom
        if self.y <= 0:
            self.y = 0
            self.velocity = (self.velocity[0], -self.velocity[1])
        elif self.y + self.size >= HEIGHT:
            self.y = HEIGHT - self.size
            self.velocity = (self.velocity[0], -self.velocity[1])

    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, LINE_COLOR, self.rect())


class PongGame:
    """Encapsulates the Pong gameplay loop and state."""

    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Mouse vs AI Pong")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(FONT_NAME, 32)
        self.big_font = pygame.font.SysFont(FONT_NAME, 48, bold=True)

        self.left_paddle = Paddle(40, HEIGHT // 2 - PADDLE_HEIGHT // 2, PADDLE_WIDTH, PADDLE_HEIGHT)
        self.right_paddle = Paddle(WIDTH - 40 - PADDLE_WIDTH, HEIGHT // 2 - PADDLE_HEIGHT // 2, PADDLE_WIDTH, PADDLE_HEIGHT)
        self.ball = Ball(WIDTH / 2 - BALL_SIZE / 2, HEIGHT / 2 - BALL_SIZE / 2, BALL_SIZE, (BALL_SPEED, BALL_SPEED * 0.5))

        self.left_score = 0
        self.right_score = 0
        self.game_over = False
        self.winner: str | None = None

    def reset_round(self, direction: int) -> None:
        """Reset the ball for a new rally."""
        self.ball.reset(direction)
        self.left_paddle.move_to(HEIGHT / 2)
        self.right_paddle.move_to(HEIGHT / 2)

    def reset_game(self) -> None:
        """Reset scores and ball for a fresh game."""
        self.left_score = 0
        self.right_score = 0
        self.game_over = False
        self.winner = None
        self.reset_round(direction=1)

    def handle_ai(self) -> None:
        """Move the right paddle toward the ball with a capped speed."""
        target_y = self.ball.y + self.ball.size / 2
        paddle_center = self.right_paddle.y + self.right_paddle.height / 2
        if abs(target_y - paddle_center) <= PADDLE_SPEED:
            self.right_paddle.move_to(target_y)
        elif target_y > paddle_center:
            self.right_paddle.move_to(paddle_center + PADDLE_SPEED)
        else:
            self.right_paddle.move_to(paddle_center - PADDLE_SPEED)

    def update_ball(self) -> None:
        """Advance the ball and handle collisions and scoring."""
        self.ball.update()

        ball_rect = self.ball.rect()
        left_rect = self.left_paddle.rect()
        right_rect = self.right_paddle.rect()

        if ball_rect.colliderect(left_rect) and self.ball.velocity[0] < 0:
            self.ball.x = left_rect.right
            self.ball.velocity = (-self.ball.velocity[0], self.ball.velocity[1])
            self.ball.increase_speed()
        elif ball_rect.colliderect(right_rect) and self.ball.velocity[0] > 0:
            self.ball.x = right_rect.left - self.ball.size
            self.ball.velocity = (-self.ball.velocity[0], self.ball.velocity[1])
            self.ball.increase_speed()

        # Scoring
        if ball_rect.right < 0:
            self.right_score += 1
            self.check_winner()
            if not self.game_over:
                self.reset_round(direction=-1)
        elif ball_rect.left > WIDTH:
            self.left_score += 1
            self.check_winner()
            if not self.game_over:
                self.reset_round(direction=1)

    def check_winner(self) -> None:
        if self.left_score >= WINNING_SCORE:
            self.game_over = True
            self.winner = "Player"
        elif self.right_score >= WINNING_SCORE:
            self.game_over = True
            self.winner = "Computer"

        if self.game_over:
            self.ball.x = WIDTH / 2 - self.ball.size / 2
            self.ball.y = HEIGHT / 2 - self.ball.size / 2
            self.ball.velocity = (0.0, 0.0)

    def draw_center_line(self) -> None:
        segment_height = 20
        gap = 20
        for y in range(0, HEIGHT, segment_height + gap):
            pygame.draw.rect(
                self.screen,
                LINE_COLOR,
                pygame.Rect(WIDTH // 2 - 2, y, 4, segment_height),
            )

    def draw_scores(self) -> None:
        score_text = self.font.render(f"{self.left_score} : {self.right_score}", True, SCORE_COLOR)
        rect = score_text.get_rect(center=(WIDTH // 2, 40))
        self.screen.blit(score_text, rect)

    def draw_game_over(self) -> None:
        if not self.game_over or not self.winner:
            return

        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        title = self.big_font.render("Game Over", True, SCORE_COLOR)
        title_rect = title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 60))
        self.screen.blit(title, title_rect)

        winner_text = self.font.render(f"{self.winner} wins!", True, SCORE_COLOR)
        winner_rect = winner_text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        self.screen.blit(winner_text, winner_rect)

        prompt_text = self.font.render("Play again? (Y/N)", True, SCORE_COLOR)
        prompt_rect = prompt_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 60))
        self.screen.blit(prompt_text, prompt_rect)

    def run(self) -> None:
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and self.game_over:
                    if event.key == pygame.K_y:
                        self.reset_game()
                    elif event.key == pygame.K_n:
                        running = False

            if not self.game_over:
                mouse_y = pygame.mouse.get_pos()[1]
                self.left_paddle.move_to(mouse_y)
                self.handle_ai()
                self.update_ball()

            self.screen.fill(BACKGROUND_COLOR)
            self.draw_center_line()
            self.left_paddle.draw(self.screen)
            self.right_paddle.draw(self.screen)
            self.ball.draw(self.screen)
            self.draw_scores()
            if self.game_over:
                self.draw_game_over()

            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()


def main() -> None:
    """Entry point for running the Pong game."""
    PongGame().run()


if __name__ == "__main__":
    main()
