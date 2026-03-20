#version 330

in vec3 fragPosition;
in vec2 fragTexCoord;
in vec4 fragColor;
in vec3 fragNormal;

uniform sampler2D texture0;
uniform vec4 colDiffuse;

out vec4 finalColor;

#define     MAX_LIGHTS              4
#define     LIGHT_DIRECTIONAL       0
#define     LIGHT_POINT             1
#define     LIGHT_SPOT              2 // <-- Ajout du Spotlight

struct Light {
    int enabled;
    int type;
    vec3 position;
    vec3 target;
    vec4 color;
};

uniform Light lights[MAX_LIGHTS];
uniform vec4 ambient;
uniform vec3 viewPos;

void main()
{
    vec4 texelColor = texture(texture0, fragTexCoord);
    vec3 lightDot = vec3(0.0);
    vec3 normal = normalize(fragNormal);
    vec3 viewD = normalize(viewPos - fragPosition);
    vec3 specular = vec3(0.0);
    vec4 tint = colDiffuse * fragColor;

    for (int i = 0; i < MAX_LIGHTS; i++)
    {
        if (lights[i].enabled == 1)
        {
            vec3 light = vec3(0.0);
            float attenuation = 1.0; // Sert pour le fondu du Spotlight

            if (lights[i].type == LIGHT_DIRECTIONAL)
            {
                light = -normalize(lights[i].target - lights[i].position);
            }
            else if (lights[i].type == LIGHT_POINT)
            {
                light = normalize(lights[i].position - fragPosition);
            }
            else if (lights[i].type == LIGHT_SPOT)
            {
                // 1. Direction du pixel vers la lampe
                light = normalize(lights[i].position - fragPosition);
                // 2. Direction dans laquelle pointe le projecteur
                vec3 spotDir = normalize(lights[i].target - lights[i].position);
                
                // 3. Calcul de l'angle entre les deux
                float theta = dot(light, -spotDir);
                
                // 4. Définition du cône (ex: 15° de lumière pure, 25° de fondu vers le noir)
                float cutOff = cos(radians(15.0));
                float outerCutOff = cos(radians(25.0));
                
                // 5. Application du fondu doux sur les bords
                float epsilon = cutOff - outerCutOff;
                attenuation = clamp((theta - outerCutOff) / epsilon, 0.0, 1.0);
            }

            float NdotL = max(dot(normal, light), 0.0);
            // On multiplie par l'atténuation du Spotlight
            lightDot += lights[i].color.rgb * NdotL * attenuation;

            float specCo = 0.0;
            if (NdotL > 0.0) specCo = pow(max(0.0, dot(viewD, reflect(-(light), normal))), 16.0);
            // Idem pour le reflet
            specular += specCo * attenuation;
        }
    }

    finalColor = (texelColor*((tint + vec4(specular, 1.0))*vec4(lightDot, 1.0)));
    finalColor += texelColor*(ambient/10.0)*tint;

    finalColor = pow(finalColor, vec4(1.0/2.2));
}