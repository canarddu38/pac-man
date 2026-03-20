"""Character module for the Pac-man game.

This module defines the game characters: the player (Pacman) and the
ghost AI helpers. It includes small helper classes used by the game
logic and pathfinding integrations. All public classes and methods are
documented using Google-style docstrings.
"""

import time
from pydantic import BaseModel
from typing import Any
from enums import Bit_position, CharacterDirection, CharacterType, PacgumsType
import pyray as pr
from pathfinding import (
    make_neighbors,
    manhattan,
    a_star,
    distance,
    compute_escape_goal,
)
import random


class DummyPacman:
    """Lightweight representation of Pacman for AI calculations.

    This class is used by ghost AI routines when a simplified Pacman
    object is required (for example during unit tests or pathfinding
    computations). It mirrors only the minimal state needed by the
    ghost algorithms.

    Attributes:
        pos: Current grid position as [x, y].
        last_edible_mode: Timestamp of the last time Pacman ate a super
            pacgum and made ghosts edible.
        direction: Current movement direction.
        spectator_mode: When True, collisions and AI targeting are
            ignored.
    """

    def __init__(self, pos: list[int], last_edible: float) -> None:
        self.pos = pos
        self.last_edible_mode = last_edible
        self.direction = CharacterDirection.RIGHT
        self.spectator_mode = False


class Character(BaseModel):
    """Base model for all characters in the game.

    This Pydantic model stores runtime state used by both player and
    ghost entities. Several fields are intentionally public and used by
    the engine directly (for example `pos`, `vis_pos`, `direction`).

    Attributes:
        manager: Reference to the global game manager that holds shared
            state and helpers (joystick, resource loaders, etc.).
        name: Optional logical name of the character.
        spawn: Tuple with spawn coordinates used for respawn paths.
        pos: Current integer grid position [x, y].
        old_pos: Previous grid position used for collision checks.
        vis_pos: Interpolated position used for smooth rendering.
        is_active: Whether the character is currently active in-game.
        spectator_mode: When True the character will not collide or be
            targeted by ghosts.
        direction: Current movement direction enum value.
        character_type: Enum describing whether the character is the
            player or one of the ghost types.
        textures: Texture tuples used for rendering the character.
        edible_textures: Special textures used when ghosts are edible.
        death_anim_frame: Frame counter used during death animations.
        death_path: Path to follow when returning to spawn after death.
        ghost_is_edible_mode: Ghost-specific flag indicating edible state.
        score: Player score counter (used only on player instance).
        lerp_speed: Speed used for visual interpolation of positions.
        health: Remaining lives / health for the player.
        respawn_timer: Timestamp until which the character is inactive.
        path: Last computed path for AI debugging or movement.
    """

    manager: Any = None
    name: str | None = None
    spawn: tuple[int, int] | None = None
    pos: list[int] = [0, 0]
    old_pos: list[int] = [0, 0]
    vis_pos: list[float] = [0.0, 0.0]
    is_active: bool = False
    spectator_mode: bool = False
    direction: CharacterDirection | None = None
    character_type: CharacterType | None = None
    textures: tuple[
        tuple[Any, Any], tuple[Any, Any], tuple[Any, Any], tuple[Any, Any]
    ] | None = None
    edible_textures: tuple[tuple[Any, Any], tuple[Any, Any]] | None = None
    death_anim_frame: int = 0
    death_anim: (
        tuple[Any, Any, Any, Any]
        | tuple[Any, Any, Any, Any, Any, Any, Any, Any, Any, Any, Any]
    ) | None = None
    death_path: list[tuple[int, int]] = []
    ghost_is_edible_mode: bool = False
    ghost_random_pos: tuple[int, int] | None = None
    ghost_random_frame: int = -1
    ghost_weird_pos: int = 0
    last_edible_mode: float = 0
    force_non_edible_respawn: bool = False
    score: int = 0
    lerp_speed: float = 12.0
    health: int = 3
    respawn_timer: float = 0.0
    path: list[tuple[int, int]] = []

    def model_post_init(self, __context: Any) -> None:
        """Initialize visual and old position after model creation.

        This method ensures that `old_pos` and `vis_pos` are initialized
        to the current `pos` value when the model is created so the
        renderer and collision checks have sensible defaults.

        Args:
            __context: Context passed by pydantic during model init. It
                is unused but required by the hook signature.
        """
        if self.pos:
            self.old_pos = list(self.pos)
            self.vis_pos = list(self.pos)

    def control_movement(self) -> None:
        """Map keyboard input to the player character direction.

        Only applies to the player character. The method updates
        `direction` according to WASD or arrow key presses and updates
        the manager joystick visual tilt for feedback.
        """
        if self.character_type != CharacterType.PLAYER:
            return
        if self.on_death() or self.spectator_mode:
            return
        if (pr.is_key_down(pr.KEY_W)  # type: ignore[attr-defined]
                or pr.is_key_down(pr.KEY_UP)):  # type: ignore[attr-defined]
            self.direction = CharacterDirection.TOP
            self.manager.joystick_obj.set_tilt(-45.0, -90.0, 0.0)
        elif (pr.is_key_down(pr.KEY_S)  # type: ignore[attr-defined]
                or pr.is_key_down(pr.KEY_DOWN)):  # type: ignore[attr-defined]
            self.direction = CharacterDirection.BOTTOM
            self.manager.joystick_obj.set_tilt(45.0, -90.0, 0.0)
        elif (pr.is_key_down(pr.KEY_A)  # type: ignore[attr-defined]
                or pr.is_key_down(pr.KEY_LEFT)):  # type: ignore[attr-defined]
            self.direction = CharacterDirection.LEFT
            self.manager.joystick_obj.set_tilt(0.0, -90.0, 45.0)
        elif (pr.is_key_down(pr.KEY_D)  # type: ignore[attr-defined]
                or pr.is_key_down(pr.KEY_RIGHT)):  # type: ignore[attr-defined]
            self.direction = CharacterDirection.RIGHT
            self.manager.joystick_obj.set_tilt(0.0, -90.0, -45.0)
        else:
            self.manager.joystick_obj.set_tilt(0.0, -90.0, 0.0)

    def respawn(self) -> None:
        """Reset the character position to its spawn point.

        The method also resets `old_pos` and `vis_pos` to ensure smooth
        interpolation after the respawn. If `spawn` is not set the
        position is left untouched.
        """
        if self.spawn:
            self.pos = list(self.spawn)
        self.old_pos = list(self.pos)
        self.vis_pos = list(self.pos)
        self.is_active = True

    def find_pacman_pos(self, pos: list[int],
                        direction: CharacterDirection | None,
                        maze: list[list[int]],
                        distance: int) -> list[int] | tuple[int, int]:
        """Predict Pacman's future position for ambush ghosts.

        For the ambush ghost AI type, this computes a position ahead of
        Pacman in the given `direction` up to `distance` tiles unless a
        wall blocks the path.

        Args:
            pos: Pacman's current [x, y] tile coordinates.
            direction: Pacman's current movement direction.
            maze: The maze grid containing wall bitflags.
            distance: Number of tiles ahead to project.

        Returns:
            A coordinate pair representing the projected position. For
            non-ambush ghosts returns (0, 0).
        """
        if self.character_type != CharacterType.GHOST_AMBUSH:
            return (0, 0)
        result = pos.copy()
        if (
            direction == CharacterDirection.BOTTOM
            and result[1] + distance < len(maze)
            and not
            maze[result[1] + distance][result[0]] & Bit_position.SOUTH.value
        ):
            result[1] += distance
        if (
            direction == CharacterDirection.LEFT
            and result[0] - distance >= 0
            and not
            maze[result[1]][result[0] - distance] & Bit_position.WEST.value
        ):
            result[0] -= distance
        if (
            direction == CharacterDirection.RIGHT
            and result[0] + distance < len(maze[1])
            and not
            maze[result[1]][result[0] + distance] & Bit_position.EAST.value
        ):
            result[0] += distance
        if (
            direction == CharacterDirection.TOP
            and result[1] - distance >= 0
            and not
            maze[result[1] - distance][result[0]] & Bit_position.NORTH.value
        ):
            result[1] -= distance
        return result

    def find_corner_pos(self, maze: list[list[int]]) -> tuple[int, int]:
        """Return the next corner goal for 'weird' ghost behavior.

        The weird ghost cycles between the four corners of the maze.
        This method returns the next corner and advances the internal
        corner pointer when the ghost reaches the current target.

        Args:
            maze: The maze grid used to compute corner coordinates.

        Returns:
            Tuple with the target corner coordinates.
        """
        if self.character_type != CharacterType.GHOST_WEIRD:
            return (0, 0)
        pos = [
            (0, 0),
            (0, len(maze) - 1),
            (len(maze[0]) - 1, len(maze) - 1),
            (len(maze[0]) - 1, 0),
        ]
        if (
            self.pos[0] == pos[self.ghost_weird_pos][0]
            and self.pos[1] == pos[self.ghost_weird_pos][1]
        ):
            self.ghost_weird_pos = (self.ghost_weird_pos + 1) % 4

        return pos[self.ghost_weird_pos % len(pos)]

    def find_random_pos(self, maze: list[list[int]]) -> tuple[int, int]:
        """Return a pseudo-random goal for 'random' ghost behavior.

        The method caches a random target for a short duration (10
        frames) to avoid excessive goal changes and returns a new
        random target when the counter expires.

        Args:
            maze: The maze grid used to bound the random coordinates.

        Returns:
            Tuple with the random target coordinates.
        """
        if self.character_type != CharacterType.GHOST_RANDOM:
            return (0, 0)
        if self.ghost_random_frame > 10 or self.ghost_random_frame == -1:
            self.ghost_random_frame = 0
            x = random.randint(0, len(maze[0]) - 1)
            y = random.randint(0, len(maze) - 1)
            self.ghost_random_pos = (x, y)
        else:
            self.ghost_random_frame += 1
            if self.ghost_random_pos:
                x, y = self.ghost_random_pos
            else:
                x, y = 0, 0
        return (x, y)

    def move_loop(self, maze: list[list[int]],
                  ghosts: list[Any], pacgums: Any) -> None:
        """Update player position and handle pacgum consumption.

        This method is executed for the player character and moves the
        player according to the currently set `direction`. When a
        pacgum is present on the new tile it is consumed and
        side-effects (edible mode activation) are applied to ghosts.

        Args:
            maze: The maze grid with wall flags.
            ghosts: List of ghost character instances in the game.
            pacgums: Pacgums manager handling pellet state and scoring.
        """
        if self.character_type != CharacterType.PLAYER:
            return
        if self.on_death() or self.spectator_mode:
            return
        self.old_pos = list(self.pos)
        ghost_positions = [
            tuple(ghost.pos)
            for ghost in ghosts
            if time.time() - self.last_edible_mode > 10.0
            and time.time() > ghost.respawn_timer
        ]
        if (
            self.direction == CharacterDirection.BOTTOM
            and not maze[self.pos[1]][self.pos[0]] & Bit_position.SOUTH.value
        ):
            self.pos[1] += 1
        if (
            self.direction == CharacterDirection.LEFT
            and not maze[self.pos[1]][self.pos[0]] & Bit_position.WEST.value
        ):
            self.pos[0] -= 1
        if (
            self.direction == CharacterDirection.RIGHT
            and not maze[self.pos[1]][self.pos[0]] & Bit_position.EAST.value
        ):
            self.pos[0] += 1
        if (
            self.direction == CharacterDirection.TOP
            and not maze[self.pos[1]][self.pos[0]] & Bit_position.NORTH.value
        ):
            self.pos[1] -= 1
        if not tuple(self.pos) in ghost_positions and pacgums.pacgums.get(
            tuple(self.pos)
        ):
            if pacgums.pacgums[tuple(self.pos)] == PacgumsType.SUPER:
                self.last_edible_mode = time.time()
                for ghost in ghosts:
                    ghost.force_non_edible_respawn = False
                    ghost.ghost_is_edible_mode = True
            pacgums.on_eat(self, tuple(self.pos))

    def ghost_ai(self, maze: list[list[int]], pacman: Any) -> None:
        """Compute ghost movement using A* pathfinding.

        This method is only applicable to ghost character types. It
        computes a path towards a type-specific goal (ambush,
        rusher, random or weird) and advances the ghost along the
        first step of the path. When Pacman has recently eaten a super
        pacgum, the ghost will try to escape using a computed escape
        goal.

        Args:
            maze: The maze grid used for neighbor calculations.
            pacman: The player character instance used as the target.
        """
        if self.character_type not in [
            CharacterType.GHOST_RUSHER,
            CharacterType.GHOST_AMBUSH,
            CharacterType.GHOST_RANDOM,
            CharacterType.GHOST_WEIRD,
        ]:
            return
        if not self.is_active:
            return
        if len(self.death_path) > 0 or time.time() < self.respawn_timer:
            return
        if pacman.spectator_mode or (hasattr(pacman, "on_death")
                                     and pacman.on_death()):
            return
        target = [
            tuple(pacman.pos),
            tuple(self.find_pacman_pos(pacman.pos, pacman.direction, maze, 4)),
            tuple(self.find_random_pos(maze)),
            tuple(self.find_corner_pos(maze)),
        ]

        start = (self.pos[0], self.pos[1])
        goal = (target[self.character_type.value - 1]
                if self.character_type else target[0])
        neighbors = make_neighbors(maze)
        current_time = time.time()

        if not self.is_active:
            if len(self.death_path) > 0:
                if self.death_anim_frame % 5 == 0:
                    self.pos = list(self.death_path.pop(0))
                self.death_anim_frame += 1
            return

        if current_time - pacman.last_edible_mode <= 10.0:
            goal = compute_escape_goal(start, goal, maze, radius=5)

        path = a_star(start, goal, manhattan(goal), neighbors, distance)

        if path and len(path) > 1:
            delta_x = path[1][0] - self.pos[0]
            delta_y = path[1][1] - self.pos[1]
            if delta_x != 0 and delta_y != 0:
                if abs(delta_x) > abs(delta_y):
                    delta_y = 0
                else:
                    delta_x = 0
            self.pos[0] += delta_x
            self.pos[1] += delta_y
            if delta_y != 0:
                self.direction = (
                    CharacterDirection.TOP
                    if delta_y == -1
                    else CharacterDirection.BOTTOM
                )
            else:
                self.direction = (
                    CharacterDirection.LEFT
                    if delta_x == -1
                    else CharacterDirection.RIGHT
                )
            self.path = path
        else:
            self.path = []

    def collide(self, config: Any, maze: list[list[int]], pacman: Any,
                godmode: bool) -> bool:
        """Handle collisions between ghosts and Pacman.

        This method checks for collisions using both current and
        previous positions (to detect crossing). When a ghost collides
        with Pacman it resolves the outcome depending on whether the
        ghost is edible or the player has godmode. Edible ghosts are
        sent back to spawn following a computed death path.

        Args:
            config: Game configuration object used to read point values.
            maze: The maze grid for path computation back to spawn.
            pacman: The player character instance involved in the
                collision.
            godmode: When True the player will not lose health on
                collision.

        Returns:
            True when the collision resulted in player death, False
            otherwise.
        """
        if self.character_type not in [
            CharacterType.GHOST_RUSHER,
            CharacterType.GHOST_AMBUSH,
            CharacterType.GHOST_RANDOM,
            CharacterType.GHOST_WEIRD,
        ]:
            return False
        if not self.is_active:
            return False
        if pacman.spectator_mode:
            return False
        current_time = time.time()

        if len(self.death_path) > 0:
            self.pos = list(self.death_path.pop(0))
            if len(self.death_path) == 0:
                self.respawn_timer = current_time + 5.0
            return False

        if current_time < self.respawn_timer:
            return False
        if (self.pos[0] == pacman.pos[0] and self.pos[1] == pacman.pos[1]) or (
            (self.old_pos[0] == pacman.pos[0]
             and self.old_pos[1] == pacman.pos[1])
            and (self.pos[0] == pacman.old_pos[0]
                 and self.pos[1] == pacman.old_pos[1])
        ):
            if current_time - pacman.last_edible_mode <= 10.0:
                self.death_anim_frame = 0
                neighbors = make_neighbors(maze)
                if self.spawn:
                    result = a_star(
                        (self.pos[0], self.pos[1]),
                        self.spawn,
                        manhattan(self.spawn),
                        neighbors,
                        distance,
                    )
                    self.death_path = result if result is not None else []
                self.path = []
                pacman.score += config.get("points_per_ghost")
                self.ghost_is_edible_mode = False
                self.force_non_edible_respawn = True
                return False
            elif not godmode:
                pacman.health -= 1
                pacman.death_anim_frame = 0
                pacman.is_active = False
                return True
        return False

    def on_death(self) -> bool:
        """Return whether the character is dead or inactive.

        Returns:
            True when health is exhausted or the character is not
            active; False otherwise.
        """
        return self.health <= 0 or not self.is_active

    def update_pos(self, delta_time: float) -> None:
        """Interpolate visual position towards logical grid position.

        This function updates `vis_pos` using linear interpolation so
        that rendering appears smooth even when logic updates happen at
        a lower frequency.

        Args:
            delta_time: Time elapsed since the last frame, used to
                scale the interpolation step.
        """
        self.vis_pos[0] += (
            (self.pos[0] - self.vis_pos[0]) * self.lerp_speed * delta_time
        )
        self.vis_pos[1] += (
            (self.pos[1] - self.vis_pos[1]) * self.lerp_speed * delta_time
        )
