class Player:
    """
    Represents a player (tank) in the game.
    """
    def __init__(self, name, position=(0, 0), direction=(1, 0), ip_address=None):
        """
        Initialize a new player.

        Args:
            name (str): The name of the player.
            position (tuple): The initial position as (x, y).
            direction (tuple): The initial direction as (dx, dy).
            ip_address (str): The IP address of the player (for network play).
        """
        self.name = name
        self.is_alive = True
        self.position = position
        self.direction = direction
        self.bullets = []
        self.ip_address = ip_address

        # Tank dimensions for hitbox
        self.width = 0.6  # Width of the tank in cells
        self.height = 0.6  # Height of the tank in cells

        # Movement and rotation speed parameters
        self.movement_speed = 0.07  # Cells per tick
        self.rotation_speed = 0.05  # Radians per tick

        # Movement and rotation cooldowns
        self.move_cooldown = 0
        self.rotate_cooldown = 0
        self.move_cooldown_max = 1  # Ticks between movements
        self.rotate_cooldown_max = 1  # Ticks between rotations

        # Firing cooldown and bullet limit
        self.fire_cooldown = 0
        self.fire_cooldown_max = 60  # Ticks between shots (60 ticks = 1 second at 60 tick rate)
        self.max_bullets = 5  # Maximum number of bullets a player can have active at once

    def fire_bullet(self):
        """
        Fire a bullet in the current direction.
        Checks if the player can fire (cooldown is 0 and hasn't reached max bullets).

        Returns:
            Bullet: The fired bullet object, or None if the player can't fire.
        """
        # Check if the player is on cooldown
        if self.fire_cooldown > 0:
            return None

        # Check if the player has reached the maximum number of bullets
        if len(self.bullets) >= self.max_bullets:
            return None

        # Fire a bullet
        from common.bullet import Bullet
        bullet = Bullet(self.position, self.direction, owner=self)
        self.bullets.append(bullet)

        # Set cooldown
        self.fire_cooldown = self.fire_cooldown_max

        return bullet

    def _get_angle_from_direction(self):
        """
        Convert direction vector to angle in radians.

        Returns:
            float: Angle in radians.
        """
        import math
        dx, dy = self.direction
        return math.atan2(dy, dx)

    def _get_direction_from_angle(self, angle):
        """
        Convert angle in radians to direction vector.

        Args:
            angle (float): Angle in radians.

        Returns:
            tuple: Direction vector as (dx, dy).
        """
        import math
        return (math.cos(angle), math.sin(angle))

    def turn_left(self):
        """
        Turn the player left (counter-clockwise) by rotation_speed radians.
        Returns True if rotation was performed, False if on cooldown.
        """
        if self.rotate_cooldown > 0:
            return False

        # Get current angle
        angle = self._get_angle_from_direction()

        # Rotate counter-clockwise
        angle += self.rotation_speed

        # Update direction
        self.direction = self._get_direction_from_angle(angle)

        # Set cooldown
        self.rotate_cooldown = self.rotate_cooldown_max
        return True

    def turn_right(self):
        """
        Turn the player right (clockwise) by rotation_speed radians.
        Returns True if rotation was performed, False if on cooldown.
        """
        if self.rotate_cooldown > 0:
            return False

        # Get current angle
        angle = self._get_angle_from_direction()

        # Rotate clockwise
        angle -= self.rotation_speed

        # Update direction
        self.direction = self._get_direction_from_angle(angle)

        # Set cooldown
        self.rotate_cooldown = self.rotate_cooldown_max
        return True

    def move_forward(self, game_map):
        """
        Move the player forward in the current direction if possible.
        If direct movement is blocked, try to slide along the wall.

        Args:
            game_map (Map): The game map to check for collisions.

        Returns:
            bool: True if the move was successful, False otherwise.
        """
        if self.move_cooldown > 0:
            return False

        dx, dy = self.direction
        new_x = self.position[0] + dx * self.movement_speed
        new_y = self.position[1] + dy * self.movement_speed

        # Check if the new position is valid using the rectangle hitbox
        if game_map.is_rectangle_valid(new_x, new_y, self.width, self.height):
            self.position = (new_x, new_y)
            self.move_cooldown = self.move_cooldown_max
            return True
        else:
            # Try sliding horizontally (keeping y the same)
            horizontal_x = new_x
            horizontal_y = self.position[1]
            horizontal_valid = game_map.is_rectangle_valid(horizontal_x, horizontal_y, self.width, self.height)

            # Try sliding vertically (keeping x the same)
            vertical_x = self.position[0]
            vertical_y = new_y
            vertical_valid = game_map.is_rectangle_valid(vertical_x, vertical_y, self.width, self.height)

            # Choose one of the valid sliding directions
            if horizontal_valid:
                self.position = (horizontal_x, horizontal_y)
                self.move_cooldown = self.move_cooldown_max
                return True
            elif vertical_valid:
                self.position = (vertical_x, vertical_y)
                self.move_cooldown = self.move_cooldown_max
                return True

            return False

    def move_backward(self, game_map):
        """
        Move the player backward (opposite of current direction) if possible.
        If direct movement is blocked, try to slide along the wall.

        Args:
            game_map (Map): The game map to check for collisions.

        Returns:
            bool: True if the move was successful, False otherwise.
        """
        if self.move_cooldown > 0:
            return False

        dx, dy = self.direction
        new_x = self.position[0] - dx * self.movement_speed
        new_y = self.position[1] - dy * self.movement_speed

        # Check if the new position is valid using the rectangle hitbox
        if game_map.is_rectangle_valid(new_x, new_y, self.width, self.height):
            self.position = (new_x, new_y)
            self.move_cooldown = self.move_cooldown_max
            return True
        else:
            # Try sliding horizontally (keeping y the same)
            horizontal_x = new_x
            horizontal_y = self.position[1]
            horizontal_valid = game_map.is_rectangle_valid(horizontal_x, horizontal_y, self.width, self.height)

            # Try sliding vertically (keeping x the same)
            vertical_x = self.position[0]
            vertical_y = new_y
            vertical_valid = game_map.is_rectangle_valid(vertical_x, vertical_y, self.width, self.height)

            # Choose one of the valid sliding directions
            if horizontal_valid:
                self.position = (horizontal_x, horizontal_y)
                self.move_cooldown = self.move_cooldown_max
                return True
            elif vertical_valid:
                self.position = (vertical_x, vertical_y)
                self.move_cooldown = self.move_cooldown_max
                return True

            return False

    def wall_collision_check(self, game_map):
        """
        Check if the player is colliding with a wall.

        Args:
            game_map (Map): The game map to check for collisions.

        Returns:
            bool: True if the player is colliding with a wall, False otherwise.
        """
        # Check if the current position is valid using the rectangle hitbox
        return not game_map.is_rectangle_valid(self.position[0], self.position[1], self.width, self.height)

    def update(self):
        """
        Update the player state for one tick.
        Decrements cooldowns if they are greater than 0.
        """
        # Decrement cooldowns if they're greater than 0
        if self.fire_cooldown > 0:
            self.fire_cooldown -= 1
        if self.move_cooldown > 0:
            self.move_cooldown -= 1
        if self.rotate_cooldown > 0:
            self.rotate_cooldown -= 1
