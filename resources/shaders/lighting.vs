#version 330

// Entrées (in au lieu de attribute)
in vec3 vertexPosition;
in vec2 vertexTexCoord;
in vec3 vertexNormal;
in vec4 vertexColor;

// Uniformes
uniform mat4 mvp;
uniform mat4 matModel;

// Sorties vers le Fragment Shader (out au lieu de varying)
out vec3 fragPosition;
out vec2 fragTexCoord;
out vec4 fragColor;
out vec3 fragNormal;

void main()
{
    fragPosition = vec3(matModel * vec4(vertexPosition, 1.0));
    fragTexCoord = vertexTexCoord;
    fragColor = vertexColor;

    // En GLSL 330, transpose() et inverse() existent déjà ! Plus besoin de les recoder.
    mat3 normalMatrix = transpose(inverse(mat3(matModel)));
    fragNormal = normalize(normalMatrix * vertexNormal);

    gl_Position = mvp * vec4(vertexPosition, 1.0);
}