"""Run in Unreal Python to create isolated clean and B maps from saved A."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import unreal


def create_variants() -> None:
    source = "/Game/AUVInspection/Maps/AUVInspection"
    targets = {
        "clean": source + "_PatchCoreClean_20260926_v3",
        "test_b": source + "_PatchCoreB_20260926_v3",
    }
    project = Path(unreal.Paths.project_dir())
    original = project / "Content/AUVInspection/Maps/AUVInspection.umap"
    before = hashlib.sha256(original.read_bytes()).hexdigest()
    report = {"source_sha256": before, "variants": {}}
    for role, target in targets.items():
        if unreal.EditorAssetLibrary.does_asset_exist(target):
            raise RuntimeError(f"Refusing to overwrite existing map: {target}")
        if not unreal.EditorLevelLibrary.load_level(source):
            raise RuntimeError("Cannot load saved source map")
        world = unreal.EditorLevelLibrary.get_editor_world()
        if not unreal.EditorLoadingAndSavingUtils.save_map(world, target):
            raise RuntimeError(f"Cannot save isolated copy: {target}")
        if not unreal.EditorLevelLibrary.load_level(target):
            raise RuntimeError(f"Cannot load isolated copy: {target}")
        world = unreal.EditorLevelLibrary.get_editor_world()
        if world.get_outermost().get_name() != target:
            raise RuntimeError("Loaded world is not the isolated target")
        actors = unreal.EditorLevelLibrary.get_all_level_actors()
        decals = [actor for actor in actors if isinstance(actor, unreal.DecalActor)]
        inventory = []
        for actor in decals:
            name = actor.get_name()
            if role == "clean":
                if not unreal.EditorLevelLibrary.destroy_actor(actor):
                    raise RuntimeError(f"Cannot remove decal from copy: {name}")
                continue
            locations = {
                "DecalActor_1": (-450.0, -40.0, -1020.0),
                "DecalActor_2": (350.0, -40.0, -1020.0),
                "DecalActor_6": (990.0, 550.0, -820.0),
            }
            if name not in locations:
                raise RuntimeError(f"Unexpected decal in saved A: {name}")
            actor.set_actor_location(unreal.Vector(*locations[name]), False, False)
            position = actor.get_actor_location()
            inventory.append({"actor": name, "label": actor.get_actor_label(),
                              "location_cm": [position.x, position.y, position.z]})
        if not unreal.EditorLoadingAndSavingUtils.save_map(world, target):
            raise RuntimeError(f"Cannot save variant: {target}")
        report["variants"][role] = {"world": target, "decals": inventory}
    after = hashlib.sha256(original.read_bytes()).hexdigest()
    if after != before:
        raise RuntimeError("Source map changed unexpectedly")
    report["source_preserved"] = True
    output = project.parent.parent / "auv_inspection/output/validation_maps_20260926.json"
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")


create_variants()
