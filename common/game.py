import random
import time
from common.map import Map
from common.player import Player
from common.bullet import Bullet

class Game:
    """
    Represents the main game logic and state.
    """
    def __init__(self, map_size=(20, 20), max_players=4, tick_rate=60):
        """
        Initialize a new game.

        Args:
            map_size (tuple): The size of the game map as (width, height).
            max_players (int): Maximum number of players allowed in the game.
            tick_rate (int): Number of game ticks per second.
        """
        self.map = Map(map_size)
        self.map.generate_random_map()
        self.players = []
        self.defeated_players = []
        self.max_players = max_players
        self.tick_rate = tick_rate
        self.tick_interval = 1.0 / tick_rate
        self.is_running = False
        self.start_time = None
        self.current_tick = 0

    def add_player(self, name, ip_address=None):
        """
        Add a new player to the game.

        Args:
            name (str): The name of the player.
            ip_address (str): The IP address of the player.

        Returns:
            Player: The newly created player, or None if the game is full.
        """
        if len(self.players) >= self.max_players:
            return None

        # Find a valid spawn position
        position = self._find_spawn_position()

        # Random initial direction using angle
        import math
        angle = random.uniform(0, 2 * math.pi)  # Random angle between 0 and 2π
        direction = (math.cos(angle), math.sin(angle))

        player = Player(name, position, direction, ip_address)
        self.players.append(player)
        return player

    def _find_spawn_position(self):
        """
        Find a valid spawn position for a new player.

        Returns:
            tuple: A valid (x, y) position.
        """
        max_attempts = 100
        for _ in range(max_attempts):
            x = random.randint(1, self.map.size[0] - 2)
            y = random.randint(1, self.map.size[1] - 2)

            # Check if position is valid (not a wall and not occupied)
            if self.map.is_position_valid(x, y) and not self._is_position_occupied(x, y):
                return (x, y)

        # If no position found, use a default position
        return (1, 1)

    def _is_position_occupied(self, x, y):
        """
        Check if a position is occupied by any player.

        Args:
            x (int): The x-coordinate to check.
            y (int): The y-coordinate to check.

        Returns:
            bool: True if the position is occupied, False otherwise.
        """
        for player in self.players:
            if player.is_alive:
                # Round player position for comparison
                player_x = round(player.position[0])
                player_y = round(player.position[1])
                if (player_x, player_y) == (x, y):
                    return True
        return False

    def start_game(self):
        """
        Start the game.
        """
        if not self.players:
            return False

        self.is_running = True
        self.start_time = time.time()
        self.current_tick = 0
        return True

    def end_game(self):
        """
        End the game.

        Returns:
            list: List of players in order of elimination (last is the winner).
        """
        self.is_running = False

        # Add remaining alive players to the defeated list
        alive_players = [p for p in self.players if p.is_alive]
        self.defeated_players.extend(alive_players)

        # Reset player states
        for player in self.players:
            player.is_alive = False

        return self.defeated_players

    def restart_game(self):
        """
        Restart the game for a new round.

        Returns:
            bool: True if the game was restarted successfully, False otherwise.
        """
        if not self.players:
            return False

        # Clear defeated players list
        self.defeated_players = []

        # Reset player states and positions
        for player in self.players:
            # Find a new spawn position
            player.position = self._find_spawn_position()
            player.is_alive = True
            player.bullets = []  # Clear bullets

        # Reset game state
        self.is_running = True
        self.start_time = time.time()
        self.current_tick = 0

        return True

    def eliminate_player(self, player):
        """
        Eliminate a player from the game.

        Args:
            player (Player): The player to eliminate.
        """
        if player in self.players and player.is_alive:
            player.is_alive = False
            self.defeated_players.append(player)

    def spawn_player(self, player):
        """
        Respawn a player in the game.

        Args:
            player (Player): The player to respawn.
        """
        if player in self.players:
            player.position = self._find_spawn_position()
            player.is_alive = True

    def update(self):
        """
        Update the game state for one tick.

        Returns:
            bool: True if the game is still running, False if it has ended.
        """
        if not self.is_running:
            return False

        self.current_tick += 1

        # Update all players and their bullets
        for player in self.players:
            if not player.is_alive:
                continue

            # Update player state
            player.update()

            # Update player's bullets
            active_bullets = []
            for bullet in player.bullets:
                if bullet.update(self.map, self.players):
                    active_bullets.append(bullet)
            player.bullets = active_bullets

        # Check game end condition
        alive_count = sum(1 for p in self.players if p.is_alive)
        if alive_count <= 1:
            self.end_game()
            return False

        return True

    def get_state(self):
        """
        Get the current game state.

        Returns:
            dict: The current game state.
        """
        return {
            'tick': self.current_tick,
            'map': {
                'size': self.map.size,
                'walls': self.map.walls_list
            },
            'players': [
                {
                    'name': player.name,
                    'position': player.position,
                    'direction': player.direction,
                    'is_alive': player.is_alive,
                    'bullets': [
                        {
                            'position': bullet.position,
                            'direction': bullet.direction
                        }
                        for bullet in player.bullets
                    ]
                }
                for player in self.players
            ],
            'is_running': self.is_running
        }

    def process_player_action(self, player_id, action):
        """
        Process a player action.

        Args:
            player_id (int): The index of the player in the players list.
            action (dict): The action to process.

        Returns:
            bool: True if the action was processed successfully, False otherwise.
        """
        if not self.is_running or player_id >= len(self.players):
            return False

        player = self.players[player_id]
        if not player.is_alive:
            return False

        action_type = action.get('type')

        if action_type == 'move_forward':
            return player.move_forward(self.map)
        elif action_type == 'move_backward':
            return player.move_backward(self.map)
        elif action_type == 'turn_left':
            player.turn_left()
            return True
        elif action_type == 'turn_right':
            player.turn_right()
            return True
        elif action_type == 'fire':
            bullet = player.fire_bullet()
            return bullet is not None

        return False
