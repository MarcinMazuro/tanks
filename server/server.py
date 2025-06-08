import sys
import time
import threading
from pathlib import Path

# Add parent directory to path to import common modules
sys.path.append(str(Path(__file__).parent.parent))

from common.game import Game
from common.network import NetworkManager, NetworkMessage
from common.network import (
    MSG_TYPE_JOIN, MSG_TYPE_LEAVE, MSG_TYPE_ACTION, 
    MSG_TYPE_STATE, MSG_TYPE_START, MSG_TYPE_END, MSG_TYPE_READY, MSG_TYPE_RESTART
)

class GameServer:
    """
    The main game server that manages the game and client connections.
    """
    def __init__(self, host='0.0.0.0', port=12345, tick_rate=60, max_players=4):
        """
        Initialize the game server.

        Args:
            host (str): The host address to bind to.
            port (int): The port to use.
            tick_rate (int): Number of game ticks per second.
            max_players (int): Maximum number of players allowed in the game.
        """
        self.host = host
        self.port = port
        self.tick_rate = tick_rate
        self.tick_interval = 1.0 / tick_rate
        self.max_players = max_players

        self.network = NetworkManager(True, host, port)
        self.game = Game(max_players=max_players, tick_rate=tick_rate)

        self.running = False
        self.game_thread = None
        self.player_names = {}  # Maps player_id to player name
        self.ready_players = set()  # Set of player_ids that are ready

    def start(self):
        """
        Start the game server.
        """
        self.running = True
        self.game_thread = threading.Thread(target=self._game_loop)
        self.game_thread.daemon = True
        self.game_thread.start()

        print(f"Game server started on {self.host}:{self.port}")

        try:
            self._handle_clients()
        except KeyboardInterrupt:
            print("Server shutting down...")
        finally:
            self.stop()

    def stop(self):
        """
        Stop the game server.
        """
        self.running = False
        if self.game_thread:
            self.game_thread.join(timeout=1.0)
        self.network.close()
        print("Server stopped")

    def _game_loop(self):
        """
        The main game loop that updates the game state at a fixed rate.
        """
        last_tick_time = time.time()

        while self.running:
            current_time = time.time()
            elapsed = current_time - last_tick_time

            if elapsed >= self.tick_interval:
                # Update game state
                if self.game.is_running:
                    game_running = self.game.update()

                    # Send game state to all clients
                    state_message = NetworkMessage(MSG_TYPE_STATE, self.game.get_state())
                    self.network.send_message(state_message)

                    # If the game just ended, send an END message
                    if not game_running:
                        # Get the last player from defeated_players (the winner)
                        winner = None
                        if self.game.defeated_players:
                            winner = self.game.defeated_players[-1].name

                        # Send end message to all clients
                        end_message = NetworkMessage(MSG_TYPE_END, {
                            'winner': winner
                        })
                        self.network.send_message(end_message)
                        print(f"Game ended. Winner: {winner}")

                last_tick_time = current_time
            else:
                # Sleep to reduce CPU usage
                time.sleep(max(0, self.tick_interval - elapsed))

    def _handle_clients(self):
        """
        Handle client connections and messages.
        """
        while self.running:
            message, address = self.network.receive_message()

            if message is None:
                # No message received, sleep briefly to reduce CPU usage
                time.sleep(0.001)
                continue

            self._process_message(message, address)

    def _process_message(self, message, address):
        """
        Process a message from a client.

        Args:
            message (NetworkMessage): The message to process.
            address (tuple): The client's address.
        """
        if message.msg_type == MSG_TYPE_JOIN:
            self._handle_join(message, address)
        elif message.msg_type == MSG_TYPE_LEAVE:
            self._handle_leave(address)
        elif message.msg_type == MSG_TYPE_ACTION:
            self._handle_action(message, address)
        elif message.msg_type == MSG_TYPE_READY:
            self._handle_ready(address)
        elif message.msg_type == MSG_TYPE_RESTART:
            self._handle_restart(address)

    def _handle_join(self, message, address):
        """
        Handle a join message from a client.

        Args:
            message (NetworkMessage): The join message.
            address (tuple): The client's address.
        """
        player_name = message.data.get('name', f"Player_{len(self.game.players) + 1}")

        # Check if the game is full
        if len(self.game.players) >= self.max_players:
            # Send rejection message
            reject_message = NetworkMessage(MSG_TYPE_JOIN, {
                'success': False,
                'reason': 'Game is full'
            })
            self.network.send_message(reject_message, address)
            return

        # Add player to the game
        player = self.game.add_player(player_name, str(address))
        player_id = self.game.players.index(player)

        # Add client to network manager
        self.network.add_client(address, player_id)
        self.player_names[player_id] = player_name

        # Update player_ids to match indices in game.players
        self._update_player_ids()

        # Get the updated player_id after _update_player_ids
        player_id = self.network.clients.get(address, player_id)

        # Send acceptance message
        accept_message = NetworkMessage(MSG_TYPE_JOIN, {
            'success': True,
            'player_id': player_id,
            'player_count': len(self.game.players),
            'max_players': self.max_players
        })
        self.network.send_message(accept_message, address)

        print(f"Player {player_name} joined the game (ID: {player_id})")

        # If the game is already running, mark the player as ready
        if self.game.is_running:
            # Mark player as ready
            self.ready_players.add(player_id)
            print(f"Player {player_name} is automatically ready (joined mid-game)")

            # Send start message to the new player
            start_message = NetworkMessage(MSG_TYPE_START, {
                'players': [
                    {'id': i, 'name': p.name}
                    for i, p in enumerate(self.game.players)
                ]
            })
            self.network.send_message(start_message, address)

            # Send game state to the new player
            state_message = NetworkMessage(MSG_TYPE_STATE, self.game.get_state())
            self.network.send_message(state_message, address)
        # Otherwise, the game will start only when at least 2 real players have joined and are ready

    def _handle_leave(self, address):
        """
        Handle a leave message from a client.

        Args:
            address (tuple): The client's address.
        """
        player_id = self.network.remove_client(address)

        if player_id is not None and player_id < len(self.game.players):
            player = self.game.players[player_id]
            player_name = self.player_names.get(player_id, f"Player_{player_id}")

            # Remove player from ready players
            self.ready_players.discard(player_id)

            # Eliminate player from the game
            self.game.eliminate_player(player)

            # Update player_ids to match indices in game.players
            if self.network.clients:  # Only update if there are still clients connected
                self._update_player_ids()

            print(f"Player {player_name} left the game (ID: {player_id})")

    def _handle_action(self, message, address):
        """
        Handle an action message from a client.

        Args:
            message (NetworkMessage): The action message.
            address (tuple): The client's address.
        """
        player_id = self.network.clients.get(address)

        if player_id is not None and self.game.is_running:
            action = message.data
            self.game.process_player_action(player_id, action)

    def _update_player_ids(self):
        """
        Update player_ids in network.clients dictionary to match indices in game.players list.
        This ensures that player_ids are always consistent between client and server.
        """
        # Store old player_ids to track changes
        old_player_ids = {addr: player_id for addr, player_id in self.network.clients.items()}

        # Make sure game.players only contains players that correspond to connected clients
        connected_player_ids = set(self.network.clients.values())
        self.game.players = [p for i, p in enumerate(self.game.players) if i in connected_player_ids]

        # Simply assign sequential IDs to all connected clients
        addresses = list(self.network.clients.keys())
        for i, addr in enumerate(addresses):
            if i < len(self.game.players):
                self.network.clients[addr] = i
                self.game.players[i].ip_address = str(addr)  # Update player's IP address to match

        # Update player_names dictionary
        new_player_names = {}
        for addr, player_id in self.network.clients.items():
            if player_id < len(self.game.players):
                new_player_names[player_id] = self.game.players[player_id].name

        self.player_names = new_player_names

        print(f"Updated player IDs: {self.network.clients}")

        # Notify clients of their new player_ids if they've changed
        for addr, new_player_id in self.network.clients.items():
            old_player_id = old_player_ids.get(addr)
            if old_player_id is not None and old_player_id != new_player_id:
                # Send a message to the client with their new player_id
                update_message = NetworkMessage(MSG_TYPE_JOIN, {
                    'success': True,
                    'player_id': new_player_id,
                    'player_count': len(self.game.players),
                    'max_players': self.max_players
                })
                self.network.send_message(update_message, addr)
                print(f"Notified client at {addr} of new player_id: {new_player_id} (was {old_player_id})")

    def _handle_ready(self, address):
        """
        Handle a ready message from a client.

        Args:
            address (tuple): The client's address.
        """
        player_id = self.network.clients.get(address)

        if player_id is not None:
            # Mark player as ready
            self.ready_players.add(player_id)
            print(f"Player {self.player_names.get(player_id, f'Player_{player_id}')} is ready")

            # Check if we have at least 2 ready players
            if len(self.ready_players) >= 2 and not self.game.is_running:
                # Update player_ids to match indices in game.players
                self._update_player_ids()

                # Send start message to all clients
                start_message = NetworkMessage(MSG_TYPE_START, {
                    'players': [
                        {'id': i, 'name': p.name}
                        for i, p in enumerate(self.game.players)
                    ]
                })
                self.network.send_message(start_message)

                # Start the game
                self.game.start_game()
                print("Game started with", len(self.ready_players), "players")

                # Send game state to all clients
                state_message = NetworkMessage(MSG_TYPE_STATE, self.game.get_state())
                self.network.send_message(state_message)

    def _handle_restart(self, address):
        """
        Handle a restart message from a client.

        Args:
            address (tuple): The client's address.
        """
        player_id = self.network.clients.get(address)

        if player_id is not None:
            # Only restart if the game is not running (has ended)
            if not self.game.is_running:
                # Reset ready players
                self.ready_players.clear()

                # Update player_ids to match indices in game.players
                self._update_player_ids()

                success = self.game.restart_game()
                if success:
                    print("Game restarted")

                    # Send start message to all clients
                    start_message = NetworkMessage(MSG_TYPE_START, {
                        'players': [
                            {'id': i, 'name': p.name}
                            for i, p in enumerate(self.game.players)
                        ]
                    })
                    self.network.send_message(start_message)

                    # Send game state to all clients
                    state_message = NetworkMessage(MSG_TYPE_STATE, self.game.get_state())
                    self.network.send_message(state_message)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Czolgi Game Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host address to bind to")
    parser.add_argument("--port", type=int, default=12345, help="Port to use")
    parser.add_argument("--tick-rate", type=int, default=60, help="Game tick rate")
    parser.add_argument("--max-players", type=int, default=4, help="Maximum number of players")

    args = parser.parse_args()

    server = GameServer(args.host, args.port, args.tick_rate, args.max_players)
    server.start()
