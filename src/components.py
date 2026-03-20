"""UI components used by the game.

This module contains small UI building blocks such as buttons,
text rendering helpers and simple input widgets. Each public class
and function includes a Google-style docstring for maintainability.
"""

from pydantic import BaseModel, Field
from typing import Any, Literal
from enums import Colors
import pyray as pr
import math

from config import ParserException


def load_texture(path: str) -> Any:
    """Load a texture using pyray with a file existence check.

    Args:
        path: Filesystem path to the texture file.

    Returns:
        A pyray texture object loaded from the provided path.

    Raises:
        ParserException: When the texture file cannot be found or
            opened.
    """
    try:
        with open(path, "r"):
            pass
    except Exception:
        raise ParserException(f"Could not find texture: {path}")
    return pr.load_texture(path)


class Button(BaseModel):
    """Interactive button widget with optional click sound.

    The Button class wraps texture, sound and hitbox information and
    provides methods to update its state using the mouse and to draw
    itself on screen.
    """
    state: int = 0
    coords: tuple[int, int] = (0, 0)
    x_anchor: Literal["left", "center", "right"] = "left"
    y_anchor: Literal["top", "center", "bottom"] = "top"
    screen: tuple[int, int] = (0, 0)
    action: bool = False
    scale: float = 1.0
    color: Any = pr.WHITE
    texture_path: str = Field(...)
    sound_path: str = Field(...)
    num_frames: int = 0
    texture: Any = None
    sound: Any = None
    frameHeight: int | float | None = None
    sourceRec: Any = None
    bounds: Any = None

    def model_post_init(self, __context: Any) -> None:
        """Load sound and texture resources and compute bounds.

        Args:
            __context: Unused pydantic context parameter required by the
                model hook signature.
        """
        self.sound = pr.load_sound(self.sound_path)
        self.texture = load_texture(self.texture_path)
        self.frameHeight = self.texture.height / max(self.num_frames, 1)
        base_w = float(self.texture.width)
        base_h = self.frameHeight
        scaled_w = base_w * self.scale
        scaled_h = base_h * self.scale

        offset_x: int | float = 0
        if self.x_anchor == "center":
            offset_x = scaled_w // 2.0
        elif self.x_anchor == "right":
            offset_x = scaled_w

        offset_y: int | float = 0
        if self.y_anchor == "center":
            offset_y = scaled_h // 2.0
        elif self.y_anchor == "bottom":
            offset_y = scaled_h

        self.sourceRec = pr.Rectangle(0, 0, base_w, base_h)
        self.bounds = pr.Rectangle(
            self.coords[0] - offset_x,
            self.coords[1] - offset_y,
            scaled_w,
            scaled_h,
        )

    def update(self, virtual_mouse: pr.Vector2) -> bool:
        """Update button state and check for clicks.

        Args:
            virtual_mouse: Current mouse coordinates used for hit
                testing.

        Returns:
            True when the button was clicked during this update.
        """
        self.action = False
        if pr.check_collision_point_rec(virtual_mouse, self.bounds):
            if pr.is_mouse_button_down(pr.MouseButton.MOUSE_BUTTON_LEFT):
                self.state = 2 if self.num_frames == 3 else 1
            else:
                self.state = 1
            if pr.is_mouse_button_released(pr.MouseButton.MOUSE_BUTTON_LEFT):
                self.action = True
        else:
            self.state = 0

        if self.action:
            pr.play_sound(self.sound)
        return self.action

    def draw(self) -> None:
        """Render the button using pyray draw calls.

        The source rectangle is adjusted according to the button state
        and the texture is drawn using draw_texture_pro.
        """
        if self.sourceRec is None:
            return
        self.sourceRec.y = self.state * (self.frameHeight if self.frameHeight
                                         else 0)
        pr.draw_texture_pro(
            self.texture,
            self.sourceRec,
            self.bounds,
            pr.Vector2(0, 0),
            0.0,
            self.color,
        )


class Text(BaseModel):
    """Simple text rendering helper wrapping pyray font measurements.

    Provides convenience methods to update positioning when the text
    content changes and to draw text with optional typewriter
    animation.
    """
    text: str = Field(...)
    text_size: int = 50
    coords: tuple[int, int] = (0, 0)
    colors: Any = Colors.PACGUMS.value
    background: bool = False
    background_color: Any = pr.Color(255, 255, 255, 180)
    x_anchor: Literal["left", "center", "right"] = "left"
    y_anchor: Literal["top", "center", "bottom"] = "top"
    animation: bool = False
    animation_speed: int = 5
    frames_counter: int = 0
    x: float = 0.0
    y: float = 0.0
    text_size_vec: Any = None
    text_w: float = 0.0
    text_h: float = 0.0
    font: Any = None
    spacing: float = 2.0

    def _update_positions(self) -> None:
        """Recompute pixel coordinates according to anchoring.

        This internal helper is used by the model_post_init and refresh
        methods to keep `x` and `y` in sync with the anchor options.
        """
        if self.x_anchor == "center":
            self.x = self.coords[0] - (self.text_w / 2.0)
        elif self.x_anchor == "right":
            self.x = self.coords[0] - self.text_w
        else:
            self.x = self.coords[0]

        if self.y_anchor == "center":
            self.y = self.coords[1] - (self.text_h / 2.0)
        elif self.y_anchor == "bottom":
            self.y = self.coords[1] - self.text_h
        else:
            self.y = self.coords[1]

    def model_post_init(self, __context: Any) -> None:
        """Initialize font metrics and compute initial positioning.

        Args:
            __context: Unused pydantic context parameter required by the
                model hook signature.
        """
        if self.font is None:
            self.font = pr.get_font_default()

        self.text_size_vec = pr.measure_text_ex(
            self.font, self.text, float(self.text_size), self.spacing
        )
        self.text_w, self.text_h = self.text_size_vec.x, self.text_size_vec.y
        self._update_positions()

    def change_coords(self, coords: tuple[int, int]) -> None:
        """Change the anchor coordinates and refresh internal layout.

        Args:
            coords: New (x, y) coordinates for the text anchor.
        """
        self.coords = coords
        self._update_positions()

    def refresh_text(self) -> None:
        """Re-measure text metrics and update positioning.

        Use this after mutating the `text` or `text_size` fields so the
        displayed coordinates are accurate.
        """
        self.text_size_vec = pr.measure_text_ex(
            self.font, self.text, float(self.text_size), self.spacing
        )
        self.text_w, self.text_h = self.text_size_vec.x, self.text_size_vec.y
        self._update_positions()

    def update(self) -> None:
        """Advance internal animation counters.

        When `animation` is True this method increments the frame
        counter used to display progressively more characters.
        """
        if self.animation:
            self.frames_counter += 1

    def draw(self) -> None:
        """Draw the text to the screen with optional background.

        When `animation` is enabled the text is rendered using a
        typewriter effect determined by `frames_counter` and
        `animation_speed`.
        """
        if self.animation:
            chars_to_show = self.frames_counter // self.animation_speed
            display_text = pr.text_subtext(self.text, 0, chars_to_show)
        else:
            display_text = self.text
        if self.background:
            pr.draw_text_ex(
                self.font,
                display_text,
                pr.Vector2(self.x + 4, self.y + 4),
                float(self.text_size),
                self.spacing,
                self.background_color,
            )
        pr.draw_text_ex(
            self.font,
            display_text,
            pr.Vector2(self.x, self.y),
            float(self.text_size),
            self.spacing,
            self.colors,
        )


class Sprite(BaseModel):
    """A simple 2D sprite wrapper for images with anchor support.

    The Sprite class loads a texture and provides drawing helpers that
    take into account anchors and scaling.
    """
    texture_path: str = Field(...)
    texture: Any = None
    screen: tuple[int, int] = (0, 0)
    coords: tuple[int, int] = (0, 0)
    x_anchor: Literal["left", "center", "right"] = "left"
    y_anchor: Literal["top", "center", "bottom"] = "top"
    scale_x: float = 1.0
    scale_y: float = 1.0
    offset_x: float = 0.0
    offset_y: float = 0.0
    rotation: float = 0.0

    def refresh_anchor(self) -> None:
        """Recompute anchor offsets based on current texture and scale.

        This should be called whenever the scale or texture changes so
        drawing anchors remain correct.
        """
        display_w = float(self.texture.width) * self.scale_x
        display_h = float(self.texture.height) * self.scale_y

        if self.x_anchor == "center":
            self.offset_x = display_w / 2.0
        elif self.x_anchor == "right":
            self.offset_x = display_w
        if self.y_anchor == "center":
            self.offset_y = display_h / 2.0
        elif self.y_anchor == "bottom":
            self.offset_y = display_h

    def model_post_init(self, __context: Any) -> None:
        """Load the texture and initialize anchor offsets.

        Args:
            __context: Unused pydantic context parameter required by the
                model hook signature.
        """
        self.texture = load_texture(self.texture_path)
        self.refresh_anchor()

    def draw(self) -> None:
        """Render the sprite using pyray's model drawing helper."""
        source_rec = pr.Rectangle(
            0.0, 0.0, float(self.texture.width), float(self.texture.height)
        )
        dest_rec = pr.Rectangle(
            float(self.coords[0]),
            float(self.coords[1]),
            float(self.texture.width) * self.scale_x,
            float(self.texture.height) * self.scale_y,
        )
        origin = pr.Vector2(self.offset_x, self.offset_y)
        pr.draw_texture_pro(
            self.texture, source_rec, dest_rec, origin, self.rotation, pr.WHITE
        )

    def apply_rotation(self, rotation: float) -> None:
        """Apply a rotation value to the sprite that will be used when
        drawing.
        """
        self.rotation = rotation

    def set_tilt(self, rotation_angle: float,
                 squash_factor: float = 1.0) -> None:
        """Tilt the sprite by applying rotation and vertical scaling.

        Args:
            rotation_angle: Rotation in degrees to apply around the
                sprite center.
            squash_factor: Vertical scaling applied to simulate tilt.
        """
        self.rotation = rotation_angle
        self.scale_y = squash_factor
        self.refresh_anchor()


class LeaderBoard(BaseModel):
    """Simple leaderboard display populated from saved scores."""
    saves: Any = Field(...)
    count: int = 10
    total: list[tuple[str, int]] = []
    coords: tuple[int, int] = (0, 0)
    texts: list[Text] = []
    text_size: int = 20
    title: Text | None = None

    def model_post_init(self, __context: Any) -> None:
        """Prepare the title and entries using provided saves."""
        self.title = Text(
            text="LEADERBOARD - TOP 10",
            text_size=self.text_size,
            x_anchor="center",
            y_anchor="center",
            colors=pr.WHITE,
            coords=(self.coords[0], self.coords[1]),
            font=pr.load_font_ex("resources/fonts/Square.ttf", 50, None, 250),
        )
        for i in range(self.count):
            self.texts.append(
                Text(
                    text="",
                    text_size=self.text_size,
                    x_anchor="center",
                    y_anchor="center",
                    colors=pr.WHITE,
                    coords=(
                        self.coords[0],
                        self.coords[1] + (self.text_size * (i + 1)),
                    ),
                    font=pr.load_font_ex("resources/fonts/Square.ttf", 50,
                                         None, 250),
                )
            )
        total = [
            (name, sum(v.get("score", 0) for v in i.values()))
            for name, i in self.saves.items()
        ]
        total = sorted(total, key=lambda x: x[1], reverse=True)
        total = [value for id, value in enumerate(total) if id < 10]
        for id, value in enumerate(total):
            self.texts[id].text = f"{value[0]} - {value[1]}"
            self.texts[id].refresh_text()

    def draw(self) -> None:
        """Draw leaderboard entries and title to screen."""
        for i in self.texts:
            i.draw()
        if self.title:
            self.title.draw()


class Model(BaseModel):
    """3D model wrapper used in menu scenes for interactive items."""
    model: Any = Field(...)
    coords: Any = Field(...)
    visual_coords: Any = None
    scale: Any = Field(...)
    rotation: float = 0.0
    rotation_axe: Any = Field(...)
    bounds: Any = None
    action: bool = False
    state: int = 0

    def model_post_init(self, __context: Any) -> None:
        """Compute bounding box and initial visual coordinates."""
        self.visual_coords = pr.Vector3(self.coords.x,
                                        self.coords.y,
                                        self.coords.z)
        bbox = pr.get_model_bounding_box(self.model)
        bbox.min = pr.vector3_add(pr.vector3_scale(bbox.min, self.scale.x),
                                  self.coords)
        bbox.max = pr.vector3_add(pr.vector3_scale(bbox.max, self.scale.x),
                                  self.coords)
        self.bounds = bbox

    def set_tilt(self, rot_x: float, rot_y: float, rot_z: float) -> None:
        """Apply a tilt transformation to the underlying 3D model.

        Args:
            rot_x: Rotation around the X axis in degrees.
            rot_y: Rotation around the Y axis in degrees.
            rot_z: Rotation around the Z axis in degrees.
        """
        mat_turn: Any = pr.matrix_rotate_y(math.radians(rot_y))
        mat_tilt_x: Any = pr.matrix_rotate_x(math.radians(rot_x))
        mat_tilt_z: Any = pr.matrix_rotate_z(math.radians(rot_z))

        mat_tilt: Any = pr.matrix_multiply(mat_tilt_x, mat_tilt_z)
        self.model.transform = pr.matrix_multiply(mat_tilt, mat_turn)

    def update(self, camera: Any) -> bool:
        """Update model visual state based on mouse interaction.

        Performs a raycast against the model bounding box and updates
        `visual_coords` to slightly lift the model when hovered. Returns
        True when the model was clicked during this update.
        """
        self.action = False
        mouse_pos = pr.get_mouse_position()
        ray = pr.get_screen_to_world_ray(mouse_pos, camera)
        collision: Any = pr.get_ray_collision_box(ray, self.bounds)
        if collision.hit:
            self.visual_coords = pr.Vector3(
                self.coords.x, self.coords.y - 0.001, self.coords.z
            )
            if pr.is_mouse_button_down(pr.MouseButton.MOUSE_BUTTON_LEFT):
                self.state = 2
            else:
                self.state = 1
            if pr.is_mouse_button_released(pr.MouseButton.MOUSE_BUTTON_LEFT):
                self.action = True
        else:
            if self.state != 0:
                self.visual_coords = pr.Vector3(
                    self.coords.x, self.coords.y, self.coords.z
                )
            self.state = 0
        return self.action

    def draw(self) -> None:
        """Draw the 3D model to the screen using pyray."""
        pr.draw_model_ex(
            self.model,
            self.visual_coords,
            self.rotation_axe,
            self.rotation,
            self.scale,
            pr.WHITE,
        )


class Input(BaseModel):
    """Keyboard input widget for text entry used in menus.

    The Input widget tracks focus, cursor state and enforces a limited
    character set. It is intentionally lightweight and used only in
    menus where a simple name entry is required.
    """
    name: str = ""
    default: str = Field(...)
    max_size: int = Field(...)
    screen: tuple[int, int] = (0, 0)
    coords: tuple[int, int] = (0, 0)
    allowed: str = "abcdefghijklmnopqrstuvwxyz\
ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 "
    x_anchor: Literal["left", "center", "right"] = "left"
    y_anchor: Literal["top", "center", "bottom"] = "top"
    mouse_on_text: bool = False
    write: bool = False
    scale: float = 1.0
    letter_count: int = 0
    offset_x: float = 0.0
    frames_counter: int = 0
    offset_y: float = 0.0
    text_box: Any = None

    def model_post_init(self, __context: Any) -> None:
        """Initialize visual metrics and the hitbox for entry."""
        self.letter_count = len(self.default)
        self.name = self.default
        width = pr.measure_text("a" * self.max_size, 40) + 8
        display_w = float(width) * self.scale
        display_h = float(50) * self.scale
        if self.x_anchor == "center":
            self.offset_x = display_w / 2.0
        elif self.x_anchor == "right":
            self.offset_x = display_w
        if self.y_anchor == "center":
            self.offset_y = display_h / 2.0
        elif self.y_anchor == "bottom":
            self.offset_y = display_h
        self.text_box = pr.Rectangle(
            self.coords[0] - self.offset_x,
            self.coords[1] - self.offset_y,
            display_w,
            display_h,
        )

    def onUpdate(self) -> bool:
        """Return whether the widget is currently accepting input."""
        return self.write

    def update(self, virtual_mouse: pr.Vector2) -> None:
        """Update focus state based on the virtual mouse position.

        This toggles `mouse_on_text` according to whether the virtual
        mouse is hovering the input box so the caller can manage
        focus and keyboard events.
        """
        if pr.check_collision_point_rec(virtual_mouse, self.text_box):
            self.mouse_on_text = True
        else:
            self.mouse_on_text = False
        if self.mouse_on_text:
            self.write = False
            pr.set_mouse_cursor(pr.MouseCursor.MOUSE_CURSOR_IBEAM)
            key = pr.get_char_pressed()
            while key > 0:
                if (
                    (key >= 32)
                    and (key <= 125)
                    and (self.letter_count < self.max_size)
                    and chr(key) in self.allowed
                ):
                    self.name += chr(key)
                    self.letter_count += 1
                    self.write = True

                key = pr.get_char_pressed()

            if pr.is_key_pressed(pr.KeyboardKey.KEY_BACKSPACE):
                self.write = True
                self.name = self.name[:-1]
                self.letter_count -= 1
                if self.letter_count < 0:
                    self.letter_count = 0
        else:
            pr.set_mouse_cursor(pr.MouseCursor.MOUSE_CURSOR_DEFAULT)

        if self.mouse_on_text:
            self.frames_counter += 1
        else:
            self.frames_counter = 0

    def draw(self) -> None:
        pr.draw_rectangle_rec(self.text_box, pr.LIGHTGRAY)
        if self.mouse_on_text:
            pr.draw_rectangle_lines(
                int(self.text_box.x),
                int(self.text_box.y),
                int(self.text_box.width),
                int(self.text_box.height),
                Colors.WALL.value,
            )
        else:
            pr.draw_rectangle_lines(
                int(self.text_box.x),
                int(self.text_box.y),
                int(self.text_box.width),
                int(self.text_box.height),
                pr.DARKGRAY,
            )

        pr.draw_text(
            self.name,
            int(self.text_box.x) + 5,
            int(self.text_box.y) + 8,
            int(40 * self.scale),
            pr.BLACK,
        )

        if self.mouse_on_text:
            if self.letter_count < self.max_size:
                if ((self.frames_counter // 20) % 2) == 0:
                    pr.draw_text(
                        "_",
                        int(self.text_box.x)
                        + 8
                        + pr.measure_text(self.name, int(40 * self.scale)),
                        int(self.text_box.y) + 12,
                        int(40 * self.scale),
                        Colors.WALL.value,
                    )


def draw_rectangle_between(a: tuple[int, int], b: tuple[int, int],
                           color: pr.Color) -> None:
    a_x, a_y = a
    b_x, b_y = b
    x = min(a_x, b_x)
    y = min(a_y, b_y)
    w = abs(
        b_x - a_x,
    )
    h = abs(b_y - a_y)

    pr.draw_rectangle(int(x), int(y), int(w), int(h), color)


class Background(BaseModel):
    """Background, midground and foreground layers for parallax effect.

    The Background class handles loading multiple texture layers and
    scrolling them at different speeds to create a sense of depth.
    """
    background_path: str = Field(...)
    midground_path: str = Field(...)
    foreground_path: str = Field(...)
    screen: tuple[int, int] = (0, 0)
    background: Any = None
    midground: Any = None
    foreground: Any = None
    scrollingBack: float = 0.0
    scrollingMid: float = 0.0
    scrollingFore: float = 0.0
    scaleBack: float = 0.1
    scaleMid: float = 0.1
    scaleFore: float = 0.1
    credit: Text | None = None

    def model_post_init(self, __context: Any) -> None:
        """Load textures and initialize scrolling speeds and credits text.

        Args:
            __context: Unused pydantic context parameter required by the
                model hook signature.
        """
        self.background = load_texture(self.background_path)
        self.midground = load_texture(self.midground_path)
        self.foreground = load_texture(self.foreground_path)

        self.scaleBack = self.screen[1] / self.background.height
        self.scaleMid = self.screen[1] / self.midground.height
        self.scaleFore = self.screen[1] / self.foreground.height
        self.credit = Text(
            text="(c) Pac man by @julcleme & @sservant",
            text_size=30,
            x_anchor="center",
            y_anchor="bottom",
            coords=(self.screen[0] // 2, self.screen[1] - 100),
        )

    def draw(self) -> None:
        """Draw the parallax layers and the credits text."""
        self.scrollingBack -= 0.1
        self.scrollingMid -= 0.5
        self.scrollingFore -= 1.0

        if self.scrollingBack <= -self.background.width * self.scaleBack:
            self.scrollingBack = 0
        if self.scrollingMid <= -self.midground.width * self.scaleMid:
            self.scrollingMid = 0
        if self.scrollingFore <= -self.foreground.width * self.scaleFore:
            self.scrollingFore = 0

        pr.draw_texture_ex(
            self.background,
            pr.Vector2(self.scrollingBack, 0),
            0.0,
            self.scaleBack,
            pr.WHITE,
        )
        pr.draw_texture_ex(
            self.background,
            pr.Vector2(self.background.width * self.scaleBack
                       + self.scrollingBack, 0),
            0.0,
            self.scaleBack,
            pr.WHITE,
        )
        pr.draw_texture_ex(
            self.midground,
            pr.Vector2(self.scrollingMid, 20),
            0.0,
            self.scaleMid,
            pr.WHITE,
        )
        pr.draw_texture_ex(
            self.midground,
            pr.Vector2(self.midground.width * self.scaleMid
                       + self.scrollingMid, 20),
            0.0,
            self.scaleMid,
            pr.WHITE,
        )
        pr.draw_texture_ex(
            self.foreground,
            pr.Vector2(self.scrollingFore, 70),
            0.0,
            self.scaleFore,
            pr.WHITE,
        )
        pr.draw_texture_ex(
            self.foreground,
            pr.Vector2(self.foreground.width * self.scaleFore
                       + self.scrollingFore, 70),
            0.0,
            self.scaleFore,
            pr.WHITE,
        )
        if self.credit:
            self.credit.draw()
