"""Enumeration definitions used across the Pac-man project.

This module groups colors, level endings, directions, character types
and name templates used throughout the codebase.
"""

from enum import Enum
import pyray as pr


class Colors(Enum):
    """Common color constants used by the renderer.

    Attributes:
        LOGO (pr.Color): Color used for logo elements.
        PACGUMS (pr.Color): Color used for pacgums.
        BACKGROUND (pr.Color): Background color.
        WALL (pr.Color): Color used for walls.
        COMPLETED (pr.Color): Color used to indicate completion.
    """

    LOGO = pr.Color(19, 27, 189, 255)
    PACGUMS = pr.Color(236, 232, 58, 255)
    BACKGROUND = pr.Color(2, 4, 27, 255)
    WALL = pr.Color(0, 0, 255, 255)
    COMPLETED = pr.Color(0, 255, 0, 255)


class LevelEnding(Enum):
    """Possible outcomes when a level finishes.

    Values:
        FAILURE: The player failed the level.
        NO_TIME: The player ran out of time.
        SUCCESS: The player completed the level successfully.
    """

    FAILURE = 0
    NO_TIME = 1
    SUCCESS = 2


class Direction(Enum):
    """Cardinal directions used for general purpose logic.

    Values correspond to integers used throughout the codebase.
    """

    NORTH = 0
    EAST = 1
    SOUTH = 2
    WEST = 3


class Bit_position(Enum):
    """Bitmask values representing blocked directions in the maze.

    These values are intended to be bitwise-ANDed with maze cell data to
    determine whether movement is possible in a given direction.
    """

    NORTH = 0b0001
    EAST = 0b0010
    SOUTH = 0b0100
    WEST = 0b1000


class CharacterType(Enum):
    """Types of characters (player and ghost AI variations).

    Values:
        PLAYER: The human player character.
        GHOST_RUSHER: Ghost that rushes the player.
        GHOST_AMBUSH: Ghost that tries to ambush ahead of the player.
        GHOST_RANDOM: Ghost that moves randomly.
        GHOST_WEIRD: Ghost that cycles between corners.
    """

    PLAYER = 0
    GHOST_RUSHER = 1
    GHOST_AMBUSH = 2
    GHOST_RANDOM = 3
    GHOST_WEIRD = 4


class CharacterDirection(Enum):
    """Simplified rendering directions for character sprites.

    Values reflect directions used by the sprite system.
    """

    RIGHT = 0
    LEFT = 1
    TOP = 2
    BOTTOM = 3


class PacgumsType(Enum):
    """Types of pacgums present on the map.

    NORMAL: Regular pacgum that grants points.
    SUPER: Power-up pacgum that makes ghosts edible.
    """

    NORMAL = 0
    SUPER = 1


class NameTemplate(Enum):
    """Templates used to generate random player names.

    PREFIX and SUFFIX provide lists of strings used to assemble
    lightweight randomized names for multiplayer sessions or local
    defaults.
    """

    PREFIX = [
        "Vibe",
        "Cool",
        "ft",
        "pac-",
        "Tasty",
        "man",
        "wrapFoyer",
        "IndexOutOfRange",
        "julcleme",
        "sservant",
        "Raise",
        "alu",
        "Try",
        "Except",
        "SizeT",
        "Partition2Mathis",
        "ValueError",
        "KO",
        "Outstanding",
        "125",
        "Mbou",
        "rpetit",
    ]
    SUFFIX = [
        "Coder",
        "Crousty",
        "Ko",
        "Segfault",
        "Malloc",
        "Python-module-07-ex0",
        "Man",
        "Pac",
        "atoi",
        "itoa",
        "lstnew",
        "putendl_fd",
        "strlcat",
        "substr",
        "bzero",
        "lstadd_back",
        "lstsize",
        "putnbr_fd",
        "slu",
        "strlcpy",
        "tolower",
        "calloc",
        "lstadd_front",
        "memchr",
        "putstr_fd",
        "strlen",
        "toupper",
        "isalnum",
        "lstclear",
        "memcmp",
        "split",
        "strmapi",
        "isalpha",
        "lstdelone",
        "memcpy",
        "strchr",
        "strncmp",
        "isascii",
        "lstiter",
        "memmove",
        "strdup",
        "strnstr",
        "isdigit",
        "lstlast",
        "memset",
        "striteri",
        "strrchr",
        "isprint",
        "lstmap",
        "putchar_fd",
        "strjoin",
        "strtrim",
    ]
