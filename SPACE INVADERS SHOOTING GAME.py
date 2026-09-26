import pygame
import sys
import random

# Initialize Pygame globally
pygame.init()

# --- CONSTANTS ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (255, 50, 50)
YELLOW = (255, 255, 0)

# ==========================================
# 1. BULLET CLASS
# ==========================================
class Bullet(pygame.sprite.Sprite):
    """Manages individual bullets fired from the spaceship."""
    def __init__(self, x, y):
        super().__init__()
        # Visual representation: small glowing rectangle.
        self.image = pygame.Surface((4, 12))
        self.image.fill(YELLOW)
        self.rect = self.image.get_rect()
        self.rect.centerx = x
        self.rect.bottom = y
        self.speed = -8  # Negative moves upward.

    def update(self):
        """Move the bullet up the screen and delete it if it leaves bounds."""
        self.rect.y += self.speed
        if self.rect.bottom < 0:
            self.kill()

# ==========================================
# 2. PLAYER CLASS
# ==========================================
class Player(pygame.sprite.Sprite):
    """Manages the player's spaceship, movement, and firing cooldown."""
    def __init__(self):
        super().__init__()
        # Create a simple triangular spaceship shape.
        self.image = pygame.Surface((50, 30), pygame.SRCALPHA)
        pygame.draw.polygon(self.image, GREEN, [(25, 0), (0, 30), (50, 30)])
        
        self.rect = self.image.get_rect()
        self.rect.centerx = SCREEN_WIDTH // 2
        self.rect.bottom = SCREEN_HEIGHT - 30
        self.speed = 6
        
        # Cooldown management (in milliseconds).
        self.last_shot = pygame.time.get_ticks()
        self.shoot_delay = 300 

    def update(self):
        """Handle movement controls."""
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] and self.rect.left > 0:
            self.rect.x -= self.speed
        if keys[pygame.K_RIGHT] and self.rect.right < SCREEN_WIDTH:
            self.rect.x += self.speed

    def shoot(self, bullet_group, all_sprites_group):
        """Create a new bullet if the cooldown timer permits."""
        now = pygame.time.get_ticks()
        if now - self.last_shot > self.shoot_delay:
            self.last_shot = now
            bullet = Bullet(self.rect.centerx, self.rect.top)
            bullet_group.add(bullet)
            all_sprites_group.add(bullet)

# ==========================================
# 3. INVADER CLASS
# ==========================================
class Invader(pygame.sprite.Sprite):
    """Represents a single alien enemy."""
    def __init__(self, x, y):
        super().__init__()
        # Draw a blocky alien sprite surface.
        self.image = pygame.Surface((40, 25), pygame.SRCALPHA)
        pygame.draw.rect(self.image, RED, (5, 5, 30, 15))
        pygame.draw.rect(self.image, RED, (0, 10, 40, 5)) # Antennae/legs effect.
        
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

    def move(self, dx, dy):
        """Move horizontal or shift vertical based on collective fleet movement."""
        self.rect.x += dx
        self.rect.y += dy

# ==========================================
# 4. INVADER FLEET CLASS
# ==========================================
class InvaderFleet:
    """Manages rows of invaders, checking boundaries and sync'd movements."""
    def __init__(self, rows=4, cols=8):
        self.group = pygame.sprite.Group()
        self.direction = 1  # 1 = Right, -1 = Left
        self.horizontal_speed = 2
        self.drop_distance = 15
        
        # Populate the grid of invaders.
        for row in range(rows):
            for col in range(cols):
                x = 80 + col * 75
                y = 60 + row * 45
                invader = Invader(x, y)
                self.group.add(invader)

    def update(self):
        """Shift fleet horizontally. If any hit an edge, bounce down."""
        shift_down = False
        dx = self.horizontal_speed * self.direction
        
        # Move all fleet members first.
        for invader in self.group.sprites():
            invader.move(dx, 0)
            
        # Check if anyone touched the screen boundary bounds.
        for invader in self.group.sprites():
            if invader.rect.right >= SCREEN_WIDTH or invader.rect.left <= 0:
                shift_down = True
                break
                
        # If an edge was triggered, switch direction and step down.
        if shift_down:
            self.direction *= -1
            for invader in self.group.sprites():
                invader.move(0, self.drop_distance)

# ==========================================
# 5. SCOREBOARD CLASS
# ==========================================
class Scoreboard:
    """Manages the text UI overlay tracking score, lives, and states."""
    def __init__(self):
        self.score = 0
        self.font = pygame.font.SysFont("Courier", 24, bold=True)
        self.game_over_font = pygame.font.SysFont("Courier", 48, bold=True)

    def add_points(self, points):
        self.score += points

    def draw(self, surface, is_game_over=False, has_won=False):
        """Render score dashboard text onto the active window surface."""
        score_text = self.font.render(f"SCORE: {self.score}", True, WHITE)
        surface.blit(score_text, (20, 20))
        
        if is_game_over:
            text = "GAME OVER" if not has_won else "YOU WIN!"
            color = RED if not has_won else GREEN
            end_text = self.game_over_font.render(text, True, color)
            text_rect = end_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            surface.blit(end_text, text_rect)

# ==========================================
# 6. GAME ENGINE CLASS
# ==========================================
class GameEngine:
    """The master orchestrator containing the game loop and collision setup."""
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("OOD Space Invaders Clone")
        self.clock = pygame.time.Clock()
        self.running = True
        self.game_over = False
        self.victory = False

        # Initialize core single-instance structural elements.
        self.player = Player()
        self.fleet = InvaderFleet(rows=4, cols=10)
        self.scoreboard = Scoreboard()

        # Group Categorizations.
        self.all_sprites = pygame.sprite.Group()
        self.bullets = pygame.sprite.Group()

        # Add initial actors to unified drawing pool.
        self.all_sprites.add(self.player)
        for invader in self.fleet.group.sprites():
            self.all_sprites.add(invader)

    def check_collisions(self):
        """Scans engine frames for projectile and bounding collisions."""
        if self.game_over:
            return

        # 1. Bullet vs Invader collisions.
        # True, True means remove both the bullet and invader upon overlap.
        hits = pygame.sprite.groupcollide(self.bullets, self.fleet.group, True, True)
        for hit_bullet, hit_invaders in hits.items():
            for invader in hit_invaders:
                self.all_sprites.remove(invader) # Remove from visual loop.
                self.scoreboard.add_points(10)

        # Win condition check.
        if len(self.fleet.group) == 0:
            self.game_over = True
            self.victory = True

        # 2. Invader vs Player / Ground boundaries (Loss condition).
        for invader in self.fleet.group.sprites():
            if invader.rect.colliderect(self.player.rect) or invader.rect.bottom >= SCREEN_HEIGHT - 50:
                self.game_over = True
                self.victory = False

    def run(self):
        """Launches the primary loop handling event tracking, updates, and renders."""
        while self.running:
            # Event Tracking Frame.
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE and not self.game_over:
                        self.player.shoot(self.bullets, self.all_sprites)

            # Processing Engine States.
            if not self.game_over:
                self.player.update()
                self.fleet.update()
                self.bullets.update() # Explicitly updates bullet limits.
                self.check_collisions()

            # Graphic Layer Buffering.
            self.screen.fill(BLACK)
            self.all_sprites.draw(self.screen)
            self.scoreboard.draw(self.screen, self.game_over, self.victory)
            
            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()

# Run the game.
if __name__ == "__main__":
    game = GameEngine()
    game.run()
