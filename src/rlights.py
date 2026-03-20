"""Helpers for runtime lights and shader uploads.

This module provides a lightweight wrapper around pyray shader light
uniform updates. It exposes a simple `Light` container and functions to
create lights and push their values into the shader.
"""

import pyray as rl
from typing import Any

# Max dynamic lights supported by shader
MAX_LIGHTS = 4

# Light types
LIGHT_DIRECTIONAL = 0
LIGHT_POINT = 1
LIGHT_SPOT = 2
# Global variable to keep track of the number of lights
lights_count = 0


class Light:
    """Light container holding properties and cached shader locations.

    The class stores a small set of properties (type, position, target,
    color, attenuation) and the corresponding shader uniform locations.
    Instances are manipulated with `create_light` and `update_light_values`.
    """

    def __init__(self: Any):
        self.type = 0
        self.enabled = True
        self.position = rl.Vector3(0, 0, 0)
        self.target = rl.Vector3(0, 0, 0)
        self.color = rl.Color(0, 0, 0, 255)
        self.attenuation = 0.0

        self.enabled_loc = 0
        self.type_loc = 0
        self.position_loc = 0
        self.target_loc = 0
        self.color_loc = 0
        self.attenuation_loc = 0


def create_light(light_type: int, position: Any,
                 target: Any, color: Any, shader: Any) -> Any:
    """Construct a Light and obtain shader uniform locations.

    Args:
        light_type: One of the LIGHT_* constants describing the light type.
        position: Vector3-like position for the light.
        target: Vector3-like target (for spot/directional lights).
        color: Color-like object describing RGBA values (0..255).
        shader: Compiled pyray shader object where uniforms will be set.

    Returns:
        A `Light` object with shader locations populated. If the maximum
        number of lights has been reached an inactive Light is returned.
    """
    global lights_count

    light: Light = Light()

    if lights_count < MAX_LIGHTS:
        light.enabled = True
        light.type = light_type
        light.position = position
        light.target = target
        light.color = color

        # NOTE: Lighting shader naming must be the provided ones
        light.enabled_loc = rl.get_shader_location(
            shader, f"lights[{lights_count}].enabled"
        )
        light.type_loc = rl.get_shader_location(shader,
                                                f"lights[{lights_count}].type")
        light.position_loc = rl.get_shader_location(
            shader, f"lights[{lights_count}].position"
        )
        light.target_loc = rl.get_shader_location(
            shader, f"lights[{lights_count}].target"
        )
        light.color_loc = rl.get_shader_location(
            shader, f"lights[{lights_count}].color"
        )

        update_light_values(shader, light)

        lights_count += 1

    return light


def update_light_values(shader: Any, light: Any) -> None:
    """Upload a light's properties into shader uniforms.

    This function converts Python-side light attributes into the C-types
    required by the shader API and calls `rl.set_shader_value` for each
    uniform location cached on the `Light` instance.

    Args:
        shader: The compiled shader to receive the uniform values.
        light: Light instance with properties and cached uniform locations.
    """
    # Send to shader light enabled state and type
    rl.set_shader_value(
        shader,
        light.enabled_loc,
        rl.ffi.new("int *", light.enabled),
        rl.ShaderUniformDataType.SHADER_UNIFORM_INT,
    )
    rl.set_shader_value(
        shader, light.type_loc, rl.ffi.new("int *", light.type),
        rl.ShaderUniformDataType.SHADER_UNIFORM_INT
    )

    # Send to shader light position values
    position = rl.ffi.new(
        "float[3]", [light.position.x, light.position.y, light.position.z]
    )
    rl.set_shader_value(shader, light.position_loc, position,
                        rl.ShaderUniformDataType.SHADER_UNIFORM_VEC3)

    # Send to shader light target position values
    target = rl.ffi.new("float[3]", [light.target.x,
                                     light.target.y,
                                     light.target.z])
    rl.set_shader_value(shader, light.target_loc, target,
                        rl.ShaderUniformDataType.SHADER_UNIFORM_VEC3)

    # Send to shader light color values
    color = rl.ffi.new(
        "float[4]",
        [
            light.color[0] / 255.0,
            light.color[1] / 255.0,
            light.color[2] / 255.0,
            light.color[3] / 255.0,
        ],
    )
    rl.set_shader_value(shader, light.color_loc, color,
                        rl.ShaderUniformDataType.SHADER_UNIFORM_VEC4)
