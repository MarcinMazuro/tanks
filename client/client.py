import sys
import time
import threading
import pygame
from pathlib import Path

# Add parent directory to path to import common modules
sys.path.append(str(Path(__file__).parent.parent))

from common.network import NetworkManager, NetworkMessage
from common.network import (
    MSG_TYPE_JOIN, MSG_TYPE_LEAVE, MSG_TYPE_ACTION, 
    MSG_TYPE_STATE, MSG_TYPE_START, MSG_TYPE_END, MSG_TYPE_READY, MSG_TYPE_RESTART
)

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)

# Player colors
PLAYER_COLORS = [RED, GREEN, BLUE, YELLOW]

class GameClient:
    """
    The game client that connects to the server and renders the game.
    """
    def __init__(self, player_name, server_host='localhost', server_port=12345, cell_size=30):
        """
        Initialize the game client.

        Args:
            player_name (str): The name of the player.
            server_host (str): The server host address.
            server_port (int): The server port.
            cell_size (int): The size of each cell in pixels.
        """
        self.player_name = player_name
        self.server_host = server_host
        self.server_port = server_port
        self.cell_size = cell_size

        self.network = NetworkManager(False)
        self.player_id = None
        self.game_state = None
        self.running = False
        self.connected = False
        self.game_started = False
        self.game_ended = False
        self.winner = None

        # Initialize pygame
        pygame.init()
        self.screen = None
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont('Arial', 20)
        self.big_font = pygame.font.SysFont('Arial', 32)

    def connect(self):
        """
        Connect to the game server.

        Returns:
            bool: True if connected successfully, False otherwise.
        """
        try:
            # Connect to server
            self.network.connect_to_server(self.server_host, self.server_port)

            # Send join message with player name
            join_message = NetworkMessage(MSG_TYPE_JOIN, {
                'name': self.player_name
            })
            self.network.send_message(join_message)

            # Wait for response
            for _ in range(50):  # Try for 5 seconds
                message, _ = self.network.receive_message()
                if message and message.msg_type == MSG_TYPE_JOIN:
                    if message.data.get('success', False):
                        self.player_id = message.data.get('player_id')
                        self.connected = True
                        print(f"Connected to server as player {self.player_id}")
                        return True
                    else:
                        reason = message.data.get('reason', 'Unknown reason')
                        print(f"Failed to join game: {reason}")
                        return False
                time.sleep(0.1)

            print("Timed out waiting for server response")
            return False
        except Exception as e:
            print(f"Error connecting to server: {e}")
            return False

    def start(self):
        """
        Start the game client.
        """
        if not self.connected:
            if not self.connect():
                return

        self.running = True

        # Create network thread
        network_thread = threading.Thread(target=self._network_loop)
        network_thread.daemon = True
        network_thread.start()

        # Send ready message
        ready_message = NetworkMessage(MSG_TYPE_READY, {})
        self.network.send_message(ready_message)

        # Main game loop
        self._game_loop()

    def stop(self):
        """
        Stop the game client.
        """
        self.running = False

        # Send leave message
        if self.connected:
            leave_message = NetworkMessage(MSG_TYPE_LEAVE, {})
            self.network.send_message(leave_message)

        self.network.close()
        pygame.quit()

    def _network_loop(self):
        """
        The network loop that receives messages from the server.
        """
        while self.running:
            message, _ = self.network.receive_message()

            if message:
                self._process_message(message)

            time.sleep(0.001)  # Small sleep to reduce CPU usage

    def _process_message(self, message):
        """
        Process a message from the server.

        Args:
            message (NetworkMessage): The message to process.
        """
        if message.msg_type == MSG_TYPE_STATE:
            self.game_state = message.data
        elif message.msg_type == MSG_TYPE_START:
            self.game_started = True
            self.game_ended = False
            self.winner = None
            print("Game started!")
            print("Players:", ", ".join([p['name'] for p in message.data.get('players', [])]))
        elif message.msg_type == MSG_TYPE_END:
            self.game_started = False
            self.game_ended = True
            self.winner = message.data.get('winner')
            print(f"Game ended! Winner: {self.winner}")
        elif message.msg_type == MSG_TYPE_JOIN:
            # Handle player_id updates after initial connection
            if self.connected and message.data.get('success', False):
                old_player_id = self.player_id
                self.player_id = message.data.get('player_id')
                print(f"Player ID updated from {old_player_id} to {self.player_id}")

    def send_restart_request(self):
        """
        Send a restart request to the server.
        """
        if self.connected and self.game_ended:
            restart_message = NetworkMessage(MSG_TYPE_RESTART, {})
            self.network.send_message(restart_message)
            print("Sent restart request to server")

    def _game_loop(self):
        """
        The main game loop that handles input and rendering.
        """
        # Initialize screen
        if self.game_state:
            map_size = self.game_state.get('map', {}).get('size', (20, 20))
            screen_width = map_size[0] * self.cell_size
            screen_height = map_size[1] * self.cell_size
        else:
            screen_width = 600
            screen_height = 600

        self.screen = pygame.display.set_mode((screen_width, screen_height))
        pygame.display.set_caption(f"Czolgi - {self.player_name}")

        # Main loop
        while self.running:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    # Check if restart button was clicked
                    if self.game_ended and hasattr(self, 'restart_button_rect'):
                        mouse_pos = pygame.mouse.get_pos()
                        if self.restart_button_rect.collidepoint(mouse_pos):
                            self.send_restart_request()

            # Handle input
            self._handle_input()

            # Render game
            self._render()

            # Cap at 60 FPS
            self.clock.tick(60)

    def _handle_input(self):
        """
        Handle user input.
        """
        if not self.game_started or not self.game_state or self.player_id is None:
            return

        # Get player state
        players = self.game_state.get('players', [])
        if self.player_id >= len(players) or not players[self.player_id].get('is_alive', False):
            return

        keys = pygame.key.get_pressed()

        # Movement
        if keys[pygame.K_w]:
            action = {'type': 'move_forward'}
            self.network.send_message(NetworkMessage(MSG_TYPE_ACTION, action))
        elif keys[pygame.K_s]:
            action = {'type': 'move_backward'}
            self.network.send_message(NetworkMessage(MSG_TYPE_ACTION, action))

        # Rotation
        if keys[pygame.K_d]:
            action = {'type': 'turn_left'}
            self.network.send_message(NetworkMessage(MSG_TYPE_ACTION, action))
        elif keys[pygame.K_a]:
            action = {'type': 'turn_right'}
            self.network.send_message(NetworkMessage(MSG_TYPE_ACTION, action))

        # Fire
        if keys[pygame.K_SPACE]:
            action = {'type': 'fire'}
            self.network.send_message(NetworkMessage(MSG_TYPE_ACTION, action))

    def _render(self):
        """
        Render the game state.
        """
        if not self.screen:
            return

        # Clear screen
        self.screen.fill(BLACK)

        if not self.game_state:
            # Render waiting message
            text = self.font.render("Waiting for game to start...", True, WHITE)
            text_rect = text.get_rect(center=(self.screen.get_width() // 2, self.screen.get_height() // 2))
            self.screen.blit(text, text_rect)
        else:
            # Render map
            self._render_map()

            # Render players
            self._render_players()

            # Render bullets
            self._render_bullets()

            # Render game end screen if the game has ended
            if self.game_ended:
                self._render_game_end()

        pygame.display.flip()

    def _render_game_end(self):
        """
        Render the game end screen with a restart button.
        """
        # Create a semi-transparent overlay
        overlay = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))  # Black with alpha
        self.screen.blit(overlay, (0, 0))

        # Render game end message
        if self.winner:
            message = f"Game Over! Winner: {self.winner}"
        else:
            message = "Game Over!"

        text = self.big_font.render(message, True, WHITE)
        text_rect = text.get_rect(center=(self.screen.get_width() // 2, self.screen.get_height() // 2 - 50))
        self.screen.blit(text, text_rect)

        # Render restart button
        button_width, button_height = 200, 50
        button_x = self.screen.get_width() // 2 - button_width // 2
        button_y = self.screen.get_height() // 2 + 50

        # Store button rect for click detection
        self.restart_button_rect = pygame.Rect(button_x, button_y, button_width, button_height)

        # Draw button
        pygame.draw.rect(self.screen, GREEN, self.restart_button_rect)
        pygame.draw.rect(self.screen, WHITE, self.restart_button_rect, 2)  # Border

        # Button text
        button_text = self.font.render("Restart Game", True, BLACK)
        button_text_rect = button_text.get_rect(center=self.restart_button_rect.center)
        self.screen.blit(button_text, button_text_rect)

    def _render_map(self):
        """
        Render the game map.
        """
        if not self.game_state:
            return

        map_data = self.game_state.get('map', {})
        walls = map_data.get('walls', [])

        for wall_pos in walls:
            x, y = wall_pos
            rect = pygame.Rect(
                x * self.cell_size,
                y * self.cell_size,
                self.cell_size,
                self.cell_size
            )
            pygame.draw.rect(self.screen, WHITE, rect)

    def _render_players(self):
        """
        Render the players.
        """
        if not self.game_state:
            return

        players = self.game_state.get('players', [])

        for i, player in enumerate(players):
            if not player.get('is_alive', False):
                continue

            position = player.get('position', (0, 0))
            direction = player.get('direction', (1, 0))

            # Calculate center of the cell
            center_x = position[0] * self.cell_size + self.cell_size // 2
            center_y = position[1] * self.cell_size + self.cell_size // 2

            # Draw player as a rectangle with a line indicating direction
            color = PLAYER_COLORS[i % len(PLAYER_COLORS)]
            rect_width = self.cell_size - 4
            rect_height = self.cell_size - 4

            # Calculate angle from direction vector (in degrees)
            import math
            angle_rad = math.atan2(direction[1], direction[0])
            angle_deg = math.degrees(angle_rad)

            # Create a surface for the tank
            tank_surface = pygame.Surface((rect_width, rect_height), pygame.SRCALPHA)
            tank_surface.fill((0, 0, 0, 0))  # Transparent background

            # Draw the rectangle on the surface
            pygame.draw.rect(tank_surface, color, pygame.Rect(0, 0, rect_width, rect_height))

            # Draw the direction line (barrel) on the surface
            pygame.draw.line(tank_surface, BLACK, 
                            (rect_width // 2, rect_height // 2), 
                            (rect_width, rect_height // 2), 3)

            # Rotate the surface
            rotated_surface = pygame.transform.rotate(tank_surface, -angle_deg)  # Negative for clockwise rotation

            # Get the rect of the rotated surface and position it
            rotated_rect = rotated_surface.get_rect(center=(center_x, center_y))

            # Draw the rotated tank
            self.screen.blit(rotated_surface, rotated_rect.topleft)

    def _render_bullets(self):
        """
        Render the bullets.
        """
        if not self.game_state:
            return

        players = self.game_state.get('players', [])

        for i, player in enumerate(players):
            bullets = player.get('bullets', [])
            color = PLAYER_COLORS[i % len(PLAYER_COLORS)]

            for bullet in bullets:
                position = bullet.get('position', (0, 0))

                # Calculate center of the bullet
                center_x = position[0] * self.cell_size + self.cell_size // 2
                center_y = position[1] * self.cell_size + self.cell_size // 2

                # Draw bullet as a small circle
                radius = self.cell_size // 4
                pygame.draw.circle(self.screen, color, (center_x, center_y), radius)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Czolgi Game Client")
    parser.add_argument("--name", default="Player", help="Player name")
    parser.add_argument("--host", default="localhost", help="Server host address")
    parser.add_argument("--port", type=int, default=12345, help="Server port")
    parser.add_argument("--cell-size", type=int, default=30, help="Cell size in pixels")

    args = parser.parse_args()

    client = GameClient(args.name, args.host, args.port, args.cell_size)

    try:
        client.start()
    except KeyboardInterrupt:
        pass
    finally:
        client.stop()
