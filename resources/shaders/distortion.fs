#version 330

in vec2 fragTexCoord;
in vec4 fragColor;
out vec4 finalColor;
uniform sampler2D texture0;

uniform vec2 resolution; 

void main()
{
    vec2 uv = fragTexCoord;
    uv = uv * 2.0 - 1.0;
    float r = dot(uv, uv);
    uv *= 1.0 + 0.1 * r + 0.05 * r * r;
    
    vec2 vignetteUV = uv;
    
    uv = uv * 0.5 + 0.5;
    
    if (uv.x < 0.0 || uv.x > 1.0 || uv.y < 0.0 || uv.y > 1.0) {
        finalColor = vec4(0.0, 0.0, 0.0, 0.0);
    } else {
        vec4 baseColor = texture(texture0, uv) * fragColor;

        float scanline_factor = mix(1.0, 0.9, floor(mod(gl_FragCoord.y, 2.0)));
        baseColor.rgb *= scanline_factor;

        float vign_dist = length(vignetteUV);
        float vignette = smoothstep(1.5, 0.95, vign_dist);
        baseColor.rgb *= vignette;
        
        finalColor = baseColor;
    }
}