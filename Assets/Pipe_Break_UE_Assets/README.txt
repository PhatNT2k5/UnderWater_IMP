PIPE BREAK DECAL - UNREAL ENGINE

Import these files:
- T_PipeBreak_BaseColor.png
- T_PipeBreak_Normal.png
- T_PipeBreak_ORM.png
- T_PipeBreak_Opacity.png
- T_PipeBreak_Height.png (optional)

Texture settings:
- BaseColor: sRGB ON, Sampler Type Color.
- Normal: sRGB OFF, Compression Normalmap, Sampler Type Normal.
- ORM: sRGB OFF, Compression Masks, Sampler Type Masks.
- Opacity/Height: sRGB OFF, Compression Grayscale, Sampler Type Linear Grayscale.

Material connections:
- BaseColor RGB -> Base Color
- Normal RGB -> Normal
- ORM R -> Ambient Occlusion
- ORM G -> Roughness
- ORM B -> Metallic
- Opacity R -> Opacity

Do not use OneMinus for the supplied Opacity map: white is already visible and
black is already transparent. All maps are derived from the same alpha mask and
therefore align with one another.

Recommended material:
- Material Domain: Deferred Decal
- Blend Mode: Translucent
- Shading Model: Default Lit

Place the Decal Actor perpendicular to the pipe surface. Keep Decal Size X
(projection depth) small so it does not project through the back of the pipe.
