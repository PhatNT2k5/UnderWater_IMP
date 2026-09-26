# Robot camera regression fixtures

These are unmodified `camera.png` sensor frames copied from
`output/run_20260923_200549_863948/damage_events/event_NNN/` on 2026-09-23.
Keep these fixtures when cleaning disposable runtime output.

Labels were assigned by visual inspection of the actual camera images:

| Files | Label | Visible feature |
| --- | --- | --- |
| event_001.png | Damage | Single dark hole on front pipe surface |
| event_002.png | Damage | Branching crack on front pipe surface |
| event_003.png | Damage | Second branching crack on front pipe surface |
| event_004.png | Clean | Rear pipe end, flange, lamp reflection |
| event_005.png through event_014.png | Clean | Rear pipe flanges, lamp reflection and surface texture |

The test checks that boxes for the three positive images overlap the visible
damage, not merely that the detector returns a box somewhere in the frame.
Horizontal flips of positive frames test that detection is not disabled based
on which way a feature faces. They do not establish rear-side recall.

These images were used to diagnose and calibrate the filter. They are regression
fixtures, not an independent benchmark for precision or recall. No model was
trained. All images are 640 x 480 pixels.
