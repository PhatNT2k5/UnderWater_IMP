"""Finish the isolated B fixture before inspecting detector output."""
import hashlib
import json
from pathlib import Path

import unreal

project = Path(unreal.Paths.project_dir())
source = project / "Content/AUVInspection/Maps/AUVInspection.umap"
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
target = "/Game/AUVInspection/Maps/AUVInspection_PatchCoreB_20260926_v3"
if not unreal.EditorLevelLibrary.load_level(target):
    raise RuntimeError("Cannot load isolated B map")
world = unreal.EditorLevelLibrary.get_editor_world()
if world.get_outermost().get_name() != target:
    raise RuntimeError("Wrong world loaded")
actors = unreal.EditorLevelLibrary.get_all_level_actors()
if any(actor.get_actor_label().startswith("B_Hole") for actor in actors):
    raise RuntimeError("B fixture already finalized")
decals = {actor.get_name(): actor for actor in actors if isinstance(actor, unreal.DecalActor)}
for name, factor, roll_offset in (("DecalActor_1", 0.8, 20),
                                  ("DecalActor_2", 1.2, -20),
                                  ("DecalActor_6", 0.8, 15)):
    actor = decals[name]
    scale = actor.get_actor_scale3d()
    actor.set_actor_scale3d(unreal.Vector(scale.x * factor, scale.y * factor, scale.z * factor))
    rotation = actor.get_actor_rotation()
    rotation.roll += roll_offset
    actor.set_actor_rotation(rotation, False)
template = decals["DecalActor_1"]
material = unreal.load_asset("/Game/AUVInspection/Materials/M_PipeBreak")
for label, x, scale in (("B_HoleSmall", 0.0, 0.08), ("B_HoleLarge", 850.0, 0.25)):
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.DecalActor, unreal.Vector(x, -40.0, -1020.0), template.get_actor_rotation())
    if actor is None:
        raise RuntimeError("Cannot spawn B decal")
    actor.set_actor_label(label)
    actor.set_actor_scale3d(unreal.Vector(scale, scale, scale))
    component = actor.get_component_by_class(unreal.DecalComponent)
    component.set_editor_property("decal_size", unreal.Vector(128, 256, 256))
    component.set_decal_material(material)
if not unreal.EditorLoadingAndSavingUtils.save_map(world, target):
    raise RuntimeError("Cannot save B fixture")
inventory = []
for actor in unreal.EditorLevelLibrary.get_all_level_actors():
    if isinstance(actor, unreal.DecalActor):
        inventory.append({"actor": actor.get_name(), "label": actor.get_actor_label(),
                          "location": str(actor.get_actor_location()),
                          "scale": str(actor.get_actor_scale3d())})
if hashlib.sha256(source.read_bytes()).hexdigest() != source_hash:
    raise RuntimeError("Source map changed")
output = project.parent.parent / "auv_inspection/output/validation_B_inventory.json"
output.write_text(json.dumps({"world": target, "defects": inventory,
                              "source_preserved": True}, indent=2), encoding="utf-8")
