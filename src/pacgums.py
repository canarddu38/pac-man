"""Pacgum placement and consumption logic.

This module defines the Pacgums model used to populate the maze with normal
and super pacgums and to apply their effects when collected by a character.
"""

import random
from enums import PacgumsType, Colors
from pydantic import BaseModel, ConfigDict
from typing import Any
from character import Character
from config import Config
import pyray as pr


class Pacgums(BaseModel):
    """Container for pacgum positions and game configuration.

    Attributes:
        pacgums: Mapping of (x, y) tile coordinates to pacgum type.
        config: Game configuration providing scoring values.
        maze: The maze grid used to avoid placing pacgums on walls.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)
    pacgums: dict[tuple[int, int], PacgumsType] = {}
    config: Config | None = None
    maze: list[list[int]] = []

    def model_post_init(self: Any, __context: Any) -> None:
        """Initialize the pacgums mapping from config and the maze.

        The method ensures the four corner pacgums are 'SUPER' and fills the
        remainder randomly up to the configured number.
        """
        i = (
            self.config.get("pacgum")
            if self.config.get("pacgum")
            < (len(self.maze[0]) - 1) * (len(self.maze) - 1)
            else (len(self.maze[0]) - 1) * (len(self.maze) - 1)
        )
        w, h = len(self.maze[0]) - 1, len(self.maze) - 1
        self.pacgums = {
            (0, 0): PacgumsType.SUPER,
            (w, 0): PacgumsType.SUPER,
            (w, h): PacgumsType.SUPER,
            (0, h): PacgumsType.SUPER,
        }
        j = 0
        while j < i:
            x = random.randint(0, len(self.maze[0]) - 1)
            y = random.randint(0, len(self.maze) - 1)
            if not (x, y) in self.pacgums.keys() and self.maze[y][x] != 15:
                self.pacgums[(x, y)] = PacgumsType.NORMAL
                j += 1

    def on_eat(self: Any, character: Character,
               pacgum_pos: tuple[int, int]) -> None:
        """Apply pacgum effects when collected by a character.

        Args:
            character: The Character instance that collected the pacgum.
            pacgum_pos: Coordinate of the collected pacgum.
        """
        if not self.config or pacgum_pos not in self.pacgums.keys():
            return
        try:
            t = self.pacgums.pop(pacgum_pos)
            match (t):
                case PacgumsType.NORMAL:
                    character.score += self.config.get("points_per_pacgum")
                case PacgumsType.SUPER:
                    character.score += self.config.get(
                        "points_per_super_pacgum"
                    )
        except ValueError:
            raise Exception("Could not access pacgum")

    def draw_pacgum(self: Any, c: int, r: int, x: int, y: int) -> None:
        """Draw a pacgum at the given cell coordinates to screen.

        Args:
            c: Cell x coordinate.
            r: Cell y coordinate.
            x: Pixel x coordinate to draw the pacgum center.
            y: Pixel y coordinate to draw the pacgum center.
        """
        if self.pacgums.get((c, r)) is None:
            return
        if self.pacgums.get((c, r)) == PacgumsType.NORMAL:
            radius = 6
        else:
            radius = 10
        pr.draw_circle(x - radius // 2, y - radius // 2, radius,
                       Colors.PACGUMS.value)
