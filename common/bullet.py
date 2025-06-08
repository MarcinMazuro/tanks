class Bullet:
    """
    Represents a bullet fired by a player.
    """
    def __init__(self, position, direction, owner=None, max_bounces=15, speed=0.09):
        """
        Initialize a new bullet.

        Args:
            position (tuple): The initial position as (x, y).
            direction (tuple): The direction of travel as (dx, dy).
            owner (Player): The player who fired this bullet.
            max_bounces (int): Maximum number of wall bounces before despawning.
            speed (float): The speed of the bullet (cells per tick).
        """
        self.position = position
        self.direction = direction
        self.owner = owner
        self.hit = False
        self.bounces = 0
        self.max_bounces = max_bounces
        self.speed = speed
        self.life_time = 0

    def update(self, game_map, players):
        """
        Update the bullet's position and check for collisions.

        Args:
            game_map (Map): The game map to check for wall collisions.
            players (list): List of Player objects to check for player collisions.

        Returns:
            bool: True if the bullet is still active, False if it should be removed.
        """
        if self.hit:
            return False

        # Increment lifetime
        self.life_time += 1

        # Move the bullet
        new_x = self.position[0] + self.direction[0] * self.speed
        new_y = self.position[1] + self.direction[1] * self.speed
        new_position = (new_x, new_y)

        # Round positions for wall collision checks
        round_new_x = round(new_x)
        round_new_y = round(new_y)
        round_current_x = round(self.position[0])
        round_current_y = round(self.position[1])

        # Check for wall collision
        if not game_map.is_position_valid(round_new_x, round_new_y):
            # Handle bounce
            dx, dy = self.direction

            # Check which wall was hit (horizontal or vertical)
            hit_horizontal = game_map.is_wall_at(round_current_x, round_new_y)
            hit_vertical = game_map.is_wall_at(round_new_x, round_current_y)

            if hit_horizontal and not hit_vertical:
                # Horizontal wall (top/bottom), reverse y direction
                self.direction = (dx, -dy)
            elif hit_vertical and not hit_horizontal:
                # Vertical wall (left/right), reverse x direction
                self.direction = (-dx, dy)
            else:
                # Corner case or both walls, reverse both
                self.direction = (-dx, -dy)

            self.bounces += 1

            # Check if max bounces reached
            if self.bounces >= self.max_bounces:
                return False

            # Recalculate new position after bounce
            dx, dy = self.direction
            new_x = self.position[0] + dx * self.speed
            new_y = self.position[1] + dy * self.speed
            new_position = (new_x, new_y)

            # Round for wall check
            round_new_x = round(new_x)
            round_new_y = round(new_y)

            # If still in a wall after bounce, despawn
            if not game_map.is_position_valid(round_new_x, round_new_y):
                return False

        # Update position
        self.position = new_position

        # Check for player collision
        for player in players:
            # Skip collision with the owner of the bullet only if less than 0.5 seconds (30 ticks) have passed
            if player is self.owner and self.life_time < 30:
                continue

            if player.is_alive and self.collision_with_player(player):
                self.hit = True
                player.is_alive = False
                return False

        return True

    def collision_with_player(self, player):
        """
        Check if the bullet is colliding with a player.

        Args:
            player (Player): The player to check for collision.

        Returns:
            bool: True if the bullet is colliding with the player, False otherwise.
        """
        # Use distance-based collision detection for floating-point positions
        bullet_x, bullet_y = self.position
        player_x, player_y = player.position

        # Calculate distance squared (faster than using sqrt)
        distance_squared = (bullet_x - player_x) ** 2 + (bullet_y - player_y) ** 2

        # If distance is less than 0.5, consider it a collision
        return distance_squared < 0.5

    @staticmethod
    def spawn_bullet(position, direction):
        """
        Create a new bullet at the specified position and direction.

        Args:
            position (tuple): The position to spawn the bullet at.
            direction (tuple): The direction for the bullet to travel.

        Returns:
            Bullet: A new bullet object.
        """
        return Bullet(position, direction)

    def despawn_bullet(self):
        """
        Mark the bullet as hit to be removed in the next update.
        """
        self.hit = True
