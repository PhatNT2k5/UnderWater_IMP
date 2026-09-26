"""Inspect damage materials in Unreal without modifying assets."""
import json
from pathlib import Path

import unreal

rows = {}
for name in ("M_HairCrack", "M_PipeBreak", "M_Crack"):
    material = unreal.load_asset("/Game/AUVInspection/Materials/" + name)
    rows[name] = {
        "class": material.get_class().get_name(),
        "domain": str(material.get_editor_property("material_domain")),
        "blend": str(material.get_editor_property("blend_mode")),
    }
output = Path(unreal.Paths.project_dir()).parent.parent / "auv_inspection/output/validation_materials.json"
output.write_text(json.dumps(rows, indent=2), encoding="utf-8")
