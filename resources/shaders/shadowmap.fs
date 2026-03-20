#version 330

// --- Entrées du Vertex Shader ---
in vec3 fragPosition;
in vec2 fragTexCoord;
in vec4 fragColor;
in vec3 fragNormal;

// --- Sortie finale ---
out vec4 finalColor;

// --- Uniformes de base ---
uniform sampler2D texture0;
uniform vec4 colDiffuse;

// --- Uniformes : Soleil et Ombres ---
uniform vec3 lightDir;
uniform vec4 lightColor;
uniform vec4 ambient;
uniform vec3 viewPos;
uniform mat4 lightVP;
uniform sampler2D shadowMap;
uniform int shadowMapResolution;

// --- Uniformes : rlights (Lumières colorées) ---
#define MAX_LIGHTS 4
struct Light {
    int enabled;
    int type;
    vec3 position;
    vec3 target;
    vec4 color;
};
uniform Light lights[MAX_LIGHTS];

void main()
{
    // 1. Couleur de base du modèle (Texture + Teinte)
    vec4 texelColor = texture(texture0, fragTexCoord);
    vec4 baseColor = texelColor * colDiffuse * fragColor;

    vec3 normal = normalize(fragNormal);
    vec3 viewD = normalize(viewPos - fragPosition);

    // 2. Calcul des OMBRES (Uniquement projetées par le soleil)
    vec4 fragPosLightSpace = lightVP * vec4(fragPosition, 1.0);
    fragPosLightSpace.xyz /= fragPosLightSpace.w;
    fragPosLightSpace.xyz = (fragPosLightSpace.xyz + 1.0) / 2.0;

    float curDepth = fragPosLightSpace.z;
    vec3 sunDir = -normalize(lightDir);
    float bias = max(0.0008 * (1.0 - dot(normal, sunDir)), 0.00008);
    
    int shadowCounter = 0;
    int numSamples = 9;
    vec2 texelSize = vec2(1.0 / float(shadowMapResolution));
    
    // PCF : Adoucissement des bords de l'ombre
    for (int x = -1; x <= 1; x++)
    {
        for (int y = -1; y <= 1; y++)
        {
            float sampleDepth = texture(shadowMap, fragPosLightSpace.xy + texelSize * vec2(x, y)).r;
            if (curDepth - bias > sampleDepth) shadowCounter++;
        }
    }
    // shadowFactor : 1.0 = Pleine lumière, 0.0 = Dans l'ombre pure
    float shadowFactor = 1.0 - (float(shadowCounter) / float(numSamples));

    // 3. Éclairage Directionnel (Soleil) + Application de l'ombre
    float sunNdotL = max(dot(normal, sunDir), 0.0);
    vec3 sunLighting = lightColor.rgb * sunNdotL * shadowFactor; 

    // 4. Éclairage rlights (Tes lumières Gold et Purple)
    vec3 pointLightsTotal = vec3(0.0);
    for (int i = 0; i < MAX_LIGHTS; i++)
    {
        if (lights[i].enabled == 1)
        {
            vec3 lightVec = lights[i].position - fragPosition;
            float distance = length(lightVec);
            vec3 lDir = normalize(lightVec);

            // Atténuation physique (la lumière s'estompe avec la distance)
            float attenuation = 1.0 / (1.0 + 0.1 * distance + 0.05 * (distance * distance));

            float NdotL = max(dot(normal, lDir), 0.0);
            pointLightsTotal += lights[i].color.rgb * NdotL * attenuation;
        }
    }

    // 5. Assemblage final
    vec3 ambientLight = ambient.rgb * ambient.a;
    // On additionne l'ambiance, le soleil (avec ombre) et tes lumières colorées
    vec3 totalLighting = ambientLight + sunLighting + pointLightsTotal;

    finalColor = vec4(baseColor.rgb * totalLighting, baseColor.a);

    // 6. Correction Gamma (empêche la scène d'être trop sombre)
    finalColor = pow(finalColor, vec4(1.0/2.2));
}