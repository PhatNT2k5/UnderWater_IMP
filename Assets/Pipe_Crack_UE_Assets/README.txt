PIPE CRACK TEXTURES - UNREAL ENGINE IMPORT GUIDE

Folders
- raw_crops: exact crops from the supplied atlas; dimensions are not uniform.
- UE_1024: normalized 1024 x 1024 textures for easier Unreal Engine import.

Recommended Unreal settings
1. T_PipeCrack_BaseColor
   - sRGB: ON
   - Compression Settings: Default
   - Connect RGB to Base Color.

2. T_PipeCrack_Normal
   - sRGB: OFF
   - Compression Settings: Normalmap
   - Connect RGB to Normal.
   - If the relief looks inverted, enable Flip Green Channel in the texture asset.

3. T_PipeCrack_ORM (recommended packed map)
   - sRGB: OFF
   - Compression Settings: Masks (no sRGB)
   - R -> Ambient Occlusion
   - G -> Roughness
   - B -> Metallic

4. T_PipeCrack_Displacement
   - sRGB: OFF
   - Compression Settings: Grayscale or Masks
   - Use with Bump Offset / Parallax Occlusion Mapping, or a displacement setup
     appropriate for the mesh and Unreal Engine version.

Important limitation
The supplied source is a presentation atlas, not a professionally baked PBR
texture set. The six maps depict similar cracks but are not perfectly registered
pixel-for-pixel. Cropping and resizing cannot fully correct that mismatch. For
the most accurate material, bake all maps from the same high-poly mesh or derive
them from one shared height mask.

Naming
- BaseColor: color/albedo input
- Normal: surface direction detail
- Metallic: metal/non-metal mask
- Roughness: surface microsurface roughness
- AO: ambient occlusion
- Displacement: height/depth information
- ORM: packed AO/Roughness/Metallic texture
