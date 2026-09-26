"""Run with Unreal 5.3 PythonScriptCommandlet; all distances below are cm."""
from __future__ import annotations

import json
import math
import os
import random
import shutil
from datetime import datetime
from pathlib import Path

import unreal

HERE = Path(os.environ.get("AUV_INSPECTION_ROOT", str(Path(__file__).resolve().parent)))
MAP = "/Game/AUVInspection/Maps/AUVInspection"
ASSETS = "/Game/AUVInspection/Materials"
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LEVELS = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
RNG = random.Random(302)
DEFECTS: list[dict] = []


def material(name: str, color: tuple, metallic: float = 0.0) -> unreal.Material:
    path = f"{ASSETS}/{name}"
    asset = unreal.load_asset(path)
    if asset:
        return asset
    asset = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        name, ASSETS, unreal.Material, unreal.MaterialFactoryNew())
    lib = unreal.MaterialEditingLibrary
    rgb = lib.create_material_expression(asset, unreal.MaterialExpressionConstant3Vector)
    rgb.set_editor_property("constant", unreal.LinearColor(*color, 1.0))
    lib.connect_material_property(rgb, "", unreal.MaterialProperty.MP_BASE_COLOR)
    rough = lib.create_material_expression(asset, unreal.MaterialExpressionConstant)
    rough.set_editor_property("r", 0.85)
    lib.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    metal = lib.create_material_expression(asset, unreal.MaterialExpressionConstant)
    metal.set_editor_property("r", metallic)
    lib.connect_material_property(metal, "", unreal.MaterialProperty.MP_METALLIC)
    lib.recompile_material(asset)
    unreal.EditorAssetLibrary.save_loaded_asset(asset)
    return asset


def mesh(name: str, shape: str, pos: tuple, size: tuple,
         mat: unreal.MaterialInterface, rotation: tuple = (0, 0, 0),
         collision: bool = True, defect_id: int = 0) -> unreal.StaticMeshActor:
    actor = ACTORS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*pos),
                                         unreal.Rotator(pitch=rotation[0], yaw=rotation[1], roll=rotation[2]))
    if not actor:
        raise RuntimeError(f"Cannot spawn {name}")
    actor.set_actor_label(name)
    component = actor.static_mesh_component
    asset = unreal.load_asset(f"/Engine/BasicShapes/{shape}")
    if not asset:
        raise RuntimeError(f"Missing mesh {shape}")
    component.set_static_mesh(asset)
    component.set_material(0, mat)
    actor.set_actor_scale3d(unreal.Vector(*(v / 100 for v in size)))
    component.set_collision_profile_name("BlockAll" if collision else "NoCollision")
    if defect_id:
        component.set_render_custom_depth(True)
        component.set_custom_depth_stencil_value(defect_id)
        actor.set_editor_property("tags", [f"defect_{defect_id:03d}"])
        actor.set_folder_path("Inspection/Defects")
    else:
        actor.set_folder_path("Inspection/Structures")
    return actor


def defect(kind: str, pos: tuple, surface: str, severity: float,
           materials: dict, enabled: bool) -> None:
    index = len(DEFECTS) + 1
    DEFECTS.append({"id": index, "class": kind, "structure": surface,
                    "severity": severity, "enabled": enabled,
                    "location_m": [pos[0] / 100, -pos[1] / 100, pos[2] / 100],
                    "label_source": "scene_ground_truth", "stencil_id": index})
    if not enabled:
        return
    x, y, z = pos
    if kind == "crack":
        # Thin connected segments on the camera-facing surface, with two branches.
        points = [(-35, -42), (-19, -28), (-23, -10), (-5, 5), (2, 21), (25, 38)]
        for n, (a, b) in enumerate(zip(points, points[1:])):
            dx, dz = b[0] - a[0], b[1] - a[1]
            length = math.hypot(dx, dz)
            mesh(f"D{index:03d}_Crack_{n}", "Cube",
                 (x + (a[0] + b[0]) / 2, y, z + (a[1] + b[1]) / 2),
                 (length + 2, 1.5, 1.5 + severity * 2), materials[kind],
                 (math.degrees(math.atan2(dz, dx)), 0, 0), False, index)
        mesh(f"D{index:03d}_Branch", "Cube", (x + 9, y - 0.2, z - 4),
             (36, 1.5, 2), materials[kind], (-27, 0, 0), False, index)
    else:
        count = 32 if kind == "biofouling" else 24
        for n in range(count):
            dx, dz = RNG.uniform(-36, 36), RNG.uniform(-26, 26)
            radius = RNG.uniform(7, 20) * (0.6 + severity)
            mesh(f"D{index:03d}_{kind}_{n}", "Sphere",
                 (x + dx, y - RNG.uniform(0, 2), z + dz),
                 (radius, 3 if kind == "corrosion" else radius * 0.45, radius),
                 materials[kind], collision=False, defect_id=index)


def main() -> None:
    settings = json.loads((HERE / "scene.json").read_text(encoding="utf-8"))
    output = HERE / "output"
    output.mkdir(exist_ok=True)
    project = Path(unreal.Paths.project_dir())
    map_file = project / "Content/AUVInspection/Maps/AUVInspection.umap"
    if map_file.exists():
        backup = output / "backups" / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup.mkdir(parents=True)
        shutil.copy2(map_file, backup / map_file.name)
        if not LEVELS.load_level(MAP):
            raise RuntimeError("Could not load generated map for rebuild")
        for actor in ACTORS.get_all_level_actors():
            if not ACTORS.destroy_actor(actor):
                raise RuntimeError(f"Could not clear generated actor {actor}")
    elif not LEVELS.new_level(MAP):
        raise RuntimeError("Could not create inspection map")
    materials = {
        "crack": material("M_Crack", (0.006, 0.008, 0.009)),
        "corrosion": material("M_Corrosion", (0.42, 0.095, 0.023)),
        "biofouling": material("M_Biofouling", (0.055, 0.24, 0.025)),
        "pipe": material("M_Pipe", (0.22, 0.28, 0.30), 0.3),
    }
    sand = unreal.load_asset("/Game/StarterContent/Materials/M_Brown_Sand")
    concrete = unreal.load_asset("/Game/StarterContent/TestWorld/Materials/concrete")
    if not sand or not concrete:
        raise RuntimeError("Required project sand/concrete materials are missing")
    mesh("Seabed", "Cube", (0, 0, -1250), (7000, 6000, 100), sand)
    backdrop = material("M_WaterBackdrop", (0.025, 0.13, 0.17))
    backdrop.set_editor_property("two_sided", True)
    backdrop.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    expression = unreal.MaterialEditingLibrary.get_material_property_input_node(
        backdrop, unreal.MaterialProperty.MP_BASE_COLOR)
    unreal.MaterialEditingLibrary.connect_material_property(
        expression, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    unreal.MaterialEditingLibrary.recompile_material(backdrop)
    enclosure = mesh("DistantWaterBackdrop", "Cube", (0, 0, -800),
                     (9000, 8000, 4000), backdrop, collision=False)
    enclosure.static_mesh_component.set_editor_property("cast_shadow", False)
    # Pipe main axis is X. Engine cylinder is 100 cm high and 100 cm diameter.
    for i in range(12):
        x = -1650 + i * 300
        deformed = settings["defects"]["deformation"] and i == 8
        mesh(f"Pipeline_{i:02d}", "Cylinder", (x, 0, -1030),
             (90, 65 if deformed else 90, 302), materials["pipe"], (90, 0, 0))
        mesh(f"Flange_{i:02d}", "Cylinder", (x - 145, 0, -1030),
             (112, 112, 12), materials["pipe"], (90, 0, 0))
        if i % 2 == 0:
            mesh(f"PipeSupport_{i:02d}", "Cube", (x, 0, -1152),
                 (90, 160, 96), concrete)
    for i, x in enumerate((-1000, 1000)):
        mesh(f"PierFooting_{i}", "Cube", (x, 650, -1120), (400, 400, 160), concrete)
        mesh(f"BridgePier_{i}", "Cube", (x, 650, -440), (190, 190, 1200), concrete)
    mesh("BridgeCrossBeam", "Cube", (0, 650, 190), (2500, 280, 170), concrete)
    for i, kind in enumerate(("crack", "corrosion", "biofouling")):
        defect(kind, (-950 + i * 900, -45.5, -1030), "pipeline", 0.65,
               materials, settings["defects"][kind])
        defect(kind, (-1000 if i < 2 else 1000, 553.5, -850 + (i % 2) * 220),
               "bridge_pier", 0.8, materials, settings["defects"][kind])
    DEFECTS.append({"id": 7, "class": "deformation", "structure": "pipeline",
                    "severity": 0.5, "enabled": settings["defects"]["deformation"],
                    "location_m": [7.5, 0, -10.3], "label_source": "scene_ground_truth"})
    for i in range(30):
        x, y = RNG.uniform(-3000, 3000), RNG.choice((-1, 1)) * RNG.uniform(1400, 2400)
        mesh(f"SeabedRock_{i}", "Sphere", (x, y, -1190),
             (RNG.uniform(50, 180), RNG.uniform(50, 160), RNG.uniform(35, 100)), concrete)
    light = ACTORS.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 500))
    light.set_actor_rotation(unreal.Rotator(pitch=-55, yaw=-35, roll=0), False)
    light.light_component.set_intensity(4.0)
    light.light_component.set_light_color(unreal.LinearColor(0.65, 0.85, 1.0))
    sky = ACTORS.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 200))
    sky.light_component.set_intensity(1.0)
    # Local fill lights keep underside defects visible to the camera.
    for i, x in enumerate((-1300, 0, 1300)):
        fill = ACTORS.spawn_actor_from_class(unreal.PointLight, unreal.Vector(x, -600, -600))
        fill.set_actor_label(f"UnderwaterFill_{i}")
        fill.point_light_component.set_editor_property("intensity", 16000.0)
        fill.point_light_component.set_editor_property("attenuation_radius", 2200.0)
    fog = ACTORS.spawn_actor_from_class(unreal.ExponentialHeightFog, unreal.Vector(0, 0, -1300))
    fog.component.set_editor_property("fog_density", settings["fog_density"])
    fog.component.set_editor_property("fog_height_falloff", 0.05)
    fog.component.set_fog_inscattering_color(unreal.LinearColor(0.035, 0.20, 0.25))
    water = unreal.load_asset("/Game/StarterContent/Materials/M_TranslucentBlue_Water")
    mesh("WaterSurface", "Plane", (0, 0, 0), (7000, 6000, 100), water, collision=False)
    for asset_path, label in (("/Game/WeatherContent/BP_WeatherManager.BP_WeatherManager_C", "WeatherManager"),
                              ("/Script/Holodeck.FlashlightManager", "FlashlightManager")):
        cls = unreal.load_class(None, asset_path)
        if not cls:
            raise RuntimeError(f"Missing manager {asset_path}")
        actor = ACTORS.spawn_actor_from_class(cls, unreal.Vector(0, 0, 0))
        if not actor:
            raise RuntimeError(f"Could not spawn manager {asset_path}")
        actor.set_actor_label(label)
    # Editor-only mesh preview; the actual physics AUV is spawned by HoloOcean.
    preview = ACTORS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(-1400, -350, -1030),
                                           unreal.Rotator(pitch=0, yaw=90, roll=0))
    preview.set_actor_label("AUV_EditorPreview_RuntimeSpawnedByPython")
    preview.static_mesh_component.set_static_mesh(unreal.load_asset(
        "/Game/HolodeckContent/Agents/HoveringAUV/HoveringAUVMesh"))
    preview.static_mesh_component.set_collision_profile_name("NoCollision")
    preview.set_editor_property("is_editor_only_actor", True)
    preview.set_actor_hidden_in_game(True)
    camera = ACTORS.spawn_actor_from_class(unreal.CameraActor, unreal.Vector(2700, -3200, -200),
                                           unreal.Rotator(pitch=-13, yaw=140, roll=0))
    camera.set_actor_label("InspectionOverview")
    unreal.EditorLevelLibrary.set_level_viewport_camera_info(camera.get_actor_location(), camera.get_actor_rotation())
    if not LEVELS.save_current_level():
        raise RuntimeError("Map save failed")
    unreal.EditorAssetLibrary.save_directory("/Game/AUVInspection", only_if_is_dirty=True, recursive=True)
    report = {"map": MAP, "actor_count": len(ACTORS.get_all_level_actors()),
              "coordinate_system": "HoloOcean meters: x=UE.x/100, y=-UE.y/100, z=UE.z/100",
              "defects": DEFECTS, "simulation_only": True}
    (HERE / "scene_manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    unreal.log("AUV_BUILD_SUCCESS " + json.dumps(report))


if __name__ == "__main__":
    main()
