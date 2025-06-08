class Map:
    """
    Represents the game map with walls and obstacles.
    """
    def __init__(self, size=(20, 20), name="Default Map"):
        """
        Initialize a new map with the given size and name.

        Args:
            size (tuple): The size of the map as (width, height).
            name (str): The name of the map.
        """
        self.size = size
        self.name = name
        self.walls_list = []

    def add_wall(self, x, y):
        """
        Add a wall at the specified position.

        Args:
            x (int): The x-coordinate of the wall.
            y (int): The y-coordinate of the wall.
        """
        self.walls_list.append((x, y))

    def is_wall_at(self, x, y):
        """
        Check if there is a wall at the specified position.

        Args:
            x (int): The x-coordinate to check.
            y (int): The y-coordinate to check.

        Returns:
            bool: True if there is a wall at the position, False otherwise.
        """
        return (x, y) in self.walls_list

    def is_position_valid(self, x, y):
        """
        Check if the position is valid (within map bounds and not a wall).

        Args:
            x (int): The x-coordinate to check.
            y (int): The y-coordinate to check.

        Returns:
            bool: True if the position is valid, False otherwise.
        """
        return (0 <= x < self.size[0] and 
                0 <= y < self.size[1] and 
                not self.is_wall_at(x, y))

    def is_rectangle_valid(self, center_x, center_y, width, height):
        """
        Check if a rectangle is valid (all corners are within map bounds and not in walls).

        Args:
            center_x (float): The x-coordinate of the rectangle's center.
            center_y (float): The y-coordinate of the rectangle's center.
            width (float): The width of the rectangle.
            height (float): The height of the rectangle.

        Returns:
            bool: True if the rectangle is valid, False otherwise.
        """
        # Calculate the half-width and half-height
        half_width = width / 2
        half_height = height / 2

        # Check all four corners of the rectangle
        top_left = (round(center_x - half_width), round(center_y - half_height))
        top_right = (round(center_x + half_width), round(center_y - half_height))
        bottom_left = (round(center_x - half_width), round(center_y + half_height))
        bottom_right = (round(center_x + half_width), round(center_y + half_height))

        # Check if all corners are valid positions
        return (self.is_position_valid(top_left[0], top_left[1]) and
                self.is_position_valid(top_right[0], top_right[1]) and
                self.is_position_valid(bottom_left[0], bottom_left[1]) and
                self.is_position_valid(bottom_right[0], bottom_right[1]))

    def generate_random_map(self, wall_density=0.3):
        """
        Generate a random map with walls, ensuring all areas are accessible.

        Args:
            wall_density (float): The density of walls (0.0 to 1.0).
        """
        import random
        from collections import deque

        # Clear existing walls
        self.walls_list = []

        # Add walls around the perimeter
        for x in range(self.size[0]):
            self.add_wall(x, 0)
            self.add_wall(x, self.size[1] - 1)

        for y in range(self.size[1]):
            self.add_wall(0, y)
            self.add_wall(self.size[0] - 1, y)

        # Add random walls inside
        for x in range(1, self.size[0] - 1):
            for y in range(1, self.size[1] - 1):
                if random.random() < wall_density:
                    self.add_wall(x, y)

        # Ensure all areas are connected
        self._ensure_connectivity()

    def _ensure_connectivity(self):
        """
        Ensure that all open spaces in the map are connected.
        Uses a breadth-first search to identify disconnected regions and removes walls to connect them.
        """
        from collections import deque
        import random

        # Find all open cells (non-wall cells)
        open_cells = []
        for x in range(1, self.size[0] - 1):
            for y in range(1, self.size[1] - 1):
                if not self.is_wall_at(x, y):
                    open_cells.append((x, y))

        if not open_cells:
            return  # No open cells, nothing to connect

        # Start BFS from the first open cell
        start = open_cells[0]
        visited = {start}
        queue = deque([start])

        # Directions for adjacent cells (up, right, down, left)
        directions = [(-1, 0), (0, 1), (1, 0), (0, -1)]

        # Perform BFS to find all connected cells
        while queue:
            x, y = queue.popleft()

            for dx, dy in directions:
                nx, ny = x + dx, y + dy

                # Check if the adjacent cell is within bounds and not a wall
                if (0 < nx < self.size[0] - 1 and 
                    0 < ny < self.size[1] - 1 and 
                    not self.is_wall_at(nx, ny) and 
                    (nx, ny) not in visited):
                    visited.add((nx, ny))
                    queue.append((nx, ny))

        # Find all disconnected cells
        disconnected = [cell for cell in open_cells if cell not in visited]

        # Connect disconnected regions by removing walls
        while disconnected:
            # Find the closest pair of connected and disconnected cells
            min_distance = float('inf')
            wall_to_remove = None
            connected_cell = None
            disconnected_cell = None

            for c_cell in visited:
                for d_cell in disconnected:
                    # Manhattan distance between cells
                    distance = abs(c_cell[0] - d_cell[0]) + abs(c_cell[1] - d_cell[1])

                    if distance < min_distance:
                        min_distance = distance
                        connected_cell = c_cell
                        disconnected_cell = d_cell

            if min_distance == 1:
                # Cells are adjacent, just remove the wall between them
                wall_x = (connected_cell[0] + disconnected_cell[0]) // 2
                wall_y = (connected_cell[1] + disconnected_cell[1]) // 2

                # Remove the wall
                if (wall_x, wall_y) in self.walls_list:
                    self.walls_list.remove((wall_x, wall_y))
            else:
                # Find a path between the cells and remove a wall along that path
                path_x = connected_cell[0]
                path_y = connected_cell[1]

                # Move horizontally first
                while path_x != disconnected_cell[0]:
                    if path_x < disconnected_cell[0]:
                        path_x += 1
                    else:
                        path_x -= 1

                    # If we hit a wall, remove it
                    if self.is_wall_at(path_x, path_y):
                        self.walls_list.remove((path_x, path_y))
                        break

                # If we haven't removed a wall yet, move vertically
                if not self.is_wall_at(path_x, path_y):
                    while path_y != disconnected_cell[1]:
                        if path_y < disconnected_cell[1]:
                            path_y += 1
                        else:
                            path_y -= 1

                        # If we hit a wall, remove it
                        if self.is_wall_at(path_x, path_y):
                            self.walls_list.remove((path_x, path_y))
                            break

            # Run BFS again from the first open cell to find all connected cells
            visited = {start}
            queue = deque([start])

            while queue:
                x, y = queue.popleft()

                for dx, dy in directions:
                    nx, ny = x + dx, y + dy

                    if (0 < nx < self.size[0] - 1 and 
                        0 < ny < self.size[1] - 1 and 
                        not self.is_wall_at(nx, ny) and 
                        (nx, ny) not in visited):
                        visited.add((nx, ny))
                        queue.append((nx, ny))

            # Update the list of disconnected cells
            disconnected = [cell for cell in open_cells if cell not in visited]
