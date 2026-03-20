"""Graphics layer and main loop for the Pac-man game.

This module initializes the pyray context, loads 3D assets and
manages the main rendering loop. Public helper functions and the
Graphics class are documented with Google-style docstrings.
"""

import pyray as pr
from scenes import (
    DeathScreenScene,
    IntroScene,
    GameScene,
    NameScene,
    MultiplayerWaitingScene,
    Scene,
)
from components import Model
import math
from rlights import create_light, update_light_values, LIGHT_SPOT
import time
from typing import Any

SHADOWMAP_RESOLUTION = 4096


def load_shadowmap_render_texture(width: int, height: int) -> Any:
    """Create and initialize a high resolution render texture.

    Args:
        width: Width in pixels for the shadowmap texture.
        height: Height in pixels for the shadowmap texture.

    Returns:
        A pyray RenderTexture configured for shadow rendering.
    """
    target = pr.RenderTexture()
    target.id = pr.rl_load_framebuffer()
    target.texture.width = width
    target.texture.height = height
    if target.id > 0:
        pr.rl_enable_framebuffer(target.id)
        target.depth.id = pr.rl_load_texture_depth(width, height, False)
        target.depth.width = width
        target.depth.height = height
        target.depth.format = 19
        target.depth.mipmaps = 1
        pr.rl_framebuffer_attach(
            target.id,
            target.depth.id,
            100,
            100,
            0,
        )
        pr.rl_disable_framebuffer()
    return target


def unload_shadowmap_render_texture(target: Any) -> None:
    """Release GPU resources associated with a shadow map texture.

    Args:
        target: RenderTexture instance previously created by
            `load_shadowmap_render_texture`.
    """
    if target.id > 0:
        pr.rl_unload_framebuffer(target.id)


class Graphics:
    """Encapsulates window, rendering targets and the game loop.

    The Graphics class is responsible for creating the main window,
    loading models/shaders and driving the currently active scenes
    through update/draw cycles.
    """
    def __init__(self, config: Any):
        self.window_width = 1920
        self.window_height = 1000
        self.screen_width = 1133
        self.screen_height = 1133
        self.screen_top_width = 1133
        self.screen_top_height = 500
        self.title = "Pac-man"
        self.history_stack: list[Any] = []
        self.config = config
        self.mouse_status = True
        pr.set_trace_log_level(7)
        pr.set_config_flags(pr.ConfigFlags.FLAG_MSAA_4X_HINT)
        pr.init_window(self.window_width, self.window_height, self.title)
        pr.set_exit_key(pr.KeyboardKey.KEY_NULL)
        pr.set_target_fps(60)

        self.move_speed = 0.1
        self.camera = pr.Camera3D()
        self.camera.up = pr.Vector3(0.0, 1.0, 0.0)
        self.camera.fovy = 75.0
        self.camera.projection = pr.CameraProjection.CAMERA_PERSPECTIVE
        self.camera.target = pr.Vector3(-1.75, 0.9, 0.55)
        self.camera.position = pr.Vector3(-2.3, 1.2, 0.55)

        self.scene_model = pr.load_model("resources/models/arcade_scene.glb")
        self.arcade_model = pr.load_model("resources/models/borne.glb")
        self.joystick_model = pr.load_model("resources/models/joystick.glb")
        self.button_model = pr.load_model("resources/models/button.glb")
        pr.gui_load_style("resources/styles/cyber.rgs")
        pr.gui_set_style(pr.GuiControl.DEFAULT,
                         pr.GuiDefaultProperty.TEXT_SIZE, 30)
        self.shader = pr.load_shader("", "resources/shaders/distortion.fs")
        self.game_target_raw = pr.load_render_texture(
            self.screen_width, self.screen_height
        )
        self.game_target_shaded = pr.load_render_texture(
            self.screen_width, self.screen_height
        )
        self.top_target_raw = pr.load_render_texture(
            self.screen_top_width, self.screen_top_height
        )
        self.top_target_shaded = pr.load_render_texture(
            self.screen_top_width, self.screen_top_height
        )

        mesh = pr.gen_mesh_plane(1.0, 1.0, 1, 1)
        self.fake_screen = pr.load_model_from_mesh(mesh)
        pr.set_material_texture(
            self.fake_screen.materials[0],
            pr.MaterialMapIndex.MATERIAL_MAP_ALBEDO,
            self.game_target_shaded.texture,
        )

        mesh_top = pr.gen_mesh_plane(1.0, 1.0, 1, 1)
        self.fake_screen_top = pr.load_model_from_mesh(mesh_top)
        pr.set_material_texture(
            self.fake_screen_top.materials[0],
            pr.MaterialMapIndex.MATERIAL_MAP_ALBEDO,
            self.top_target_shaded.texture,
        )

        self.shadow_shader = pr.load_shader(
            "resources/shaders/shadowmap.vs", "resources/shaders/shadowmap.fs"
        )
        self.shadow_shader.locs[
            pr.ShaderLocationIndex.SHADER_LOC_VECTOR_VIEW] = \
            pr.get_shader_location(
                self.shadow_shader, "viewPos"
            )

        self.light_dir = pr.vector3_normalize(pr.Vector3(0.35, -1.0, -0.35))
        pr.set_shader_value(
            self.shadow_shader,
            pr.get_shader_location(self.shadow_shader, "lightDir"),
            pr.ffi.new(
                "Vector3 *", [self.light_dir.x,
                              self.light_dir.y,
                              self.light_dir.z]
            ),
            pr.ShaderUniformDataType.SHADER_UNIFORM_VEC3,
        )
        pr.set_shader_value(
            self.shadow_shader,
            pr.get_shader_location(self.shadow_shader, "shadowMapResolution"),
            pr.ffi.new("int *", SHADOWMAP_RESOLUTION),
            pr.ShaderUniformDataType.SHADER_UNIFORM_INT,
        )
        light_color = pr.color_normalize(pr.Color(50, 50, 50, 100))
        pr.set_shader_value(
            self.shadow_shader,
            pr.get_shader_location(self.shadow_shader, "lightColor"),
            pr.ffi.new(
                "Vector4 *",
                [light_color.x, light_color.y, light_color.z, light_color.w],
            ),
            pr.ShaderUniformDataType.SHADER_UNIFORM_VEC4,
        )
        ambient_color = pr.ffi.new("float[4]", [0.0, 0.0, 0.0, 1.0])
        pr.set_shader_value(
            self.shadow_shader,
            pr.get_shader_location(self.shadow_shader, "ambient"),
            ambient_color,
            pr.ShaderUniformDataType.SHADER_UNIFORM_VEC4,
        )

        self.lights = [
            create_light(
                LIGHT_SPOT,
                pr.Vector3(-1.735, 0.9475, 0.55),
                pr.Vector3(-2, 0.9475, 0.55),
                [2, 4, 27, 255],
                self.shadow_shader,
            ),
            create_light(
                LIGHT_SPOT,
                pr.Vector3(1, 3, 0.55),
                pr.Vector3(1, 0, 0.55),
                [255, 255, 255, 255],
                self.shadow_shader,
            ),
        ]

        for i in range(self.scene_model.materialCount):
            self.scene_model.materials[i].shader = self.shadow_shader
        for i in range(self.arcade_model.materialCount):
            self.arcade_model.materials[i].shader = self.shadow_shader
        for i in range(self.joystick_model.materialCount):
            self.joystick_model.materials[i].shader = self.shadow_shader
        for i in range(self.button_model.materialCount):
            self.button_model.materials[i].shader = self.shadow_shader
        self.scene_obj = Model(
            model=self.scene_model,
            coords=pr.Vector3(0.0, 0.0, 0.0),
            rotation=0.0,
            scale=pr.Vector3(1.0, 1.0, 1.0),
            rotation_axe=pr.Vector3(0.0, 1.0, 0.0),
        )
        self.borne_obj = Model(
            model=self.arcade_model,
            coords=pr.Vector3(-1.75, 0.0, 0.55),
            rotation=-90.0,
            scale=pr.Vector3(1.0 / 40, 1.0 / 40, 1.0 / 40),
            rotation_axe=pr.Vector3(0.0, 1.0, 0.0),
        )
        self.joystick_obj = Model(
            model=self.joystick_model,
            coords=pr.Vector3(-2.032, 0.755, 0.555),
            rotation=0.0,
            scale=pr.Vector3(1.0 / 40, 1.0 / 40, 1.0 / 40),
            rotation_axe=pr.Vector3(0.0, 1.0, 0.0),
        )
        self.joystick_obj.set_tilt(0.0, 0.0, 0.0)
        self.button_obj = Model(
            model=self.button_model,
            coords=pr.Vector3(-1.962, 0.7645, 0.81),
            rotation=-90.0,
            scale=pr.Vector3(1.0 / 40, 1.0 / 40, 1.0 / 40),
            rotation_axe=pr.Vector3(0.0, 1.0, 0.0),
        )
        self.button2_obj = Model(
            model=self.button_model,
            coords=pr.Vector3(-2.05, 0.7645, 0.81),
            rotation=-90.0,
            scale=pr.Vector3(1.0 / 40, 1.0 / 40, 1.0 / 40),
            rotation_axe=pr.Vector3(0.0, 1.0, 0.0),
        )
        self.shadow_map = load_shadowmap_render_texture(
            SHADOWMAP_RESOLUTION, SHADOWMAP_RESOLUTION
        )
        self.light_cam = pr.Camera3D(
            pr.vector3_scale(self.light_dir, -15.0),
            pr.Vector3(0, 0, 0),
            pr.Vector3(0, 1, 0),
            40.0,
            pr.CameraProjection.CAMERA_ORTHOGRAPHIC
        )

        self.current_scene = IntroScene(self)
        self.current_scene_top = Scene(self)

    def get_virtual_mouse_position(self) -> pr.Vector2:
        mouse_pos = pr.get_mouse_position()
        ray = pr.get_screen_to_world_ray(mouse_pos, self.camera)

        mat_scale = pr.matrix_scale(0.655, 0.655, 0.6)
        mat_turn = pr.matrix_rotate_y(math.radians(90.0))
        mat_tilt = pr.matrix_rotate_x(math.radians(-43.15))
        mat_rot = pr.matrix_multiply(mat_tilt, mat_turn)
        mat_trans = pr.matrix_translate(-1.735, 0.9475, 0.55)

        mat_transform = pr.matrix_multiply(
            pr.matrix_multiply(mat_scale, mat_rot), mat_trans
        )

        collision = pr.get_ray_collision_mesh(
            ray, self.fake_screen.meshes[0], mat_transform
        )

        if not collision.hit:
            return pr.Vector2(-1.0, -1.0)

        mat_inv = pr.matrix_invert(mat_transform)

        local_point = pr.vector3_transform(collision.point, mat_inv)

        u = local_point.x + 0.5
        v = 1.0 - (local_point.z + 0.5)
        virtual_x = u * self.screen_width
        virtual_y = v * self.screen_height

        return pr.Vector2(virtual_x, virtual_y)

    def change_scene(self, new_scene: Any) -> None:
        self.history_stack.append(self.current_scene)
        self.current_scene = new_scene

    def change_scene_top(self, new_scene: Any) -> None:
        self.current_scene_top = new_scene

    def go_back(self) -> None:
        if len(self.history_stack) == 0 or isinstance(
            self.history_stack[-1], (IntroScene, NameScene)
        ):
            import sys

            sys.exit(0)
        elif isinstance(
            self.history_stack[-1],
            (GameScene, DeathScreenScene, MultiplayerWaitingScene),
        ):
            self.history_stack.pop()
            self.go_back()
        else:
            self.current_scene = self.history_stack.pop()

    def _refresh_camera(self) -> None:
        mouse_delta = pr.get_mouse_delta()
        rotation = pr.Vector3(mouse_delta.x * 0.1, mouse_delta.y * 0.1, 0.0)
        movement = pr.Vector3(0.0, 0.0, 0.0)
        zoom = 0.0
        pr.update_camera_pro(self.camera, movement, rotation, zoom)

    def _draw_3d_models(self) -> None:
        self.scene_obj.draw()
        self.borne_obj.draw()
        self.joystick_obj.draw()
        self.button_obj.draw()
        self.button2_obj.draw()

    def run(self) -> None:
        while not pr.window_should_close():
            if pr.is_mouse_button_down(pr.MouseButton.MOUSE_BUTTON_RIGHT):
                if self.mouse_status:
                    pr.disable_cursor()
                    self.mouse_status = False
                self._refresh_camera()
            else:
                if not self.mouse_status:
                    pr.enable_cursor()
                    self.mouse_status = True
            self.current_scene.update(self.get_virtual_mouse_position())
            self.current_scene_top.update(self.get_virtual_mouse_position())
            if (
                self.button_obj.update(self.camera)
                and isinstance(self.current_scene, GameScene)
                and not self.current_scene.cheat
            ):
                self.current_scene.pause = not self.current_scene.pause
                if not getattr(self.current_scene, "is_multi", False):
                    if self.current_scene.pause:
                        self.current_scene.last_pause_time = time.time()
                    else:
                        self.current_scene.total_pause_time += (
                            time.time() - self.current_scene.last_pause_time
                        )
            if self.button2_obj.update(self.camera) and isinstance(
                self.current_scene, GameScene
            ):
                self.current_scene.cheat = not self.current_scene.cheat
                if self.current_scene.cheat:
                    self.current_scene.pause = True
                    if not getattr(self.current_scene, "is_multi", False):
                        self.current_scene.last_pause_time = time.time()
                else:
                    self.current_scene.pause = False
                    if not getattr(self.current_scene, "is_multi", False):
                        self.current_scene.total_pause_time += (
                            time.time() - self.current_scene.last_pause_time
                        )

            if pr.is_key_pressed(pr.KeyboardKey.KEY_ESCAPE):
                self.go_back()

            camera_pos = pr.ffi.new(
                "Vector3 *",
                [
                    self.camera.position.x,
                    self.camera.position.y,
                    self.camera.position.z,
                ],
            )
            pr.set_shader_value(
                self.shadow_shader,
                self.shadow_shader.locs[
                    pr.ShaderLocationIndex.SHADER_LOC_VECTOR_VIEW],
                camera_pos,
                pr.ShaderUniformDataType.SHADER_UNIFORM_VEC3,
            )
            for light in self.lights:
                update_light_values(self.shadow_shader, light)

            pr.begin_texture_mode(self.game_target_raw)
            pr.clear_background(pr.BLACK)
            self.current_scene.draw()
            pr.end_texture_mode()
            pr.begin_texture_mode(self.game_target_shaded)
            pr.clear_background(pr.BLACK)
            pr.begin_shader_mode(self.shader)
            source_rec = pr.Rectangle(
                0,
                0,
                -self.game_target_raw.texture.width,
                -self.game_target_raw.texture.height,
            )
            pr.draw_texture_rec(
                self.game_target_raw.texture, source_rec, pr.Vector2(0, 0),
                pr.WHITE
            )
            pr.end_shader_mode()
            pr.end_texture_mode()

            pr.begin_texture_mode(self.top_target_raw)
            pr.clear_background(pr.BLACK)
            self.current_scene_top.draw()
            pr.end_texture_mode()
            pr.begin_texture_mode(self.top_target_shaded)
            pr.clear_background(pr.BLACK)
            pr.begin_shader_mode(self.shader)
            source_rec = pr.Rectangle(
                0,
                0,
                -self.top_target_raw.texture.width,
                -self.top_target_raw.texture.height,
            )
            pr.draw_texture_rec(
                self.top_target_raw.texture, source_rec, pr.Vector2(0, 0),
                pr.WHITE
            )
            pr.end_shader_mode()
            pr.end_texture_mode()

            pr.begin_texture_mode(self.shadow_map)
            pr.clear_background(pr.WHITE)
            pr.begin_mode_3d(self.light_cam)

            light_view = pr.rl_get_matrix_modelview()
            light_proj = pr.rl_get_matrix_projection()

            self._draw_3d_models()

            pr.end_mode_3d()
            pr.end_texture_mode()

            light_view_proj = pr.matrix_multiply(light_view, light_proj)
            pr.set_shader_value_matrix(
                self.shadow_shader,
                pr.get_shader_location(self.shadow_shader, "lightVP"),
                light_view_proj,
            )
            pr.rl_enable_shader(self.shadow_shader.id)
            pr.rl_active_texture_slot(10)
            pr.rl_enable_texture(self.shadow_map.depth.id)
            pr.rl_set_uniform(
                pr.get_shader_location(self.shadow_shader, "shadowMap"),
                pr.ffi.new("int *", 10),
                pr.ShaderUniformDataType.SHADER_UNIFORM_INT,
                1,
            )

            pr.begin_drawing()
            pr.clear_background(pr.BLACK)

            pr.begin_mode_3d(self.camera)

            self._draw_3d_models()
            mat_turn = pr.matrix_rotate_y(math.radians(90.0))
            mat_tilt = pr.matrix_rotate_x(math.radians(-43.15))
            self.fake_screen.transform = pr.matrix_multiply(mat_tilt, mat_turn)

            pr.draw_model_ex(
                self.fake_screen,
                pr.Vector3(-1.735, 0.9475, 0.55),
                pr.Vector3(0.0, 1.0, 0.0),
                0.0,
                pr.Vector3(0.655, 0.655, 0.6),
                pr.WHITE,
            )

            mat_turn_top = pr.matrix_rotate_y(math.radians(90.0))
            mat_tilt_top = pr.matrix_rotate_x(math.radians(-135.5))
            self.fake_screen_top.transform = pr.matrix_multiply(
                mat_tilt_top, mat_turn_top
            )

            pr.draw_model_ex(
                self.fake_screen_top,
                pr.Vector3(-1.6, 1.3, 0.55),
                pr.Vector3(0.0, 1.0, 0.0),
                0.0,
                pr.Vector3(0.3, 0.3, 0.6),
                pr.WHITE,
            )
            pr.end_mode_3d()
            pr.end_drawing()

        pr.unload_render_texture(self.game_target_raw)
        pr.unload_render_texture(self.game_target_shaded)
        pr.unload_render_texture(self.top_target_raw)
        pr.unload_render_texture(self.top_target_shaded)
        unload_shadowmap_render_texture(self.shadow_map)
        pr.unload_model(self.fake_screen)
        pr.unload_model(self.fake_screen_top)
        pr.unload_shader(self.shader)
        pr.unload_shader(self.shadow_shader)
        pr.close_window()
