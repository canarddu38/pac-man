#!/usr/bin/env python3

"""Configuration handling for the Pac-man game.

This module exposes a Config object used to load and persist game
settings and per-player saves. It also defines helper exceptions and a
simple parser that reads a JSON-like configuration file while ignoring
comments.
"""

import json
from pathlib import Path
import random
import sys
from typing import Any
from pydantic import BaseModel, Field
from mazegenerator import MazeGenerator


class ParserException(Exception):
    """Exception raised when configuration parsing or validation fails.

    Attributes:
        message: Human readable description of the error.
    """

    def __init__(self, message: str) -> None:
        """Initialize the exception with an error message.

        Args:
            message: Description of the parsing error.
        """
        super().__init__(message)
        self.message = message

    def pretty_print(self) -> None:
        """Print the error message to stderr in a user-friendly format.

        The message is colored in red for visibility.
        """
        print(f"\033[31mERROR\033[0m: {self.message}", file=sys.stderr)


class Level(BaseModel):
    """Data model representing a game level.

    Attributes correspond to the pydantic fields used to validate
    level configuration loaded from the config file.
    """

    id: int = Field(...)
    name: str = Field(...)
    width: int = Field(..., ge=14, le=20)
    height: int = Field(..., ge=14, le=20)
    best_score: int = 0
    is_locked: bool = True
    is_completed: bool = False


class Config:
    """Main configuration container for the game.

    The Config object stores runtime configuration values, manages
    per-player saves and exposes helpers to generate a maze for a
    selected level.
    """

    def __init__(self, **kwargs: Any) -> None:
        """Create a new Config using provided keyword arguments.

        Unknown keys are ignored with a warning using ParserException.
        Values are validated against expected types and sensible
        defaults are applied where appropriate (for example, random
        seed generation when seed == 0).

        Args:
            **kwargs: Raw configuration values (typically from JSON).
        """
        self.data: dict[str, Any] = {
            "seed": 0,
            "level_max_time": 90,
            "highscore_filename": "scores.json",
            "levels": [Level(name="level 1", width=15, height=15, id=0)],
            "lives": 3,
            "pacgum": 42,
            "points_per_pacgum": 10,
            "points_per_ghost": 200,
            "points_per_super_pacgum": 50,
        }
        self.saves: dict[str, dict[str, Any]] = {}
        self.current_level: int | None = None
        self.multiplayer = False
        self.is_completed = False
        self.name: str = str(kwargs.get("name", "Player"))
        self.maze: list[list[int]] = []
        for key, value in kwargs.items():
            if key not in self.data:
                ParserException(f"Unknown attribute: {key} \
in json file").pretty_print()
                continue
            if key == "levels":
                if not isinstance(value, list):
                    ParserException("levels must be a list").pretty_print()
                    continue
                self.data[key] = [Level(**lvl, id=len(self.data[key]))
                                  for lvl in value]
            elif key == "highscore_filename":
                if "/" in value or ".." in value:
                    ParserException(f"Invalid path: {value}, defaults to \
{self.data['highscore_filename']}").pretty_print()
                    continue
                self.data[key] = value
            else:
                if not isinstance(value, type(self.data[key])):
                    ParserException(f"Invalid type for '{key}', expected \
{type(self.data[key]).__name__}").pretty_print()
                    continue
                if isinstance(value, int) and value < 0:
                    ParserException(
                        f"Invalid integer: {value} \
must be greater or equal to zero"
                    ).pretty_print()
                    continue
                if key == "seed":
                    if value == 0:
                        value = random.randint(0, 2147483647)
                self.data[key] = value

    def unlock_next_level(self) -> None:
        """Unlock the next level for the current player.

        This updates the in-memory saves dictionary ensuring the next
        level becomes available and initializes its save entry if
        missing.
        """
        if self.current_level is None:
            return
        idx = self.current_level + 1
        if idx > len(self.get("levels")) - 1:
            return
        level = self.get("levels")[idx]
        level.is_locked = False
        self.saves[self.name] = self.saves.get(self.name, {})
        self.saves[self.name][self.get("levels")[idx].name] = \
            self.saves[self.name].get(self.get("levels")[idx].name, {})
        self.saves[self.name][self.get("levels")[idx].name]["score"] = \
            self.saves[self.name][self.get("levels")[idx].name].get("score", 0)
        self.saves[self.name][self.get("levels")[idx].name]["is_completed"] = \
            self.saves[self.name][
                self.get("levels")[idx].name
            ].get("is_completed", False)

    def set_level(self, level_id: int) -> None:
        """Prepare maze data for the given level id.

        The MazeGenerator is used to build the maze layout which is
        stored in the Config instance for use by the game logic.

        Args:
            level_id: Index of the level to initialize.
        """
        if level_id < len(self.get("levels")):
            idx, level = level_id, self.get("levels")[level_id]
            seed = {"seed": self.get("seed")} if idx == 0 else {}
            generator = MazeGenerator(
                size=(level.width, level.height),
                perfect=False,
                entry_cell=(0, 0),
                exit_cell=(level.width - 1, level.height - 1),
                **seed,
            )
            self.maze = generator.maze
            self.current_level = idx

    def get(self, name: str) -> Any:
        """Return a configuration value by name.

        Args:
            name: The key to retrieve from the internal data mapping.

        Returns:
            The stored configuration value or None if missing.
        """
        return self.data.get(name)

    def check_is_game_completed(self) -> None:
        """Update the 'is_completed' flag based on level completion.

        Marks the overall game as completed when every configured level
        has been flagged as completed.
        """
        completed = [level for level in self.get("levels")
                     if level.is_completed]
        if len(completed) == len(self.get("levels")):
            self.is_completed = True
        else:
            self.is_completed = False

    def saves_dir(self) -> Path:
        """Return the path where save files are written.

        Ensures the parent directory exists and returns the Path to the
        JSON file used to persist player saves.
        """
        save_str = f".cache/{self.get('highscore_filename')}"
        save_path = Path(save_str)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        return save_path

    def load_saves(self) -> None:
        """Load per-player saves from disk into memory.

        The method will create an empty saves structure on failure and
        unlock the first level by default.
        """
        save_path = self.saves_dir()
        try:
            with save_path.open("r", encoding="utf-8") as f:
                self.saves = json.load(f)
                self.saves[self.name] = self.saves.get(self.name, {})
                data = self.saves.get(self.name, {})
                for id, i in enumerate(data):
                    level = next(
                        (lvl for lvl in self.get("levels") if lvl.name == i),
                        None,
                    )
                    self.saves[self.name][i]["score"] = self.saves[
                        self.name
                    ][i].get(
                        "score", 0
                    )
                    self.saves[self.name][i]["is_completed"] = self.saves[
                        self.name
                    ][i].get("is_completed", False)
                    if level:
                        level.best_score = self.saves[self.name][i]["score"]
                        level.is_locked = False
                        level.is_completed = self.saves[self.name][i][
                            "is_completed"
                        ]
                        if level.is_completed:
                            try:
                                nxt_level = self.get("levels")[id + 1]
                            except Exception:
                                nxt_level = None
                            if nxt_level:
                                nxt_level.is_locked = False
                self.check_is_game_completed()
        except Exception:
            self.saves = {}
        if len(self.get("levels")) > 0:
            self.get("levels")[0].is_locked = False

    def save_scores(self, level: int, score: int, completed: bool) -> bool:
        """Persist a player's score for a given level to disk.

        Args:
            level: Index of the level whose score should be saved.
            score: The score value to persist.
            completed: Whether the level was completed in this run.

        Returns:
            True if the save resulted in an update of persisted data,
            False if no update was necessary.
        """
        self.saves[self.name] = self.saves.get(self.name, {})
        level_obj = self.get("levels")[level]
        level_name = level_obj.name
        self.saves[self.name][level_name] = self.saves[self.name].get(
            level_name, {"score": 0, "is_completed": False}
        )
        if (
            level_name not in self.saves
            or self.saves[self.name][level_name].get("score", 0) < score
        ):
            if level_obj:
                level_obj.best_score = score
                level_obj.is_locked = False
            self.saves[self.name][level_name]["score"] = score
            if completed:
                self.saves[self.name][level_name]["is_completed"] = True
            self.check_is_game_completed()
            save_path = self.saves_dir()
            with open(save_path, "w") as f:
                json.dump(self.saves, f, indent=4)
            return True
        return False


def parser(path: str) -> Config:
    """Parse a JSON configuration file while ignoring comments.

    The parser accepts both '#' and '//' style comments at the start of
    lines and will return a Config instance built from the cleaned
    JSON content.

    Args:
        path: Filesystem path to the configuration JSON file.

    Returns:
        Config: A populated Config instance.

    Raises:
        ParserException: If the file cannot be opened or the JSON is
            invalid.
    """
    try:
        with open(path, "r") as f:
            lines = []
            for line in f:
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith("//"):
                    continue
                lines.append(line)
    except Exception:
        raise ParserException(f"Could not open file {path}")
    try:
        data = json.loads("".join(lines))
        return Config(**data)
    except Exception as e:
        raise ParserException(f"Json is not valid:\n{e}")
