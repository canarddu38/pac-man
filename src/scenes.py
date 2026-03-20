import math
import time
from config import Level, ParserException
import pyray as pr
from components import (
    Button,
    Background,
    Sprite,
    draw_rectangle_between,
    Input,
    Text,
    LeaderBoard,
)
from multiplayer import MultiPlayerPacMan
from pacgums import Pacgums
from enums import Bit_position, CharacterType, CharacterDirection, LevelEnding
from character import Character, DummyPacman
from enums import Colors, NameTemplate
import random
from typing import Any
from pathfinding import a_star, distance, make_neighbors, manhattan


class Scene:
    def __init__(self: Any, manager: Any):
        """Base scene interface.

        Args:
            manager: Graphics manager that owns this scene and global state.
        """
        self.manager = manager
        self.manager.font_custom = pr.load_font_ex(
            "resources/fonts/Square.ttf", 32, None, 250
        )

    def update(self: Any, _: pr.Vector2) -> None:
        """Update scene state.

        Subclasses should override this to react to input and advance their
        internal state. The default implementation does nothing.

        Args:
            _: Virtual mouse position (unused base signature for compatibility)
        """
        pass

    def draw(self: Any) -> None:
        """Render the scene to the screen.

        Subclasses should override to draw their content each frame.
        """
        pass


class IntroScene(Scene):
    def __init__(self, manager: Any):
        """Brief animated intro/logo scene.

        Args:
            manager: Graphics manager used for rendering and config access.
        """
        super().__init__(manager)
        self.config = manager.config
        self.intro_x = 100.0
        self.intro_frame = 0
        self.logo = Sprite(
            coords=(self.manager.screen_width // 2,
                    self.manager.screen_height // 2),
            x_anchor="center",
            y_anchor="center",
            scale_x=0.15,
            scale_y=0.15,
            texture_path="resources/textures/backgrounds/logo.png",
            screen=(self.manager.screen_width, self.manager.screen_height),
        )

    def update(self: Any, _: pr.Vector2) -> None:
        """Advance intro animation.

        Called each frame to advance the small intro animation.
        """
        self.intro_x += 12.0
        self.intro_frame += 1
        if self.intro_x > self.manager.screen_width + 100:
            self.manager.change_scene(NameScene(self.manager))

    def draw(self) -> None:
        """Draw the intro/logo and the moving mask used for the effect."""
        self.logo.draw()
        pr.draw_rectangle(
            int(self.intro_x),
            0,
            self.manager.screen_width,
            self.manager.screen_height,
            pr.BLACK,
        )

        for i in range(1, 15):
            dot_x = self.manager.screen_width * (i / 15.0)
            if dot_x > self.intro_x + 30:
                pr.draw_circle(
                    int(dot_x),
                    self.manager.screen_height // 2,
                    20,
                    Colors.PACGUMS.value,
                )

        mouth_angle = abs(math.sin(self.intro_frame * 0.15)) * 45
        pr.draw_circle_sector(
            pr.Vector2(self.intro_x, self.manager.screen_height // 2),
            60.0,
            mouth_angle,
            360 - mouth_angle,
            36,
            pr.YELLOW,
        )


class NameScene(Scene):
    def __init__(self: Any, manager: Any) -> None:
        """Scene used to input the player's name.

        Args:
            manager: Graphics manager instance.
        """
        super().__init__(manager)
        self.name = ""
        self.frames_counter = 0
        bg_texture = "resources/textures/backgrounds"
        self.background = Background(
            background_path=f"{bg_texture}/pacman_background.png",
            foreground_path=f"{bg_texture}/pacman_foreground.png",
            midground_path=f"{bg_texture}/pacman_midground.png",
            screen=(self.manager.screen_width, self.manager.screen_height),
        )

        center_x = self.manager.screen_width // 2
        center_y = self.manager.screen_height // 2
        self.title = Text(
            text="Enter your name",
            background=True,
            animation=True,
            x_anchor="center",
            y_anchor="center",
            coords=(center_x, center_y - 100),
            font=pr.load_font_ex("resources/fonts/Square.ttf", 50, None, 250),
        )
        self.input = Input(
            coords=(center_x, center_y),
            default="",
            allowed="abcdefghijklmnopqrstuvwxyz\
ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ",
            max_size=10,
            x_anchor="center",
            y_anchor="center",
            scale=1.5,
        )

        self.button = Button(
            coords=(center_x, center_y + 120),
            scale=0.7,
            x_anchor="center",
            y_anchor="center",
            sound_path="resources/sounds/buttonfx.wav",
            texture_path="resources/textures/buttons/start_button.png",
            num_frames=3,
            screen=(self.manager.screen_width, self.manager.screen_height),
        )

    def update(self, virtual_mouse: Any) -> None:
        """Handle input and advance the name entry UI.

        Args:
            virtual_mouse: Current virtual mouse coordinates/controls.
        """
        self.frames_counter += 1
        self.input.update(virtual_mouse)
        self.title.update()
        if self.input.onUpdate():
            self.name = self.input.name

        if self.button.update(virtual_mouse):
            if self.name.strip() == "":
                self.name = f"{random.choice(NameTemplate.PREFIX.value)}\
{random.choice(NameTemplate.SUFFIX.value).capitalize()}"
            self.manager.config.name = self.name
            self.manager.config.load_saves()
            self.manager.change_scene(MainMenuScene(self.manager))
            self.manager.change_scene_top(MainMenuTopScene(self.manager))

    def draw(self) -> None:
        """Render the name entry UI."""
        self.background.draw()
        panel_w = 700
        panel_h = 350
        panel_x = self.manager.screen_width // 2 - panel_w // 2
        panel_y = self.manager.screen_height // 2 - panel_h // 2

        pr.draw_rectangle(panel_x, panel_y, panel_w, panel_h,
                          pr.Color(10, 10, 15, 220))
        pr.draw_rectangle_lines_ex(
            pr.Rectangle(panel_x, panel_y, panel_w, panel_h),
            4, Colors.LOGO.value
        )
        self.input.draw()
        self.title.draw()
        self.button.draw()


class MainMenuTopScene(Scene):
    def __init__(self: Any, manager: Any) -> None:
        """Top (HUD) portion of the main menu containing leaderboard/logo."""
        super().__init__(manager)
        self.time = 0.0
        self.leaderboard = LeaderBoard(
            coords=(300, 150), saves=self.manager.config.saves
        )
        self.logo = Sprite(
            coords=(self.manager.screen_top_width,
                    self.manager.screen_top_height // 2),
            x_anchor="right",
            y_anchor="center",
            scale_x=0.15,
            scale_y=0.15,
            texture_path="resources/textures/backgrounds/logo.png",
            screen=(self.manager.screen_top_width,
                    self.manager.screen_top_height),
        )

    def update(self, _: pr.Vector2) -> None:
        """Update animated background in the top menu."""
        self.time += pr.get_frame_time()

    def draw(self) -> None:
        """Draw the top menu background and leaderboard."""
        grid_size = 60
        offset = (self.time * 30) % grid_size
        grid_color = pr.Color(20, 20, 30, 255)
        for i in range(-100, self.manager.screen_width + 100, grid_size):
            pr.draw_line(
                int(i - offset),
                0,
                int(i - offset),
                self.manager.screen_height,
                grid_color,
            )
        for i in range(-100, self.manager.screen_height + 100, grid_size):
            pr.draw_line(
                0,
                int(i - offset),
                self.manager.screen_width,
                int(i - offset),
                grid_color,
            )
        self.leaderboard.draw()
        self.logo.draw()


class MainMenuScene(Scene):
    def __init__(self: Any, manager: Any) -> None:
        """Main menu with navigation buttons to game modes and settings."""
        super().__init__(manager)
        bg_texture = "resources/textures/backgrounds"
        self.background = Background(
            background_path=f"{bg_texture}/pacman_background.png",
            foreground_path=f"{bg_texture}/pacman_foreground.png",
            midground_path=f"{bg_texture}/pacman_midground.png",
            screen=(self.manager.screen_width, self.manager.screen_height),
        )
        self.banner = Sprite(
            coords=(self.manager.screen_width // 2, 240),
            x_anchor="center",
            y_anchor="center",
            scale_x=0.25,
            scale_y=0.25,
            texture_path="resources/textures/backgrounds/banner.png",
            screen=(self.manager.screen_width, self.manager.screen_height),
        )
        self.banner_win = Sprite(
            coords=(self.manager.screen_width // 2, 240),
            x_anchor="center",
            y_anchor="center",
            scale_x=0.15,
            scale_y=0.15,
            texture_path="resources/textures/backgrounds/banner_win.png",
            screen=(self.manager.screen_width, self.manager.screen_height),
        )
        self.buttons = [
            Button(
                coords=(self.manager.screen_width // 2, 500),
                scale=0.9,
                x_anchor="center",
                y_anchor="center",
                sound_path="resources/sounds/buttonfx.wav",
                texture_path="resources/textures/buttons/singleplayer.png",
                num_frames=3,
                screen=(self.manager.screen_width, self.manager.screen_height),
            ),
            Button(
                coords=(self.manager.screen_width // 2, 650),
                scale=0.9,
                x_anchor="center",
                y_anchor="center",
                sound_path="resources/sounds/buttonfx.wav",
                texture_path="resources/textures/buttons/multiplayer.png",
                num_frames=3,
                screen=(self.manager.screen_width, self.manager.screen_height),
            ),
            Button(
                coords=(self.manager.screen_width // 2, 800),
                scale=0.9,
                x_anchor="center",
                y_anchor="center",
                sound_path="resources/sounds/buttonfx.wav",
                texture_path="resources/textures/buttons/how_to_play.png",
                num_frames=3,
                screen=(self.manager.screen_width, self.manager.screen_height),
            ),
            Button(
                coords=(self.manager.screen_width // 2, 950),
                scale=0.9,
                x_anchor="center",
                y_anchor="center",
                sound_path="resources/sounds/buttonfx.wav",
                texture_path="resources/textures/buttons/exit.png",
                num_frames=3,
                screen=(self.manager.screen_width, self.manager.screen_height),
            ),
        ]
        self.manager.history_stack = []

    def update(self, virtual_mouse: Any) -> None:
        """Handle button presses on the main menu.

        Args:
            virtual_mouse: Current virtual mouse coordinates/controls.
        """
        if self.buttons[0].update(virtual_mouse):
            self.manager.change_scene(LevelsMenuScene(self.manager))
        elif self.buttons[1].update(virtual_mouse):
            self.manager.change_scene(MultiplayerMenuScene(self.manager))
        elif self.buttons[2].update(virtual_mouse):
            self.manager.change_scene(InstructionsScene(self.manager))
        elif self.buttons[3].update(virtual_mouse):
            import sys

            sys.exit(0)
        for button in self.buttons:
            button.update(virtual_mouse)

    def draw(self) -> None:
        """Render the main menu including banner and buttons."""
        self.background.draw()
        if not self.manager.config.is_completed:
            self.banner.draw()
        else:
            self.banner_win.draw()
        for button in self.buttons:
            button.draw()


class GameTopScene(Scene):
    def __init__(self, manager: Any,
                 multiplayer: MultiPlayerPacMan | None = None) -> None:
        """Top HUD for in-game display (score, time, lives).

        Args:
            manager: Graphics manager owning scenes.
            multiplayer: Optional multiplayer manager when in a networked game.
        """
        super().__init__(manager)
        self.time = 0.0
        self.multiplayer = None
        if multiplayer:
            self.multiplayer = multiplayer
        self.is_multi = self.multiplayer is not None
        self.is_host = self.multiplayer.is_host \
            if self.multiplayer is not None else False
        self.game = self.manager.current_scene
        self.multiplayer_tag = {}
        if self.multiplayer is not None:
            for id, player in enumerate(
                [
                    x
                    for x in list(self.multiplayer.other_players.values())
                    if x["name"] != self.game.config.name
                ]
            ):
                self.multiplayer_tag[player["name"]] = Text(
                    text="",
                    text_size=30,
                    x_anchor="right",
                    y_anchor="center",
                    coords=(self.manager.screen_top_width
                            - 100, 100 + (100 * id)),
                )
        self.logo = Sprite(
            coords=(self.manager.screen_top_width,
                    self.manager.screen_top_height // 2),
            x_anchor="right",
            y_anchor="center",
            scale_x=0.15,
            scale_y=0.15,
            texture_path="resources/textures/backgrounds/logo.png",
            screen=(self.manager.screen_top_width,
                    self.manager.screen_top_height),
        )
        self.your_score_text = Text(
            text=f"Your score - {self.game.pacman.score}",
            text_size=30,
            x_anchor="left",
            y_anchor="center",
            coords=(100, self.manager.screen_top_height // 2 - 150),
        )
        self.remaining_time_text = Text(
            text=f"Remaining Time - {self.game.remaining_time:.2f}",
            text_size=30,
            x_anchor="left",
            y_anchor="center",
            coords=(100, self.manager.screen_top_height // 2 - 80),
        )
        self.remaining_health_text = Text(
            text=f"Remaining Health - {self.game.pacman.health}",
            text_size=30,
            x_anchor="left",
            y_anchor="center",
            coords=(100, self.manager.screen_top_height // 2),
        )
        level_name = (self.manager.config.get(
            "levels")[self.game.level].name if
                       not self.is_multi else self.game.level.name)
        self.current_level_text = Text(
            text=f"Current Level - {level_name}",
            text_size=30,
            x_anchor="left",
            y_anchor="center",
            coords=(100, self.manager.screen_top_height // 2 + 80),
        )

    def update(self, _: pr.Vector2) -> None:
        """Refresh displayed HUD values each frame."""
        self.time += pr.get_frame_time()
        self.your_score_text.text = f"Your score - {self.game.pacman.score}"
        self.your_score_text.refresh_text()
        self.remaining_time_text.text = (
            f"Remaining Time - {self.game.remaining_time:.2f}"
        )
        self.remaining_time_text.refresh_text()
        self.remaining_health_text.text = (
            f"Remaining Health - {self.game.pacman.health}"
        )
        self.remaining_health_text.refresh_text()
        level_name = (self.manager.config.get(
            "levels")[self.game.level].name if
                       not self.is_multi else self.game.level.name)
        self.current_level_text.text = f"Current Level - {level_name}"
        self.current_level_text.refresh_text()

    def draw(self) -> None:
        """Draw the top HUD grid and text elements."""
        grid_size = 60
        offset = (self.time * 30) % grid_size
        grid_color = pr.Color(20, 20, 30, 255)
        for i in range(-100, self.manager.screen_width + 100, grid_size):
            pr.draw_line(
                int(i - offset),
                0,
                int(i - offset),
                self.manager.screen_height,
                grid_color,
            )
        for i in range(-100, self.manager.screen_height + 100, grid_size):
            pr.draw_line(
                0,
                int(i - offset),
                self.manager.screen_width,
                int(i - offset),
                grid_color,
            )
        if not self.multiplayer:
            self.logo.draw()
        self.your_score_text.draw()
        self.remaining_time_text.draw()
        self.remaining_health_text.draw()
        self.current_level_text.draw()
        if self.is_multi:
            for id, player in enumerate(
                [
                    x
                    for x in list(self.game.multiplayer.other_players.values())
                    if x["name"] != self.game.config.name
                ]
            ):
                self.multiplayer_tag[player["name"]].text = (
                    f"{player['name']} {player.get('score', 0)}"
                )
                self.multiplayer_tag[player["name"]].refresh_text()
                self.multiplayer_tag[player["name"]].draw()


class GameScene(Scene):
    def __init__(
        self,
        manager: Any,
        multiplayer: MultiPlayerPacMan | None = None,
        health: int | None = None,
        score: int | None = None,
    ) -> None:
        """Main game scene handling game logic and rendering.

        Args:
            manager: Graphics manager instance.
            multiplayer: Optional multiplayer manager for network play.
            health: Optional health override to carry between levels.
            score: Optional score override to carry between levels.
        """
        super().__init__(manager)
        self.config = manager.config
        self.pause = False
        self.cheat = False
        self.backup_health = health
        if health is None:
            self.backup_health = self.config.get("lives")
        self.backup_score = score
        self.god_mode_ptr = False
        self.freeze_ghost_ptr = False
        self.freeze_time_ptr = False
        self.ghost_trajectory = False
        if multiplayer:
            self.level = multiplayer.level
        else:
            self.level = self.config.current_level
        self.maze = manager.config.maze
        self.last_pause_time = 0.0
        self.last_freeze_time = 0.0
        self.start_time = time.time()
        self.total_pause_time = 0.0
        self.rows = len(self.maze)
        self.cols = len(self.maze[0])
        self.cell_w = (self.manager.screen_height - 100) // self.cols
        self.cell_h = (self.manager.screen_height - 100) // self.rows
        self.center_x = self.manager.screen_width // 2
        self.center_y = self.manager.screen_height // 2
        self.wall_thickness = 5.0
        self.offset_x = int(
            self.manager.screen_width - (self.cell_w * self.cols) - (
                self.wall_thickness * (self.cols - 1)))
        self.remaining_time = 0
        self.offset_y = 50
        self.maze_w = self.cols * self.cell_w
        self.maze_h = self.rows * self.cell_h
        self.wall_color = Colors.WALL.value
        self.logo_color = Colors.LOGO.value
        self.pacgums = Pacgums(config=self.manager.config, maze=self.maze)
        self.j = 0
        self.multiplayer = None
        if multiplayer:
            self.multiplayer = multiplayer
        self.multiplayer_name: dict[str, Text] = {}
        self.is_multi = self.multiplayer is not None
        self.is_host = self.multiplayer.is_host \
            if self.multiplayer is not None else False
        menu_width = 500
        menu_height = 800
        self.cheat_menu_rect = pr.Rectangle(
            self.center_x - menu_width // 2,
            self.center_y - menu_height // 2,
            menu_width,
            menu_height,
        )
        self.dragging_cheat = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.move_timer = 0.0
        self.move_interval = 0.15
        self.anim_state = 0
        self.ghosts: list[Character] = []
        self.load_ghosts()
        self.quit_button = Button(
            coords=(self.center_x, self.center_y + 150),
            scale=0.7,
            x_anchor="center",
            y_anchor="center",
            sound_path="resources/sounds/buttonfx.wav",
            texture_path="resources/textures/buttons/exit.png",
            num_frames=3,
            screen=(self.manager.screen_width, self.manager.screen_height),
        )
        self.pause_text = Text(
            text="PAUSE",
            background=True,
            animation=True,
            text_size=200,
            x_anchor="center",
            y_anchor="center",
            colors=pr.WHITE,
            coords=(self.center_x, self.center_y - 50),
            font=pr.load_font_ex("resources/fonts/Square.ttf", 50, None, 250),
        )

    def load_char_texture(self, path: str) -> Any:
        """Load and return a scaled texture for characters.

        Args:
            path: File path to the image to load.

        Returns:
            A pyray texture object suitable for rendering characters.
        """
        try:
            with open(path, "r"):
                pass
        except Exception:
            raise ParserException(f"Could not find texture: {path}")
        img = pr.load_image(path)
        pr.image_resize(
            img,
            int(self.cell_w - 2 * self.wall_thickness),
            int(self.cell_h - 2 * self.wall_thickness),
        )
        texture = pr.load_texture_from_image(img)
        pr.unload_image(img)
        return texture

    def load_ghosts(self) -> None:
        """Instantiate ghost Character objects and the player character."""
        spawns = [
            (0, 0),
            (self.cols - 1, 0),
            (0, self.rows - 1),
            (self.cols - 1, self.rows - 1),
        ]
        ghost_type = [
            CharacterType.GHOST_WEIRD,
            CharacterType.GHOST_RANDOM,
            CharacterType.GHOST_AMBUSH,
            CharacterType.GHOST_RUSHER,
        ]
        chr_texture = "resources/textures/characters/"
        for i in range(4):
            self.ghosts.append(
                Character(
                    textures=(
                        (
                            self.load_char_texture(
                                f"{chr_texture}/ghost{i}_d0_0.png"
                            ),
                            self.load_char_texture(
                                f"{chr_texture}/ghost{i}_d0_1.png"
                            ),
                        ),
                        (
                            self.load_char_texture(
                                f"{chr_texture}/ghost{i}_d1_0.png"
                            ),
                            self.load_char_texture(
                                f"{chr_texture}/ghost{i}_d1_1.png"
                            ),
                        ),
                        (
                            self.load_char_texture(
                                f"{chr_texture}/ghost{i}_d2_0.png"
                            ),
                            self.load_char_texture(
                                f"{chr_texture}/ghost{i}_d2_1.png"
                            ),
                        ),
                        (
                            self.load_char_texture(
                                f"{chr_texture}/ghost{i}_d3_0.png"
                            ),
                            self.load_char_texture(
                                f"{chr_texture}/ghost{i}_d3_1.png"
                            ),
                        ),
                    ),
                    edible_textures=(
                        (
                            self.load_char_texture(
                                f"{chr_texture}/edible_blue0.png"
                            ),
                            self.load_char_texture(
                                f"{chr_texture}edible_blue1.png"
                            ),
                        ),
                        (
                            self.load_char_texture(
                                f"{chr_texture}/edible_white0.png"
                            ),
                            self.load_char_texture(
                                f"{chr_texture}/edible_white1.png"
                            ),
                        ),
                    ),
                    death_anim=tuple(
                        [
                            self.load_char_texture(
                                f"{chr_texture}/death{i}.png"
                            )
                            for i in range(4)
                        ]
                    ),
                    is_active=True,
                    spawn=spawns[i],
                    pos=list(spawns[i]),
                    direction=CharacterDirection.RIGHT,
                    character_type=ghost_type[i],
                )
            )
        spawn = [self.cols // 2, self.rows // 2]
        if self.cols % 2 == 0:
            spawn[0] -= 1
        self.pacman = Character(
            manager=self.manager,
            textures=(
                (
                    self.load_char_texture(
                        f"{chr_texture}/pacman_d0_0.png"
                    ),
                    self.load_char_texture(
                        f"{chr_texture}/pacman_d0_1.png"
                    ),
                ),
                (
                    self.load_char_texture(
                        f"{chr_texture}/pacman_d1_0.png"
                    ),
                    self.load_char_texture(
                        f"{chr_texture}/pacman_d1_1.png"
                    ),
                ),
                (
                    self.load_char_texture(
                        f"{chr_texture}/pacman_d2_0.png"
                    ),
                    self.load_char_texture(
                        f"{chr_texture}/pacman_d2_1.png"
                    ),
                ),
                (
                    self.load_char_texture(
                        f"{chr_texture}/pacman_d3_0.png"
                    ),
                    self.load_char_texture(
                        f"{chr_texture}/pacman_d3_1.png"
                    ),
                ),
            ),
            death_anim=tuple(
                [
                    self.load_char_texture(
                        f"{chr_texture}/pacman_death{i}.png"
                    )
                    for i in range(11)
                ]
            ),
            is_active=True,
            spawn=(spawn[0], spawn[1]),
            pos=[spawn[0], spawn[1]],
            direction=CharacterDirection.RIGHT,
            name=self.manager.config.name,
            character_type=CharacterType.PLAYER,
        )
        if type(self.backup_score) is int:
            self.pacman.score = self.backup_score
        if type(self.backup_health) is int:
            self.pacman.health = self.backup_health

    def draw_pause(self) -> None:
        """Draw the pause overlay and quit button."""
        pr.draw_rectangle(
            0,
            0,
            self.manager.screen_width,
            self.manager.screen_height,
            pr.Color(0, 0, 0, 150),
        )
        self.quit_button.draw()
        self.pause_text.draw()

    def draw_cheat(self) -> None:
        """Render the cheat/debug menu when active."""
        if self.is_multi and not self.is_host:
            return

        pr.draw_rectangle(
            0,
            0,
            self.manager.screen_width,
            self.manager.screen_height,
            pr.Color(0, 0, 0, 150),
        )

        mouse_pos = self.manager.get_virtual_mouse_position()

        pr.draw_rectangle_rec(self.cheat_menu_rect, pr.RAYWHITE)
        pr.draw_rectangle_lines_ex(self.cheat_menu_rect, 2, pr.DARKGRAY)
        title_bar_height = 40
        title_bar_rect = pr.Rectangle(
            self.cheat_menu_rect.x,
            self.cheat_menu_rect.y,
            self.cheat_menu_rect.width,
            title_bar_height,
        )

        pr.draw_rectangle_rec(title_bar_rect, pr.LIGHTGRAY)
        pr.draw_rectangle_lines_ex(title_bar_rect, 2, pr.DARKGRAY)
        pr.draw_text("Cheat Menu", int(self.cheat_menu_rect.x + 10),
                     int(self.cheat_menu_rect.y + 10), 20, pr.BLACK)
        if pr.check_collision_point_rec(mouse_pos, title_bar_rect):
            if pr.is_mouse_button_pressed(pr.MouseButton.MOUSE_BUTTON_LEFT):
                self.dragging_cheat = True

                self.drag_offset_x = -mouse_pos.x - self.cheat_menu_rect.x
                self.drag_offset_y = mouse_pos.y - self.cheat_menu_rect.y

        if self.dragging_cheat:
            if pr.is_mouse_button_down(pr.MouseButton.MOUSE_BUTTON_LEFT):
                if -mouse_pos.x - self.drag_offset_x \
                    < self.manager.screen_width - self.cheat_menu_rect.width \
                        and -mouse_pos.x - self.drag_offset_x > 0:
                    self.cheat_menu_rect.x = -mouse_pos.x - self.drag_offset_x
                if mouse_pos.y - self.drag_offset_y > 0 \
                        and (
                            mouse_pos.y - self.drag_offset_y
                            + self.cheat_menu_rect.height) \
                        < self.manager.screen_height:
                    self.cheat_menu_rect.y = mouse_pos.y - self.drag_offset_y
            else:
                self.dragging_cheat = False

        def draw_custom_button(rect: Any, text: str) -> bool:
            hover = pr.check_collision_point_rec(mouse_pos, pr.Rectangle(
                self.manager.screen_width - rect.x - rect.width, rect.y,
                rect.width, rect.height))
            clicked = hover and pr.is_mouse_button_released(
                pr.MouseButton.MOUSE_BUTTON_LEFT)
            if hover:
                bg_color = pr.DARKGRAY if pr.is_mouse_button_down(
                    pr.MouseButton.MOUSE_BUTTON_LEFT) else pr.GRAY
            else:
                bg_color = pr.LIGHTGRAY
            pr.draw_rectangle_rec(rect, bg_color)
            pr.draw_rectangle_lines_ex(rect, 2, pr.BLACK)
            text_width = pr.measure_text(text, 20)
            text_x = int(rect.x + (rect.width - text_width) / 2)
            text_y = int(rect.y + (rect.height - 20) / 2)
            pr.draw_text(text, text_x, text_y, 20, pr.BLACK)

            return clicked

        def draw_custom_checkbox(rect: Any, text: str, ptr: bool) -> bool:
            hover = pr.check_collision_point_rec(mouse_pos, pr.Rectangle(
                self.manager.screen_width - rect.x - rect.width, rect.y,
                rect.width, rect.height))
            if hover and pr.is_mouse_button_released(
                 pr.MouseButton.MOUSE_BUTTON_LEFT):
                ptr = not ptr

            pr.draw_rectangle_rec(rect, pr.LIGHTGRAY)
            pr.draw_rectangle_lines_ex(rect, 2, pr.BLACK)
            if ptr:
                inner_rect = pr.Rectangle(rect.x + 4, rect.y + 4,
                                          rect.width - 8, rect.height - 8)
                pr.draw_rectangle_rec(inner_rect, pr.BLACK)
            pr.draw_text(text, int(rect.x + rect.width + 10), int(rect.y), 20,
                         pr.BLACK)
            return ptr

        button_x = self.cheat_menu_rect.x + 50
        menu_y = self.cheat_menu_rect.y
        button_width = 400
        button_height = 65
        spacing = 90

        if draw_custom_button(pr.Rectangle(button_x, menu_y + 40, button_width,
                              button_height), "+1000 Points"):
            self.pacman.score += 1000

        if draw_custom_button(pr.Rectangle(button_x, menu_y + 40 + spacing,
                              button_width, button_height), "+1 Health"):
            self.pacman.health += 1

        if draw_custom_button(pr.Rectangle(button_x, menu_y + 40 + spacing * 2,
                              button_width, button_height), "Kill All Ghosts"):
            for ghost in self.ghosts:
                ghost.respawn_timer = time.time() + 10.0
                self.ghost_is_edible_mode = False
                self.force_non_edible_respawn = True
                self.death_anim_frame = 0
                neighbors = make_neighbors(self.maze)
                self.death_path = a_star(
                    (ghost.pos[0], ghost.pos[1]),
                    ghost.spawn if ghost.spawn else (0, 0),
                    manhattan(ghost.spawn if ghost.spawn else (0, 0)),
                    neighbors,
                    distance,
                )

        if draw_custom_button(pr.Rectangle(button_x, menu_y + 40 + spacing * 3,
                              button_width, button_height), "Instant Win"):
            self.pacgums.pacgums.clear()

        self.god_mode_ptr = draw_custom_checkbox(pr.Rectangle(button_x,
                                                 menu_y + 40 + spacing * 4,
                                                 65, 65),
                                                 "God Mode (Invincible)",
                                                 self.god_mode_ptr)
        self.freeze_ghost_ptr = draw_custom_checkbox(pr.Rectangle(button_x,
                                                     menu_y + 40 + spacing * 5,
                                                     65, 65), "Freeze ghost",
                                                     self.freeze_ghost_ptr)
        self.ghost_trajectory = draw_custom_checkbox(pr.Rectangle(button_x,
                                                     menu_y + 40 + spacing * 6,
                                                     65, 65),
                                                     "Trajectory ghost",
                                                     self.ghost_trajectory)
        self.freeze_time_ptr = draw_custom_checkbox(pr.Rectangle(button_x,
                                                    menu_y + 40 + spacing * 7,
                                                    65, 65), "Freeze time",
                                                    self.freeze_time_ptr)

    def update(self, virtual_mouse: Any) -> None:
        """Main update loop for the game scene, advances time, movement and AI.

        Args:
            virtual_mouse: Current virtual mouse coordinates/controls.
        """
        delta_time = pr.get_frame_time()
        self.frame = 0
        if not self.is_multi:
            current_time = time.time()

            if self.pause:
                if getattr(self, "last_pause_time", 0) == 0:
                    self.last_pause_time = current_time
                else:
                    self.total_pause_time += current_time \
                        - self.last_pause_time
                    self.last_pause_time = current_time
            else:
                self.last_pause_time = 0
        elif self.is_host:
            current_time = time.time()

            if self.freeze_time_ptr:
                if getattr(self, "last_freeze_time", 0) == 0:
                    self.last_freeze_time = current_time
                else:
                    self.total_pause_time += current_time \
                        - self.last_freeze_time
                    self.last_freeze_time = current_time
            else:
                self.last_freeze_time = 0

        if self.pause and not self.cheat:
            self.pause_text.update()
            if self.quit_button.update(virtual_mouse):
                self.manager.go_back()
        if self.is_multi:
            if self.multiplayer:
                self.multiplayer.update_network()
            if self.multiplayer and not self.is_host and getattr(
                    self.multiplayer, "connected", False):
                for i, gs in enumerate(self.multiplayer.ghost_states):
                    if i < len(self.ghosts):
                        self.ghosts[i].pos = gs["pos"]
                        self.ghosts[i].direction = CharacterDirection(
                            gs["dir"]
                        )
                        self.ghosts[i].is_active = gs["active"]
                        self.ghosts[i].ghost_is_edible_mode = gs["edible"]
            for p_id, p_state in getattr(self.multiplayer,
                                         "other_players", {}).items():
                pos = p_state.get("pos")
                if pos and tuple(pos) in self.pacgums.pacgums:
                    self.pacgums.pacgums.pop(tuple(pos), None)

        for ghost in self.ghosts:
            if self.pacman.on_death() and not self.pacman.spectator_mode:
                if not self.is_multi:
                    ghost.is_active = False
            elif not self.pacman.spectator_mode:
                ghost.collide(self.config, self.maze, self.pacman,
                              self.god_mode_ptr)
            if self.multiplayer and self.is_multi and self.is_host:
                for p_id, p_state in self.multiplayer.other_players.items():
                    if (
                        ghost.is_active
                        and p_state.get("active", False)
                        and p_state.get("health", 3) > 0
                    ):
                        p_pos = p_state.get("pos", (0, 0))
                        if (ghost.pos[0] == p_pos[0]
                                and ghost.pos[1] == p_pos[1]):
                            if ghost.ghost_is_edible_mode:
                                ghost.is_active = False
        if not self.pause or self.is_multi:
            self.pacman.control_movement()
            self.move_timer += delta_time
        if self.move_timer >= self.move_interval and (self.is_multi or
                                                      not self.pause):
            self.move_timer -= self.move_interval
            self.pacman.move_loop(self.maze, self.ghosts, self.pacgums)
            if (not self.is_multi or self.is_host) and len(
                self.pacgums.pacgums.keys()
            ) == 0:
                if self.multiplayer and self.is_multi:
                    self.multiplayer.send_to_clients(
                        {"type": "event", "data": "Ending.SUCCESS"}
                    )
                else:
                    self.config.unlock_next_level()
                self.manager.change_scene(
                    DeathScreenScene(
                        self.manager,
                        LevelEnding.SUCCESS,
                        self.pacman,
                        self.manager.config.save_scores(
                            self.manager.config.current_level,
                            self.pacman.score,
                            False,
                        ),
                        self.is_multi,
                    )
                )
            self.anim_state = 1 if self.anim_state == 0 else 0
            if not self.is_multi or self.is_host:
                for ghost in self.ghosts:
                    closest_pacman: Character | DummyPacman = self.pacman
                    if self.is_multi and self.multiplayer:
                        min_dist = float("inf")
                        max_edible = self.pacman.last_edible_mode
                        if (self.pacman.is_active and
                                not self.pacman.on_death()):
                            min_dist = abs(ghost.pos[0] - self.pacman.pos[0])
                            + abs(
                                ghost.pos[1] - self.pacman.pos[1]
                            )
                        for (
                            p_id,
                            p_state,
                        ) in self.multiplayer.other_players.items():
                            p_spec = p_state.get("spectator_mode", True)
                            if p_state.get("edible_time", 0) > max_edible:
                                max_edible = p_state.get("edible_time", 0)
                            if (
                                p_state.get("active", False)
                                and p_state.get("health", 3) > 0
                            ):
                                p_pos = p_state.get("pos", (0, 0))
                                dist = abs(ghost.pos[0] - p_pos[0]) + abs(
                                    ghost.pos[1] - p_pos[1]
                                )
                                if dist < min_dist and not p_spec:
                                    min_dist = dist
                                    closest_pacman = DummyPacman(p_pos,
                                                                 max_edible)
                        if isinstance(closest_pacman, self.pacman.__class__):
                            closest_pacman.last_edible_mode = max_edible
                        elif hasattr(closest_pacman, "last_edible_mode"):
                            closest_pacman.last_edible_mode = max_edible
                    ghost.old_pos = list(ghost.pos)
                    if (
                        not self.freeze_ghost_ptr
                        and not closest_pacman.spectator_mode
                        and self.frame % 2 == 0
                    ):
                        ghost.ghost_ai(self.maze, closest_pacman)
        self.frame += 1

        for ghost in self.ghosts:
            ghost.update_pos(delta_time)
        self.pacman.update_pos(delta_time)
        if self.multiplayer and self.is_multi:
            self.multiplayer.send_state(self)

    def _draw_maze_lines(self, thickness: float, color: pr.Color) -> None:
        """Draw maze grid lines with the requested thickness and color.

        Args:
            thickness: Line thickness in pixels.
            color: pyray Color object used to draw the lines.
        """
        half_t = thickness / 2.0
        for r in range(self.rows):
            for c in range(self.cols):
                cell = self.maze[r][c]
                x = c * self.cell_w + self.offset_x
                y = r * self.cell_h + self.offset_y

                if cell & Bit_position.NORTH.value:
                    pr.draw_line_ex(
                        pr.Vector2(x, y),
                        pr.Vector2(x + self.cell_w, y),
                        thickness,
                        color,
                    )
                    pr.draw_circle(int(x), int(y), half_t, color)
                    pr.draw_circle(int(x + self.cell_w), int(y), half_t, color)

                if cell & Bit_position.SOUTH.value:
                    pr.draw_line_ex(
                        pr.Vector2(x, y + self.cell_h),
                        pr.Vector2(x + self.cell_w, y + self.cell_h),
                        thickness,
                        color,
                    )
                    pr.draw_circle(int(x), int(y + self.cell_h), half_t, color)
                    pr.draw_circle(
                        int(x + self.cell_w),
                        int(y + self.cell_h),
                        half_t,
                        color,
                    )

                if cell & Bit_position.WEST.value:
                    pr.draw_line_ex(
                        pr.Vector2(x, y),
                        pr.Vector2(x, y + self.cell_h),
                        thickness,
                        color,
                    )
                    pr.draw_circle(int(x), int(y), half_t, color)
                    pr.draw_circle(int(x), int(y + self.cell_h), half_t, color)

                if cell & Bit_position.EAST.value:
                    pr.draw_line_ex(
                        pr.Vector2(x + self.cell_w, y),
                        pr.Vector2(x + self.cell_w, y + self.cell_h),
                        thickness,
                        color,
                    )
                    pr.draw_circle(int(x + self.cell_w), int(y), half_t, color)
                    pr.draw_circle(
                        int(x + self.cell_w),
                        int(y + self.cell_h),
                        half_t,
                        color,
                    )

    def draw(self) -> None:
        """Render the entire game world, characters and UI."""
        if (self.multiplayer and self.is_multi and not self.is_host
                and hasattr(self.multiplayer, "time")):
            self.remaining_time = self.multiplayer.time
        else:
            active_pause = 0.0
            if (
                getattr(self, "pause", False)
                and getattr(self, "last_pause_time", 0) != 0
            ):
                active_pause = time.time() - self.last_pause_time
            self.remaining_time = self.config.get("level_max_time") - (
                time.time() - self.start_time
                - self.total_pause_time - active_pause
            )
        if self.remaining_time <= 0:
            if self.multiplayer and self.is_multi and self.is_host:
                self.multiplayer.send_to_clients(
                    {"type": "event", "data": "Ending.NO_TIME"}
                )
            self.manager.change_scene(
                DeathScreenScene(
                    self.manager,
                    LevelEnding.NO_TIME,
                    self.pacman,
                    self.manager.config.save_scores(
                        self.manager.config.current_level,
                        self.pacman.score,
                        False,
                    ),
                    self.is_multi,
                )
            )
        outer_thickness = self.wall_thickness * 2.5
        inner_thickness = self.wall_thickness * 1.5
        self._draw_maze_lines(outer_thickness, self.wall_color)
        self._draw_maze_lines(inner_thickness, pr.BLACK)
        for r in range(self.rows):
            for c in range(self.cols):
                cell = self.maze[r][c]
                x = c * self.cell_w + self.offset_x
                y = r * self.cell_h + self.offset_y
                if cell == 15:
                    draw_rectangle_between(
                        (x, y),
                        (x + self.cell_w, y + self.cell_h),
                        self.logo_color,
                    )
                if self.pacgums.pacgums.get((c, r)):
                    self.pacgums.draw_pacgum(
                        c, r, x + self.cell_w // 2, y + self.cell_h // 2
                    )

        for ghost in self.ghosts:
            current_time = time.time()
            if not ghost.direction:
                ghost.direction = CharacterDirection.TOP
            if not ghost.textures or not ghost.death_anim:
                continue
            if (ghost.death_anim and
                    ghost.is_active and ghost.respawn_timer >= current_time):
                texture = ghost.death_anim[ghost.direction.value]
            else:
                texture = ghost.textures[ghost.direction.value][
                    self.anim_state
                ]
                if current_time - self.pacman.last_edible_mode <= 10.0:
                    if not ghost.force_non_edible_respawn:
                        ghost.ghost_is_edible_mode = True
                else:
                    ghost.force_non_edible_respawn = False
                    ghost.ghost_is_edible_mode = False
                if ghost.ghost_is_edible_mode and ghost.edible_textures:
                    if (7 <= current_time - self.pacman.last_edible_mode
                            and current_time - self.pacman.last_edible_mode
                            <= 10):
                        texture = ghost.edible_textures[1][self.anim_state]
                    else:
                        texture = ghost.edible_textures[0][self.anim_state]
            if (
                self.ghost_trajectory
                and ghost.path is not None
                and len(ghost.death_path) == 0
            ):
                for i, value in enumerate(ghost.path[:-1]):
                    pr.draw_line_ex(
                        pr.Vector2(
                            int(
                                value[0] * self.cell_w
                                + self.wall_thickness
                                + self.offset_x
                                + self.cell_w // 2
                            ),
                            int(
                                value[1] * self.cell_h
                                + self.wall_thickness
                                + self.offset_y
                                + self.cell_h // 2
                            ),
                        ),
                        pr.Vector2(
                            int(
                                ghost.path[i + 1][0] * self.cell_w
                                + self.wall_thickness
                                + self.offset_x
                                + self.cell_w // 2
                            ),
                            int(
                                ghost.path[i + 1][1] * self.cell_h
                                + self.wall_thickness
                                + self.offset_y
                                + self.cell_h // 2
                            ),
                        ),
                        3.0,
                        pr.WHITE,
                    )
            pr.draw_texture(
                texture,
                int(
                    ghost.vis_pos[0] * self.cell_w
                    + self.wall_thickness + self.offset_x
                ),
                int(
                    ghost.vis_pos[1] * self.cell_h
                    + self.wall_thickness + self.offset_y
                ),
                pr.WHITE,
            )

        if self.multiplayer and self.pacman.textures:
            for p_id, p_state in self.multiplayer.other_players.items():
                if (
                    not p_state.get("active", True)
                    or p_state.get("name", "") == self.config.name
                ):
                    continue
                dir_val = p_state.get("dir", 0)
                if p_id not in self.multiplayer_name.keys():
                    self.multiplayer_name[p_id] = Text(
                        text=p_state.get("name", "test"),
                        text_size=12,
                        x_anchor="center",
                        y_anchor="center",
                        coords=(100, 100),
                    )
                self.multiplayer_name[p_id].change_coords(
                    (
                        int(
                            p_state["pos"][0] * self.cell_w
                            + self.wall_thickness
                            + self.offset_x
                            + (self.cell_w / 2)
                        ),
                        int(
                            p_state["pos"][1] * self.cell_h
                            + self.wall_thickness
                            + self.offset_y
                            - 20
                        ),
                    )
                )
                self.multiplayer_name[p_id].draw()
                p_texture = self.pacman.textures[dir_val][self.anim_state]
                if p_state.get("health", 3) <= 0 and self.pacman.death_anim:
                    death_frame = p_state.get("death_frame", 0)
                    p_texture = self.pacman.death_anim[
                        death_frame % len(self.pacman.death_anim)
                    ]
                pr.draw_texture(
                    p_texture,
                    int(
                        p_state["pos"][0] * self.cell_w
                        + self.wall_thickness
                        + self.offset_x
                    ),
                    int(
                        p_state["pos"][1] * self.cell_h
                        + self.wall_thickness
                        + self.offset_y
                    ),
                    pr.WHITE,
                )
        if not self.pacman.textures:
            self.pacman.textures = ((0, 0), (0, 0), (0, 0), (0, 0))
        texture = self.pacman.textures[
            self.pacman.direction.value if self.pacman.direction else 0
        ][
            self.anim_state
        ]
        if self.pacman.on_death() and not self.pacman.spectator_mode \
                and self.pacman.death_anim:
            texture = self.pacman.death_anim[
                self.pacman.death_anim_frame % len(self.pacman.death_anim)
            ]
            if self.pacman.death_anim_frame \
                    >= len(list(self.pacman.death_anim)) - 1:
                if self.pacman.health <= 0:
                    if self.is_multi:
                        self.pacman.spectator_mode = True
                    else:
                        self.manager.change_scene(
                            DeathScreenScene(
                                self.manager,
                                LevelEnding.FAILURE,
                                self.pacman,
                                self.manager.config.save_scores(
                                    self.manager.config.current_level,
                                    self.pacman.score,
                                    False,
                                ),
                            )
                        )
                        return
                else:
                    for ghost in [self.pacman] + self.ghosts:
                        ghost.respawn()
            else:
                self.pacman.death_anim_frame += 1

        if not self.pacman.spectator_mode:
            pr.draw_texture(
                texture,
                int(
                    self.pacman.vis_pos[0] * self.cell_w
                    + self.wall_thickness
                    + self.offset_x
                ),
                int(
                    self.pacman.vis_pos[1] * self.cell_h
                    + self.wall_thickness
                    + self.offset_y
                ),
                pr.WHITE,
            )

        if self.pause and not self.cheat:
            self.draw_pause()

        if self.cheat:
            self.draw_cheat()


class DeathScreenScene(Scene):
    def __init__(
        self, manager: Any, ending_type: LevelEnding,
        pacman: Character,
        state: bool,
        is_multiplayer: bool = False
    ) -> None:
        """Display the end-of-level or game-over screen.

        Args:
            manager: Graphics manager instance.
            ending_type: What type of ending occurred (success, failure).
            pacman: Player Character instance (to display score/health).
            state: Whether a new high score was reached.
            is_multiplayer: Whether this was a multiplayer end.
        """
        super().__init__(manager)
        self.manager.font_custom = pr.load_font_ex(
            "resources/fonts/Square.ttf", 32, None, 250
        )
        self.pacman = pacman
        self.state = state
        self.time = 0.0
        self.is_multiplayer = is_multiplayer
        center_x = self.manager.screen_width // 2
        center_y = self.manager.screen_height // 2

        self.ending_type = ending_type
        last_level_idx = len(self.manager.config.get("levels")) - 1

        if ending_type == LevelEnding.FAILURE:
            message = ("YOU ARE DEAD", pr.RED)
        elif ending_type == LevelEnding.NO_TIME:
            message = ("RAN OUT OF TIME", pr.RED)
        else:
            current_level = self.manager.config.current_level
            if current_level == last_level_idx or self.is_multiplayer:
                message = ("GAME FINISHED!", pr.YELLOW)
            else:
                message = ("LEVEL FINISHED!", pr.GREEN)

        self.respawn_button = Button(
            coords=(center_x, center_y + 50),
            scale=0.7,
            x_anchor="center",
            y_anchor="center",
            sound_path="resources/sounds/buttonfx.wav",
            texture_path="resources/textures/buttons/"
            + (
                "respawn.png"
                if ending_type in [LevelEnding.FAILURE, LevelEnding.NO_TIME]
                else "start_button.png"
            ),
            num_frames=3,
            screen=(self.manager.screen_width, self.manager.screen_height),
        )
        self.quit_button = Button(
            coords=(center_x, center_y + 150),
            scale=0.7,
            x_anchor="center",
            y_anchor="center",
            sound_path="resources/sounds/buttonfx.wav",
            texture_path="resources/textures/buttons/exit.png",
            num_frames=3,
            screen=(self.manager.screen_width, self.manager.screen_height),
        )
        self.you_are_dead = Text(
            text=message[0],
            font=self.manager.font_custom,
            x_anchor="center",
            y_anchor="center",
            coords=(center_x, center_y // 2),
            colors=message[1],
            text_size=100,
            animation=True,
            animation_speed=5,
        )
        self.score_text = Text(
            text=f"Score - {self.pacman.score}",
            font=self.manager.font_custom,
            x_anchor="center",
            y_anchor="center",
            coords=(center_x, center_y // 2 + 100),
            colors=pr.RAYWHITE,
            text_size=40,
        )
        self.best_score_text = Text(
            text="The new best score",
            font=self.manager.font_custom,
            x_anchor="center",
            y_anchor="center",
            coords=(center_x, center_y // 2 + 150),
            colors=pr.GREEN,
            text_size=40,
        )

    def update(self, virtual_mouse: Any) -> None:
        """Handle button presses on the death/level complete screen."""
        self.time += pr.get_frame_time()
        self.you_are_dead.frames_counter += 1
        self.score_text.frames_counter += 1
        if not self.is_multiplayer \
                and self.respawn_button.update(virtual_mouse):
            current_level = self.manager.history_stack[-1].level
            next_level = current_level
            try:
                if self.ending_type == LevelEnding.SUCCESS:
                    next_level += 1
                self.manager.config.set_level(next_level)
                self.manager.change_scene(GameScene(
                    self.manager,
                    score=(self.pacman.score
                           if self.ending_type == LevelEnding.SUCCESS
                           else None),
                    health=(self.pacman.health
                            if self.ending_type == LevelEnding.SUCCESS
                            else None)
                ))
                self.manager.change_scene_top(GameTopScene(self.manager))
            except Exception as e:
                raise Exception(f"Unknown loaded level: \
{next_level}, {e.args[0]}")
        if self.quit_button.update(virtual_mouse):
            self.manager.change_scene(MainMenuScene(self.manager))
            self.manager.change_scene_top(MainMenuTopScene(self.manager))

    def draw(self) -> None:
        """Render the death screen and associated UI elements."""
        grid_size = 60
        offset = (self.time * 30) % grid_size
        grid_color = pr.Color(20, 20, 30, 255)
        for i in range(-100, self.manager.screen_width + 100, grid_size):
            pr.draw_line(
                int(i - offset),
                0,
                int(i - offset),
                self.manager.screen_height,
                grid_color,
            )
        for i in range(-100, self.manager.screen_height + 100, grid_size):
            pr.draw_line(
                0,
                int(i - offset),
                self.manager.screen_width,
                int(i - offset),
                grid_color,
            )
        if (self.you_are_dead.text != "GAME FINISHED!"
                and not self.is_multiplayer):
            self.respawn_button.draw()
        self.quit_button.draw()
        self.you_are_dead.draw()
        self.score_text.draw()
        if self.state:
            self.best_score_text.draw()


class InstructionsScene(Scene):
    def __init__(self: Any, manager: Any) -> None:
        """A static scene showing controls and rules for the game."""
        super().__init__(manager)
        self.manager.font_custom = pr.load_font_ex(
            "resources/fonts/Square.ttf", 32, None, 250
        )
        self.time = 0.0
        center_x = self.manager.screen_width // 2
        center_y = self.manager.screen_height // 2

        self.title = Text(
            text="INSTRUCTIONS",
            font=self.manager.font_custom,
            x_anchor="center",
            y_anchor="center",
            coords=(center_x, center_y // 4),
            colors=pr.WHITE,
            text_size=70,
        )
        self.rules_subtitle = Text(
            text="Rules :",
            font=self.manager.font_custom,
            x_anchor="center",
            y_anchor="center",
            coords=(center_x, center_y // 2 - 50),
            colors=pr.WHITE,
            text_size=30,
        )
        self.rules = Text(
            text="Your goal is to eat all the pacgums without \
getting killed by the ghosts.",
            font=self.manager.font_custom,
            x_anchor="center",
            y_anchor="center",
            coords=(center_x, center_y // 2),
            colors=pr.WHITE,
            text_size=30,
        )
        self.controles_subtitle = Text(
            text="Controles :",
            font=self.manager.font_custom,
            x_anchor="center",
            y_anchor="center",
            coords=(center_x, center_y // 2 + 50),
            colors=pr.WHITE,
            text_size=30,
        )
        self.arrow_up = Sprite(
            coords=(100 + 2, center_y - 150),
            x_anchor="center",
            y_anchor="center",
            scale_x=1.0,
            scale_y=1.0,
            texture_path="resources/textures/keys/arrow-up_white.png",
            screen=(self.manager.screen_width, self.manager.screen_height),
        )
        self.w_up = Sprite(
            coords=(180, center_y - 150),
            x_anchor="center",
            y_anchor="center",
            scale_x=1.0,
            scale_y=1.0,
            texture_path="resources/textures/keys/w_white.png",
            screen=(self.manager.screen_width, self.manager.screen_height),
        )
        self.text_up = Text(
            text="To move upwards you can press W or the arrow key.",
            font=self.manager.font_custom,
            x_anchor="left",
            y_anchor="center",
            coords=(230, center_y - 150),
            colors=pr.WHITE,
            text_size=25,
        )
        self.arrow_down = Sprite(
            coords=(100, center_y - 80),
            x_anchor="center",
            y_anchor="center",
            scale_x=1.0,
            scale_y=1.0,
            texture_path="resources/textures/keys/arrow-down_white.png",
            screen=(self.manager.screen_width, self.manager.screen_height),
        )
        self.s_down = Sprite(
            coords=(180, center_y - 80),
            x_anchor="center",
            y_anchor="center",
            scale_x=1.0,
            scale_y=1.0,
            texture_path="resources/textures/keys/s_white.png",
            screen=(self.manager.screen_width, self.manager.screen_height),
        )
        self.text_down = Text(
            text="To move downwards you can press S or the down arrow key.",
            font=self.manager.font_custom,
            x_anchor="left",
            y_anchor="center",
            coords=(230, center_y - 80),
            colors=pr.WHITE,
            text_size=25,
        )
        self.arrow_left = Sprite(
            coords=(100, center_y - 10),
            x_anchor="center",
            y_anchor="center",
            scale_x=1.0,
            scale_y=1.0,
            texture_path="resources/textures/keys/arrow-left_white.png",
            screen=(self.manager.screen_width, self.manager.screen_height),
        )
        self.a_left = Sprite(
            coords=(180, center_y - 10),
            x_anchor="center",
            y_anchor="center",
            scale_x=1.0,
            scale_y=1.0,
            texture_path="resources/textures/keys/a_white.png",
            screen=(self.manager.screen_width, self.manager.screen_height),
        )
        self.text_left = Text(
            text="To move left you can press A or the left arrow key.",
            font=self.manager.font_custom,
            x_anchor="left",
            y_anchor="center",
            coords=(230, center_y - 10),
            colors=pr.WHITE,
            text_size=25,
        )
        self.arrow_right = Sprite(
            coords=(100, center_y + 60),
            x_anchor="center",
            y_anchor="center",
            scale_x=1.0,
            scale_y=1.0,
            texture_path="resources/textures/keys/arrow-right_white.png",
            screen=(self.manager.screen_width, self.manager.screen_height),
        )
        self.d_right = Sprite(
            coords=(180, center_y + 60),
            x_anchor="center",
            y_anchor="center",
            scale_x=1.0,
            scale_y=1.0,
            texture_path="resources/textures/keys/d_white.png",
            screen=(self.manager.screen_width, self.manager.screen_height),
        )
        self.text_right = Text(
            text="To move right you can press D or the right arrow key.",
            font=self.manager.font_custom,
            x_anchor="left",
            y_anchor="center",
            coords=(230, center_y + 60),
            colors=pr.WHITE,
            text_size=25,
        )
        self.exit_button = Button(
            coords=(self.manager.screen_width // 2,
                    self.manager.screen_height - 300),
            scale=0.9,
            x_anchor="center",
            y_anchor="center",
            sound_path="resources/sounds/buttonfx.wav",
            texture_path="resources/textures/buttons/exit.png",
            num_frames=3,
            screen=(self.manager.screen_width, self.manager.screen_height),
        )

    def update(self, virtual_mouse: Any) -> None:
        """Allow the instructions scene to respond to navigation input."""
        self.time += pr.get_frame_time()
        if self.exit_button.update(virtual_mouse):
            self.manager.change_scene(MainMenuScene(self.manager))
            self.manager.change_scene_top(MainMenuTopScene(self.manager))

    def draw(self) -> None:
        """Draw the instructions text and key sprites."""
        grid_size = 60
        offset = (self.time * 30) % grid_size
        grid_color = pr.Color(20, 20, 30, 255)
        for i in range(-100, self.manager.screen_width + 100, grid_size):
            pr.draw_line(
                int(i - offset),
                0,
                int(i - offset),
                self.manager.screen_height,
                grid_color,
            )
        for i in range(-100, self.manager.screen_height + 100, grid_size):
            pr.draw_line(
                0,
                int(i - offset),
                self.manager.screen_width,
                int(i - offset),
                grid_color,
            )
        self.title.draw()
        self.rules_subtitle.draw()
        self.rules.draw()
        self.controles_subtitle.draw()
        self.arrow_up.draw()
        self.w_up.draw()
        self.text_up.draw()
        self.arrow_down.draw()
        self.s_down.draw()
        self.arrow_left.draw()
        self.a_left.draw()
        self.d_right.draw()
        self.arrow_right.draw()
        self.text_down.draw()
        self.text_left.draw()
        self.text_right.draw()
        self.exit_button.draw()


class MultiplayerWaitingScene(Scene):
    def __init__(self, manager: Any, ip: str, level: Level | None) -> None:
        """Waiting room for multiplayer: shows connected players and status.

        Args:
            manager: Graphics manager instance.
            ip: Host IP string (empty if hosting locally).
            level: Optional Level object when joining a host.
        """
        super().__init__(manager)
        self.manager = manager
        self.ip = ip
        self.is_host = ip == ""
        self.level = level
        self.init_state = False
        self.multiplayer = MultiPlayerPacMan(
            manager=self.manager, is_host=self.is_host, level=level, ip=ip
        )
        self.time = 0.0
        self.center_x = self.manager.screen_width // 2
        self.center_y = self.manager.screen_height // 2

        self.title = Text(
            text="Waiting For Players",
            x_anchor="center",
            y_anchor="center",
            coords=(self.center_x, self.center_y - 250),
            colors=pr.GOLD,
            font=pr.load_font_ex("resources/fonts/Square.ttf", 50, None, 250),
        )

        self.host = Text(
            text=f"Host: {'Me' if self.is_host else self.ip}",
            x_anchor="center",
            colors=pr.SKYBLUE,
            y_anchor="center",
            coords=(self.center_x, self.center_y - 190),
            font=pr.load_font_ex("resources/fonts/Square.ttf", 20, None, 250),
        )

        self.play = Button(
            coords=(self.center_x, self.center_y + 200),
            scale=0.7,
            x_anchor="center",
            y_anchor="center",
            sound_path="resources/sounds/buttonfx.wav",
            texture_path="resources/textures/buttons/start_button.png",
            num_frames=3,
            screen=(self.manager.screen_width, self.manager.screen_height),
        )

    def draw(self) -> None:
        """Render the waiting UI including connected players list."""
        grid_size = 60
        offset = (self.time * 30) % grid_size
        grid_color = pr.Color(10, 15, 40, 255)

        for i in range(-100, self.manager.screen_width + 100, grid_size):
            pr.draw_line(
                int(i - offset),
                0,
                int(i - offset),
                self.manager.screen_height,
                grid_color,
            )
        for i in range(-100, self.manager.screen_height + 100, grid_size):
            pr.draw_line(
                0,
                int(i - offset),
                self.manager.screen_width,
                int(i - offset),
                grid_color,
            )

        if getattr(self.multiplayer, "connection_failed", False):
            self.title.text = "Connection Failed!"
            self.title.colors = pr.RED
            self.title.refresh_text()
        else:
            dot_count = int(self.time * 3) % 4
            self.title.text = "Waiting For Players" + "." * dot_count
            pulse_alpha = int(200 + 55 * math.sin(self.time * 4))
            self.title.colors = pr.Color(255, 203, 0, pulse_alpha)
            self.title.refresh_text()

        self.title.draw()
        self.host.draw()
        panel_width = 350
        panel_height = 250
        panel_x = self.center_x - panel_width // 2
        panel_y = self.center_y - 140

        pr.draw_rectangle(
            panel_x,
            panel_y,
            panel_width,
            panel_height,
            pr.Color(15, 15, 20, 220),
        )
        pr.draw_rectangle_lines_ex(
            pr.Rectangle(panel_x, panel_y, panel_width, panel_height),
            2,
            pr.SKYBLUE,
        )

        t_header = "CONNECTED PLAYERS"
        header_width = pr.measure_text(t_header, 20)
        pr.draw_text(
            t_header,
            self.center_x - header_width // 2,
            panel_y + 15,
            20,
            pr.RAYWHITE,
        )
        pr.draw_line(
            panel_x + 20,
            panel_y + 45,
            panel_x + panel_width - 20,
            panel_y + 45,
            pr.SKYBLUE,
        )
        players = [{"name": self.manager.config.name}] + [
            player
            for player in list(self.multiplayer.other_players.values())
            if player["name"] != self.manager.config.name
        ]
        for id, player in enumerate(players):
            p_name = f"{player.get('name', f'Player {id + 1}')}"
            p_width = pr.measure_text(p_name, 20)
            p_color = pr.YELLOW if id == 0 else pr.RAYWHITE

            pr.draw_text(
                p_name,
                self.center_x - p_width // 2,
                panel_y + 60 + (id * 30),
                20,
                p_color,
            )

        if self.is_host and len(self.multiplayer.other_players.keys()) >= 1:
            self.play.draw()

        if not self.init_state and self.multiplayer.connected:
            self.multiplayer.send_state(None, True)
            self.init_state = True

        if not self.is_host and self.multiplayer.level:
            self.manager.config.data["levels"] = [self.multiplayer.level]
            self.manager.config.set_level(0)
            self.manager.change_scene(
                GameScene(self.manager, multiplayer=self.multiplayer)
            )
            self.manager.change_scene_top(
                GameTopScene(self.manager, multiplayer=self.multiplayer)
            )

        self.multiplayer.update_network()

    def update(self, virtual_mouse: Any) -> None:
        """Process input (start button) and monitor network updates."""
        self.time += pr.get_frame_time()
        if self.play.update(virtual_mouse):
            self.multiplayer.start_game()
            self.manager.config.set_level(0)
            self.manager.change_scene(
                GameScene(self.manager, multiplayer=self.multiplayer)
            )
            self.manager.change_scene_top(
                GameTopScene(self.manager, multiplayer=self.multiplayer)
            )


class MultiplayerMenuScene(Scene):
    def __init__(self: Any, manager: Any) -> None:
        """Menu used to input an IP address or start hosting a game."""
        super().__init__(manager)
        self.ip_address = ""
        bg_path = "resources/textures/backgrounds"
        self.background = Background(
            background_path=f"{bg_path}/pacman_background.png",
            foreground_path=f"{bg_path}/pacman_foreground.png",
            midground_path=f"{bg_path}/pacman_midground.png",
            screen=(self.manager.screen_width, self.manager.screen_height),
        )

        center_x = self.manager.screen_width // 2
        center_y = self.manager.screen_height // 2
        self.center_y = center_y
        self.ip_input = Input(
            coords=(center_x, center_y - 40),
            default="127.0.0.1",
            allowed="abcdefghijklmnopqrstuvwxyz\
ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.",
            max_size=15,
            x_anchor="center",
            y_anchor="center",
            scale=1.2,
        )

        self.connect_button = Button(
            coords=(center_x, center_y + 50),
            scale=0.7,
            x_anchor="center",
            y_anchor="center",
            sound_path="resources/sounds/buttonfx.wav",
            texture_path="resources/textures/buttons/connect.png",
            num_frames=3,
            screen=(self.manager.screen_width, self.manager.screen_height),
        )

        self.host_button = Button(
            coords=(center_x, center_y + 130),
            scale=0.7,
            x_anchor="center",
            y_anchor="center",
            sound_path="resources/sounds/buttonfx.wav",
            texture_path="resources/textures/buttons/host.png",
            num_frames=3,
            screen=(self.manager.screen_width, self.manager.screen_height),
        )

    def update(self, virtual_mouse: Any) -> None:
        """Handle connect/host button presses on the multiplayer menu."""
        self.ip_input.update(virtual_mouse)
        if self.ip_input.onUpdate():
            self.ip_address = self.ip_input.name

        if self.connect_button.update(virtual_mouse):
            ip_to_connect = self.ip_input.name
            print(f"Connection to IP : {ip_to_connect}")
            self.manager.change_scene(
                MultiplayerWaitingScene(self.manager,
                                        ip=ip_to_connect,
                                        level=None)
            )

        if self.host_button.update(virtual_mouse) and len(
             self.manager.config.data["levels"]) > 0:
            print("Hosting a game...")
            self.manager.change_scene(
                MultiplayerWaitingScene(
                    self.manager,
                    ip="",
                    level=self.manager.config.data["levels"][0],
                )
            )

    def draw(self) -> None:
        """Draw the multiplayer connection UI."""
        self.background.draw()
        panel_w = 600
        panel_h = 450
        panel_x = self.manager.screen_width // 2 - panel_w // 2
        panel_y = self.manager.screen_height // 2 - panel_h // 2

        pr.draw_rectangle(panel_x, panel_y, panel_w, panel_h,
                          pr.Color(10, 10, 15, 220))
        pr.draw_rectangle_lines_ex(
            pr.Rectangle(panel_x, panel_y, panel_w, panel_h),
            4,
            Colors.LOGO.value,
        )

        title = "MULTIPLAYER"
        font_size = 50
        text_w = pr.measure_text(title, font_size)
        pr.draw_text(
            title,
            self.manager.screen_width // 2 - text_w // 2,
            panel_y + 30,
            font_size,
            Colors.LOGO.value,
        )

        label = "HOST IP ADDRESS:"
        label_size = 20
        label_w = pr.measure_text(label, label_size)
        pr.draw_text(
            label,
            self.manager.screen_width // 2 - label_w // 2,
            self.center_y - 90,
            label_size,
            pr.RAYWHITE,
        )

        self.ip_input.draw()
        self.connect_button.draw()
        self.host_button.draw()


class LevelsMenuScene(Scene):
    def __init__(self: Any, manager: Any) -> None:
        """Scene that lists available levels for singleplayer play."""
        super().__init__(manager)

        self.levels = manager.config.data["levels"]
        self.selected_index = 0
        self.levels_count = len(self.levels)
        self.time = 0.0
        self.card_base_w = 320
        self.card_base_h = 450
        self.spacing = 80

    def update(self: Any, _: pr.Vector2) -> None:
        """Update level selection UI (keyboard/controller handling)."""
        self.time += pr.get_frame_time()
        if self.levels_count > 0 and pr.is_key_pressed(
             pr.KeyboardKey.KEY_RIGHT):
            self.selected_index = (self.selected_index + 1) % len(self.levels)
        elif self.levels_count > 0 and pr.is_key_pressed(
             pr.KeyboardKey.KEY_LEFT):
            self.selected_index = (self.selected_index - 1) % len(self.levels)

        if (
            self.levels_count > 0 and
            pr.is_key_pressed(pr.KeyboardKey.KEY_ENTER)
            or pr.is_key_pressed(pr.KeyboardKey.KEY_SPACE)
        ) and not self.levels[self.selected_index].is_locked:
            self.manager.config.set_level(self.selected_index)
            self.manager.change_scene(GameScene(self.manager))
            self.manager.change_scene_top(GameTopScene(self.manager))

    def draw(self) -> None:
        """Render the levels selection grid and UI controls."""
        pr.clear_background(Colors.BACKGROUND.value)
        grid_size = 60
        offset = (self.time * 30) % grid_size
        grid_color = pr.Color(20, 20, 30, 255)
        for i in range(-100, self.manager.screen_width + 100, grid_size):
            pr.draw_line(
                int(i - offset),
                0,
                int(i - offset),
                self.manager.screen_height,
                grid_color,
            )
        for i in range(-100, self.manager.screen_height + 100, grid_size):
            pr.draw_line(
                0,
                int(i - offset),
                self.manager.screen_width,
                int(i - offset),
                grid_color,
            )
        title = "SELECT THE LEVEL"
        font_size = 50
        text_w = pr.measure_text(title, font_size)
        pr.draw_text(
            title,
            self.manager.screen_width // 2 - text_w // 2 + 4,
            264,
            font_size,
            pr.Color(0, 0, 0, 150),
        )
        pr.draw_text(
            title,
            self.manager.screen_width // 2 - text_w // 2,
            260,
            font_size,
            pr.WHITE,
        )
        center_x = self.manager.screen_width // 2
        center_y = self.manager.screen_height // 2 + 30
        for i, level in enumerate(self.levels):
            diff = i - self.selected_index
            card_x = center_x + diff * (self.card_base_w + self.spacing)
            if (
                card_x < -self.card_base_w
                or card_x > self.manager.screen_width + self.card_base_w
            ):
                continue

            is_selected = i == self.selected_index
            scale = 1.0 if is_selected else 0.5
            current_w = int(self.card_base_w * scale)
            current_h = int(self.card_base_h * scale)
            y_offset = 0

            draw_x = int(card_x - current_w // 2)
            draw_y = int(center_y - current_h // 2) + y_offset
            lvl_color = (
                Colors.WALL.value if not level.is_completed
                else Colors.COMPLETED.value
            )
            pr.draw_rectangle(
                draw_x, draw_y, current_w, current_h, pr.Color(10, 10, 15, 240)
            )
            if is_selected:
                pulse = (math.sin(self.time * 6) + 1) / 2
                alpha_glow = int(100 + 155 * pulse)
                glow_color = pr.Color(lvl_color.r,
                                      lvl_color.g,
                                      lvl_color.b,
                                      alpha_glow)
                pr.draw_rectangle_lines_ex(
                    pr.Rectangle(
                        draw_x - 6, draw_y - 6, current_w + 12, current_h + 12
                    ),
                    6,
                    pr.Color(lvl_color.r, lvl_color.g, lvl_color.b,
                             alpha_glow // 4),
                )
                pr.draw_rectangle_lines_ex(
                    pr.Rectangle(draw_x - 2, draw_y - 2, current_w + 4,
                                 current_h + 4),
                    2,
                    glow_color,
                )
                border_thick = 4
                text_color = pr.WHITE
            else:
                border_thick = 2
                lvl_color = pr.Color(lvl_color.r,
                                     lvl_color.g,
                                     lvl_color.b,
                                     100)
                text_color = pr.GRAY
            pr.draw_rectangle_lines_ex(
                pr.Rectangle(draw_x, draw_y, current_w, current_h),
                border_thick,
                lvl_color,
            )

            maze_pad = int(25 * scale)
            maze_y_start = draw_y + int(70 * scale)
            maze_h = current_h - int(140 * scale)

            pr.draw_rectangle_lines_ex(
                pr.Rectangle(
                    draw_x + maze_pad,
                    maze_y_start,
                    current_w - maze_pad * 2,
                    maze_h,
                ),
                2,
                pr.Color(lvl_color.r, lvl_color.g, lvl_color.b, 150),
            )

            for r in range(4):
                for c in range(6):
                    px = (
                        draw_x
                        + maze_pad
                        + int((current_w - maze_pad * 2) * (c + 0.5) / 6)
                    )
                    py = maze_y_start + int(maze_h * (r + 0.5) / 4)
                    pr.draw_circle(
                        px,
                        py,
                        int(3 * scale),
                        pr.Color(240, 240, 200, 255 if is_selected else 100),
                    )

            name = level.name
            font_s = int(32 * scale)
            nw = pr.measure_text(name, font_s)
            pr.draw_text(
                name,
                draw_x + current_w // 2 - nw // 2,
                draw_y + int(20 * scale),
                font_s,
                text_color,
            )

            score_text = (
                f"SCORE MAX: {level.best_score}" if not level.is_locked
                else "LOCKED"
            )
            font_s_small = int(18 * scale)
            sw = pr.measure_text(score_text, font_s_small)
            pr.draw_text(
                score_text,
                draw_x + current_w // 2 - sw // 2,
                draw_y + current_h - int(45 * scale),
                font_s_small,
                pr.WHITE if not level.is_locked else pr.DARKGRAY,
            )
