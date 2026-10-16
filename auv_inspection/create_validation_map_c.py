"""Run in Unreal Python to create the isolated P8 held-out map C from the saved map A.

Map C keeps map A's structures and moves or adds decal defects to places no detector has seen:
both pipe sides (the back of the pipe never had a defect in A or B), the back face of pier 0 and
the front face of pier 1 at a new height. Positions are fixed here before any capture of map C;
held-out labels are still traced from capture images (the inventory written below only
cross-checks them, as for map B). The source map is never saved; its hash is checked before and
after. Refuses to overwrite an existing target map or inventory.

UE units are centimetres, world = (x, -y, z) / 100. Pipe axis z ~ -1029, radius ~42; pier faces at
y = 650 -/+ 88 (front/back) around x = -/+1000.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import unreal

SOURCE = "/Game/AUVInspection/Maps/AUVInspection"
TARGET = SOURCE + "_PatchCoreC_20261016_v1"
EXPECTED_DECALS = {"DecalActor_1", "DecalActor_2", "DecalActor_6"}  # map A: two pipe cracks, one pier crack
# Existing decals: new location, scale factor, extra roll (deg).
MOVED = {
    "DecalActor_1": ((-1350.0, -40.0, -1020.0), 1.0, 35.0),    # pipe front, x -13.5
    "DecalActor_2": ((450.0, -40.0, -1035.0), 0.9, -30.0),     # pipe front, x 4.5
    "DecalActor_6": ((-960.0, 740.0, -700.0), 0.9, -20.0),     # pier 0 back face, z -7.0
}
# New decals: label, template (rotation, size, material unless overridden), location, scale factor or
# absolute scale, extra roll, material override.
SPAWNED = (
    ("C_PierCrack", "DecalActor_6", (1040.0, 550.0, -640.0), ("factor", 0.8), 25.0, None),  # pier 1 front, z -6.4
    ("C_BackCrack", "DecalActor_2", (1050.0, 40.0, -1010.0), ("factor", 1.0), 20.0, None),  # pipe back, x 10.5
    ("C_BackHole", "DecalActor_1", (-750.0, 40.0, -1020.0), ("absolute", 0.1), 0.0,
     "/Game/AUVInspection/Materials/M_PipeBreak"),                                           # pipe back, x -7.5
)
HOLE_DECAL_SIZE = (128.0, 256.0, 256.0)  # as map B's holes
# A decal paints every surface inside its box (half-depth = decal_size.x * scale.x along its
# projection axis). Decals sit 40 cm from the pipe axis; capping the half-depth at 30 cm keeps a
# back-side decal off the front side (radius ~42 cm) and vice versa.
MAX_HALF_DEPTH_CM = 30.0


def decal_component(actor: unreal.DecalActor) -> unreal.DecalComponent:
    component = actor.get_component_by_class(unreal.DecalComponent)
    if component is None:
        raise RuntimeError(f"No decal component on {actor.get_name()}")
    return component


def set_scale(actor: unreal.DecalActor, x: float, y: float, z: float) -> None:
    depth = decal_component(actor).get_editor_property("decal_size").x
    actor.set_actor_scale3d(unreal.Vector(min(x, MAX_HALF_DEPTH_CM / depth), y, z))


def record(actor: unreal.DecalActor) -> dict:
    location, rotation, scale = actor.get_actor_location(), actor.get_actor_rotation(), actor.get_actor_scale3d()
    component = decal_component(actor)
    material = component.get_decal_material()
    size = component.get_editor_property("decal_size")
    return {"actor": actor.get_name(), "label": actor.get_actor_label(),
            "location_cm": [location.x, location.y, location.z],
            "world_m": [location.x / 100, -location.y / 100, location.z / 100],
            "rotation_deg": [rotation.roll, rotation.pitch, rotation.yaw],
            "scale": [scale.x, scale.y, scale.z], "decal_size": [size.x, size.y, size.z],
            "material": material.get_path_name() if material else None}


def create_map_c() -> None:
    project = Path(unreal.Paths.project_dir())
    original = project / "Content/AUVInspection/Maps/AUVInspection.umap"
    output = project.parent.parent / "auv_inspection/output/validation_C_inventory.json"
    if unreal.EditorAssetLibrary.does_asset_exist(TARGET):
        raise RuntimeError(f"Refusing to overwrite existing map: {TARGET}")
    if output.exists():
        raise RuntimeError(f"Refusing to overwrite {output}")
    before = hashlib.sha256(original.read_bytes()).hexdigest()
    if not unreal.EditorLevelLibrary.load_level(SOURCE):
        raise RuntimeError("Cannot load saved source map")
    world = unreal.EditorLevelLibrary.get_editor_world()
    if not unreal.EditorLoadingAndSavingUtils.save_map(world, TARGET):
        raise RuntimeError(f"Cannot save isolated copy: {TARGET}")
    if not unreal.EditorLevelLibrary.load_level(TARGET):
        raise RuntimeError(f"Cannot load isolated copy: {TARGET}")
    world = unreal.EditorLevelLibrary.get_editor_world()
    if world.get_outermost().get_name() != TARGET:
        raise RuntimeError("Loaded world is not the isolated target")
    decals = {actor.get_name(): actor for actor in unreal.EditorLevelLibrary.get_all_level_actors()
              if isinstance(actor, unreal.DecalActor)}
    if set(decals) != EXPECTED_DECALS:
        raise RuntimeError(f"Map A decals differ from the expected set: {sorted(decals)}")
    templates = {name: {"rotation": actor.get_actor_rotation(), "scale": actor.get_actor_scale3d(),
                        "material": decal_component(actor).get_decal_material(),
                        "size": decal_component(actor).get_editor_property("decal_size")}
                 for name, actor in decals.items()}

    for name, (location, factor, roll) in MOVED.items():
        actor = decals[name]
        actor.set_actor_location(unreal.Vector(*location), False, False)
        scale = templates[name]["scale"]
        set_scale(actor, scale.x * factor, scale.y * factor, scale.z * factor)
        rotation = templates[name]["rotation"]
        actor.set_actor_rotation(unreal.Rotator(rotation.roll + roll, rotation.pitch, rotation.yaw), False)

    for label, template_name, location, (scale_kind, scale_value), roll, material_path in SPAWNED:
        template = templates[template_name]
        rotation = template["rotation"]
        actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
            unreal.DecalActor, unreal.Vector(*location),
            unreal.Rotator(rotation.roll + roll, rotation.pitch, rotation.yaw))
        if actor is None:
            raise RuntimeError(f"Cannot spawn {label}")
        actor.set_actor_label(label)
        component = decal_component(actor)
        if material_path:
            material = unreal.load_asset(material_path)
            if material is None:
                raise RuntimeError(f"Cannot load {material_path}")
            component.set_editor_property("decal_size", unreal.Vector(*HOLE_DECAL_SIZE))
        else:
            material = template["material"]
            component.set_editor_property("decal_size", template["size"])
        component.set_decal_material(material)
        if scale_kind == "factor":
            scale = template["scale"]
            set_scale(actor, scale.x * scale_value, scale.y * scale_value, scale.z * scale_value)
        else:
            set_scale(actor, scale_value, scale_value, scale_value)

    if not unreal.EditorLoadingAndSavingUtils.save_map(world, TARGET):
        raise RuntimeError(f"Cannot save map C: {TARGET}")
    inventory = [record(actor) for actor in unreal.EditorLevelLibrary.get_all_level_actors()
                 if isinstance(actor, unreal.DecalActor)]
    if hashlib.sha256(original.read_bytes()).hexdigest() != before:
        raise RuntimeError("Source map changed unexpectedly")
    output.write_text(json.dumps({"world": TARGET, "source_sha256": before, "source_preserved": True,
                                  "decals": inventory}, indent=2), encoding="utf-8")
    unreal.log(f"Map C saved: {TARGET}; {len(inventory)} decals; inventory {output}")


create_map_c()
