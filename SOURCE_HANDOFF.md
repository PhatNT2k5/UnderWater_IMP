# Source handoff — UnderwaterDemo

> Tài liệu bàn giao dành cho AI/agent và thành viên mới. Hãy đọc file này trước khi sửa source.
>
> Cập nhật gần nhất: **2026-10-16** - Dashboard chạy được ứng viên P8 (`run_dashboard.py --p8`, service `--p8-rules`); phát lại seed 3 qua `PatchCoreClient` cho cảnh báo trùng harness `dino_floor_bgsr` (3/3 tick và box). Ứng viên P8 trên tập phát triển `dino_floor_bgsr`: 90,9% recall, 0,74 báo nhầm/100 m (offline, chưa heldout, chưa live; dashboard chưa có tùy chọn cổng P8). P8.2 phần 2 (offline, từ cache): `dino_floor_b` 73,1%/0,19, `dino_floor_br` 70,3%/0,02, `dino_floor_bgr` 93,1%/1,78 báo nhầm/100 m (marine snow 5 chiếm 253/306). P8.2: cache lưới token v2 cho thí nghiệm offline (`robustness/score_cache.py`, `benchmark --score-cache`, phát lại khớp benchmark), bằng chứng chỉ từ vùng ≥ 196 px (`without_small_hits`, hậu tố `r`). P8.2 phần 1 (offline, 12 capture phát triển): cổng P8 recall 95,4% nhưng 5,6 báo nhầm/100 m (ứng viên P7: 73,7%, 0,29); giới hạn trụ bỏ 17 báo nhầm chân trụ, không mất recall. P8.2 (code): cổng P8 tùy chọn (`GATE_MIN_REGION_PX`, bỏ tiêu chí một vùng lớn), `GeometryParams.pier_floor_z` + `calibration/geometry_v3.json`, model v2 khai `geometry_file`, harness `_bg` và `dino_floor`. Vì `live_service.py` và `geometry.py` đổi, cổng D11 không còn bật mặc định v2 trong dashboard cho tới khi P8 được đăng ký (dùng `--v2-model` để chạy v2). P8.1 chẩn đoán offline (`output/p8_diagnosis/`, không sửa code): marine snow mất recall vì cổng lan tỏa (> 6 vùng), báo nhầm chân trụ là mặt đáy trong ROI (`geometry.PIER_Z_RANGE` thấp hơn đáy ≈ -10,4). D11: cổng phê duyệt kiểm thêm SHA256 code chấm điểm (`approval_gate.SCORING_CODE`); mặc định v2 vẫn hợp lệ, cổng v1 không còn tự chọn PatchCore v1 vì báo cáo B cũ không có hash code. Live P7 với v2 mặc định: map A 3/3 vết, 0 báo nhầm (`session_20261015_103902_679289`); map B 4/5 vết, 2 báo nhầm theo quy tắc chấm, 1 báo nhầm nằm trên vết nứt trụ khi xem ảnh (`session_20261015_105712_694396`). Dashboard mặc định dùng detector v2 + lề mép ảnh khi file khớp SHA256 đăng ký P7 (`approval_gate.registered_candidate_matches()`), `--v1` chọn PatchCore v1, `--world` chọn map (live map B). P7 offline: ứng viên v2 + lề mép ảnh **không đạt** nghiệm thu (recall 72,3% < 90%; báo nhầm 0,345/100 m và FPR ô 0,031% đạt; đối chứng v1.4 58,9%, 2,89/100 m), `output/benchmark_p7_acceptance/acceptance_report.json`. Nhãn map B (`inventories/map_B.json`, 5 vết) đã khóa. P7 đã đăng ký trước (`robustness/acceptance_preregistration.json`, `acceptance.py`). Live v2 + lề mép ảnh (`session_20261014_161937_404843`): 3/3 vết, 0 báo nhầm. P6 dừng sau P6.1 (lợi ích tối đa 2-4/15 vết sót). P6.1: đo vùng bằng chứng mơ hồ (`SurfaceEvidence.ambiguous_regions()`, báo cáo `ambiguity` trong harness). Kết thúc P4: ứng viên v2 + lề mép ảnh; biến thể kết hợp NFAD + Mahalanobis không tốt hơn. P4.3: biến đổi đặc trưng NFAD và Mahalanobis cho v2 (`detector_v2/transforms.py`, `derive_model.py`), benchmark 6 capture; mặc định không đổi. P4 phần 4: benchmark tập phát triển 6 capture; v2 dùng lề 24 px cả ở mép ảnh (`--border-margin`), mặc định trong dashboard `--v2-model`. Live v2 (`session_20261013_091452_126695`): 3/3 vết map A, 1 báo nhầm trên vân bê tông trụ 1; 4 capture heldout mới (seed 3-6) mở rộng tập phát triển. P4 phần 3: benchmark lại với hình học v2 (v2 + suy giảm mức 1: 17/21 vết, 2 báo nhầm trên 14 lượt tập phát triển); dashboard có tùy chọn `--v2-model` (opt-in, chưa chạy live). Hình học v2 làm mặc định (offset camera theo socket HoveringAUV), nhãn map A tính lại, calibration bề mặt `surface_v2.json` và bank v2 `_g2` đang dựng lại. P4 phần 2: bank DINOv2 thật (4 capture train seed 21-24) và benchmark tập phát triển; cổng lan tỏa đếm hit của quy tắc bề mặt. P4 phần 1: package `auv_inspection/detector_v2/` (DINOv2 kNN) tích hợp vào service, chưa có bank thật; nhãn `A_pipe_front_2` thành đoạn. P5 xong và đã chạy live (v1.4: 3/3 vết, 0 báo nhầm, 0 báo trùng trên map A): quy tắc bằng chứng trên bề mặt (k = 3 lượt nhìn trên ô 10 cm, ngưỡng pixel AND ngưỡng tương đối theo tầng) là mặc định PatchCore của dashboard; calibration từ 3 capture sạch mới; cổng `diffuse_anomaly` đo độ phân tán (đã sửa sau live, chưa chạy live lại); không chỉnh map thủ công.

## 1. Mục tiêu và phạm vi

Project mô phỏng AUV khảo sát đường ống và trụ cầu dưới nước bằng HoloOcean + Unreal Engine 5.3. AUV có thể:

- Chạy tự động theo tuyến cố định bám hai phía đường ống và bay quanh hai trụ cầu.
- Điều khiển thủ công bằng bàn phím.
- Hiển thị camera trực tiếp, bật hai đèn trước, phân tích vết nứt trên ống và ghi telemetry/report/bằng chứng cảnh báo.
- Mở dashboard Tkinter để ưu tiên độ mượt của cửa sổ Unreal nhúng trực tiếp, kèm sơ đồ tuyến XYZ 3D, camera robot, ba bước xử lý ảnh và marker hư hại.
- Dựng lại map mẫu bằng Unreal Python commandlet khi thực sự cần.

Source do project quản lý trực tiếp nằm chủ yếu ở root, `auv_inspection/` và dashboard Tkinter `auv_dashboard/`. Thư mục `holoocean/` là checkout framework upstream; chỉ có một thay đổi C++ riêng của project được ghi rõ trong mục 6.

## 2. Cấu trúc quan trọng

```text
UnderwaterDemo/
├── AGENTS.md                         # Quy tắc cho AI/agent làm việc trong repo
├── SOURCE_HANDOFF.md                 # Tài liệu đang đọc; phải cập nhật cùng source
├── PROJECT_STATUS_AND_ROADMAP.md     # Báo cáo hiện trạng, kết quả và kế hoạch tiếp theo
├── GENERALIZATION_PLAN.md            # Kế hoạch tổng quát hóa P0-P7, tiến độ, tiêu chí nghiệm thu
├── README.md                         # Setup repo chia sẻ, overlay HoloOcean và chạy dashboard
├── scripts/setup_project.ps1         # Clone/pin HoloOcean và cài overlay/artifact trên máy mới
├── holoocean_overlay/                # Map/asset/C++/plugin riêng để áp dụng lên HoloOcean upstream
├── patchcore_artifacts/              # Artifact PatchCore portable, quản lý bằng Git LFS
├── auv_dashboard/                    # Dashboard Tkinter hiện hành
│   ├── README.md                     # Cách chạy, điều khiển, kiến trúc và giới hạn
│   ├── __init__.py                   # Package dashboard
│   ├── run_dashboard.py              # CLI, DPI, Tk mainloop, live smoke test
│   ├── start_dashboard.cmd           # Launcher nhấp đúp dùng Python mainenv (DASHBOARD_PYTHON/conda)
│   ├── app.py                        # UI, queue, lifecycle, bằng chứng kiểm thử
│   ├── bridge.py                     # Adapter runtime trong worker riêng
│   ├── viewport.py                   # Nhúng cửa sổ Unreal theo PID sở hữu
│   ├── widgets.py                    # Camera tile và sơ đồ tuyến XYZ 3D tương tác
│   ├── test_dashboard.py             # Test queue, codec, phép đổi trục camera
│   └── output/session_*/             # Kết quả và audit riêng của dashboard
├── auv_inspection/
│   ├── README.md                     # Hướng dẫn sử dụng AUVInspection
│   ├── PATCHCORE_GUIDE_VI.md          # Giải thích tiếng Việt về dữ liệu và pipeline PatchCore
│   ├── NOISE_ROBUSTNESS_TODO.md        # Backlog độ bền PatchCore trước nhiễu quan sát
│   ├── robustness/degradation.py       # Suy giảm ảnh có seed, 7 yếu tố × 5 mức (P1)
│   ├── robustness/tests/test_degradation.py # Tính tái lập và tính đơn điệu theo mức
│   ├── robustness/conditions.py        # Điều kiện mô phỏng theo seed: train/heldout (P1)
│   ├── robustness/tests/test_conditions.py # Khoảng train/heldout, route an toàn, lịch chụp
│   ├── robustness/geometry.py          # Camera pinhole, pixel <-> điểm trên ống/trụ (P1, nền cho P2)
│   ├── robustness/defect_inventory.py  # Vị trí vết vật lý, khớp cảnh báo với vết
│   ├── robustness/inventories/map_A.json # 3 vết của map A (proposed, đã duyệt bằng ảnh heldout)
│   ├── robustness/inventories/map_B.json # 5 vết của map B (P7, khóa 2026-10-14)
│   ├── robustness/metrics.py           # Wilson, quãng đường khảo sát, tỷ lệ trên 100 m
│   ├── robustness/evaluate_capture.py  # Phát lại capture qua detector, chấm theo vết vật lý
│   ├── robustness/benchmark.py         # Lưới detector × capture × điều kiện, bảng tổng hợp
│   ├── run_inspection.py             # Entry point chạy map và điều khiển AUV
│   ├── crack_detection.py            # Tiền xử lý ảnh và phát hiện nghi vấn vết nứt
│   ├── tests/test_crack_detection.py # Regression test detector bằng ảnh tổng hợp
│   ├── tests/test_camera_regression.py # Regression bằng 14 frame camera thật
│   ├── tests/test_clean_structure_capture.py # Kiểm tra PNG/metadata thu ảnh ống và trụ
│   ├── tests/test_find_editor.py       # Thứ tự tìm UnrealEditor.exe
│   ├── tests/data/pipe_views/          # Fixture/nhãn được giữ khi dọn output
│   ├── test_detection_gate.py         # Regression test phạm vi bật detector camera
│   ├── inspection_route.py            # Sinh tuyến khảo sát cố định
│   ├── test_inspection_route.py       # Unit test hình học của tuyến
│   ├── check_flashlight_runtime.py    # Harness kiểm tra tắt/bật đèn runtime
│   ├── check_detection_runtime.py     # QA hai mặt ống, tự tiếp tục sau cảnh báo
│   ├── build_map.py                   # Unreal Python generator map cũ (launcher rebuild.py không có trong repo)
│   ├── create_validation_maps.py      # Unreal Python: tạo bản sao map sạch/B, giữ nguyên map A
│   ├── finalize_validation_b.py       # Unreal Python: hoàn thiện năm vết của map B
│   ├── inspect_validation_assets.py   # Unreal Python read-only: đọc domain/blend material hư hại
│   ├── scenario.json                  # Scenario runtime, agent, sensor, exposure
│   ├── scene.json                     # Input cho build_map.py
│   ├── scene_manifest.json            # Manifest của lần build map cũ
│   ├── ROUTE_VALIDATION.md            # Bằng chứng/giới hạn của tuyến hiện tại
│   ├── VALIDATION.md                  # Bằng chứng lịch sử cho map/tuyến cũ 2026-09-19
│   └── output/
│       ├── run_*/                     # Kết quả runtime; có thể là dữ liệu lịch sử
│       └── backups/                   # Backup .umap/config; không xóa tùy tiện
├── holoocean/
│   ├── client/src/holoocean/          # Python client dùng trực tiếp từ checkout
│   └── engine/
│       ├── Holodeck.uproject          # Unreal project cần mở/build
│       ├── Plugins/FunplayMCP/        # MCP editor-only, thuần Python, dùng với UE 5.3
│       ├── Content/AUVInspection/     # Map và asset nhị phân của project
│       └── Source/Holodeck/            # Source C++ HoloOcean
├── worlds/2.3.0/worlds/Ocean/         # Package Ocean standalone đã tải sẵn
└── Assets/                            # Texture/asset nguồn cho vết nứt, vỡ ống
```

Không coi `worlds/` là bản build của `AUVInspection`: package Ocean có sẵn không chứa map tùy chỉnh này. Map thực tế là:

```text
holoocean/engine/Content/AUVInspection/Maps/AUVInspection.umap
```

## 3. Luồng chạy chính

```text
run_inspection.py
  ├─ đọc scenario.json
  ├─ nhập ROUTE từ inspection_route.py
  ├─ tìm UnrealEditor.exe 5.3
  ├─ mở Holodeck.uproject + map AUVInspection ở chế độ -game
  ├─ kết nối HoloOcean bằng named semaphore/UUID
  ├─ spawn HoveringAUV theo scenario
  ├─ bật flashlight1 + flashlight2
  ├─ auto: gửi pose target từ ROUTE
  │   manual: cập nhật pose target từ bàn phím
  ├─ khi camera nhìn ống: CLAHE → làm mượt → tương phản tối cục bộ → lọc vùng → xác nhận 3 frame
  ├─ khi có cảnh báo: ghi ảnh/thời gian/tọa độ; dashboard giữ AUV 5 giây rồi tự tiếp tục
  │   GUI trực tiếp: giữ AUV đến khi nhấn Space; headless auto: lưu bằng chứng rồi kết thúc lượt chạy
  └─ ghi output/run_<timestamp>/
      ├─ telemetry.json
      ├─ report.json
      ├─ damage_events/event_001/{camera,preprocessed,mask,annotated}.png + event.json
      └─ unreal.log
```

Source chỉ lưu frame camera khi có cảnh báo; không suy luận loại/mức độ hư hỏng. Preview camera chỉ xuất hiện khi không dùng `--headless`.

Ngoại lệ là `--capture-clean-structures`: bỏ qua detector/cảnh báo, chạy auto route, sau 30 tick khởi động lưu frame `InspectionCamera` gốc mỗi 10 tick đủ điều kiện trong các đoạn quét hai mặt ống và vòng khảo sát bốn tầng của hai trụ. Output tách tại `output/clean_structures_<timestamp>/` với `images/{pipe_front,pipe_back,pier_0,pier_1}/`, `frames.jsonl`, telemetry/report/log. `--capture-clean-pipe` vẫn chỉ chụp ống. Hai chế độ không kiểm tra map sạch; người dùng tự chuẩn bị map và duyệt ảnh trước khi dùng để học bề mặt bình thường.

Luồng dashboard hiện hành: `auv_dashboard/run_dashboard.py` tạo UI Tkinter, sau đó spawn `auv_dashboard.bridge.run_worker()`. Worker import và gọi chính `run_inspection.run()`; adapter chuyển `cv2.imshow`/`waitKey` và phím sang queue, giữ detector/controller gốc, rồi lưu kết quả vào folder phiên. Các thay thế runtime chỉ tồn tại trong worker.

Dashboard Tkinter trong `auv_dashboard/` nhúng đúng cửa sổ Unreal do worker sở hữu bằng Win32, vẽ route XYZ trên Canvas và nhận camera robot trực tiếp từ `InspectionCamera`. Preview mục tiêu 12 FPS; ảnh cũ được bỏ nếu UI chậm, còn cảnh báo/hoàn tất/lỗi dùng queue riêng. Ba ô dưới thể hiện CLAHE/mask/annotation ở Classical hoặc ROI/heatmap/annotation ở PatchCore; ảnh gốc đã là camera robot lớn. Khi có cảnh báo, các ô giữ đúng PNG đã lưu của event và ghi tick. Pause từ UI tạm ngừng bước mô phỏng; cảnh báo giữ AUV tại vị trí 5 giây rồi tự tiếp tục, còn Space/nút Tiếp tục chỉ bỏ qua thời gian chờ. Mặc định hiện là PatchCore vì báo cáo B offline đạt và hash artifact khớp; chưa qua live Unreal, người dùng tự test dashboard.

## 4. API/hàm Python theo từng file


### `auv_inspection/inspection_route.py`

Không đọc/ghi Unreal asset. File này tạo tuyến cố định từ tọa độ map được kiểm kê ngày 2026-09-22.

Các hằng hình học quan trọng:

- Ống: `x = -18.01..15.11 m`, `z = -10.3 m`, offset hai bên `2.0 m`.
- Trụ: tâm `x = -10 hoặc 10 m`, `y = -6.5 m`, bán kính quỹ đạo `2.8 m`.
- Các tầng trụ: `z = -9.2, -6.8, -4.4, -2.0 m`.
- Khoảng lookahead: `ROUTE_LOOKAHEAD_M = 1.2`.
- `Waypoint = tuple[str, list[float]]`; pose có dạng `[x, y, z, roll, pitch, yaw]`.

Hàm:

- `angle_delta(target: float, current: float) -> float`
  - Chuẩn hóa sai lệch góc về khoảng `[-180, 180)`.
- `advance_station(route, station, location, lookahead_m=1.2) -> tuple[int, list[str]]`
  - Bỏ qua các waypoint trung gian đã nằm trong bán kính lookahead để AUV chuyển động liên tục.
  - Không tự vượt qua waypoint cuối; trả về index mới và danh sách tên đã đi qua.
- `build_route(pipe_offset=PIPE_OFFSET, pier_radius=PIER_RADIUS) -> list[Waypoint]`
  - Dùng helper cục bộ `append(...)` để nội suy đoạn dài thành bước tối đa khoảng `0.8 m` và nội suy yaw theo đường ngắn nhất.
  - Đi mặt trước ống, vòng ngoài đầu ống, quay lại mặt sau, rồi thực hiện bốn vòng đủ quanh mỗi trụ.
  - Camera luôn được hướng vào bề mặt cần quan sát. Mặc định cho đúng route đã validate; khoảng cách khác chỉ dùng cho capture ngẫu nhiên hóa (số waypoint nội suy đổi theo độ dài đoạn, bán kính trụ trên khoảng 3,07 m tách mỗi cung 15° thành hai waypoint).
- `STRUCTURE_BOXES`, `CLEARANCE_MARGIN_M`: hộp bao ống/trụ/móng và biên an toàn 0,65 m, trước đây nằm trong test.
- `smooth_noise(count, rng)`: tổng ba sóng sin chu kỳ 15-60 waypoint, chuẩn hóa về [-1, 1], tránh target zig-zag.
- `perturb_route(route, rng, depth_jitter_m, yaw_jitter_deg)`: cộng lệch độ sâu và yaw mượt; giữ nguyên tên và số waypoint.
- `clearance_violations(route, margin_m=0.65)`: lấy mẫu 21 điểm mỗi đoạn, trả các điểm đi vào hộp bao đã nới biên.
- `ROUTE`
  - Giá trị module-level được tạo ngay khi import bằng `build_route()`; hiện có 359 waypoint theo validation hiện hành.

Nếu di chuyển ống/trụ trong editor, phải cập nhật các hằng hình học, chạy unit test và chạy thực tế lại. Đây không phải thuật toán tránh vật cản online.

### `auv_inspection/crack_detection.py`

Module thị giác cổ điển, tham khảo pipeline và nhóm kỹ thuật trong bài tổng quan Mohan & Poobal (2018). Không phải model đã huấn luyện hoặc thuật toán định lượng accuracy của bài báo.

- `CrackCandidate`: bounding box `(x, y, width, height)`, diện tích pixel và score; `CrackAnalysis`: ảnh CLAHE, mask nhị phân và tuple ứng viên.
- `CrackTracker(required_frames=3, max_gap_px=60)`: `update(analysis)` yêu cầu ứng viên score ≥ 15 trong 3 frame liên tiếp, tâm không lệch quá 60 px; `reset()` xóa chuỗi khi rời vùng ống hoặc tiếp tục sau cảnh báo.
- `preprocess_image(frame)`: kiểm tra ảnh BGR `uint8`, đổi grayscale và tăng tương phản cục bộ bằng CLAHE.
- `_detect_large_central_hole(preprocessed)`: xét vùng rộng quanh tâm ống (`x=25..75%`, `y=32..80%`). Chỉ tạo ứng viên khi lõi giữa ảnh có ít nhất `68%` pixel CLAHE `≤45`, median `≤38`, đồng thời percentile 90 của vùng rộng `≥70` để chứng minh vẫn có bề mặt được chiếu sáng. Closing 9×9 + opening 5×5 tạo vùng rỗng liên tục; component phải phủ ít nhất `12%` ROI, đủ rộng/cao và giao với lõi tâm. Điều kiện sáng xung quanh ngăn ảnh tối toàn cục bị gọi là lỗ.
- `detect_cracks(preprocessed)`: nếu nhánh lỗ lớn tạo ứng viên thì trả ứng viên đó. Nhánh nứt tính Gaussian 5×5 và nền Gaussian `sigma=9` trên **toàn frame trước khi cắt ROI**, tránh biên phản chiếu giả do lọc ảnh đã cắt. Sau đó xét ROI `x=35..65%`, `y=48..75%`, ngưỡng đáp ứng tối `18`, closing 3×3. Component phải là vết tối liên tục (`area≥500`, density `≤0.65`) hoặc hư hại tối rộng (`area≥280`, rộng/cao `≥25`, density `≤0.45`, mức CLAHE trung bình `≤65`); loại dải quá dài/hẹp. Bổ sung điều kiện một lõi tối đậm **liên thông** (đáp ứng `≥40`) chiếm ít nhất `max(64 pixel, 25% area)` của component. Nhiều đốm texture rời rạc không được cộng thành lõi. Score/output schema giữ nguyên; trả `CrackAnalysis`.
- `analyze_frame(frame)`: chạy tiền xử lý rồi tìm ứng viên; `draw_detections(frame, analysis)`: vẽ bounding box trên bản sao ảnh, không sửa frame sensor.

### `auv_inspection/run_inspection.py`

Entry point chính của hệ thống.

- `class EditorEnvironment(HoloOceanEnvironment)`
  - Override property `_timeout` thành 60 giây để giới hạn thời gian chờ khi kết nối process Unreal editor game.
- `launcher_engine_dir() -> Path | None`
  - Đọc `%PROGRAMDATA%\Epic\UnrealEngineLauncher\LauncherInstalled.dat`, trả thư mục cài `UE_5.3`; trả `None` nếu thiếu file hoặc không có bản ghi.
- `registry_engine_dir() -> Path | None`
  - Đọc `InstalledDirectory` trong `HKLM\SOFTWARE\EpicGames\Unreal Engine\5.3` (`ENGINE_REGISTRY_KEY`); trả `None` nếu không có key hoặc không phải Windows.
- `find_editor(explicit: str | None) -> Path`
  - Thứ tự: `--editor`, biến môi trường `AUV_UNREAL_EDITOR` (`EDITOR_ENV_VAR`), Epic Launcher, rồi registry. Hai nguồn cuối ghép `Engine/Binaries/Win64/UnrealEditor.exe`.
  - Xác nhận file tồn tại; ném `FileNotFoundError` (thông báo nêu `--editor`/`AUV_UNREAL_EDITOR`) nếu không tìm thấy. Dashboard luôn gọi với `editor=None` nên phụ thuộc ba nguồn sau.
- `is_key_pressed(key_code: int) -> bool`
  - Dùng `win32api.GetAsyncKeyState`; trả về trạng thái giữ phím Windows virtual-key.
- `update_manual_target(target, delta_seconds, move_speed, yaw_speed, env_min, env_max) -> np.ndarray`
  - Copy pose target hiện tại rồi cập nhật theo phím.
  - `W/S` tiến/lùi theo heading; `A/D` strafe; `R/F` lên/xuống; `Q/E` yaw.
  - Chuẩn hóa vector di chuyển chéo, clamp vị trí trong biên scenario và chuẩn hóa yaw.
- `enable_inspection_lights(env, intensity=2500, pitch_deg=0) -> None`
  - Bật `flashlight1` và `flashlight2`; mặc định intensity `2500`, beam_width `1000`, pitch/yaw `0` như các giá trị người dùng đã chỉnh. Lượt `--randomize` truyền intensity và pitch đã lấy mẫu.
- `is_pipe_view(mode, station_name, location) -> bool`
  - Kích hoạt detector trên toàn thân ống đã đo: `x=PIPE_X_MIN-0.5..PIPE_X_MAX+0.5 m` (hiện là `-18.51..15.61 m`), `|y|≤3.5 m`, `z=-12..-8.5 m`; auto cần ở `pipe_front_scan` hoặc `pipe_back_scan`, manual phụ thuộc vị trí. Biên cũ `x=-13..13 m` từng bỏ qua lỗ hiện rõ ở `pipe_front_scan_004`.
- `save_damage_event(output, frame, analysis, candidate, mode, tick, station_name, location, event_index) -> dict`
  - Tạo `damage_events/event_NNN/`, lưu `camera.png`, `preprocessed.png`, `mask.png`, `annotated.png`, `event.json` có timestamp ISO theo múi giờ máy, tick, vị trí, bbox và score. Ném lỗi rõ ràng nếu không ghi được ảnh.
- `clean_capture_category(station_name, location) -> str | None`
  - Chọn `pipe_front`/`pipe_back` bằng gate ống hiện có, hoặc `pier_0`/`pier_1` ở waypoint orbit; bỏ qua đoạn tiếp cận và di chuyển giữa các công trình.
- `save_clean_structure_frame(output, frame, tick, station_name, location, yaw, category, rotation_rpy_deg=None) -> dict`
  - Lưu PNG sensor gốc tại `images/<category>/frame_<tick>.png`, nối record JSONL gồm thời gian, tick, station, loại công trình/nhóm ảnh, vị trí, yaw, kích thước và tùy chọn `rotation_rpy_deg` vào `frames.jsonl`. Ném lỗi nếu nhóm không hợp lệ hoặc không ghi được PNG.
- `rotation_rpy_from_pose(pose) -> list[float]`
  - Đổi ma trận PoseSensor thành roll/pitch/yaw để các lượt capture mới có thể dựng lại đúng hướng camera khi preview.
- `load_preview_rows(capture, ticks) -> list[dict]`
  - Đọc pose camera đã lưu theo tick từ `frames.jsonl`, kiểm tra tick duy nhất, đủ vị trí/yaw và ảnh nguồn tồn tại; từ chối tick không có.
- `capture_pose_previews(env, rows, source, output, agent_name, map_hash) -> None`
  - Trong game runtime, teleport AUV đến từng pose đã lưu, đo sai lệch PoseSensor do offset socket rồi hiệu chỉnh vị trí agent thêm một lượt; xác nhận sai lệch vị trí ≤0,05 m/yaw ≤1°, lưu PNG sensor hiện tại và ảnh ghép nguồn/hiện tại cùng `report.json`. Với capture cũ thiếu roll/pitch, dùng 0/0 và chỉ coi ảnh ghép là kiểm tra bằng mắt. Không thay đổi hay lưu `.umap`.
- `run(args: argparse.Namespace) -> None`
  - Đọc `scenario.json`, xác nhận `.umap`, tạo thư mục output có timestamp.
  - Mở Unreal bằng `subprocess.Popen`, đợi named semaphore tối đa 180 giây rồi attach `EditorEnvironment`.
  - Auto mode: dùng `advance_station()`, gửi pose target và chỉ kết thúc khi waypoint cuối đạt `<0.25 m`, yaw `<8°` liên tục 15 tick.
  - Manual mode: gọi `update_manual_target()` mỗi tick và gửi bản sao target cho HoloOcean.
  - Sau 30 tick khởi động camera, phân tích mỗi tick khi nhìn ống; sau 3 frame ứng viên nhất quán, lưu bằng chứng và cảnh báo `POSSIBLE DAMAGE`. Trong GUI trực tiếp, giữ target tại pose hiện tại đến khi nhấn `Space`; dashboard adapter thay hành vi này bằng giữ 5 giây rồi tự tiếp tục, và manual tiếp tục từ pose hiện tại. Headless auto lưu bằng chứng rồi kết thúc.
  - Khóa cảnh báo trùng cho đến khi AUV đi cách vị trí cảnh báo trước ≥2 m. Ghi telemetry mỗi 3 tick; hiển thị camera/box/cảnh báo khi không headless.
  - Tạo `report.json` gồm mode, trạng thái tuyến, station, telemetry, `stopped_by_user`, `stopped_for_damage`, `damage_event_count`, `damage_events`.
  - Trong `finally`: đóng HoloOcean, terminate/kill Unreal nếu cần, đóng semaphore và cửa sổ OpenCV.
  - Với `capture_clean_structures=True`, `capture_clean_pipe=True` hoặc `capture_structures=True`, chỉ cho `auto`; bỏ phân tích hư hại và pause, chọn frame từ route sau warmup mỗi `capture_every_ticks` tick. Chế độ structures lấy cả pipe scan và pier orbit, chế độ pipe chỉ lấy pipe scan. Output `clean_structures_...`, `clean_pipe_...` hoặc `capture_<role>_<state>_...`; report ghi nhóm ảnh, cadence, role/state và SHA256 map cho lượt mới. Không thay đổi map hoặc kiểm chứng nhãn ảnh.
  - Với `--preview-source` và `--preview-ticks`, chỉ mở map đã lưu và chụp vài pose camera chọn từ lượt cũ; tạo `output/preview_poses_*` có ảnh hiện tại, ảnh so sánh nguồn/hiện tại và report pose/hash. Không chạy toàn route, không dùng ảnh preview để hiệu chỉnh/đánh giá.
  - Với `randomize`/`seed` (P1 phần 2): lấy `RunConditions` từ `robustness.conditions`, dùng `conditioned_route()` thay `ROUTE`, bật đèn theo intensity/pitch đã lấy mẫu, gọi `env.set_ocean_currents()` lúc đầu và mỗi giây mô phỏng, chọn tick chụp bằng `CaptureSchedule`; ghi `conditions.json` và khóa `conditions` trong `report.json`. Không truyền tùy chọn thì giữ nguyên hành vi: đọc `ROUTE` của module lúc gọi (harness QA vẫn patch được), lịch chụp `tick % capture_every_ticks`, đèn 2500/0°, không dòng chảy. Ngẫu nhiên hóa chỉ cho auto, không kết hợp preview.
- `main() -> None`
  - Parse `--editor`, `--steps`, `--headless`, `--mode`, `--move-speed`, `--yaw-speed`, ba chế độ capture và `--preview-source` loại trừ nhau, `--preview-ticks`, `--dataset-role`, `--scene-state`, `--capture-every-ticks`, `--randomize {train,heldout}`, `--seed`.
  - Validate số dương, cấm `manual + headless`, yêu cầu `auto` khi thu ảnh sạch, `--randomize` và `--seed` phải đi cùng nhau; sau đó cấu hình logging và gọi `run()`.

### `auv_inspection/patchcore_data/`

Pipeline PatchCore riêng, dùng Python 3.11 trong `.venv-patchcore`; `mainenv` vẫn chạy Unreal/dashboard. Đã cài Anomalib 2.6.2, PyTorch/torchvision CUDA 2.14.0/0.29.0 cu130 và OpenCV GUI 5.0.0.93. GPU RTX 4060 đã nạp backbone pretrained; baseline đã fit trên 552 ảnh sạch. Dashboard đã có ngưỡng và nghiệm thu B offline đạt; PatchCore được chọn mặc định khi hash khớp; kiểm tra import/GPU/offline hoặc preview camera không phải live validation của PatchCore.

- `requirements-patchcore.txt`: Ghi các phiên bản dependency đã dùng cùng PyTorch CUDA index cho việc tái lập môi trường; file này không thay thế kết quả kiểm tra GPU trên máy đích.

- `prepare.py`: `load_capture()` xác nhận report/JSONL/ảnh và kích thước; `choose_keyframes()` lấy sáu mốc theo scan/tầng vòng; `prepare_capture()` tạo manifest, trang review và summary trong folder mới, giữ ảnh gốc; `main()` cung cấp CLI.
- `roi_editor.py`: `edit_polygons()` lưu polygon bề mặt ở 60 ảnh đại diện, cho phép tiếp tục phiên; `main()` mở GUI OpenCV.
- `roi_seed.py`: `suggested_polygon()` tạo đường bao hình học dự kiến từ màu/bố cục camera, `seed()` ghi gợi ý và ảnh ghép để người duyệt xem, `main()` cung cấp CLI.
- `roi_propagate.py`: `transform_polygon()` ghép ORB/RANSAC giữa ảnh đại diện và frame lân cận; `propose()` tạo mask nháp, dùng gợi ý hình học khi ORB lỗi hoặc lệch, có thể lấy polygon từ dataset sạch khác, chỉ tự duyệt keyframe trong chính dataset; `main()` cung cấp CLI. Mask nháp phải duyệt trong `roi_review.py`.
- `roi_audit.py`: `create_sheets()` tạo ảnh ghép overlay toàn bộ mask theo nhóm để QA hàng loạt; `main()` cung cấp CLI.
- `roi_review.py`: `review()` chồng mask lên ảnh thật để duyệt/loại/để sau từng frame, lưu `roi_approved.json`; `main()` mở GUI. Frame thiếu mask hoặc căn chỉnh thất bại không tự thành ảnh sạch hợp lệ.
- `live_roi.py`: `load_references()` chỉ nạp mask sạch đã duyệt (không cần ảnh camera gốc); `nearest_references()` trả tối đa hai tham chiếu cùng nhóm/station gần nhất theo pose; `within_reference_range()` giới hạn 0,5 m/8°; `read_mask()` đọc mask đúng kích thước; `match_roi()` dùng thẳng mask khi pose ≤7 cm/1° (`pose_match`), giữa hai pose tham chiếu thì lấy **giao** hai mask gần nhất (`mask_intersection`, chỉ một tham chiếu thì `nearest_mask`), ROI dưới 1000 pixel trả `roi_too_small`; nhánh căn ORB đã bỏ (P0, 2026-10-08) vì chưa từng được đánh giá và cần ảnh gốc không có trong repo; `audit()` đo độ phủ và IoU so với dataset đã duyệt; `main()` cung cấp CLI audit. Dashboard gọi qua service khi có ngưỡng PatchCore.
- `live_service.py`: `create_session(..., roi_mode="geometry")` kiểm tra ngưỡng cùng model, nạp backbone chung và bốn bank; `geometry` (mặc định từ P2) nạp `load_params()` và không cần ảnh/mask tham chiếu, `reference` nạp mask tham chiếu như P0; dataset tham chiếu vẫn bắt buộc vì cổng phê duyệt hash nó. `select_roi()` chọn ROI theo chế độ, nhận `pose_sigma_m`/`pose_sigma_yaw_deg` tùy chọn trong request; `analyze_request()` nhận PNG/tick/nhóm/station/pose, tìm ROI, chấm điểm, xác nhận cảnh báo ba frame và trả ROI/heatmap/mask/annotation cùng trạng thái lỗi rõ; frame `analysis_unavailable` **không reset tracker** (từ P0), track cũ chỉ bị bỏ theo `max_gap_ticks`; ROI không phủ đủ tile 256 px nào (ví dụ ROI hình học co mạnh do sai số pose lớn) trả `analysis_unavailable` với `reason: no_surface_tiles` thay vì lỗi trong `predict_map`; ma trận score nén chỉ gửi khi có alert hoặc yêu cầu chẩn đoán; `serve()` xử lý JSON-lines stdin/stdout, thông điệp `ready` có `roi_mode`; `main()` cung cấp CLI có `--roi-mode {geometry,reference}`, `--score-margin-px N` và `--diffuse-gate`.
- P3: `Session`/`create_session()` thêm `score_margin_px` (mặc định 0) và `diffuse_gate` (mặc định tắt) để giữ hành vi v1.2 khi không truyền; dashboard truyền giá trị P3. `interior(roi, margin_px, image_border=False)` trả pixel ROI cách mép ROI ít nhất `margin_px` (mặc định mép ảnh không tính là mép, vì bề mặt tiếp tục ra ngoài ảnh; `image_border=True` coi cả mép ảnh là mép, bật bằng `Session.border_margin` / `create_session(..., border_margin=True)` / CLI `--border-margin`, P4 2026-10-13, mặc định tắt); `analyze_request()` đặt NaN cho score ngoài vùng này trước khi tách ứng viên. `DEFAULT_SCORE_MARGIN_PX` = 24 theo trường nhìn của descriptor (lân cận 3×3 ô layer2 stride 8 cộng layer3 stride 16), chọn trước khi đo. `above_threshold_shape(scores, threshold)` trả tỷ lệ ROI vượt ngưỡng tổng (`anomaly_share`), ngoài vùng liên thông lớn nhất (`anomaly_spread`) và của vùng lớn nhất (`largest_region_share`). `is_diffuse(scores, threshold, candidates, relative_threshold=None)` trả (lan tỏa, các tỷ lệ đó); khi có quy tắc bề mặt, `score_request()` truyền `relative_threshold` = `SurfaceCalibration.lowest_threshold(nhóm)`, nên pixel chỉ được đếm khi cũng ≥ ngưỡng đó × median frame (hit của quy tắc bề mặt) và số vùng đếm trên chính mặt nạ này (`regions`); khi bật cổng, frame có `anomaly_spread` > `DIFFUSE_MAX_SHARE` = 5%, hoặc hơn `DIFFUSE_MAX_CANDIDATES` = 6 vùng, hoặc một vùng > `DIFFUSE_MAX_REGION_SHARE` = 25% trả `analysis_unavailable` với `reason: diffuse_anomaly`, ba tỷ lệ, `candidate_count` và **không bước tracker**. Bản đầu (tổng > 5%) đã abstain trên vết lớn ở gần trong live P5, sửa ngày 2026-10-12. Đây không phải "sạch": có thể là môi trường đổi hoặc hư hại diện rộng, dashboard hiển thị cho operator. Mọi frame có tile hợp lệ kèm `quality` từ `robustness.quality.measure()` (chỉ chẩn đoán).
- P5: `score_request(session, request, frame, start)` gom phần kiểm tra request, chọn ROI, chấm điểm, lề và cổng lan tỏa; trả (response, roi, scores, candidates), `scores is None` nghĩa là response `analysis_unavailable` đã hoàn chỉnh. Dùng chung cho service và `calibrate_surface.py` để calibration chấm điểm đúng như runtime. `analyze_request()` = `decode_frame()` + `score_request()` + bước cảnh báo + ảnh minh họa. P4: `Session.scorer` (kiểu `Scorer`) được `create_session()` đặt khi `detector_v2.scorer.is_v2_model(model_dir)`; khi đó không nạp PatchCore/bank v1 (`Session.model = None`), bắt buộc `roi_mode="geometry"`, và `score_request()` gọi `session.scorer(frame, roi, group)` thay `predict_map()`; file ngưỡng vẫn phải trỏ đúng `model_dir`. `ALERT_RULES = ("track", "surface")`: `create_session(..., alert_rule="track", surface_calibration=SURFACE_CALIBRATION_FILE)`; `surface` bắt buộc `roi_mode="geometry"` và tạo `Session.evidence = SurfaceEvidence(load_calibration(...))`. `surface_evidence(calibration_file, thresholds_file, thresholds)` từ chối calibration bề mặt làm với file ngưỡng pixel khác (so SHA256). `surface_step(session, scores, category, position, yaw)` gọi `frame_cells()` và `SurfaceEvidence.observe()`, trả box ảnh của các ô vừa thành cảnh báo mới (bội của `POOL_PX`, `peak_score` là điểm cao nhất trong box) cùng `SurfaceAlert`; response thêm `surface_alerts` (`alert_id`, `category`, `surface_uv_m`). Ở chế độ `surface` tracker ảnh không được dùng. CLI thêm `--alert-rule {track,surface}`, `--surface-calibration`; thông điệp `ready` có `alert_rule`.
- P8 (2026-10-15): cổng P8 tùy chọn. `GATE_MIN_REGION_PX` = 196 (2×2 token v2, 7 px ở scale 2); `above_threshold_shape(..., min_region_px=0)` bỏ vùng nhỏ hơn khỏi số vùng, tổng và spread; `is_diffuse(..., min_region_px=0, region_share=True)`, `region_share=False` bỏ tiêu chí một vùng > 25%. `Session.gate_min_region_px` (0) và `gate_region_share` (True) giữ hành vi cũ khi không truyền; `create_session(..., gate_min_region_px=0, gate_region_share=True)`; CLI `--gate-min-region-px`, `--no-gate-region-share`. Lý do (P8.1): hạt marine snow tạo trung vị 14-25 vùng nhỏ/frame, tiêu chí > 6 vùng gây 97-99% lượt mất hit; tiêu chí > 25% chặn lỗ lớn map B. `model_geometry(model_dir)`: geometry ROI là `calibration/geometry_v2.json` mặc định, hoặc file `geometry_file` mà config model v2 khai (đường dẫn tương đối gốc repo; thiếu file thì lỗi); `create_session` dùng nó cho `Session.geometry`, nên calibration và harness chấm model đó với đúng geometry của nó. Dashboard chưa có tùy chọn cho cổng P8. Thêm `without_small_hits(scores, threshold, relative_threshold, min_region_px)`: bản sao điểm, các vùng mức hit (tuyệt đối VÀ tương đối như cổng đếm) nhỏ hơn `min_region_px` bị hạ xuống ngay dưới ngưỡng pixel, ô vẫn được tính là đã nhìn nhưng không thành hit; `Session.evidence_min_region_px` (0), `create_session(..., evidence_min_region_px=0)`, CLI `--evidence-min-region-px`; `surface_step()` dùng bản sao này khi bật. `is_diffuse(..., spread_all_regions=False)`: khi bật, độ phân tán tính trên vùng mọi cỡ như cổng cũ, chỉ số vùng bỏ vùng nhỏ; `Session.gate_spread_all_regions`, `create_session(..., gate_spread_all_regions=False)`, CLI `--gate-spread-all-regions`. Test: hạt dày đặc 8% frame vẫn bị cổng chặn khi bật. CLI `--p8-rules` (2026-10-16) bật đúng bộ quy tắc của ứng viên P8 `dino_floor_bgsr`: `gate_min_region_px` = `evidence_min_region_px` = `GATE_MIN_REGION_PX`, bỏ tiêu chí một vùng lớn, độ phân tán trên mọi vùng; ghi đè các tùy chọn cổng/bằng chứng riêng.
- `model.py`: `tile_starts()` phủ mép ảnh; `iter_tiles()` chọn ô 256×256 bước 128 có bề mặt; `to_tensor()` dùng RGB/ImageNet normalization; `make_model()` tạo Anomalib PatchcoreModel Wide ResNet50-2 layer2+layer3; `extract_embeddings()` lấy đặc trưng; `surface_grid()` chọn tâm đặc trưng thuộc ROI; `predict_map()` ghép khoảng cách nearest-neighbor theo tọa độ frame gốc; `load_roi()` bắt buộc mask đã duyệt.
- `train.py`: `load_manifest()` từ chối calibration/test/mixed; `frame_embeddings()` chỉ lấy đặc trưng trong ROI; `fit()` dùng reservoir có giới hạn, K-center greedy coreset và lưu bốn memory bank, backbone, cấu hình/phiên bản/hash nguồn; `main()` cung cấp CLI. Frame loại bỏ không tham gia, frame chưa duyệt làm fit dừng rõ lỗi.
- `predict.py`: `load_model()` nạp backbone/bank đúng nhóm; `predict()` ghi camera/ROI/heatmap/ma trận score và metadata không ngưỡng; `main()` cung cấp CLI. Đây là score bất thường chưa hiệu chỉnh, không phải xác suất hư hại.
- `label_damage.py`: `label_dataset()` cho người duyệt gắn ID vết vật lý theo nhóm xuyên frame, box hoặc đường tâm, trạng thái visible/unclear/absent và size class; chỉ sao chép vị trí frame trước khi người duyệt bấm xác nhận; không cho duyệt nhãn visible thiếu hình hợp lệ; `main()` cung cấp CLI. Nhãn được lưu trong `damage_labels.json`.
- `score_dataset.py`: `score_dataset()` nạp bốn bank theo nhóm, ghi ma trận điểm bất thường và thời gian xử lý cho từng frame có mask đã duyệt; `main()` cung cấp CLI. Chưa dùng score này làm cảnh báo khi thiếu hiệu chỉnh.
- `compare_clean.py`: `compare()` đối chiếu frame cùng tick/nhóm của capture sạch và mixed, lưu vùng thay đổi cùng ảnh ghép để hỗ trợ gắn nhãn; chỉ dùng khi hai route thực sự căn đúng, không phải detector triển khai.
- `label_from_difference.py`: `centerline()` ước lượng đường tâm từ pixel đổi; `propose()` tạo nhãn nháp visible/unclear/absent với ID do người đánh dấu cung cấp; `main()` cung cấp CLI. Không dùng nhãn nháp để hiệu chỉnh nếu chưa duyệt và tách đúng vết vật lý.
- `reconcile_inventory.py`: `reconcile()` nhận manifest thay đổi và inventory decal từ editor để tạo gợi ý riêng cho từng ID vật lý theo nhóm/khoảng tick; không tự vẽ hình khi nhiều vết cùng nhóm và giữ `review_status=proposed`; `main()` nhận ba đường dẫn CLI. File `damage_label_proposals.json` không phải nhãn đã duyệt.
- `alerts.py`: `extract_candidates()` lấy vùng score vượt ngưỡng với diện tích tối thiểu hai pixel; `AlertTracker.step()` xác nhận ba frame theo quỹ đạo chuyển động ảnh (tốc độ tối đa 13 px/tick, sai số dự đoán tối đa 60 px), reset khi đổi nhóm/gap tick. Quy tắc cũ tâm đứng yên 35 px bỏ cả hai vết ống khi AUV đi ngang.
- `tests/test_alert_tracker.py`: Kiểm tra vết di chuyển khoảng 95 px mỗi 10 tick vẫn được xác nhận đúng một lần, nhưng bước nhảy sang vùng xa hoặc đổi nhóm không được nối thành cảnh báo.
- `approval_gate.py`: `file_sha256()` hash file; `fingerprint()` hash danh sách file theo tên tương đối và nội dung; `model_fingerprint()` buộc backbone/config/bốn bank; `reference_fingerprint()` buộc manifest/summary/trạng thái ROI/toàn bộ mask; `SCORING_CODE` (17 file: `live_service.py` và mọi module project nó nạp: `alerts`, `live_roi`, `model`, `predict`, `detector_v2/*`, `robustness/{geometric_roi,geometry,quality,surface,surface_evidence}`, `inspection_route`, các `__init__`); `code_sha256(path)` hash nội dung sau khi đổi CRLF thành LF (working tree trộn LF/CRLF); `code_hashes(root, files)`; `code_matches(recorded, root, required)` cần bản ghi phủ mọi file bắt buộc và mọi hash còn khớp. `approval_matches(..., code_root=None)` chỉ cho dashboard mặc định PatchCore khi báo cáo B đạt đủ bốn điều kiện và khớp đường dẫn/hash ngưỡng, model, tham chiếu **và `code_sha256`** (D11); báo cáo cũ không có trường này nên trả False. `registered_candidate_matches(model_dir, registration_file, root)` (2026-10-15) trả True khi `model_dir` đúng thư mục ứng viên trong `acceptance_preregistration.json`, `code_sha256` của đăng ký khớp code hiện tại (`required_code`, mặc định `SCORING_CODE`) và mọi file trong `candidate.sha256` còn khớp; chỉ xác nhận artifact là bản đã chấm trên dữ liệu heldout, không phải đã đạt nghiệm thu (P7 không đạt); lỗi đọc trả False.
- `calibrate.py`: `load_scored()` kiểm tra role/state và manifest; `load_maps()` nạp score; `detect_events()` áp dụng tracker; `load_labels()` yêu cầu đủ nhãn đã duyệt, nhóm hợp lệ và hình của mọi vết visible trên tất cả frame liên quan, xác minh hash khi test đã khóa; `label_box()` và `detected_defects()` đối chiếu vị trí; `visible_ids()` xác định ID nhìn thấy; `threshold_candidates()` thử cả vùng dưới trung vị đỉnh ảnh sạch, lấy thêm điểm đỉnh trong vùng vết visible đã duyệt và giữ lưới tối đa 64 mức để xét vết yếu; `calibrate()` từ chối ID vật lý chưa thấy trong bất kỳ frame A, xác minh hai score cùng model rồi chọn kết hợp bốn ngưỡng bằng quy hoạch động với **tổng** tối đa hai báo nhầm trên toàn route sạch, ưu tiên vết nhỏ/mảnh; `main()` cung cấp CLI. Đã chạy trên A3 ba ID và lượt sạch calibration độc lập; 3/3 ID và 0 báo nhầm sạch, ngưỡng lưu ở patchcore_thresholds_v1.json.
- `lock_labels.py`: `lock()` dùng kiểm tra nhãn đầy đủ của `load_labels()`, khóa nhãn test và ghi SHA256; `main()` cung cấp CLI.
- `evaluate.py`: báo cáo ghi thêm `code_sha256` (`approval_gate.code_hashes`, D11); `classical_events()` replay detector Classical trên hai mặt ống; `evaluate()` xác minh hai score test và ngưỡng cùng model, dùng ngưỡng đã chốt trên tập test sạch/B có nhãn khóa, báo recall theo vết nhìn thấy, vết không đủ quan sát, báo nhầm, độ trễ và so sánh Classical; `acceptance.passed` cũng yêu cầu mọi ID trong inventory nhìn thấy được. Report ghi SHA256 ngưỡng và fingerprint model/tham chiếu cho cổng mặc định dashboard; `main()` cung cấp CLI. Đã chạy trên B khóa nhãn: 5/5 ID, 4/4 nhỏ/mảnh, 0 báo nhầm sạch; xem PATCHCORE_HANDOFF.md về giới hạn.
- `tests/test_approval_gate.py` (3 test): Tạo artifact và code thử, xác nhận cổng mặc định từ chối khi ngưỡng, bank model, ROI mask, code chấm điểm hoặc điều kiện nghiệm thu bị đổi sau đánh giá và khi báo cáo thiếu `code_sha256`; hash code không đổi theo kiểu xuống dòng; `registered_candidate_matches` từ chối thư mục khác, file đổi, file thiếu hoặc thiếu file đăng ký.
- `tests/test_label_integrity.py`: Kiểm tra nhãn visible thiếu hình bị từ chối và nhãn test thay đổi sau khóa bị phát hiện.
- `tests/test_live_roi.py`: Dataset mask giả trong thư mục tạm; kiểm tra `pose_match`, giao hai mask khi ở giữa hai tham chiếu, `nearest_mask` khi chỉ có một tham chiếu, `reference_unavailable` khi lệch quá 0,5 m và `roi_too_small` khi hai mask không giao. Không cần ảnh camera.
- `tests/test_live_service_unavailable.py`: `analyze_request()` với frame không có ROI không đổi trạng thái tracker; tracker vẫn xác nhận vết khi frame tốt xen kẽ frame bị bỏ (mẫu phiên live 2026-09-27) và vẫn bỏ track sau khoảng trống quá `max_gap_ticks`; chế độ `geometry` không cần station hay ảnh tham chiếu (ROI sẵn sàng ở pose bất kỳ trước ống, trả `no_structure_in_range` khi quá xa); ROI quá mỏng cho mọi tile trả `no_surface_tiles`. Test cũ dùng `roi_mode="reference"` vì mock `match_roi`.
- `tests/test_live_service_quality.py` (P3, 11 test, gồm lề tùy chọn ở mép ảnh, gồm cổng với ngưỡng tương đối không coi dịch chuyển toàn cục là lan tỏa): `interior()` bỏ dải sát mép ROI nhưng giữ phần chạm mép ảnh; lề che điểm cao trên mép ROI trước khi tách ứng viên và response có `quality`; `is_diffuse()`: một vết lớn 8% không bị coi là lan tỏa, đốm rải rác > 5% ngoài vùng lớn nhất và một vùng > 25% thì có, > 6 vùng thì có, NaN không được đếm; frame lan tỏa trả `diffuse_anomaly` và giữ nguyên tracker; tắt cổng thì giữ hành vi v1.2. P8: thêm 2 test, cổng P8 bỏ 132 đốm 25 px nhưng vẫn coi 9 vùng lớn là lan tỏa, và không chặn một vùng 30%.
- `tests/test_live_service_surface.py` (P5, 3 test): calibration bề mặt lệch file ngưỡng pixel bị từ chối; quy tắc bề mặt từ chối ROI tham chiếu; ba lượt nhìn cách nhau 0,4 m của cùng một ô cho đúng một cảnh báo, box phủ các ô đó trong frame hiện tại, `peak_score` lấy từ ma trận score, tọa độ bề mặt đúng tâm ô.
- `tests/test_calibration_budget.py`: Dữ liệu tổng hợp bốn nhóm xác minh đúng giới hạn hai cảnh báo nhầm cho toàn route, ưu tiên vết mảnh và từ chối vết A không nhìn thấy; thêm trường hợp vết mảnh có score thấp hơn trung vị đỉnh ảnh sạch nhưng vẫn được tracker xác nhận mà không báo nhầm; không thay thế hiệu chỉnh trên ảnh thật.

Ảnh train hiện có: `auv_inspection/output/patchcore_dataset_clean_20260925/`, 552 frame được xác nhận sạch từ capture 25/09, 60 keyframe, bốn nhóm. Tất cả 552 mask đã được duyệt qua ảnh ghép theo nhóm và lưu `roi_approved.json`; 398 mask dùng dự phòng hình học, 154 qua ORB. Baseline `auv_inspection/output/patchcore_model_v1/` fit thành công trên GPU với bank 678/684/800/800 theo bốn nhóm; thử offline một ảnh sạch ở `output/patchcore_smoke_20260926/`. Capture cũ không có map SHA256 vì tạo trước thay đổi CLI.

Lượt A `output/capture_calibration_mixed_20260926_005016_799810/` hoàn tất 359/359 waypoint, 552 frame, map SHA256 `3a4a1bc1...`; đã chuẩn bị dataset/mask và score tại `output/patchcore_dataset_calibration_A_20260926/`, `output/patchcore_scores_calibration_A_20260926/`. So sánh frame cùng tick với lượt sạch tìm 18 frame đổi rõ ở `pipe_front`, 14 ở `pier_0`, không có ở `pipe_back`; score median xử lý 64,6 ms/frame, chỉ là offline trên GPU không phải đo tốc độ đồng thời Unreal. Truy vấn editor chỉ đọc xác nhận 5 DecalActor: hai ở mặt trước ống, một ở trụ 0 khoảng z=-8,2 m, hai ở trụ 0 khoảng z=-5,3/-5,2 m. Ở tick 3910 tầng trụ tương ứng, ảnh sensor chỉ khác ảnh sạch bốn pixel với chênh lệch >8 và không có đường nứt liên tục; hai decal cuối hiện chưa đủ quan sát. Tại các vùng vết rõ tick 400/490/3370, median score trên pixel đổi từ khoảng 31–32 (sạch) lên 57–65 (A); không suy ra recall từ ba ví dụ. Inventory và giới hạn ghi tại `damage_inventory_A.json` trong dataset A. Đã tạo nhãn `damage_labels.json` từ so sánh ảnh sạch/A và duyệt overlay 27 frame ứng viên: `M_HairCrack` 8 frame nhìn thấy, `M_HairCrack2` 8, `M_HairCrack3` 9; hai ID trụ cao không có frame đủ rõ, giữ `unclear` trong khoảng quét có thể quan sát. `load_labels()` kiểm tra hoàn chỉnh nhãn theo mọi frame/ID liên quan. Đây là dữ liệu A cũ năm vết. Người dùng đã bỏ hai decal không quan sát được; A3 mới, calibration và test B được ghi trong cập nhật hiện tại bên dưới.

Lượt A thứ hai `output/capture_calibration_mixed_20260926_015105_231742/` cũng hoàn tất 359 waypoint/552 frame nhưng có cùng SHA256 map. So sánh từng frame cùng tick với A trước: 106/106 ảnh `pipe_front` và 107/107 ảnh `pipe_back` trùng pixel hoàn toàn; ở trụ chỉ có sai khác nhiễu tối đa 4 pixel (`pier_0`) và 9 pixel (`pier_1`) trên một frame khi ngưỡng chênh lệch kênh >8. Không có bằng chứng hai vết trụ cao đã hiện thêm, nên không đăng ký lượt này làm A mới. Editor read-only vẫn báo `DecalActor_11`/`DecalActor_12` ở UE `(-1100,650,-530/-520)` với actor scale 0,1825/0,295; decal trụ thấp thấy được (`DecalActor_6`) có scale 0,51. Đây là chẩn đoán khả năng quan sát, không phải lệnh tăng kích thước cố định hay kết luận chắc chắn về nguyên nhân.

Audit `live_roi.py` trên 552 frame A với tham chiếu train sạch: 552/552 frame có ROI, mỗi nhóm đủ số frame, IoU median 1,0 và thấp nhất 0,888 so với mask A đã duyệt (`output/patchcore_live_roi_A_audit.json`). Hai route có pose gần như trùng nên đều dùng nhánh `pose_match`; kết quả này chưa kiểm chứng ORB khi camera/route đổi hoặc hiệu năng đồng thời Unreal.

Chẩn đoán sau khi chấm điểm toàn bộ 552 ảnh train sạch (`output/patchcore_scores_train_clean_diagnostic_20260926/`, median 62,3 ms/frame): quy tắc tâm đứng yên 35 px không tạo cảnh báo ống dù hai vết rõ đi khoảng 90 px/10 tick. Tracker quỹ đạo mới, với các ngưỡng thử 52/53,5/52/54,5 theo bốn nhóm, tạo hai sự kiện ống ở tick 420/490 và hai sự kiện trụ 0 ở 2930/3390; không có sự kiện trên chính ảnh train sạch (`output/patchcore_diagnostic_A_20260926.json`). Hai sự kiện trụ là hai lần quét **cùng một vết vật lý**. Đây chỉ là chẩn đoán để sửa tracking; train sạch không phải calibration độc lập, A còn hai vết không thấy trong camera, không coi số này là recall hay ngưỡng chính thức.

Smoke offline `live_service.analyze_request()` trên frame A tick 150 cho ma trận 480×640 khớp **chính xác** score đã lưu của cùng frame (sai khác tối đa 0,0); phiên đầu gồm khởi động GPU khoảng 340 ms, ba lần gọi cùng frame đo 305/93/92 ms khi không nén ma trận score. Client subprocess JSON-lines đã xử lý liên tiếp 33 frame A ở hai nhóm qua `output/patchcore_worker_diagnostic_A_20260926_022225/`: tất cả trạng thái `ready`, bốn sự kiện đúng tick/box của offline tại 420/490/2930/3390, median 83,8 ms/frame. File ngưỡng ở phiên đó ghi rõ `diagnostic_only_not_calibrated`; đây chưa phải chạy PatchCore đồng thời Unreal hoặc nghiệm thu độc lập.

### `auv_inspection/robustness/degradation.py`

Thư viện suy giảm ảnh offline có seed cho P1 của `GENERALIZATION_PLAN.md`; chỉ dùng NumPy/OpenCV nên chạy được ở cả `mainenv` và `.venv-patchcore`. **Không dùng làm tiền xử lý live.** Hệ số là bộ mức nghiêm trọng chọn để phủ từ nước trong tới rất đục ở khoảng cách 2 m, không phải hệ số Jerlov đã khớp.

- `Degradation(factor, severity)`: một yếu tố và mức 1-5; `check_severity()` từ chối mức ngoài 1-5.
- `uniform_depth()`: khoảng cách đồng nhất 2 m cho tới khi P2 cung cấp độ sâu hình học. Đã thử tách công trình/nền theo ROI và loại bỏ vì đáy gần nằm ngoài ROI, bị xóa trắng và tạo viền giả.
- `gaussian_random_field()`: nhiễu mịn bất biến tỷ lệ làm môi trường không đồng nhất; `blur_by_depth()`: làm mờ Gaussian thay đổi theo độ sâu bằng nội suy vài bản làm mờ.
- `turbidity()`: truyền thẳng `J·e^(−βz)` + tán xạ thuận làm mờ theo `φz` với `G = 0,6β` + tán xạ ngược `B∞(1 − e^(−βz))`; β trung bình 0,15-1,2 m⁻¹, đỏ suy hao nhanh nhất.
- `marine_snow()`: hạt Gaussian 30-600 hạt, 15% thành vệt chuyển động, chỉ vẽ trong vùng nhỏ quanh hạt (mức 5 khoảng 36 ms).
- `illumination()`, `defocus()`, `motion_blur()`, `sensor_noise()` (Poisson-Gaussian), `jpeg()`: các yếu tố camera và ánh sáng.
- `apply_degradations(frame, degradations, seed, depth_m=None)`: áp theo thứ tự vật lý `PIPELINE_ORDER` (môi trường, hạt, ánh sáng, quang học, chuyển động, cảm biến, nén); mỗi yếu tố một luồng ngẫu nhiên `[seed, index]`; từ chối yếu tố lạ hoặc lặp.
- `degrade_folder(source, destination, degradations, seed)`: frame thứ i dùng `seed + i`, từ chối ghi đè, ghi `degradation.json` gồm nguồn, seed, yếu tố/mức và mô hình độ sâu; `main()` cung cấp CLI.

### `auv_inspection/robustness/conditions.py`

Điều kiện mô phỏng theo từng lượt chạy (P1 phần 2), import top-level từ thư mục `auv_inspection` như `run_inspection.py`.

- `RunConditions`: profile, seed, khoảng cách tới trục ống, bán kính vòng trụ, biên độ lệch độ sâu/yaw, dòng chảy trung bình và biên độ dao động, cường độ và pitch đèn, khoảng tick chụp.
- `NOMINAL`: đúng runtime đã validate (2,0 m, 2,8 m, không lệch, không dòng chảy, đèn 2500/0°, chụp mỗi 10 tick).
- `PROFILES`: `train` dao động quanh nominal; `heldout` lấy mọi yếu tố **ngoài** khoảng train (ví dụ ống 1,6-1,75 hoặc 2,45-3,0 m, dòng chảy 0,25-0,45 m/s, đèn ×0,4-0,7 hoặc ×1,3-1,6). Bán kính trụ heldout tối thiểu 2,35 m vì góc hộp an toàn của trụ vuông cách trục khoảng 2,26 m; giá trị 2,2 m đã bị kiểm tra va chạm từ chối.
- `draw()`: lấy mẫu đều trên hợp các khoảng; `sample_conditions(profile, seed)`: tái lập theo `profile:seed`.
- `conditioned_route(conditions)`: dựng route theo khoảng cách, cộng lệch mượt, **từ chối** nếu `clearance_violations()` khác rỗng.
- `current_at(conditions, tick, ticks_per_sec)`: dòng chảy trung bình cộng dao động ngang chu kỳ 60 s.
- `CaptureSchedule(interval_ticks, seed).due(tick)`: khoảng cố định thì đúng `tick % N == 0`; khoảng ngẫu nhiên thì cách nhau `low..high` tick, tái lập theo seed.
- `describe()`: dict để ghi `conditions.json`/report.
- Độ đục không ngẫu nhiên hóa trong mô phỏng: lệnh `water_fog` của HoloOcean chỉ sửa PostProcessVolume có tag `WaterPPV` (đơn vị: giá trị nhập × 40000 = `Fog_Depth` cm), các map dự án không có tag này. Cần tag trên bản sao map nếu muốn dùng.
- Giới hạn: tên station của route ngẫu nhiên khác số thứ tự (ví dụ `pier_0_level_1_orbit_02_002`), nên ROI PatchCore dựa trên station (P0) sẽ `reference_unavailable` ở các waypoint mới; P2 bỏ phụ thuộc này.
- Dòng chảy gần như không làm lệch pose trong mô phỏng: bộ điều khiển `HoveringAUVControlPD` có `Kp = 100`, gia tốc tối đa 1 m/s², nên lực cản khoảng 24 N (0,35 m/s, `Cd = 0,8`, `A = 0,5 m²`) trên AUV 31,02 kg chỉ gây lệch khoảng 0,8 cm. Đo trên capture heldout: sai lệch ngang giống lượt không dòng chảy. Xem D14 trong `GENERALIZATION_PLAN.md`.

### `auv_inspection/robustness/geometry.py`, `calibrate_geometry.py`, `calibration/geometry_v1.json`, `geometry_v2.json`

Mô hình camera pinhole và hình học công trình đã biết, nền cho định vị cảnh báo (P1) và ROI hình học (P2). Mọi hàm nhận `GeometryParams` (bán kính ống, độ cao trục ống, nửa cạnh trụ, offset camera ngang/tiến/đứng, pitch camera). `DEFAULT_PARAMS` là mô hình chưa hiệu chỉnh (camera ở PoseSensor, ngang, bán kính 0,5 m, nửa cạnh 0,95 m); `load_params()` đọc `calibration/geometry_v1.json` nếu có, không thì trả mặc định. P8: `GeometryParams.pier_floor_z` (mặc định `PIER_Z_RANGE[0]` = -12, hành vi cũ) là cao độ thấp nhất của trụ được chiếu; `pier_hits()` dùng nó. `calibration/geometry_v3.json` (2026-10-15) = v2 + `pier_floor_z` = -10,35: chỗ tiếp giáp trụ-đáy đo trên ảnh seed 101 tick 8329 ở z -10,36 đến -10,45, hộp vật cản trụ trong `inspection_route.py` dừng ở -10,4. Không phải mặc định của `geometry.CALIBRATION_FILE` (vẫn v2); model v2 chọn qua `geometry_file`. Test: `test_pier_floor_cuts_the_pier_below_the_seabed`, `test_geometry_v3_only_adds_the_pier_floor`.

- `FOCAL_PX` khoảng 381,4 px; `camera_frame()` (gốc và trục camera có offset/pitch), `camera_basis()`, `pixel_rays()` (theo lô), `pixel_ray()`, `project()`.
- `pipe_hits()`, `pier_hits()`, `structure_hits()` vector hóa; `intersect_pipe()`, `intersect_pier()`, `pixel_to_surface()`; `render_hits(position, yaw, category, params, step)` trả khoảng cách tới công trình trên lưới pixel; `surface_normals()` (ống: hướng tâm, trụ: mặt hộp gần nhất) và `render_surface()` trả thêm cos góc tới.
- `in_view(...)`: điểm nằm trong ảnh (lề 20 px) và là điểm công trình đầu tiên tia chạm (dung sai 0,15 m); `surface_coordinates()`.
- `calibrate_geometry.py`: khớp 5 tham số (bán kính ống, độ cao trục ống, nửa cạnh trụ, offset ngang, pitch) bằng Powell với mục tiêu trung bình (1 - IoU) có trọng số đều theo nhóm, trên lưới 4 px với 552 mask đã duyệt trong `patchcore_artifacts/` (có trong repo). Offset tiến và đứng giữ 0 vì với một khoảng cách duy nhất chúng đánh đổi đúng với bán kính/nửa cạnh và độ cao trục, không xác định được. Chia theo khối: ống x < 0 khớp, x ≥ 0 kiểm tra; trụ tầng 0-1 khớp, tầng 2-3 kiểm tra. Không ghi đè file hiệu chỉnh đã có.
- `geometry.CALIBRATION_FILE` trỏ `calibration/geometry_v2.json` từ 2026-10-12. `calibrate_geometry.py` có `calibrate(dataset, fixed)` và CLI `--camera-forward`, `--camera-up` (offset cố định), `--output` (không ghi đè). `geometry_v2.json`: offset tiến 0,41 m và đứng 0,09 m cố định theo vị trí `CameraLeftSocket` so với `IMUSocket` trên hình socket HoveringAUV (`holoocean/client/docs/agents/agents/images/hovering-top.png`, `hovering-right.png`), tỷ lệ 0,0008 m/px từ vị trí thruster trong `holoocean/client/src/holoocean/agents.py`; fit: bán kính ống 0,423 m, trục z -10,294, nửa cạnh trụ 0,878 m, offset ngang -0,207 m, pitch 0,005°. IoU kiểm tra: ống 1,00/1,00, trụ 0,889/0,901; mask ORB: ống 0,946/0,975, trụ 0,869/0,877 (tương đương v1). Hai lượt nhìn cùng vết trụ từ hai tầng lệch 0,030 m (v1: 0,351 m), hai lượt vết ống 0,015 m (v1: 0,057 m).
- Kết quả `geometry_v1.json` (2026-10-09, giữ để đối chiếu): bán kính ống 0,534 m, trục z -10,564, nửa cạnh trụ 0,985 m, offset ngang -0,205 m (camera lệch trái, khớp tên `CameraLeftSocket`), pitch 3,92° xuống. IoU median trên tập kiểm tra: ống 1,00/1,00, trụ 0,886/0,922 (trước hiệu chỉnh 0,78/0,78/0,85/0,89). Riêng 156 mask từ polygon người vẽ (ORB): ống 0,95-0,97, trụ 0,87-0,88 (mặc định 0,73-0,87). 72% mask là `geometry_fallback` sinh từ gợi ý hình học nên IoU với chúng một phần là vòng tròn; số trên mask ORB là bằng chứng độc lập hơn.

### `auv_inspection/robustness/geometric_roi.py`

ROI hình học (P2), thay ROI ảnh tham chiếu và nhóm theo tên station.

- `category_from_pose(position, yaw, params, max_range_m=4.0)`: nhóm công trình chiếm nhiều nhất vùng giữa ảnh trong tầm 4 m (quá xa thì GSD > 1 cm/pixel); ống trước/sau theo phía camera; `None` nếu không có công trình.
- `erosion_px(distance, sigma_m, sigma_yaw_deg)`: độ dời ảnh một sigma `f·σ/d + f·σ_yaw`.
- `geometric_roi(...)`: dựng mask trên lưới 2 px rồi phóng (nearest), bỏ pixel có góc tới lớn hơn `MAX_INCIDENCE_DEG` = 70° (mỗi pixel phủ diện tích bề mặt gấp 1/cos θ, khoảng 3 lần ở 70°, thiếu sáng, lẫn nền nước và mép vòng bích; ngưỡng chọn theo lập luận này trước khi đo), co theo sai số pose (mặc định 0,02 m/0,5°, phủ sai số hiệu chỉnh), trả `no_structure_in_range` hoặc `roi_too_small` (dưới 1000 px) khi không đủ điều kiện; khoảng 14-35 ms/frame.

### `auv_inspection/robustness/defect_inventory.py`, `robustness/inventories/map_A.json` và `map_B.json`

- `Defect` là điểm, hoặc **đoạn thẳng** khi có `end` (vết nứt dài); `distance_to()` đo tới điểm hoặc tới đoạn, `centre()` dùng cho khả năng quan sát. `Inventory`, `load_inventory()` (từ chối ID trùng, đọc `end_m` nếu có); `event_category()`; `locate_box()` chiếu tâm box cảnh báo lên công trình; `locate_event()` đọc `event.json` (event Classical không có yaw, mặt trước ống dùng -90°); `match_defect()` chọn vết cùng nhóm gần nhất trong bán kính; `defects_in_view()`. `locate_box()` và `defects_in_view()` nhận `GeometryParams` (harness truyền tham số đã hiệu chỉnh).
- `map_A.json` từ 2026-10-12 tính bằng hình học v2 từ đúng các nguồn ảnh cũ (người dùng duyệt): `A_pipe_front_1` điểm (-10,082; 0,419; -10,239) bán kính 0,6 m (trung bình hai event nguồn, lệch nhau 0,09 m); `A_pipe_front_2` đoạn (-7,092; 0,423; -10,31) → (-7,842; 0,384; -10,115) bán kính 0,35 m (hai lượt vẽ lệch ≤ 0,02 m); `A_pier_0_1` đoạn (-9,603; -5,622; -8,455) → (-10,525; -5,622; -7,832) bán kính 0,35 m. Mô tả lịch sử bên dưới dùng tọa độ v1.
- `map_A.json` (trạng thái `reviewed` từ 2026-10-09, người dùng duyệt bằng ảnh): 3 vết của map A (SHA256 `daba22ec...`): `A_pipe_front_1` x -10,25 bán kính 0,6 m (trung bình từ event PatchCore phiên P0 và Classical ngày 27/09); `A_pipe_front_2` từ 2026-10-12 là **đoạn** (-7,07; 0,533; -10,6) → (-7,93; 0,50; -10,375) bán kính 0,35 m, vẽ theo hai đầu mút vết nứt ở tick 463 và 478 của capture phát triển map A (người dùng duyệt; trước đó là điểm x -7,66 bán kính 0,6 m, không phủ đầu trái vết dài khoảng 0,9 m); `A_pier_0_1` là đoạn trên mặt trước trụ 0 từ (-9,81; -5,55; -8,74) tới (-10,88; -5,55; -8,01), bán kính 0,35 m, vẽ theo hai đầu mút vết nứt nhìn thấy ở tick 3478 của capture heldout. Bản đầu dùng điểm (-10,0; -5,55; -8,4) bán kính 0,6 m đã khiến baseline tính một cảnh báo PatchCore nằm ngay trên vết (cách điểm 0,71 m) là báo nhầm; sửa theo ảnh, không theo kết quả detector, ghi trong `revisions`. Đã chiếu lên capture heldout để duyệt bằng ảnh: hai vết ống trúng vết ở frame giữa đoạn quan sát.

- `map_B.json` (P7, `reviewed` và khóa 2026-10-14, SHA256 `ecedd4f0...` ghi trong `acceptance_preregistration.json`): map B (`3bee29b8...`), 5 đoạn bán kính 0,35 m, vẽ chỉ từ ảnh capture heldout seed 105 (`capture_test_mixed_20261014_193119_450647`, mỗi vết 2 frame, lệch ≤ 0,04 m, hình học v2), kiểm trên seed 106: `B_pipe_front_crack_1` x -4,77…-4,20; `B_pipe_front_hole_small` x -0,05…0,23 (sát vòng bích x = 0); `B_pipe_front_crack_2` x 3,34…3,91; `B_pipe_front_hole_large` x 8,22…9,13 (sát vòng bích x = 9); `B_pier_1_crack` mặt trước trụ 1, (10,28; -5,622; -8,60) → (9,68; -5,622; -7,92). Mặt sau ống và trụ 0 không có vết. Bảng ảnh duyệt: `output/p7_mapB_label_review/`. Không sửa sau khi khóa.

### `auv_inspection/robustness/metrics.py`

`wilson_interval()`, `surveyed_length_m()` (tổng quãng đường giữa các frame kiểm tra, bỏ bước nhảy trên 1 m giữa các đoạn), `rate_per_100m()`, `fraction()` (số đếm, tỷ lệ, Wilson 95%).

### `auv_inspection/robustness/evaluate_capture.py`

Phát lại một capture qua detector (tùy chọn suy giảm ảnh theo seed + tick) và chấm điểm theo vết vật lý; chạy trong `.venv-patchcore`.

- `FrameResult(available, flagged, alert_bbox, category, reason, more_alert_bboxes)`; `record()` đếm frame `diffuse_anomaly` thành trạng thái riêng trong `availability`, ghi mọi cảnh báo mới trong frame (quy tắc bề mặt có thể sinh nhiều vùng một lúc); `Score.rearm_m` lấy từ thuộc tính `rearm_distance_m` của detector nếu có (detector bề mặt khai 0, giống dashboard), mặc định 2 m; detector bề mặt còn khai `ambiguous_regions`, và `ambiguity_report()` (P6) ghi vào kết quả mục `ambiguity`: các vùng mơ hồ cuối lượt (kèm điểm thế giới qua `surface_point` và vết khớp), số vùng ≥ 1 / ≥ 2 hit trên 100 m, danh sách vết chạm tới; `length_of()` tính quãng đường khảo sát; `classical_detector()` theo cổng runtime (chỉ ống, reset tracker khi rời ống/đổi nhóm/sau cảnh báo); `patchcore_detector(..., roi_mode)` gọi `live_service.create_session()/analyze_request()`: `reference` dùng station và nhóm của capture (v1.1), `geometry` dùng `category_from_pose()` và ROI hình học (P2); `patchcore_detector()` nhận thêm `score_margin_px`, `diffuse_gate`, `alert_rule`, `surface_calibration`; `make_detector()` cho `classical`, `patchcore`, `patchcore_geo` (v1.2), `patchcore_geo_m` (thêm lề 24 px), `patchcore_geo_md` (lề + cổng lan tỏa), `patchcore_surface` (lề + cổng + quy tắc bề mặt P5), `dino_surface_b` (= `dino_surface` với lề cả ở mép ảnh), `dino_surface` / `dino_surface_noaug` (detector v2 từ `V2_MODELS`: `output/detector_v2_dino_s2_aug_g2` / `_noaug_g2`, `dino_nfad` / `dino_maha` / `dino_nfmaha` (P4.3: `..._aug_g2_nfad8`, `..._aug_g2_maha`, `..._aug_g2_nfmaha`), mỗi tên có bản `_b` bật lề mép ảnh (dựng lại với hình học v2; thư mục không hậu tố là bản hình học v1), mỗi thư mục có bank, `pixel_thresholds.json`, `surface_calibration.json`); import PatchCore chỉ trong nhánh PatchCore để Classical không cần torch. P8: `V2_MODELS["dino_floor"]` = `output/detector_v2_dino_s2_aug_g2_floor`; mọi model v2 có thêm biến thể `_bg` (lề mép ảnh + cổng P8: `GATE_MIN_REGION_PX`, bỏ tiêu chí một vùng lớn), `patchcore_detector(..., gate_min_region_px, gate_region_share)`. Ground truth (khả năng thấy vết, định vị box) vẫn dùng `GEOMETRY` = v2. Hậu tố detector v2 từ P8: sau `_b` có thể có `g` (cổng P8) và `r` (`evidence_min_region_px` = `GATE_MIN_REGION_PX`): `_b`, `_bg`, `_br`, `_bgr`. `SCORE_CACHE_DIR` (mặc định None): khi đặt, `patchcore_detector` bọc `session.scorer` để đọc/ghi lưới token theo tick qua `robustness.score_cache`, và `evaluate_many` mở/lưu cache cho mỗi (capture, điều kiện, seed suy giảm, khóa lưới). Đã kiểm: `dino_surface_b` trên seed 3 điều kiện gốc cho kết quả trùng benchmark cũ (vết, báo nhầm, sự kiện, availability) cả khi ghi cache (321 s) và khi đọc cache (53 s). Cờ `s` (sau `g`): cổng giữ độ phân tán trên mọi vùng (`_bgsr`).
- `perceived_pose(row, pose_noise, seed)`: pose đưa cho detector = pose thật + nhiễu định vị có seed (D14), kèm `pose_sigma_m`/`pose_sigma_yaw_deg` để ROI co tương ứng; không đổi pose thật.
- `evaluate_many(capture, detectors, inventory, degradations, seed, pose_noise)`: mỗi frame chỉ đọc và suy giảm một lần rồi đưa cho mọi detector (`Score`, `record()` tích lũy riêng); ground truth (khả năng quan sát, frame âm, nhóm) theo pose thật, còn detector và định vị cảnh báo theo pose nhiễu như AUV thật; ghi `pose_noise` và tham số hình học vào kết quả. `evaluate(...)` là trường hợp một detector: kiểm tra hash map khớp inventory (capture mixed bắt buộc có inventory), khóa cảnh báo trùng trong 2 m như runtime, định vị cảnh báo bằng `locate_box()` và khớp vết; vết **quan sát được** khi nằm trong tầm nhìn ít nhất 3 frame; trả recall theo vết (Wilson), số báo nhầm và báo nhầm trên 100 m, tỷ lệ frame có ứng viên khi không có vết trong tầm nhìn, số frame phân tích/bỏ qua theo nhóm, ms/frame trung vị trên frame được phân tích, danh sách event và các lưu ý (capture lấy mẫu thưa hơn runtime, frame tương quan, khả năng quan sát chỉ theo hình học).
- `main()`: CLI `--detector {classical,patchcore,patchcore_geo,patchcore_geo_m,patchcore_geo_md,patchcore_surface,dino_surface,dino_surface_noaug}`, `--inventory` hoặc `--clean`, `--degradation`, `--seed`, `--pose-noise σm σdeg`, `--output` (không ghi đè).

### `auv_inspection/robustness/benchmark.py`

P8: `--score-cache <thư mục>` đặt `evaluate_capture.SCORE_CACHE_DIR`. `robustness/score_cache.py`: `GridCache(path)` (`.npz` nén, khóa `<tick>_<nhóm>`, `get`/`put` chỉ nhận float32 để phát lại chính xác, đếm hit/miss, `save()` gộp các mục mà lượt khác đã lưu vào cùng file, ghi file tạm riêng theo PID rồi đổi tên, để nhiều tiến trình song song không làm mất mục của nhau), `cache_path(dir, capture, điều kiện, seed, khóa)`; chỉ dùng cho thí nghiệm offline, không dùng ở runtime. Cache tập phát triển P8: `auv_inspection/output/p8_score_cache/` (gitignored). Test `robustness/tests/test_score_cache.py`.

Chạy lưới detector × capture × điều kiện (`DEFAULT_CONDITIONS`: gốc, độ đục 2/4, marine snow 3/5, đèn yếu 4, mờ chuyển động 3); mỗi kết quả một JSON riêng, đã có thì dùng lại; ghi `summary.json` và `summary.md`. Mỗi (capture, điều kiện) chạy mọi detector còn thiếu trong một lượt `evaluate_many` (suy giảm một lần); detector mới mỗi lượt để không rò trạng thái tracker; `--pose-noise` thêm hậu tố vào tên file; bảng có cột `pose_noise` và `diffuse_share` (tỷ lệ frame bị cổng P3 trả `diffuse_anomaly`).

### `auv_inspection/detector_v2/` (P4)

Detector v2: token patch DINOv2 ViT-S/14 và bank láng giềng gần nhất theo nhóm công trình, thay PatchCore WRN50 khi thư mục model có `config.json` với `"model": "DINOv2-kNN"`. Model, ngưỡng v1 và `patchcore_artifacts/` không đổi.

- `features.py`: `MODEL_NAME = "vit_small_patch14_dinov2.lvd142m"` (timm, trọng số từ cache Hugging Face, 85 MB), `load_extractor(device, scale=2.0)` (fp16 trên GPU), `input_size()` làm tròn frame đã nhân `scale` về bội số 14 px, `frame_tokens()` trả lưới token (h, w, 384) đã chuẩn hóa L2 (ImageNet mean/std, bỏ token tiền tố), `roi_cells(roi, grid, erosion_px)` chọn ô có tâm trong ROI. Đo trên RTX 3050 không chạy Unreal: 21,5 ms ở scale 1, 114 ms ở scale 2, peak 73-120 MiB.
- `scorer.py`: `nearest_distance()` = 1 - cos lớn nhất so với bank (chia khối `BANK_CHUNK` = 16.384 hàng); `DinoScorer(frame, roi, group)` trả bản đồ điểm 640×480, NaN ngoài ROI, cùng hợp đồng với `predict_map` nên lề, cổng lan tỏa và quy tắc bề mặt dùng nguyên. `is_v2_model()`, `load_scorer()` (từ chối config khác).
- P8: `DinoScorer.grid(frame, category)` trả lưới khoảng cách token (h, w) float32 (phần tốn GPU); `scorer.expand(grid, shape, roi)` nội suy lên độ phân giải camera và NaN ngoài ROI; `__call__` = `expand(grid(...))`, kết quả không đổi. `grid_cache_key(model_dir)`: 16 ký tự đầu SHA256 của backbone, scale, nội dung bank (theo `bank_dir`) và file biến đổi; model dùng chung bank (ví dụ `_g2` và `_floor`) dùng chung lưới cache.
- `build_bank.py`: chỉ nhận capture sạch `dataset_role=train`, profile `train`, đã đi hết route; ROI hình học, token co `EROSION_PX` = 12 (nửa lề chấm điểm); tùy chọn thêm một bản suy giảm offline **mức 1** mỗi frame (một yếu tố ngẫu nhiên, `AUGMENT_SEVERITY`); tối đa `max_per_frame` token ngẫu nhiên/frame vào reservoir đều theo nhóm (`max_candidates`), bank = coreset k-center (`coreset_ratio`), chuẩn hóa L2; ghi `config.json` (nguồn, hash `frames.jsonl`, số frame theo biến thể). Không ghi đè. CLI: `python -m auv_inspection.detector_v2.build_bank <đích> <capture>... [--scale --no-augment --max-per-frame --max-candidates --coreset-ratio]`.
- `calibrate_pixel.py`: ngưỡng tuyệt đối theo nhóm cho model v2 từ capture **calibration** sạch: thống kê lượt cao thứ 3 của max điểm ô (ROI hình học, lề 24 px, không cổng vì cổng cần chính ngưỡng này), phân vị trên conformal cùng mức α như calibration bề mặt; file ra có dạng file ngưỡng v1 (`model_dir`, `groups.<nhóm>.threshold`), mặc định `<model_dir>/pixel_thresholds.json`. Sau đó chạy `calibrate_surface.py --model-dir <v2> --thresholds <file> --output <v2>/surface_calibration.json`. Từ P8 dùng `live_service.model_geometry(model_dir)` cho ROI và ghi `geometry` vào file ra.
- `transforms.py` (P4.3): `FeatureTransform(kind, matrix, mean)` với `apply()` (nuisance: chiếu rồi chuẩn hóa, metric cosine; mahalanobis: trừ trung bình, nhân Σ^-1/2, metric Euclid), `state()`/`from_state()`, `nuisance_projection(scatter, k)` (loại k vector riêng lớn nhất, trả tỷ lệ phương sai giải thích), `mahalanobis_whitening(bank, shrinkage)`. `scorer.nearest_distance(..., metric)` hỗ trợ `euclidean`; `DinoScorer.transforms` áp biến đổi cho token và (lúc nạp) cho bank; `load_scorer()` đọc `bank_dir` và `transform_file` trong config.
- `transforms.ChainedTransform` (áp nhiều biến đổi theo thứ tự, metric của bước cuối; `from_state()` nhận danh sách). `derive_model.py` (P4.3): tạo thư mục model mới dùng bank của model gốc (`bank_dir`) và thêm `transforms.pt`; loại `nuisance_mahalanobis` dùng lại phép chiếu của một model nuisance (`--from-nuisance`) rồi làm trắng trên bank đã chiếu; `nuisance` ước lượng hiệp phương sai chênh lệch token giữa frame capture bank (chỉ train profile train) và chính frame đó suy giảm mức 1 theo từng yếu tố; `mahalanobis` từ bank từng nhóm. Không ghi đè. CLI: `python -m auv_inspection.detector_v2.derive_model <gốc> <đích> {nuisance,mahalanobis} [--captures ... --k 8 --frames-per-capture 100 --shrinkage 0.1]`; sau đó calibrate lại ngưỡng pixel và ngưỡng tầng. P8: loại `geometry` (`--geometry-file`) không thêm biến đổi, chỉ ghi `geometry_file` vào config để model dùng geometry ROI khác (cần calibrate lại ngưỡng pixel và ngưỡng tầng). `output/detector_v2_dino_s2_aug_g2_floor/` (2026-10-15): bank của `_g2`, `geometry_v3.json`; ngưỡng pixel và ngưỡng tầng calibrate lại từ 3 capture calibration giống hệt `_g2` (31.968 ô) vì capture calibration profile train gần như không thấy trụ dưới -10,35 (3/159 frame trụ, thấp nhất -10,47), trong khi seed 101 heldout thấy tới -11,48 ở 51/236 frame trụ. Test `GeometryModelTests`.
- `tests/test_detector_v2.py` (11 test, không cần trọng số, gồm phép chiếu nhiễu, làm trắng, chuỗi biến đổi, khoảng cách Euclid): kích thước input bội 14, ô ROI theo ROI và độ co; khoảng cách 1 - cos qua nhiều khối bank, bank rỗng bị từ chối; bản đồ điểm đúng kích thước camera và NaN ngoài ROI, nhóm thiếu bank bị từ chối; chỉ nạp config v2; bank chỉ nhận capture train profile train; suy giảm thêm đúng một bản mức 1.

### `auv_inspection/robustness/surface.py`

Tọa độ bề mặt trải phẳng tính bằng mét (P5), chung cho mọi lượt nhìn cùng một công trình. `surface_uv(points, category, params)`: ống u = x dọc trục, v = độ dài cung từ phía đối diện nhóm camera (trước +y, sau -y), dương hướng lên; trụ u = z, v = vị trí theo chu vi tiết diện vuông ngược chiều kim đồng hồ từ góc (+x, +y), quay vòng ở 8 × nửa cạnh. `pier_perimeter_m()`. `surface_point(uv, category, params)` (P6) là nghịch đảo của `surface_uv` (ống: cung → góc; trụ: chu vi → mặt và vị trí). `render_uv(position, yaw, category, params, step=4)` trả lưới (H/step, W/step, 2) tọa độ bề mặt của tâm từng khối pixel, NaN nơi tia không chạm công trình.

### `auv_inspection/robustness/surface_evidence.py`, `calibrate_surface.py`, `calibration/surface_v1.json`

Tích lũy bằng chứng theo ô bề mặt và cảnh báo theo vùng (P5), thay tracker ảnh khi chọn `alert_rule="surface"`.

- `CALIBRATION_FILE` = `calibration/surface_v2.json` (calibrate lại với hình học v2 từ cùng 3 capture calibration, không cổng; 31.968 ô, 6.045 ô/100 m; ngưỡng mặt trụ 1,285/1,282, thân ống trước/sau 1,214/1,202, mối nối 1,341/1,332, mọi tầng `data_limited`; `surface_v1.json` giữ để đối chiếu). Hằng số: `CELL_M` = 0,10, `POOL_PX` = 4, `MIN_MOVE_M` = 0,30 (một lượt nhìn mới của ô chỉ được tính khi camera dời ít nhất 0,3 m kể từ lượt được tính trước của ô đó), `VIEWS_REQUIRED` = 3, `MERGE_RADIUS_M` = 0,6. `PIPE_JOINTS_X` là vòng bích mỗi 3 m (x = -15…15) cùng hai đầu ống, `JOINT_HALF_WIDTH_M` = 0,5 (đo trên tập phát triển: ô sạch gần vòng bích còn cao hơn thân ống tới 0,4-0,5 m ở khoảng cách 2,77 m).
- `element_of(category, u)` → `pipe_joint` / `pipe_body` / `pier_face`; `stratum()` = `nhóm/phần tử`, là tầng calibration (Mondrian). `pooled(scores)` lấy max mỗi khối 4×4, NaN khi cả khối không có điểm. `frame_cells(scores, position, yaw, category, params)` lấy max điểm theo ô 10 cm và trả cho mỗi ô cặp (điểm, điểm / **median điểm của frame**), cùng lưới chỉ số ô để vẽ box. `is_hit(value, pixel_threshold, stratum_threshold)`: một lượt nhìn là hit khi điểm ≥ ngưỡng pixel đã khóa của nhóm **và** giá trị chuẩn hóa ≥ ngưỡng tầng. Ngưỡng tuyệt đối loại công trình mà điểm tương đối tăng theo khoảng cách (vòng bích ngoài khoảng train), ngưỡng tương đối loại dịch chuyển toàn cục (độ đục, mờ); mô phỏng trên tập dev: dùng riêng một loại còn 1-32 báo nhầm mỗi capture, kết hợp còn 0-1.
- `SurfaceCalibration` (ngưỡng theo tầng, hash file ngưỡng pixel đã dùng; `threshold(key)` báo lỗi khi thiếu tầng; `lowest_threshold(nhóm)` cho cổng lan tỏa), `load_calibration()` từ chối file có `cell_m`/`pool_px`/`min_move_m`/`views_required` khác runtime. `SurfaceEvidence(calibration, pixel_thresholds)`; `ambiguous_regions(min_hits=1)` (P6) gộp các ô chưa báo có 1 đến k-1 hit trong 0,6 m, trả nhóm, số ô, số hit lớn nhất, số lượt nhìn và tâm bề mặt có trọng số; `observe(position, values)`: cập nhật `CellState` (lượt nhìn, số hit); ô đạt `VIEWS_REQUIRED` lượt vượt ngưỡng thì thành cảnh báo mới, hoặc nhập vào cảnh báo cũ cùng nhóm trong 0,6 m; trả (cảnh báo mới, ô vừa đạt). `coverage(min_views)` đếm ô đã được nhìn đủ theo nhóm.
- `calibrate_surface.py`: chấm điểm capture **sạch** bằng đúng `score_request()` (ROI hình học, lề 24 px, cổng lan tỏa), gom lượt nhìn theo ô như runtime, mỗi ô sạch có ≥ 3 lượt góp giá trị `kth_highest()` của **thống kê chuẩn hóa riêng** (lượt cao thứ 3 = ngưỡng tầng mà ô đó sẽ báo nếu chỉ xét giá trị chuẩn hóa). Hai ngưỡng được calibrate riêng rồi AND ở runtime, mỗi ngưỡng giữ mức α nên AND cũng giữ: bản calibrate thống kê kết hợp (chỉ tính lượt đạt ngưỡng pixel) cho mọi ngưỡng tầng = 0 vì không ô sạch nào đạt 3 hit theo ngưỡng pixel, khiến quy tắc lùi về chỉ ngưỡng pixel (lưu ở `output/benchmark_p5_surface_abs_degenerate_superseded/`). `calibrate(captures, destination, model_dir, thresholds)`, CLI `--model-dir`, `--thresholds` (mặc định v1) để calibrate cả model v2; từ 2026-10-12 không dùng cổng lan tỏa khi chấm frame calibration (`diffuse_gate: false` trong file ra); `conformal_threshold(values, alpha)` lấy phân vị trên conformal; α mỗi ô = `FALSE_CELLS_PER_100M` (0,5, nửa mức nghiệm thu, chọn trước) / số ô được đánh giá trên 100 m. Tầng quá ít ô cho α nhận ngưỡng ngay trên giá trị lớn nhất, đánh dấu `data_limited` và ghi `achieved_level` = 1/(m+1); giới hạn là -inf thì ngưỡng là 0 (phòng hờ). Ghi `calibration_p50`, `calibration_max`. Ghi `sources` (capture, hash map, điều kiện), hash file ngưỡng pixel, lưu ý; không ghi đè file đã có. CLI: `calibrate_surface.py <capture_sạch>... [--output]`.
- `calibration/surface_v1.json` (2026-10-12): 3 capture calibration sạch profile train seed 11/12/13 trên map sạch v3 (`ea94a84f...`), 45.591 ô, 528,9 m, 8.620 ô/100 m, α = 5,8×10⁻⁵. Ngưỡng: mặt trụ 0/1 = 1,244/1,285 (17.123/16.160 ô, mức đạt 5,8/6,2×10⁻⁵); thân ống trước/sau = 1,187/1,191 (≈4.160 ô, 2,4×10⁻⁴); mối nối trước/sau = 1,318/1,329 (≈2.000 ô, 5,0×10⁻⁴). Mọi tầng `data_limited` (trụ chỉ thiếu sát nút). Mức đảm bảo chỉ đúng cho điều kiện trao đổi được với lượt train; điều kiện heldout do benchmark đo.

`robustness/tests/test_surface_evidence.py` (15 test, gồm `lowest_threshold`, nghịch đảo `surface_point`, gộp vùng mơ hồ): độ dài cung ống theo mặt, chu vi trụ liên tục qua bốn mặt và góc, `render_uv` theo camera dọc ống; phân loại thân/mối nối/trụ; `pooled` giữ max và khối trống; cảnh báo cần 3 lượt cách nhau đủ xa và vượt **cả** ngưỡng tương đối lẫn ngưỡng pixel, chỉ báo một lần; ô gần nhập cảnh báo cũ, ô xa/nhóm khác báo riêng, `coverage`; calibration lệch hằng số bị từ chối; ngưỡng conformal giữ mức, tầng nhỏ `data_limited`, tầng không ô sạch nào báo được thì ngưỡng 0, `kth_highest` khớp quy tắc k-trên-n.

### `auv_inspection/robustness/acceptance.py`, `acceptance_preregistration.json` (P7)

- `acceptance.py`: báo cáo nghiệm thu từ kết quả benchmark trên capture heldout. `load_runs()` (lỗi nếu thiếu capture), `capture_totals()` (vết phát hiện/quan sát được, báo nhầm, quãng đường, ô sạch theo capture), `pooled()`, `bootstrap()` (lấy mẫu lại theo capture, 2.000 lần), `wilson_upper()`, `report()` trả recall gộp, báo nhầm/100 m, khoảng bootstrap 95%, FPR mức ô (cận trên Wilson), bảng theo điều kiện (gồm tỷ lệ `diffuse_anomaly`) và đạt/không đạt theo `RECALL_TARGET` 0,90, `FALSE_ALERTS_PER_100M_MAX` 1,0, `CELL_FPR_MAX` 0,05. CLI: `python -m auv_inspection.robustness.acceptance <thư_mục_kết_quả> --detector <tên> --mixed <capture>... --clean <capture>... [--output]` (không ghi đè).
- `acceptance_preregistration.json` (2026-10-14): ứng viên, đối chứng, SHA256 của bank/ngưỡng/calibration/hình học/nhãn, commit code, seed heldout 101-106, 7 điều kiện, tiêu chí và quy trình nhãn map B; mọi thay đổi sau đó cần đăng ký và dữ liệu mới.
- Harness: `clean_cell_fpr(cells, defects)` đếm ô sạch đã đánh giá (≥ 3 lượt, không nằm trên vết) có cảnh báo; detector bề mặt khai `surface_cells`; kết quả nằm trong `ambiguity.clean_cell_fpr`.
- `robustness/tests/test_acceptance.py` (3 test: tiêu chí gộp và bảng theo điều kiện, thiếu kết quả báo lỗi, cận Wilson); `test_evaluate_capture.py` thêm test FPR mức ô (bỏ ô trên vết và ô dưới 3 lượt).

### `auv_inspection/robustness/quality.py`

`measure(frame, roi)` (P3) đo chất lượng ảnh, **chỉ để chẩn đoán**, không chặn cảnh báo: `sharpness` (phương sai Laplacian chia phương sai xám, không phụ thuộc độ tương phản), `contrast`, `brightness`, `saturated_fraction` (pixel ≥ 250) trên ROI; `particles_per_100k_px` (đốm sáng nhỏ 3-150 px qua white top-hat 9 px, ngưỡng 25 mức xám) trên cả ảnh. Từ chối ROI rỗng hoặc lệch kích thước. Cổng chất lượng theo phân vị 1/99 của frame sạch đã thử và bỏ (xem docstring và `GENERALIZATION_PLAN.md`); số đo được giữ để P5 quyết định frame nào đủ tốt làm bằng chứng bề mặt sạch.

`robustness/tests/test_quality.py`: 4 test: mờ giảm `sharpness`, ảnh tối giảm độ sáng và tương phản, đốm sáng nhỏ được đếm là hạt, ROI rỗng/lệch kích thước bị từ chối.

`robustness/tests/test_geometry.py` (10 test: tiêu cự, điểm giữa ảnh chạm ống ở khoảng cách đúng, `project` nghịch đảo `pixel_to_surface`, hướng trái/phải ảnh, mặt sau ống và điểm sau camera không thấy, mặt trụ, tia trượt, `render_hits` theo lô khớp từng pixel khi có offset/pitch, pitch xuống đẩy ống lên trên ảnh, thiếu file hiệu chỉnh thì dùng mặc định); `robustness/tests/test_geometric_roi.py` (8 test: nhóm theo công trình trong tầm nhìn và `None` khi quá xa/quay lưng, ROI phủ dải ống và co lại khi sai số pose tăng, dải mép ống góc tới lớn bị loại còn tâm được giữ, pháp tuyến hướng về camera ở giữa ảnh ống/trụ, độ co tăng theo sai số và độ gần, công trình quá xa được báo chứ không đoán, file hiệu chỉnh ghi IoU kiểm tra ≥ 0,85, tham số hiệu chỉnh hơn mặc định trên mask ORB); `robustness/tests/test_metrics_inventory.py` (6 test: giá trị Wilson tham chiếu, quãng đường bỏ bước nhảy, inventory map A, khớp/không khớp vết, khớp dọc vết nứt dạng đoạn, khả năng quan sát theo vị trí); `robustness/tests/test_evaluate_capture.py` (6 test với capture và detector giả: cảnh báo trên vết được tính phát hiện và cảnh báo lặp trong 2 m bị khóa, detector kiểu bề mặt (re-arm 0) ghi đủ hai vùng trong một frame và vùng mới trong 2 m, cảnh báo xa vết là báo nhầm, capture sạch không cần inventory và capture mixed phải đúng hash, nhiễu pose có seed và không đổi pose thật, mỗi frame được đưa cho mọi detector đúng một lần).

`robustness/tests/test_conditions.py`: 9 test: nominal đúng route và đèn cũ; tái lập theo profile/seed; mẫu train nằm trong khoảng train; mẫu heldout nằm trong khoảng heldout và **không bao giờ** trong khoảng train (60 seed); route ngẫu nhiên giữ thứ tự đoạn, đủ 24 bước góc mỗi vòng trụ và qua kiểm tra va chạm (60 seed × 2 profile); lịch chụp cố định trùng quy tắc modulo cũ, lịch ngẫu nhiên giữ khoảng cách 3-17 tick; dòng chảy dao động trong biên độ; `run()` từ chối ngẫu nhiên hóa ở manual trước khi mở Unreal.

`robustness/tests/test_degradation.py`: 9 test trên ảnh tổng hợp có vết nứt: tái lập theo seed, giữ kích thước/kiểu, từ chối yêu cầu sai, độ tương phản giảm đơn điệu theo độ đục và giảm theo khoảng cách, độ nét giảm theo mất nét/mờ chuyển động, độ sáng giảm theo đèn yếu, sai khác tăng theo nhiễu/hạt/JPEG, CLI ghi tham số và không ghi đè.

### `auv_inspection/test_inspection_route.py`

`InspectionRouteTests` chỉ kiểm tra hình học, không mở Unreal:

- `test_station_advances_without_waiting_at_each_point()`
  - Xác nhận lookahead bỏ qua waypoint gần nhưng không bỏ qua điểm cuối.
- `test_short_steps_and_unique_names()`
  - Xác nhận tên waypoint duy nhất và khoảng cách giữa hai điểm liên tiếp không quá `0.80001 m`.
- `test_segments_clear_structure_bounds()`
  - Gọi `clearance_violations(ROUTE)`: không đoạn nào cắt AABB của ống/trụ/móng đã cộng biên an toàn `0.65 m`.
- `test_default_build_matches_validated_route()`, `test_clearance_check_detects_a_route_through_the_pipe()`
  - `build_route()` mặc định đúng bằng `ROUTE`; kiểm tra va chạm bắt được tuyến đi xuyên ống.
- `test_camera_faces_pipe_and_piers()`
  - Kiểm tra camera quay đúng vào hai mặt ống và tâm trụ.
- `test_both_pipe_ends_and_complete_pier_rings()`
  - Kiểm tra phủ hai đầu ống, đủ 24 điểm/vòng cho mỗi tầng của mỗi trụ và wrap góc đúng.

### `auv_inspection/tests/test_crack_detection.py`

Regression test thị giác bằng ảnh tổng hợp, không mở Unreal:

- Giữ vết nứt tối phân nhánh và vùng hư hại tối rộng.
- Giữ lỗ thủng tối lớn qua đủ chuỗi xác nhận 3 frame.
- Loại phản sáng có texture, mép vòng nối đứng, biên ống ngang và ảnh tối toàn cục.

### `auv_inspection/test_detection_gate.py`

- Xác nhận camera robot ở `pipe_front_scan_004`, vị trí `x=-16.90 m`, được đưa vào detector.
- Xác nhận auto vẫn bỏ qua station không phải scan và vị trí nằm ngoài chiều dài ống.

### `auv_inspection/tests/test_camera_regression.py`

- `load_frame(index)`: đọc fixture camera gốc từ `tests/data/pipe_views/`, báo lỗi rõ nếu thiếu ảnh.
- `overlaps_damage(box, expected)`: kiểm tra ít nhất một nửa box nằm trên vùng hư hại đã xem ảnh và đánh dấu; không chỉ chấp nhận box bất kỳ.
- `CameraRegressionTests`: giữ lỗ và hai vết nứt ở event 001–003, loại 11 ảnh báo nhầm mặt sau event 004–014, giữ hư hại khi lật ảnh ngang. Nguồn là lượt chạy người dùng `run_20260923_200549_863948`; README cạnh fixture ghi nhãn và giới hạn. Đây là dữ liệu dùng để hiệu chỉnh, không phải benchmark độc lập.

### `auv_inspection/tests/test_clean_structure_capture.py`

- `CleanStructureCaptureTests.test_saves_raw_camera_pixels_and_all_structure_categories()`: ghi ảnh mẫu của hai mặt ống và hai trụ vào thư mục tạm, đọc lại PNG để xác nhận pixel sensor không đổi; kiểm tra nhóm ảnh/metadata JSONL. Không mở Unreal.
- `test_excludes_transit_and_pier_entry()`: xác nhận không chụp đoạn chuyển tiếp hoặc waypoint tiếp cận trụ.
- `test_includes_four_orbit_levels_for_each_pier()`: xác nhận selector thu ảnh trên toàn bộ waypoint orbit của bốn tầng cho cả hai trụ trong route hiện hành.

### `auv_inspection/tests/test_find_editor.py`

- `make_engine(root, name)`: tạo cây thư mục giả có `UnrealEditor.exe` rỗng trong thư mục tạm.
- `FindEditorTests`: sáu test mock `launcher_engine_dir()`/`registry_engine_dir()` và xóa `AUV_UNREAL_EDITOR` khỏi môi trường test; kiểm tra thứ tự ưu tiên `--editor` > biến môi trường > Launcher > registry, thông báo lỗi nêu tên biến, và path tìm được phải tồn tại. Không đọc registry/manifest thật, không mở Unreal.

### `auv_inspection/check_detection_runtime.py`

- `main()`: QA thật bằng Unreal/HoloOcean, mặc định `--steps 6000`. Giữ nguyên các waypoint từ đầu đến cuối `pipe_back_scan`, chỉ cắt phần đi trụ trong bản route bộ nhớ của harness. Production route trên đĩa giữ nguyên.
- `start_offscreen(...)`: thêm `-RenderOffScreen` vào lệnh launch chuẩn, ghi nhận thư mục run. `record_gate(...)` ghi station/vị trí khi production kiểm tra gate; `record_analysis(...)` gọi detector thật trên `InspectionCamera`, lưu thống kê từng frame và ảnh gốc mỗi 30 frame mỗi phía.
- Dùng luồng GUI production nhưng ẩn `imshow`, giả lập Space qua `waitKey` và không lấy phím máy trong harness. Vì vậy chạy tiếp sau các cảnh báo, vẫn lưu event và áp dụng rearm 2 m thật. Không gọi thao tác editor hoặc save map.
- Ghi `output/detector_qa_*/frames.json`, ảnh camera, `summary.json` liên kết run report, số cảnh báo/tổng frame mỗi phía, SHA-256 map trước/sau. Báo lỗi nếu chưa xong cả hai phía hoặc map thay đổi. `route_completed` trong run QA chỉ áp dụng đoạn hai phía ống, không xác nhận toàn tuyến trụ.

### `auv_inspection/check_flashlight_runtime.py`

Harness runtime ngắn để so sánh trạng thái tắt/bật đèn; không phải unit test.

- `BACKSCAN_POSE`
  - Pose giữ cố định: `[10.0, -2.0, -10.3, 0.0, 0.0, 90.0]`.
- `class LightCheckEnvironment(inspection.EditorEnvironment)`
  - `__init__`: deep-copy scenario và thay pose spawn của AUV bằng `BACKSCAN_POSE`.
  - `step(...)`: tắt hai đèn ở tick đầu, bật lại bằng `enable_inspection_lights()` tại tick 180, rồi gọi `super().step()`.
- `main() -> None`
  - Monkey-patch environment và route bằng `unittest.mock.patch`, chạy headless 360 tick với 100 target giữ nguyên.
  - Harness có thể tạo bằng chứng vết nứt nếu frame đạt ngưỡng detector; ảnh lịch sử trong `ROUTE_VALIDATION.md` không đại diện cho recorder mặc định hiện tại.

### `auv_inspection/rebuild.py` (không có trong repo)

File này **không tồn tại** trong repo đã publish và không có trong lịch sử Git; `VALIDATION.md` (lịch sử 2026-09-19) vẫn nhắc tới nó, còn `auv_inspection/README.md` đã bỏ lệnh chạy. Theo mô tả trước đây, đây là launcher ngoài Unreal chạy `build_map.py` qua `PythonScriptCommandlet` và **có thể ghi đè toàn bộ chỉnh sửa thủ công trong map**. Không tạo lại hoặc chạy launcher này nếu người dùng chưa yêu cầu rõ ràng việc tái tạo map.

### `auv_inspection/create_validation_maps.py`

Script chỉ chạy trong Unreal Python (`import unreal`), không phải runtime.

- `create_variants() -> None`
  - Hash `AUVInspection.umap` gốc, rồi với từng role `clean`/`test_b` tạo bản sao `AUVInspection_PatchCoreClean_20260926_v3` / `AUVInspection_PatchCoreB_20260926_v3`; từ chối ghi đè map đích đã có.
  - Nạp lại đúng world đích trước khi sửa. `clean`: xóa mọi `DecalActor`. `test_b`: chỉ chấp nhận `DecalActor_1/2/6`, dời sang vị trí cố định trong source; decal lạ làm dừng lỗi.
  - Lưu map đích, xác minh hash map gốc không đổi, ghi `output/validation_maps_20260926.json`.
- Module gọi `create_variants()` ngay khi chạy. Đã dùng một lần; chạy lại sẽ dừng vì map đích đã tồn tại.

### `auv_inspection/finalize_validation_b.py`

Script Unreal Python cấp module (không có hàm), chạy sau `create_validation_maps.py`.

- Nạp map `AUVInspection_PatchCoreB_20260926_v3`, xác nhận đúng world; dừng nếu đã có actor `B_Hole*` (tránh chạy hai lần).
- Đổi scale (x0,8 / x1,2 / x0,8) và roll (+20 / -20 / +15 độ) của `DecalActor_1/2/6`; spawn thêm `B_HoleSmall` và `B_HoleLarge` dùng material `M_PipeBreak` trên mặt ống.
- Lưu map B, xác minh hash map A gốc không đổi, ghi inventory decal vào `output/validation_B_inventory.json`.

### `auv_inspection/inspect_validation_assets.py`

Script Unreal Python read-only: đọc class, `material_domain`, `blend_mode` của `M_HairCrack`, `M_PipeBreak`, `M_Crack` và ghi `output/validation_materials.json`. Không sửa asset.

### `auv_inspection/build_map.py`

Script chỉ chạy trong Unreal Python (`import unreal`); đơn vị hình học là centimet.

- `material(name, color, metallic=0.0) -> unreal.Material`
  - Load material hiện có hoặc tạo material mới với Base Color, Roughness `0.85`, Metallic theo tham số; compile và save asset.
- `mesh(name, shape, pos, size, mat, rotation=(0,0,0), collision=True, defect_id=0) -> unreal.StaticMeshActor`
  - Spawn `StaticMeshActor` từ basic shape, gắn material, scale, collision và label/folder.
  - Nếu có `defect_id`, bật custom depth/stencil và tag actor để phục vụ ground truth.
- `defect(kind, pos, surface, severity, materials, enabled) -> None`
  - Luôn thêm metadata vào `DEFECTS`.
  - Nếu enabled: crack được tạo từ các đoạn cube; corrosion/biofouling từ các sphere ngẫu nhiên có seed cố định.
- `main() -> None`
  - Đọc `scene.json`; backup `.umap` hiện tại vào `output/backups/<timestamp>/`.
  - Nếu map tồn tại thì load và xóa toàn bộ actor; nếu chưa có thì tạo level mới.
  - Tạo material, seabed, backdrop, ống/flange/support, hai trụ + dầm, defect, đá, light, fog, mặt nước và manager.
  - Tạo AUV preview chỉ dành cho editor; AUV vật lý thật vẫn do Python/HoloOcean spawn.
  - Save level/assets và ghi lại `scene_manifest.json`.

Launcher `rebuild.py` từng gọi script này không có trong repo; không có lệnh chính thức nào để chạy `build_map.py` trong bản hiện tại.

Lưu ý: map hiện tại đã được chỉnh thủ công sau lần sinh từ `build_map.py`; vì vậy `scene.json` và `scene_manifest.json` không mô tả đầy đủ state hiện tại của `.umap`.

### `auv_dashboard/run_dashboard.py`, `start_dashboard.cmd`, `__init__.py`

- `main()`: đọc `--autostart`, `--steps` (mặc định 60000, số dương), `--smoke-test`, `--v2-model` hoặc `--v1` (loại trừ nhau), `--world` (map dưới `/Game/AUVInspection/Maps/`, không có `..`; mặc định map của scenario, tức map A). Detector: `--v1` → PatchCore v1 sau cổng phê duyệt cũ; `--v2-model` → thư mục đó; mặc định `app.default_v2_model()` (ứng viên P7 khi khớp SHA256 đăng ký, nếu không ghi cảnh báo qua `logging` và dùng v1). Ghi log detector và world, thiết lập DPI, tạo Tk/`Dashboard`, chạy mainloop. Smoke test kiểm tra kết quả sau khi đóng và trả lỗi nếu không đạt. `--p8` (2026-10-16, không đi cùng `--v1`): chạy ứng viên phát triển P8 = `app.P8_MODEL` (`detector_v2_dino_s2_aug_g2_floor`, trừ khi có `--v2-model`) với quy tắc P8; chưa qua nghiệm thu nên chỉ bật khi được yêu cầu, không qua cổng D11.
- Entry point gọi `multiprocessing.freeze_support()` để tương thích spawn trên Windows.
- `start_dashboard.cmd`: chọn Python theo thứ tự `DASHBOARD_PYTHON`, `%USERPROFILE%\.conda\envs\mainenv\python.exe`, rồi `%CONDA_PREFIX%\python.exe` khi env conda đang activate là `mainenv`; báo lỗi hướng dẫn nếu không thấy, truyền tiếp tham số, giữ console khi có lỗi. `__init__.py` đánh dấu package, không có side effect.

### `auv_dashboard/bridge.py`

| Hàm / class | Trách nhiệm |
|---|---|
| `source_hashes()` | SHA-256 runtime, detector, scenario, route và map trước/sau phiên |
| `prepare_session_scenario()` | Copy `scenario.json` vào phiên dashboard, không ghi file cấu hình gốc |
| `publish_latest()` | Queue preview giới hạn, không block khi UI chậm; chỉ bỏ ảnh cũ |
| `encode_frame()` | JPEG với quality truyền vào (mặc định 87) cho ảnh màu/xám; PNG lossless cho mask |
| `viewport_pose()` | Vị trí spectator sau/trên AUV; bù phép `ConvertAngularVector` của TeleportCameraCommand hiện tại bằng đảo vector nhìn; không thay pose AUV |
| `run_worker()` | Tạo log/copy scenario, mở PatchCoreClient riêng môi trường nếu được chọn và có ngưỡng (truyền `options["patchcore_alert_rule"]`, mặc định `track`), gắn adapter theo process; với PatchCore + quy tắc `surface` patch `CRACK_REARM_DISTANCE_M` của runtime về 0 (service đã gộp trùng theo vùng bề mặt, khóa 2 m chỉ che cảnh báo thật; không sửa `run_inspection.py`), gọi `run`, ghi detector vào report, gửi report/lỗi, ghi source audit và đóng feeder preview |
| `DashboardEnvironment.step()` (class cục bộ) | Gọi nguyên `step`, đọc camera/pose/yaw/speed/tick và xóa trạng thái phân tích cũ; nhánh viewport capture còn trong bridge nhưng UI Tkinter hiện hành không kích hoạt |
| `read_commands()` | Nhận stop, pause, continue, follow và danh sách phím đang giữ |
| `launch_engine()` | Gọi Popen gốc, gửi PID và output cho UI |
| `advance()`, `gate()`, `analyze()` | Classical gọi hàm gốc; PatchCore mở gate khi `category_from_pose()` (P2, pose + hình học đã hiệu chỉnh, không dùng tên station) thấy công trình trong tầm 4 m và lưu nhóm vào `state["category"]`, gửi một frame mỗi ba tick thật của vòng `run()` đến service và lưu kết quả có tick phân tích cho preview; mỗi frame PatchCore đã phân tích được ghi một dòng vào `patchcore_frames.jsonl` của phiên (tick, nhóm, pose, trạng thái, lý do abstain, ba tỷ lệ của cổng lan tỏa, chất lượng ảnh, `surface_alerts`, số ứng viên/cảnh báo, thời gian xử lý) |
| `PatchCoreTracker.update()/reset()` | Adapter dùng sự kiện ba frame đã xác nhận từ service; không xác nhận lại trong runtime |
| `draw()` | Classical gọi hàm gốc; PatchCore trả annotation đúng frame của service |
| `damage_pause_remaining()` | Tính số giây còn lại trong khoảng giữ AUV sau cảnh báo, mặc định 5 giây |
| `save_event()` | Classical gọi lưu event gốc; PatchCore lưu camera/ROI/heatmap/mask/annotation/score và model/ngưỡng/tick/pose, `surface_alerts` (P5), sau đó giữ đúng ba ô bằng chứng, bắt đầu mốc 5 giây và gửi sự kiện tin cậy |
| `is_key_pressed()` | Thay đọc phím toàn hệ thống bằng trạng thái lệnh riêng của dashboard; ở auto PatchCore, lần kiểm tra Escape đầu mỗi vòng ghi tick của `run()` nên không lệch khi `reset()` bước camera trước vòng |
| `preview()` | Gửi viewport Unreal JPEG quality 78 và ảnh robot theo `preview_fps`; chỉ mã hóa pipeline theo `pipeline_fps` hoặc khi có bằng chứng mới; gửi pose/waypoint/candidate count, detector, trạng thái, lý do (`analysis_reason`, ví dụ `diffuse_anomaly` từ P3) và tick phân tích qua queue |
| `resume_damage_pause()`, `wait_key()` | Xử lý pause/stop; khi hết 5 giây, trả Space cho runtime để tiếp tục tự động; nút/Space của UI vẫn có thể bỏ qua chờ; gửi trạng thái resume và giới hạn nhịp 30 Hz |

`PROTECTED_FILES` gồm năm file được audit. Không đưa dữ liệu dashboard vào `auv_inspection/output/`. Dashboard sao chép nguyên scenario và nhận đủ bốn stage trong mọi preview; tham số flashlight vẫn do runtime gốc thực hiện.

### `auv_dashboard/patchcore_client.py`

`PatchCoreClient.__init__(..., roi_mode="geometry", score_margin_px=24, diffuse_gate=True, alert_rule="track", surface_calibration=None, border_margin=False)` (P4: truyền `--surface-calibration` khi có, `--border-margin` khi bật; bridge lấy từ `options["patchcore_border_margin"]`) mở Python riêng từ `.venv-patchcore` và truyền `--roi-mode`, `--score-margin-px`, `--diffuse-gate` (cấu hình P3), `--alert-rule` (P5), ghi stderr vào `patchcore_worker.log`, đọc stdout JSON-lines bằng thread và chờ thông điệp ready có timeout; bắt buộc file ngưỡng đã hiệu chỉnh. `_read_responses()` và `_receive()` chuyển lỗi/timeout/worker exit thành lỗi rõ; `analyze()` gửi PNG cùng tick/nhóm/station/pose, xác minh tick/nhóm trả về; `close()` dừng và thu hồi subprocess; `decode_image()` giải mã ảnh stage. Client đã được smoke offline với một frame A và đóng sạch. Bridge/app gọi nhánh này khi người dùng chọn PatchCore và có ngưỡng, nhưng chưa chạy thử cùng Unreal.

### `auv_dashboard/viewport.py`

`UnrealViewport.__init__()` giữ Tk host và handle; `attach()` tìm đúng cửa sổ Unreal theo PID, lưu style rồi SetParent vào host; `_area()` chọn cửa sổ có client area lớn nhất; `resize()` theo kích thước host; `detach()` khôi phục style/parent nếu cửa sổ còn sống. Không tìm hoặc điều khiển editor/cửa sổ của phiên khác.

### `auv_dashboard/widgets.py`

- `CameraTile.__init__()` tạo canvas placeholder; `set_frame()` đọc bytes ảnh vào Pillow; `render()` fit giữ tỷ lệ, giữ tham chiếu PhotoImage; `clear()` trả về placeholder.
- `project_3d()` là phép chiếu thuần từ XYZ qua yaw/pitch/scale sang tọa độ Canvas; test không cần mở Tk/Unreal.
- `RouteMap.__init__()` giữ đầy đủ XYZ của 359 waypoint, trail, marker hư hại và trạng thái orbit/zoom. `begin_orbit()`, `orbit()`, `wheel_zoom()`, `reset_view()` xử lý kéo/cuộn/đặt lại; `clear_run()` xóa dữ liệu phiên nhưng giữ góc nhìn; `add_alert()` đánh số tọa độ hư hại; `update_position()` thêm trail 3D và hướng AUV.
- `projection()`, `project()`, `line()`, `render()` tự fit theo kích thước Canvas rồi vẽ lưới đáy, ống, trụ theo chiều cao, tuyến kế hoạch, trail thực, marker và AUV. Đây là sơ đồ dựa geometry/tọa độ route đã biết, không phải cảm biến dựng bản đồ.

### `auv_dashboard/app.py`

`PATCHCORE_ALERT_RULE = "surface"` (P5) được truyền vào worker qua `options["patchcore_alert_rule"]`; `v2_files(model_dir)` (P4) trả model, `pixel_thresholds.json`, `surface_calibration.json` của một thư mục detector v2 (báo lỗi khi thiếu) và `patchcore_border_margin: True`; `DEFAULT_V2_MODEL` (`output/detector_v2_dino_s2_aug_g2`), `PREREGISTRATION`, `MAPS_PREFIX`; `default_v2_model()` trả `DEFAULT_V2_MODEL` khi `registered_candidate_matches()` đúng, ngược lại None. `Dashboard(..., v2_model=None, world=None)` dùng các file v2 thay v1 khi được truyền (chọn PatchCore, không qua cổng phê duyệt v1), từ chối `world` ngoài `MAPS_PREFIX` và gửi `options["world"]` cho worker và gửi `patchcore_surface_calibration` cho worker; đổi về `"track"` để dùng tracker ảnh ba frame cũ. `default_detector()` gọi `approval_gate.approval_matches()`; chỉ chọn PatchCore mặc định khi báo cáo B đạt đủ điều kiện và hash của ngưỡng, backbone/bốn bank/config, dataset ROI tham chiếu vẫn khớp bản đã đánh giá; hiện trả PatchCore sau khi B offline đạt. Chế độ `--smoke-test` luôn chọn Classical để giữ hợp đồng QA cũ. Đường dẫn model/dataset/ngưỡng/đánh giá là các hằng số ở đầu file. P8: `P8_MODEL`; `v2_files(model_dir, p8_rules=False)` thêm `patchcore_p8_rules`; `Dashboard(..., p8_rules=False)` (từ chối khi không có model v2) gửi tùy chọn này cho worker; `bridge.run_worker()` truyền `p8_rules` cho `PatchCoreClient(..., p8_rules=False)`, client thêm `--p8-rules` vào lệnh service.

| Thành viên `Dashboard` | Trách nhiệm |
|---|---|
| `__init__()`, `_configure()`, `_build()` | Khởi tạo trạng thái, Tk/ttk theme, bố cục theo sketch, bind phím/focus và vòng poll |
| `label()`, `button()` | Tạo widget cùng typography/màu |
| `send()`, `start()` | Gửi lệnh, kiểm tra PatchCore chỉ chạy auto và có ngưỡng, đổi nhãn ba stage, tạo session/queues và spawn worker với detector/chế độ/follow đã chọn |
| `toggle_pause()`, `continue_run()`, `set_follow()`, `stop()` | Điều khiển phiên qua queue; stop lưu thời điểm cho timeout cleanup |
| `key_down()`, `key_up()`, `release_keys()` | W/S/A/D/R/F/Q/E, Space, Esc; nhả phím khi Tk mất focus |
| `open_output()`, `open_alert()` | Mở folder phiên hoặc annotated.png của event chọn |
| `handle_event()` | Nhận PID, cảnh báo, resume tự động/thủ công, trạng thái, traceback, report; cập nhật nút/danh sách và thêm marker XYZ vào route khi có hư hại |
| `render_packet()` | Đưa `frames[1:4]` vào ba ô tương ứng Classical hoặc PatchCore vì ảnh gốc đã có ở camera robot; cập nhật route/trail XYZ, telemetry, tiến độ, FPS/latency, countdown tự tiếp tục, tick phân tích và trạng thái ROI/cảnh báo; frame `diffuse_anomaly` hiện "Bất thường lan rộng trên bề mặt · cần kiểm tra thủ công" thay vì thông báo thiếu ROI |
| `poll()` | Drain event/latest frame, nhúng Unreal, quản lý worker và cleanup chỉ tiến trình sở hữu sau timeout 12 giây |
| `save_ui_session()`, `close()`, `finish_close()` | Ghi ui_session.json khi worker kết thúc hoặc đóng UI, dừng/detach và đóng queues/Tk; giữ tóm tắt phiên trước nếu chạy lại |
| `snapshot()`, `qa_tick()`, `validate_smoke_test()` | Chụp vùng UI có DirectX, tự pause/continue/stop và xác minh chín điều kiện QA live; pause cho phép tối đa 3 tick đã nằm trong queue preview 12 FPS |

### `auv_dashboard/test_dashboard.py`

`DashboardBridgeTests` có bảy test: countdown giữ 5 giây rồi hết; mock worker (AUV đặt trước mặt ống, yaw -90°, để cổng hình học thấy công trình) xác minh PatchCore dùng tick của vòng runtime ngay cả khi `reset()` bước camera; queue không tăng khi UI chậm và giữ frame mới nhất; PNG giữ mask chính xác; JPEG giữ kích thước/kênh ảnh robot; phép chiếu route phân biệt độ sâu/chiều cao; spectator nhìn về AUV sau phép đổi trục thực tế của upstream ở năm góc yaw và không sửa mảng vị trí đầu vào. Đây là test không mở Unreal, tách với live smoke test.

## 5. File cấu hình và dữ liệu

### `auv_inspection/scenario.json`

- World: `/Game/AUVInspection/Maps/AUVInspection`.
- Main agent: `auv0`, loại `HoveringAUV`, `control_scheme = 1` (pose target).
- Simulation: 30 tick/s, spawn tại `[-14, 3.5, -10.3]`, yaw `-90°`.
- Biên môi trường: `[-35, -30, -13]` đến `[35, 30, 5]` mét.
- Sensor: Pose, Velocity, Depth, IMU và `InspectionCamera` 640×480 @ 30 Hz.
- Camera exposure compensation hiện là `0`.

### Môi trường nước Dam trên map thủ công

- `OriginalUnderwaterPostProcess` là `PostProcessVolume` có bounds xấp xỉ `x=-35..35 m`, `y=-30..30 m`, `z=-13..0 m`, `unbound=false`, `blend_weight=1` và priority `10`.
- Weighted blendable hiện tại: `/Game/AUVInspection/Materials/MI_DamWater_Inspection`, weight `1`. Instance này sao chép preset `/Game/WeatherContent/Fog/MM_Fog_Water_Dam`, dùng parent riêng `/Game/AUVInspection/Materials/M_DamWater_Absorption` sao chép từ `MM_Fog`. Các asset HoloOcean gốc không bị sửa.
- Parent riêng giữ đồ thị fog và function `MF_Depth_Fog` có sẵn; thêm hấp thụ RGB theo độ sâu từng pixel. `ScreenPosition.ViewportUV` nối vào `SceneDepth.UVs`; không lấy độ sâu từ một tọa độ UV cố định.
- Công thức hấp thụ bổ sung: `SceneRGB * exp(-Absorption_PerMeter * max(SceneDepth_cm / 100 - Near_Clear_Meters, 0))`. Các hệ số RGB lần lượt `0.18 / 0.055 / 0.025` mỗi mét, vùng gần miễn hấp thụ bổ sung `0.75 m`. Đây là xấp xỉ hình ảnh, không phải mô hình truyền bức xạ quang phổ đầy đủ.
- Material chạy **Before Tonemapping**, như material HoloOcean gốc. Không đổi exposure/cấu hình camera. Instance: `Fog_Color=(0.02, 0.08, 0.13)`, `Fog_Depth=30000 cm`, `Fog_Transition=0.1`, `Fog_Opacity=1`. Theo đồ thị gốc, alpha đạt `1` ở khoảng **30 m**; giá trị `Fog_Depth` không phải khoảng nhìn tối đa trực tiếp. Haze giảm tương phản theo khoảng cách; không thêm blur lên toàn ảnh. Viewport và sensor có exposure khác nhau nên độ sáng hiển thị không hoàn toàn giống nhau.
- Post Process Volume: bloom `0.15`, color gain toàn kênh `0.85`; không override exposure. `DirectionalLight`: intensity `1.5`, màu tuyến tính RGB `(0.65,0.88,1)`, volumetric scattering intensity `0.65`. `SkyLight`: intensity `0.7`.
- `ExponentialHeightFog`: density `0.035`, height falloff `0.05`, inscattering RGB `(0.025,0.14,0.20)`, volumetric fog bật, scattering distribution `0.45`, albedo RGB `(160,215,235)`, extinction scale `1.2`, view distance `6000 cm`.
- Ba `UnderwaterFill_*` vẫn intensity `2500`, attenuation radius `900`. WaterSurface, mọi mesh/material vật thể, decal, drone preview, camera actor, manager và mọi transform giữ nguyên. Chỉ bốn actor có thay đổi thuộc tính: DirectionalLight, SkyLight, ExponentialHeightFog, OriginalUnderwaterPostProcess; không thêm/xóa actor hoặc tạo map mới.
- Backup trước lần chỉnh này: `auv_inspection/output/backups/manual_map_before_dam_water_20260923/AUVInspection.umap`. Backup lần khôi phục blendable trước đó vẫn ở `manual_map_before_underwater_match_20260923_135048/`.
- Bằng chứng nằm cùng thư mục backup mới: `level_before.t3d`, `level_after.t3d`, `water_graph_final.t3d`, `final_audit.json`, `WATER_VALIDATION.md`, và `runtime_camera/`. Export T3D có 84 actor gồm actor nội bộ; API editor liệt kê 80 actor. Toàn bộ actor ngoài bốn actor cho phép có serialization giống hệt; toàn bộ transform và hash các file Python/config, material vật thể cũ không đổi.
- `capture_runtime_evidence.py` trong thư mục backup là harness QA, không thuộc luồng runtime: `capture_preview()` lưu mỗi ảnh preview thứ 30 rồi gọi `cv2.imshow` gốc. Harness gọi `run_inspection.run()` hiện có với 1800 tick, mode auto, giữ nguyên scenario/route/sensor/drone và phục hồi `imshow` sau khi xong. Không thêm dependency hoặc sửa source Python của project.
- Lượt QA cuối: `output/run_20260923_164234_462960/`, giới hạn 1800 tick, 60 ảnh camera 640×480. Các ảnh `camera_00510.png` và `camera_00900.png` đi qua hai decal vết nứt. Đây là kiểm tra camera/môi trường nước trong runtime; `route_completed=false` do giới hạn tick, không phải validation toàn tuyến.

### `auv_inspection/scene.json`

Input cho map generator cũ: bật crack/corrosion/biofouling/deformation và đặt `fog_density = 0.018`. Chỉnh file này không làm map thay đổi cho đến khi chạy rebuild.

### `auv_inspection/scene_manifest.json`

Ground truth của lần build cũ, không phải kết quả AI. Tọa độ client đổi từ Unreal theo:

```text
x = UE.x / 100
y = -UE.y / 100
z = UE.z / 100
```

### `auv_inspection/output/`

- Mỗi lần chạy tạo `run_<timestamp>` mới; runtime không đọc lại các run cũ.
- Không xóa `backups/` nếu chưa kiểm tra nhu cầu rollback.
- Nếu xóa run lịch sử, phải sửa tài liệu validation đang dẫn tới run đó.
- Chỉ coi tuyến auto hoàn thành khi `report.json` có `route_completed: true`.

### `auv_dashboard/output/session_*/`

- `scenario.json`: bản sao cấu hình đầu phiên; `worker.log`: trạng thái runtime/traceback.
- `source_audit.json`: dict `before`/`after` theo tên năm file bảo vệ, `finished_at`, `unchanged`.
- `ui_session.json`: trạng thái nhúng/tiếp tục, số cảnh báo, số điểm trail, worker exitcode, report và lỗi nếu có. `ticks`, `pause_tick`, `pause_delta_ticks` chủ yếu phục vụ smoke test; phiên thường không tích lũy tất cả tick vào UI.
- `output/run_*/`: schema report/telemetry/damage_events/unreal.log nguyên từ runtime gốc, nhưng nằm trong dashboard.
- `--smoke-test` thêm `dashboard_live.png`, `dashboard_alert.png`, `dashboard_resumed.png`, `qa_checks.json`. Screenshot chụp vùng dashboard đang hiển thị vì PrintWindow bỏ qua child DirectX.

## 6. Thay đổi riêng trong HoloOcean C++

File đang modified trong nested Git checkout:

```text
holoocean/engine/Source/Holodeck/ClientCommands/Private/TurnOnFlashlightCommand.cpp
```

Trong `UTurnOnFlashlightCommand::Execute()` project đã thêm logic:

- Load class Blueprint `/Game/FlashlightManager.FlashlightManager_C`.
- Kiểm tra world đã có actor đúng Blueprint class chưa.
- Nếu thiếu, spawn `AFlashlightManager` transient tại runtime.
- Sau đó mới ghi cấu hình đèn vào manager và gọi Blueprint event trên vehicle.

Lý do: AUV Blueprint truy vấn đúng Blueprint manager; actor base class C++ đặt trong custom map không đủ. Khi chuyển source sang máy khác cần build lại module Unreal/Holodeck để thay đổi này có hiệu lực.

Không coi các file trong `engine/Saved/`, autosave hoặc screenshot là source cần sửa.

### MCP điều khiển Unreal Editor

Project bật rõ plugin editor-only `FunplayMCP` phiên bản `0.2.0` trong `Holodeck.uproject` vì Unreal MCP chính thức của Epic không có trong UE 5.3. Plugin nằm tại:

```text
holoocean/engine/Plugins/FunplayMCP/
```

Plugin dùng `PythonScriptPlugin` và `EditorScriptingUtilities`, tự mở MCP HTTP trên loopback sau khi editor khởi động và tạo token theo project trong `holoocean/engine/Saved/FunplayMCP/`. Đây là công cụ thao tác editor, không phải dependency runtime của HoloOcean hay packaged simulation. Cấu hình client Codex nằm ngoài repo trong `%USERPROFILE%\.codex\config.toml`; không hardcode token vào source hoặc tài liệu.

## 7. Lệnh thường dùng

Từ root repo, sau `conda activate mainenv` (`python` là Python của `mainenv`, dù conda cài ở `%USERPROFILE%\.conda` hay nơi khác như `D:\Anaconda`; lệnh `.venv-patchcore` giữ nguyên):

```powershell
# Chạy tuyến tự động có camera preview
python .\auv_inspection\run_inspection.py

# Dashboard Tkinter hiện hành; cũng có thể nhấp đúp auv_dashboard/start_dashboard.cmd
python .\auv_dashboard\run_dashboard.py --autostart
# Mặc định: detector v2 + lề mép ảnh (ứng viên P7) khi file khớp SHA256 đăng ký; --v1 để dùng PatchCore v1
python .\auv_dashboard\run_dashboard.py --v1
# Ứng viên P8 (phát triển, chưa nghiệm thu): model _floor + quy tắc P8; thêm --world như dưới để chạy map B
python .\auv_dashboard\run_dashboard.py --p8
# Live trên map B (map nghiệm thu P7)
python .\auv_dashboard\run_dashboard.py --world /Game/AUVInspection/Maps/AUVInspection_PatchCoreB_20260926_v3

# Test adapter không mở Unreal / kiểm thử dashboard với Unreal thật
python -m unittest auv_dashboard.test_dashboard -v
python .\auv_dashboard\run_dashboard.py --smoke-test

# Chạy headless với giới hạn tick
python .\auv_inspection\run_inspection.py --headless --steps 60000

# Sau khi người dùng tự chuẩn bị map sạch: thu PNG camera gốc của ống và trụ
python .\auv_inspection\run_inspection.py --capture-clean-structures --headless --steps 60000

# Điều khiển thủ công
python .\auv_inspection\run_inspection.py --mode manual

# Khi hiện cảnh báo vết nứt trong cửa sổ camera: Space để tiếp tục, Esc để thoát

# Unit test hình học (không mở Unreal)
python .\auv_inspection\test_inspection_route.py

# Regression ảnh tổng hợp + 14 frame InspectionCamera thật (chạy từ root)
python -m unittest auv_inspection.tests.test_crack_detection auv_inspection.tests.test_camera_regression -v

# Capture có điều kiện ngẫu nhiên hóa (P1): train quanh nominal, heldout ngoài khoảng train
python .\auv_inspection\run_inspection.py --capture-structures --dataset-role train --scene-state clean --randomize train --seed 1 --headless --steps 60000
python -m unittest auv_inspection.robustness.tests.test_conditions -v

# Đánh giá theo vết vật lý trên capture (P1), chạy trong .venv-patchcore; benchmark lưới detector × điều kiện
& .\.venv-patchcore\Scripts\python.exe -m auv_inspection.robustness.evaluate_capture <capture_mixed> --detector patchcore --inventory .\auv_inspection\robustness\inventories\map_A.json --output <ket_qua.json>
& .\.venv-patchcore\Scripts\python.exe -m auv_inspection.robustness.benchmark <thu_muc_ket_qua> --mixed <capture_mixed> .\auv_inspection\robustness\inventories\map_A.json --clean <capture_clean>

# Capture calibration sạch cho quy tắc bề mặt (P5): map sạch v3, profile train, seed riêng
python .\auv_inspection\run_inspection.py --world /Game/AUVInspection/Maps/AUVInspection_PatchCoreClean_20260926_v3 --capture-structures --dataset-role calibration --scene-state clean --randomize train --seed 11 --headless --ignore-global-escape --steps 60000
# Calibration bề mặt (P5, .venv-patchcore); không ghi đè robustness/calibration/surface_v1.json đã có
& .\.venv-patchcore\Scripts\python.exe -m auv_inspection.robustness.calibrate_surface <capture_calibration_1> <capture_calibration_2> <capture_calibration_3>

# Tạo bản suy giảm có seed của một thư mục PNG (P1); không ghi đè thư mục đích
python -m auv_inspection.robustness.degradation <thu_muc_png> <thu_muc_moi> --degradation turbidity:3 --degradation marine_snow:2 --seed 0
python -m unittest auv_inspection.robustness.tests.test_degradation -v

# QA live cả hai mặt ống, tự tiếp tục cảnh báo, không mở cửa sổ
python .\auv_inspection\check_detection_runtime.py
```

Không có lệnh rebuild map: `auv_inspection/rebuild.py` không có trong repo (xem mục 4).

## 8. Trạng thái đã xác minh và giới hạn

### P7: nghiệm thu offline và live (2026-10-15)

- Live, dashboard mặc định (v2 + lề mép ảnh, khớp SHA256 đăng ký), điều kiện gốc, route 359/359. Map A `auv_dashboard/output/session_20261015_103902_679289/`: 3 cảnh báo, **3/3 vết, 0 báo nhầm** (tick 399, 645, 3276; 0,33/0,17/0,07 m). Map B `session_20261015_105712_694396/` (`--world .../AUVInspection_PatchCoreB_20260926_v3`, unreal.log xác nhận map): 6 cảnh báo; theo `locate_box` và `map_B.json` đã khóa: 4/5 vết (tick 582, 888, 1158, 1458; 0,08-0,27 m), 2 báo nhầm: tick 2352 `pipe_back` mép vòng bích x ≈ 9,2 (không có vết trong ảnh) và tick 7596 `pier_1` (tâm box cách vết nứt trụ 0,41 m > bán kính 0,35 m; ảnh annotated cho thấy box nằm trên vết, ô bề mặt cách đoạn nhãn khoảng 0,14 m). Median 296/275 ms mỗi frame, 79/94 frame `diffuse_anomaly`. Nhãn không sửa.

- `auv_inspection/output/benchmark_p7_acceptance/` (`dino_surface_b`, `patchcore_surface`, 6 capture heldout seed 101-106, 7 điều kiện, 84 kết quả) và `acceptance_report.json` từ `acceptance.py`. Ứng viên: recall 81/112 = 72,3% (bootstrap 63,5-79,4%), 0,345 báo nhầm/100 m, FPR mức ô 138/523.525 (Wilson trên 0,031%) → **không đạt** vì recall. Đối chứng: 58,9%, 2,89/100 m, 0,150%. Marine snow 8/32 vết; ngoài marine snow 73/80. 17/30 báo nhầm ở chân trụ (z < -10 m). Chi tiết ở `GENERALIZATION_PLAN.md`, Kết quả P7. Đây là kết quả offline, chưa phải live.

### Live v2 + lề mép ảnh và P6.1

- `auv_dashboard/output/session_20261014_161937_404843/` (2026-10-14, `--v2-model detector_v2_dino_s2_aug_g2`, lề mép ảnh bật qua `v2_files()`, map A, điều kiện gốc): route 359/359, 3 cảnh báo, **3/3 vết, 0 báo nhầm** (tick 399 `A_pipe_front_1` 0,20 m; 633 `A_pipe_front_2` 0,04 m; 3237 `A_pier_0_1` 0,07 m). 32 frame `diffuse_anomaly` (> 6 vùng). Median 321 ms/frame, p90 506 ms, đo khi benchmark P6.1 chạy cùng GPU.
- Benchmark `auv_inspection/output/benchmark_p6_ambiguity/` (`dino_surface_b`, 6 capture, mục `ambiguity`): vùng mơ hồ 18,7/100 m (≥ 1 hit), 3,3/100 m (≥ 2 hit); 15 vết sót, 4 nằm trong vùng mơ hồ, 2 trong vùng ≥ 2 hit. P6 dừng ở mức đo; chi tiết trong `GENERALIZATION_PLAN.md`, Kết quả P6.1.

### P4.3: NFAD và Mahalanobis (offline)

- Model: `auv_inspection/output/detector_v2_dino_s2_aug_g2_nfad8/` (8 hướng nhiễu, giải thích 47-51% phương sai nhiễu) và `..._aug_g2_maha/` (shrinkage 0,1), mỗi thư mục có `transforms.pt`, ngưỡng pixel và calibration bề mặt riêng. Log: `p4_3_build.log`, `benchmark_p4_3.log`.
- Benchmark 6 capture (42 lượt mỗi biến thể, cùng thư mục `benchmark_p4_dino_g2/`): v2 + lề 48/63 vết, 20 báo nhầm; NFAD 55/63, 30 (marine snow 8/9 mỗi mức, độ đục 4 không báo nhầm, mờ chỉ 4/9, marine snow 3 có 16 báo nhầm); Mahalanobis 40/63, 5 (≤ 0,98/100 m mọi lượt); NFAD rồi Mahalanobis (`..._aug_g2_nfmaha`, log `p4_3_nfmaha_build.log`, `benchmark_p4_3_nfmaha.log`) 42/63, 17. Mặc định dashboard không đổi: v2 + lề mép ảnh là ứng viên.

### Tập phát triển 6 capture (P4 phần 4, offline)

- Benchmark `auv_inspection/output/benchmark_p4_dino_g2/` mở rộng tới 6 capture (thêm seed 3-6; log `benchmark_p4_dino_g2_dev6*.log`, chạy qua hai lần tạm dừng của người dùng): v1.4 32/63 vết, 236 báo nhầm; v2 48/63, 42; **v2 + lề mép ảnh 48/63, 20** (lượt tệ nhất 1,81/100 m ở độ đục 4, mọi điều kiện khác ≤ 0,98). Ngoài marine snow v2 bắt 42/45 vết. Chi tiết: `GENERALIZATION_PLAN.md`, Kết quả P4 phần 4.

### Detector v2 với hình học v2 (P4 phần 3, offline)

- Model: `auv_inspection/output/detector_v2_dino_s2_aug_g2/` và `..._noaug_g2/` (dựng lại từ cùng 4 capture bank, calibration từ cùng 3 capture calibration). Log: `geometry_v2_rebuild.log`, `benchmark_p4_dino_g2.log`, `benchmark_p4_dino_g2_resume.log` (lượt cuối chạy lại sau khi người dùng tạm dừng).
- Benchmark `auv_inspection/output/benchmark_p4_dino_g2/`: v1.4 14/21 vết, 78 báo nhầm; v2 + suy giảm 17/21 vết, 2 báo nhầm (≤ 0,49/100 m mỗi lượt), abstain 13-20% frame trên map sạch; v2 không suy giảm 14/21 vết, 6 báo nhầm. Chi tiết: `GENERALIZATION_PLAN.md`, Kết quả P4 phần 3.
- Live v2 (`auv_dashboard/output/session_20261013_091452_126695/`, 2026-10-13, Tự động + PatchCore, `--v2-model detector_v2_dino_s2_aug_g2`, map A, điều kiện gốc): route 359/359, 4 cảnh báo; tick 396 → `A_pipe_front_1` (0,20 m), 627 → `A_pipe_front_2` (0,04 m), 3228 → `A_pier_0_1` (0,02 m), tick 6954 trụ 1 là báo nhầm trên vệt sẫm của vân bê tông (đã xem ảnh). Median 256 ms/frame cùng Unreal; 34 frame `diffuse_anomaly` do tiêu chí > 6 vùng (v2 cho nhiều vùng nhỏ). Một lượt ở điều kiện gốc trên map phát triển, không phải nghiệm thu.
- Capture heldout bổ sung cho tập phát triển (2026-10-12, profile heldout, đủ route): map A `auv_inspection/output/capture_test_mixed_20261012_223412_414540/` (seed 3, ống 2,85 m, trụ 3,20 m, 623 ảnh), `..._224039_596143/` (seed 4, 2,64 m, 3,53 m, 664 ảnh); map sạch `capture_test_clean_20261012_224925_781873/` (seed 5, 1,65 m, 2,36 m, 549 ảnh), `..._225923_851907/` (seed 6, 2,85 m, 3,31 m, 636 ảnh).

### Detector v2 (P4 phần 2, offline, hình học v1)

- Capture bank train sạch (2026-10-12, map sạch v3, profile train, đủ route): `auv_inspection/output/capture_train_clean_20261012_182016_486788/` (seed 21, 587 ảnh), `..._182617_290316/` (seed 22, 544), `..._183207_523279/` (seed 23, 520), `..._183703_841403/` (seed 24, 588).
- Model: `auv_inspection/output/detector_v2_dino_s2_aug/` và `..._noaug/` (bank 15.000 token mỗi nhóm, scale 2, `pixel_thresholds.json`, `surface_calibration.json`; bản calibration bề mặt có cổng cũ giữ ở `surface_calibration_abs_gate_superseded.json`). Log: `detector_v2_build.log`, `detector_v2_recalibrate.log`.
- Benchmark `auv_inspection/output/benchmark_p4_dino/` (v1.4, v2 có/không suy giảm, nhãn mới, cổng mới): tổng vết map A 11/21, 13/21, 14/21; tổng báo nhầm 89, 19, 10; marine snow 3: 86 → 0 báo nhầm với v2; map sạch gốc: v2 7 và 5 báo nhầm (mặt trụ gần mặt nước). Chi tiết trong `GENERALIZATION_PLAN.md`, Kết quả P4 phần 2. Dashboard vẫn dùng PatchCore v1; chưa chạy live v2.

### PatchCore v1.4 live trên dashboard (P5)

- `auv_dashboard/output/session_20261012_164927_783087/` (2026-10-12, Tự động + PatchCore, quy tắc bề mặt, map A, điều kiện gốc): route 359/359, 3 cảnh báo, mỗi lần giữ 5 giây rồi tự tiếp tục.
- Khớp `inventories/map_A.json` bằng `locate_box()` và đã xem ảnh annotated/heatmap: tick 429 → `A_pipe_front_1` (0,12 m), 705 → `A_pipe_front_2` (0,37 m), 3666 → `A_pier_0_1` (0,29 m). **3/3 vết, 0 báo nhầm, 0 báo trùng** (live v1.3: 3/3, 0 báo nhầm, 1 trùng). Event có `surface_alerts` với tọa độ bề mặt.
- `patchcore_frames.jsonl`: 2.155 frame phân tích (pier_0 663, pier_1 657, pipe_front 450, pipe_back 385), median 219 ms, p90 281 ms; 18 frame không có ROI (tick 1692-1743, vòng qua đầu ống); 12 frame `diffuse_anomaly` (tick 657-690) đều khi `A_pipe_front_2` trong tầm nhìn: 5,6-8,3% ROI vượt ngưỡng với 1-3 vùng. Cổng P3 đã coi vết lớn ở gần là bất thường lan tỏa; đã sửa sang đo độ phân tán ngày 2026-10-12 (benchmark `auv_inspection/output/benchmark_p5b_diffuse_spread/`), chưa chạy live lại.
- Một lượt ở điều kiện gốc trên map phát triển, không phải nghiệm thu.

### PatchCore v1.4: bằng chứng trên bề mặt (P5, offline)

- Capture calibration sạch mới (2026-10-12, map sạch v3 `ea94a84f...`, profile train, đủ route): `auv_inspection/output/capture_calibration_clean_20261012_110540_192827/` (seed 11, ống 2,33 m, 532 ảnh), `..._111452_059585/` (seed 12, 1,99 m, 566 ảnh), `..._114918_998711/` (seed 13, 2,15 m, 533 ảnh). `..._105722_271527/` chỉ có `conditions.json` (lượt bị Ctrl+C khi Unreal chưa khởi động), không dùng.
- `robustness/calibration/surface_v1.json` từ ba capture trên. Benchmark `auv_inspection/output/benchmark_p5_surface/` (tập phát triển, `patchcore_surface`): **0 báo nhầm ở 12/14 lượt** (v1.3 có 30 trên cùng 12 lượt), recall như v1.3 trừ mờ chuyển động 3 (2/3 → 1/3); marine snow 3 vẫn 19-21/100 m (v1.3: 16-17). Ở điều kiện gốc map A chỉ có 2 cảnh báo, cả hai trúng vết (`A_pipe_front_2`, `A_pier_0_1`).
- Các lượt thay thế giữ để đối chiếu: `benchmark_p5_surface_norm_only_superseded/` (chỉ ngưỡng tương đối: 10 báo nhầm map A gốc, phần lớn ở vòng bích), `benchmark_p5_surface_abs_degenerate_superseded/` (calibrate thống kê kết hợp: mọi ngưỡng tầng = 0).
- Đây là bằng chứng offline trên tập phát triển; lượt live v1.4 ở mục ngay trên.

### PatchCore v1.3 live trên dashboard (P3)

- `auv_dashboard/output/session_20261009_150224_114943/` (2026-10-09, Tự động + PatchCore, ROI hình học + lề 24 px + cổng lan tỏa, map A, điều kiện gốc): route 359/359, 4 cảnh báo, mỗi lần giữ 5 giây rồi tự tiếp tục.
- Khớp `inventories/map_A.json` bằng `locate_box()` với hình học đã hiệu chỉnh, đã xem ảnh annotated/heatmap: tick 405 → `A_pipe_front_1` (0,31 m), 654 → `A_pipe_front_2` (0,39 m), 3657 và 3888 → `A_pier_0_1` (0,22 m và 0,10 m, cùng vết nhìn từ hai pose). **3/3 vết, 0 báo nhầm, 1 báo trùng** (live P2: 3/3, 2 báo nhầm, 1 trùng).
- Session không ghi các frame `diffuse_anomaly` (trạng thái chỉ hiện trên UI); chưa biết lượt này có frame nào bị abstain. Một lượt ở điều kiện gốc trên map phát triển, không phải nghiệm thu.

### PatchCore v1.3: lề chấm điểm + cổng `diffuse_anomaly` (P3, offline)

- Benchmark `auv_inspection/output/benchmark_p3_quality/` trên tập phát triển (2 capture × 7 điều kiện, `patchcore_geo_m` và `patchcore_geo_md`; v1.2 so sánh lấy từ `benchmark_p2_geometry/`). Tổng báo nhầm 410 (v1.2) → 354 (lề) → 97 (lề + cổng); map A gốc 3,94 → 0,49/100 m, map sạch gốc 0; marine snow 5 abstain 99,7-100% frame thay vì khoảng 40/100 m báo nhầm.
- Còn lại: báo nhầm trên vòng bích `pipe_back` khi nước đục (lệch miền đặc trưng, P4/P5) và marine snow mức vừa 15-17/100 m (P5). Giới hạn 5%/6 vùng chọn trên tập phát triển, P7 phải kiểm lại trên heldout mới.
- Đây là bằng chứng offline; lượt live v1.3 ở mục ngay trên.

### PatchCore v1.2 live trên dashboard (P2)

- `auv_dashboard/output/session_20261009_103800_863732/` (2026-10-09, Tự động + PatchCore, ROI hình học, map A): route 359/359, 6 cảnh báo, mỗi lần giữ 5 giây rồi tự tiếp tục. Khớp bằng hình học đã hiệu chỉnh và xem ảnh từng event: event 001/002 đúng hai vết ống mặt trước; event 005 (tick 3942, lúc vào tầng 1 trụ 0) và 006 (tick 4119, trên vòng) đều là vết trụ `A_pier_0_1`, tức **báo trùng** vì hai vị trí cách nhau 2,08 m, vừa vượt khoảng khóa 2 m; event 003 (đầu ống x 15,1, `pipe_back_scan_002`) và 004 (`transit_pier_front_003`, nhìn xiên mép trên ống) là **báo nhầm ở biên ROI**. Kết quả 3/3 vết, 2 báo nhầm (P0: 3/3, 1 báo nhầm).
- Event 004 xảy ra khi đang chuyển tiếp: cổng hình học mở phân tích khi thấy công trình trong tầm 4 m, kể cả ngoài đoạn quét theo route (cố ý, phù hợp AUV thật, nhưng góc nhìn xiên).
- Nguyên nhân báo nhầm biên: ROI chỉ giới hạn tâm đặc trưng, còn trường nhìn của đặc trưng `layer3` rộng hàng chục pixel nên patch sát biên vẫn chứa nước, mép vòng bích hoặc nắp đầu ống. Ghi thành việc cần xử lý ở P3; báo trùng để P5 gộp theo tọa độ bề mặt.

### PatchCore v1.2: ROI hình học (P2, offline)

- Benchmark `auv_inspection/output/benchmark_p2_geometry/` (v1.2 lọc góc tới 70°; Classical và v1.1 chép từ lượt cùng hình học đã hiệu chỉnh), `.../pose_noise/` (nhiễu pose 0,1 m/2° và 0,25 m/5°), `benchmark_p2_geometry_no_incidence/` (v1.2 chưa lọc). Hai capture P1 nay là tập phát triển.
- v1.2 phân tích 100% frame (v1.1: 28-33%); vết map A 2/3 ở điều kiện gốc, 3/3 ở độ đục 2 (v1.1: 1/3); báo nhầm map sạch 0 ở gốc và đèn yếu (v1.1: 1,42 và 0,95/100 m); báo nhầm map A 3,94/100 m ở gốc, nằm trên dải mép ống/vòng bích theo ảnh đã xem; marine snow khoảng 40/100 m. Nhiễu pose 0,1 m/2°: 2/3 vết, 0,98/100 m; 0,25 m/5°: 1/3 vết, 0 báo nhầm, 93-96% frame ống ở 2,77 m trả `no_surface_tiles`.
- Chi tiết và phân tích ở mục "Kết quả P2" của `GENERALIZATION_PLAN.md`. Đây là bằng chứng offline; **dashboard live chưa chạy với ROI hình học** (đã đổi thành mặc định).

### Baseline v1.1 trên điều kiện chưa thấy (P1 phần 3, offline)

- Benchmark `auv_inspection/output/benchmark_p1_baseline_v1_1/` (28 tổ hợp: Classical/PatchCore × 2 capture heldout × 7 điều kiện suy giảm), chấm theo vết vật lý với `inventories/map_A.json` (trạng thái `proposed`). Bảng tóm tắt và phân tích ở mục "Baseline v1.1" của `GENERALIZATION_PLAN.md`.
- Classical: 0/3 vết, 0 báo nhầm ở mọi điều kiện; không có ứng viên trên các frame thấy rõ vết ở khoảng cách 2,77 m. PatchCore: 1/3 vết (vết trụ) ở 5/7 điều kiện, 0/3 với marine snow; trên map sạch 1,42 báo nhầm/100 m ở điều kiện gốc, tới 13,25/100 m với marine snow mức 5; tỷ lệ frame được phân tích sụp khi pose xa tham chiếu (ống 0% ở 2,77 m, trụ 1% ở 3,36 m). PatchCore khoảng 200-250 ms/frame offline trên RTX 3050.
- Đây là bằng chứng offline trên 2 capture Unreal thật, không phải lượt live dashboard; chưa đạt tiêu chí nghiệm thu nào.
- Bộ kết quả đầu tiên (`benchmark_p1_baseline_v1_1_superseded_point_label/`) giữ lại để đối chiếu: dùng nhãn trụ dạng điểm và thời gian xử lý tính cả frame bị bỏ qua; không dùng làm baseline.

### Capture ngẫu nhiên hóa với Unreal (P1 phần 2)

- `auv_inspection/output/capture_test_mixed_20261008_190916_184618/`: map A (SHA256 `daba22ec...`), `--randomize heldout --seed 1` (ống 2,77 m, trụ 3,19 m, dòng chảy 0,35 m/s, đèn 3839, pitch -7,1°), 550/550 waypoint, 598 ảnh (104/104/189/201 theo pipe_front/pipe_back/pier_0/pier_1).
- `auv_inspection/output/capture_test_clean_20261008_191432_831527/`: map `AUVInspection_PatchCoreClean_20260926_v3` (SHA256 `ea94a84f...`), `--randomize heldout --seed 2` (ống 1,62 m, trụ 3,36 m, dòng chảy 0,45 m/s, đèn 3446, pitch +8,7°), 551/551 waypoint, 635 ảnh (95/108/211/221).
- Đã kiểm chứng trên telemetry và ảnh: y khi quét mặt trước ống 2,83 m và 1,68 m (nominal 2,06 m); lệnh độ sâu dao động -10,49..-10,19 m và yaw -92,8..-87,5° trên mặt trước ống, AUV bám theo; khoảng cách giữa hai lần chụp 3-17 tick (15 giá trị khác nhau); ảnh mẫu thấy cả 3 vết của map A và không vết nào trên map sạch, kích thước ống và vị trí vùng sáng khác rõ so với nominal. Dòng chảy không đo được tác dụng (sai lệch ngang p95 6,5 cm so với 7,2 cm nominal), giải thích ở mục `robustness/conditions.py`.

### PatchCore live sau P0 (baseline v1.1)

- `auv_dashboard/output/session_20261008_174818_976289/` (2026-10-08, Tự động + PatchCore, map A, máy RTX 3050 4 GB): route 359/359, 4 cảnh báo, mỗi lần giữ 5 giây rồi tự tiếp tục. Đã xem ảnh từng event: event 001 (tick 405) và 002 (tick 651) đúng hai vết ống mặt trước (`mask_intersection`), event 004 (tick 3900) đúng vết trụ 0 (`nearest_mask` lệch 19 cm), event 003 (tick 1872, `pipe_back_scan_001`) là **báo nhầm** ở mép cuối ống do ROI `nearest_mask` lệch 27 cm lấn ra vùng nước. Kết quả: 3/3 vết của map A, 1 báo nhầm; Classical cùng map: 2/3, 0 báo nhầm.
- Suy luận 130-243 ms/frame khi dùng chung GPU với Unreal; mô phỏng còn 12,2 tick/s (Classical 23,5). Kết quả phát hiện không phụ thuộc tốc độ vì vòng mô phỏng khóa theo tick, nhưng đây là giới hạn vận hành (D13 trong `GENERALIZATION_PLAN.md`).
- Đây là một lượt trên map A tất định, không phải nghiệm thu tổng quát; báo cáo B offline cũ không mô tả hệ thống sau P0.

### PatchCore (offline, trước P0)

- Hiệu chỉnh trên A3 + lượt sạch calibration độc lập: 3/3 ID, 0 sự kiện sạch; ngưỡng front/back/pier0/pier1 = `61.55155/53.06446/58.91152/54.33251` trong `patchcore_thresholds_v1.json`.
- Nghiệm thu B với nhãn đã khóa trước khi score (`patchcore_evaluation_B_v1.json`): 5/5 vết, 4/4 vết nhỏ/mảnh, 0 báo nhầm trên lượt sạch test. Classical trên cùng B: 1/4 vết ống, không hỗ trợ trụ.
- Client/service JSON-lines riêng tiến trình replay 277 frame B: tất cả `ready`, khớp toàn bộ tick/box offline (`patchcore_worker_B_offline/report.json`). Thời gian score offline khoảng 62-106 ms/frame trên RTX 4060; chưa đo khi chạy đồng thời Unreal.
- `default_detector()` trả PatchCore khi `approval_gate.approval_matches()` xác nhận hash ngưỡng, model, ROI tham chiếu và điều kiện nghiệm thu B. Bản portable của ngưỡng/model/dataset sạch/báo cáo B nằm trong `patchcore_artifacts/`.
- **Chưa xác minh:** PatchCore chạy live trên dashboard cùng Unreal (FPS, pause/continue, độ trễ cảnh báo, tự tiếp tục 5 giây). Người dùng tự thực hiện.
- Giới hạn: chỉ năm vết, mô phỏng gần như tất định, ROI dùng nhánh `pose_match` vì route gần trùng; chưa chứng minh tổng quát khi ánh sáng, góc nhìn hoặc nhiễu thay đổi (xem `auv_inspection/NOISE_ROBUSTNESS_TODO.md`, `auv_inspection/PATCHCORE_HANDOFF.md`).
- Unit test PatchCore trong `auv_inspection/patchcore_data/tests/` hiện có 7 test method (tracker 2, approval gate 1, calibration budget 3, label integrity 1); không phải live validation.

### Classical, runtime và dashboard

- Dashboard Tkinter ba-stage đã chạy live với Classical tại `auv_dashboard/output/session_20260923_220549_429030/`: 9/9 smoke QA đạt, camera robot 282×230 hiển thị trực tiếp, ba ô dưới đúng CLAHE/mask/annotation, Unreal nhúng trực tiếp, route/marker cảnh báo cập nhật, pause/continue/stop sạch và worker exitcode 0. Đã xem `dashboard_alert.png`; audit năm file bảo vệ trước/sau trùng. Tại thời điểm đó 5 unit test dashboard đạt; hiện `test_dashboard.py` có 8 test (xem mục 4). Hành vi tự tiếp tục sau 5 giây ra đời sau lượt live này, mới chỉ có unit test. Hai lượt trước đó chỉ trượt ngưỡng QA pause cũ 2 tick vì đúng 3 tick preview đã nằm trong queue; mọi điều kiện khác đều đạt. Ngưỡng hiện hành là 3 tick, tương ứng một gói preview 12 FPS.
- Dashboard dùng Tkinter + Pillow + pywin32 + OpenCV/NumPy đã có trong `mainenv`, không cài dependency mới. Nhúng cửa sổ chỉ hỗ trợ Windows; 12 fps là mức tối đa preview, tốc độ thực tế phụ thuộc GPU. Chế độ manual dùng điều khiển gốc nhưng chưa kiểm tra toàn bộ phím bằng tay trong UI mới; phím chỉ được nhận khi Tk có focus, cần nhấp vùng giao diện nếu vừa tương tác với cảnh Unreal. Forced shutdown sau 12 giây có thể không lưu đủ report.
- Bản sửa mặt sau ngày 23/09: replay `run_20260923_200549_863948` giữ 3/3 ảnh hư hại mặt trước và loại 11/11 ảnh báo nhầm mặt sau. `tests/test_crack_detection.py` + `tests/test_camera_regression.py` qua 10 test method, gồm thêm 3 biến thể lật ngang. Dữ liệu này dùng để hiệu chỉnh, không phải accuracy trên tập độc lập.
- QA live `output/run_20260923_201417_730981/` đã xong cả hai mặt ống (106 waypoint của route QA): 1.062 frame mặt trước, 1.116 frame mặt sau; 3 cảnh báo đúng mặt trước tại tick 148/497/892, không ứng viên hoặc cảnh báo mặt sau. Đã xem các ảnh event và frame mặt sau. `output/detector_qa_20260923_201417/summary.json` cùng `frames.json`/ảnh cảm biến là bằng chứng. SHA-256 map trước/sau trùng `82f86647af711b386defb663dc6786c9edee9558991cc7cdc4e40ff7ad6ae78a`. Không chạy phần trụ trong harness này.
- Báo cáo replay trước/sau: `output/backscan_validation_20260923/replay.json`, ảnh tổng hợp `comparison.png`, bản detector trước chỉnh và script replay. Các ngưỡng mạnh hơn có thể bỏ sót nứt mảnh/tương phản thấp; chưa có hư hại thật được gán nhãn ở mặt sau để đo recall riêng phía đó. Không dùng station hoặc phía ống để tắt/bỏ qua detector.
- Unit test hình học và bằng chứng live runtime là hai tầng xác minh khác nhau.
- Chế độ thu ảnh sạch đã qua kiểm tra cú pháp, CLI help và unit lưu PNG/metadata; chưa chạy Unreal trên map sạch do người dùng đang tự chỉnh. Chỉ dùng dataset sau khi xác nhận `route_completed`, có ảnh đủ bốn nhóm và duyệt thấy không còn hư hại.
- `ROUTE_VALIDATION.md` ghi nhận một lượt live cũ hoàn thành 359/359 waypoint; cần chạy lại sau mọi thay đổi route, map, controller hoặc physics có ảnh hưởng.
- `VALIDATION.md` là lịch sử của map/tuyến cũ ngày 2026-09-19, không dùng để xác nhận bản hiện tại.
- Route cố định không tự phát hiện geometry mới và không tránh vật cản bằng sensor.
- Lượt live auto headless `output/run_20260923_174421_283669/` vẫn là bằng chứng detector sau khi dashboard đã bị gỡ: cảnh báo ở tick 502; `report.json` ghi `stopped_for_damage: true`, `damage_event_count: 1`.
- Detector cải tiến đã qua 7/7 unit test hình ảnh; cổng vị trí và tuyến qua thêm 8/8 test. Crop 640×480 từ chính cửa sổ camera robot người dùng gửi tạo ứng viên lỗ `(224,230,114,104)`, diện tích `1.764 px`, score `193,7`; bằng chứng ở `output/diagnostic_robot_camera_hole/`. Lượt live `output/run_20260923_200332_666151/` cảnh báo đúng lỗ tại `pipe_front_scan_004`, tick 148, vị trí `x=-16.90 m`, box `(224,230,122,104)`, score `192,37`; `damage_event_count=1`. Đây là xác minh trực tiếp frame `InspectionCamera` trong runtime, chưa phải đo precision/recall trên dataset độc lập.
- Đã chạy live manual với scenario test tạm spawn gần vết nứt và giả lập giữ phím A để đi qua bề mặt ống (không sửa scenario gốc/map): báo ở tick 92 với vết nứt nhìn thấy trong ảnh; telemetry ghi `damage_pause` từ tick 93 đến 108, trở lại `manual` từ tick 111 sau khi giả lập nhấn Space. Bằng chứng: `auv_inspection/output/manual_probe_scenario/output/run_20260923_172426_656460/`.
- Detector là heuristic hiệu chỉnh theo camera/map này, không phải model AI đã huấn luyện. Chưa có tập ảnh nhãn độc lập để đo precision/recall; bounding box có thể chỉ bao một nhánh vết nứt. Không suy luận mức hư hỏng.
- Chưa kiểm tra trực tiếp thao tác bàn phím/cửa sổ GUI bởi người dùng; manual probe giả lập `waitKey` và ẩn preview, nhưng dùng Unreal/HoloOcean thật.
- Build/compile thành công không chứng minh camera, vật lý hoặc route đã chạy end-to-end.

## 9. Quy tắc cập nhật tài liệu này

Agent sửa code/config/asset hành vi phải cập nhật `SOURCE_HANDOFF.md` trong cùng task khi có một trong các thay đổi:

- Thêm, xóa, đổi tên hoặc đổi trách nhiệm file.
- Thêm/xóa/đổi signature, side effect hoặc luồng của hàm/class.
- Đổi CLI, phím điều khiển, dependency, đường dẫn, config hoặc output schema.
- Đổi map/geometry/route, camera/light, Unreal C++ hoặc quy trình build/run/test.
- Có kết quả validation mới làm thay đổi trạng thái đã xác minh.

Checklist trước khi bàn giao:

1. So sánh source vừa sửa với các mục liên quan trong file này.
2. Cập nhật ngày ở đầu file và nội dung API/luồng/cấu trúc.
3. Nếu behavior thay đổi, cập nhật lệnh chạy và giới hạn tương ứng.
4. Chỉ ghi “đã xác minh” khi có bằng chứng test/runtime trong task hiện tại.
5. Không xóa cảnh báo về map thủ công, backup và ranh giới giữa static test với live Unreal.

## 10. Nhật ký cập nhật tài liệu

- `2026-10-16`: Dashboard/ứng viên P8: `live_service --p8-rules`, `PatchCoreClient(p8_rules)`, `bridge` truyền `patchcore_p8_rules`, `app.P8_MODEL`, `v2_files(p8_rules)`, `Dashboard(p8_rules)`, `run_dashboard.py --p8`. Kiểm: phát lại `capture_test_mixed_20261012_223412_414540` (điều kiện gốc) qua client thật cho 3 cảnh báo trùng tick và box với kết quả harness `dino_floor_bgsr`; dựng Dashboard với `--p8` và map B; 7 test dashboard pass. Chưa chạy live với Unreal.
- `2026-10-16`: Kết quả `dino_floor_bgsr` trên tập phát triển ghi vào `GENERALIZATION_PLAN.md`. Chỉ đổi tài liệu.
- `2026-10-16`: `live_service.is_diffuse(spread_all_regions)`, `Session.gate_spread_all_regions`, CLI `--gate-spread-all-regions`; harness cờ `s` (`dino_floor_bgsr`). 134 test `.venv-patchcore` pass (1 bỏ qua).
- `2026-10-16`: Kết quả P8.2 phần 2 (`benchmark_p8_dev_floor`, `benchmark_p8_dev_variants`, cache `p8_score_cache`) ghi vào `GENERALIZATION_PLAN.md`. Chỉ đổi tài liệu.
- `2026-10-16`: `score_cache.GridCache.save()` gộp với file trên đĩa và dùng file tạm theo PID (hai tiến trình đã ghi cùng file cache khi chạy song song); test `test_saves_from_two_runs_are_merged`. 71 file cache hiện có đều đọc được.
- `2026-10-16`: P8.2. `detector_v2/scorer.py` tách `grid()`/`expand()`, thêm `grid_cache_key()`; `robustness/score_cache.py` mới; harness `SCORE_CACHE_DIR` và hậu tố `g`/`r`; `benchmark.py --score-cache`; `live_service.without_small_hits()`, `evidence_min_region_px`. 132 test `.venv-patchcore` pass (1 bỏ qua). Đang nạp cache bằng lượt `dino_floor_b` trên 12 capture phát triển.
- `2026-10-15`: Kết quả P8.2 phần 1 (`benchmark_p8_dev`, `benchmark_p8_dev_floor`, `output/p8_diagnosis/p8_compare.py`) ghi vào `GENERALIZATION_PLAN.md`. Chỉ đổi tài liệu.
- `2026-10-15`: P8.2 code: cổng P8 tùy chọn trong `live_service` (`GATE_MIN_REGION_PX`, `min_region_px`, `region_share`, CLI), `model_geometry()`; `geometry.GeometryParams.pier_floor_z`, `calibration/geometry_v3.json`; `derive_model` loại `geometry`; `calibrate_pixel` dùng geometry của model; harness `_bg`, `dino_floor`; model `detector_v2_dino_s2_aug_g2_floor`. 130 test `.venv-patchcore` pass (1 bỏ qua). Hệ quả D11: hash code chấm điểm khác đăng ký P7 nên `default_v2_model()` trả None (dashboard về cổng v1 → Classical; `--v2-model` vẫn chạy được). Benchmark `benchmark_p8_dev` / `benchmark_p8_dev_floor` đang chạy.
- `2026-10-15`: P8.1 chẩn đoán (`auv_inspection/output/p8_diagnosis/`, script phân tích lưu cùng kết quả, không thuộc runtime). Ghi kết quả vào `GENERALIZATION_PLAN.md`. Không đổi code, ngưỡng hay artifact.
- `2026-10-15`: D11. `approval_gate.SCORING_CODE`, `code_sha256()`, `code_hashes()`, `code_matches()`; `approval_matches()` và `registered_candidate_matches()` kiểm hash code; `evaluate.py` ghi `code_sha256`; `acceptance_preregistration.json` thêm `code_sha256` lấy từ commit `2114d6a`; log của `run_dashboard.py` nói rõ khi quay về cổng v1. Cổng v1 nay trả Classical (báo cáo B cũ không có hash code). 125 test `.venv-patchcore` (1 bỏ qua) + 11 test cần `win32api` + 7 test dashboard pass; chưa chạy live sau thay đổi.
- `2026-10-15`: Ghi kết quả live P7 (map A 3/3, 0 báo nhầm; map B 4/5, 2 báo nhầm theo quy tắc). Chỉ đổi tài liệu.
- `2026-10-15`: Dashboard mặc định detector v2 + lề mép ảnh (`app.default_v2_model()`, `approval_gate.registered_candidate_matches()` kiểm SHA256 theo `acceptance_preregistration.json`); `run_dashboard.py --v1`, `--world`; `Dashboard(world)`; `bridge.run_worker()` truyền `world` vào `argparse.Namespace` của `run_inspection.run()` (dùng `--world` sẵn có của runtime, không sửa `run_inspection.py`). 134 test auv_inspection (123 trong `.venv-patchcore`, 1 bỏ qua; 11 cần `win32api` chạy trong mainenv) và 7 test dashboard pass; chưa chạy live.
- `2026-10-15`: Kết quả nghiệm thu P7 offline (`benchmark_p7_acceptance`, `acceptance_report.json`): ứng viên không đạt recall 90%, đạt báo nhầm và FPR ô. Chỉ đổi tài liệu.
- `2026-10-14`: P7. Kiểm 6 capture heldout seed 101-106 (đủ route, hash map đúng, artifact khớp SHA256 đăng ký); thêm và khóa `inventories/map_B.json` (người dùng duyệt), ghi SHA256 vào `acceptance_preregistration.json`. Benchmark `benchmark_p7_acceptance` đang chạy. Không đổi code.
- `2026-10-14`: P7 đăng ký trước: `robustness/acceptance.py`, `acceptance_preregistration.json`, FPR mức ô trong harness; 113 test pass. Chờ 6 capture heldout seed 101-106.
- `2026-10-14`: Ghi live v2 + lề mép ảnh (3/3 vết, 0 báo nhầm) và kết quả P6.1 (`benchmark_p6_ambiguity`); P6 dừng ở mức đo, chuyển P7. Chỉ đổi tài liệu.
- `2026-10-14`: P6.1. `surface.surface_point()`, `SurfaceEvidence.ambiguous_regions()`, harness `ambiguity_report()`/`length_of()` và mục `ambiguity` trong kết quả benchmark; thiết kế P6 ghi ở `GENERALIZATION_PLAN.md` mục 3.7. 109 test pass. Benchmark `benchmark_p6_ambiguity` đang chạy.
- `2026-10-14`: P4.3 phần cuối: `ChainedTransform`, `derive_model.py nuisance_mahalanobis --from-nuisance`, harness `dino_nfmaha(_b)`. Benchmark 6 capture: 42/63 vết, 17 báo nhầm, không hơn v2 + lề mép ảnh; kết thúc P4 với ứng viên đó. 107 test pass.
- `2026-10-14`: P4.3. Thêm `detector_v2/transforms.py`, `detector_v2/derive_model.py`; `scorer.py` hỗ trợ biến đổi theo nhóm, metric Euclid, `bank_dir`; harness thêm `dino_nfad`, `dino_maha` và bản `_b` cho mọi model v2. Benchmark 6 capture: NFAD 55/63 vết, 30 báo nhầm; Mahalanobis 40/63, 5; v2 + lề 48/63, 20. 106 test pass. Không đổi mặc định.
- `2026-10-13`: Đo hồ sơ ô sạch theo khoảng cách tới vòng bích (v2 + lề mép ảnh, 3 capture calibration và 6 capture phát triển, gốc và độ đục 4; `auv_inspection/output/joint_profile_v2.log`): giữ `JOINT_HALF_WIDTH_M` = 0,5; báo nhầm độ đục 4 rải dọc thân ống, không do vòng bích. Không đổi code.
- `2026-10-13`: P4 phần 4. `live_service.interior(..., image_border)`, `Session.border_margin`, CLI `--border-margin`; harness detector `dino_surface_b`; dashboard: `v2_files()` bật `patchcore_border_margin`, client/bridge truyền `--border-margin`. Benchmark 6 capture: v2 + lề mép ảnh 48/63 vết, 20 báo nhầm (v2 không lề 42, v1.4 236). Test service quality 11, dashboard 7/7, service v2 khởi động tới `ready` với `--border-margin`. Chưa chạy live với lề mép ảnh.
- `2026-10-13`: Ghi live v2 (`session_20261013_091452_126695`: 3/3 vết, 1 báo nhầm) và 4 capture heldout mới (seed 3-6) cho tập phát triển. Chỉ đổi tài liệu.
- `2026-10-13`: Sửa lỗi `NameError` khi chạy `run_dashboard.py --v2-model` (người dùng gặp khi chạy live): `Dashboard._build()` dùng biến cục bộ `v2_model` của `__init__`; nay lưu thành `Dashboard.v2_model`. Đã dựng Dashboard ở cả hai chế độ và khởi động `PatchCoreClient` với tham số v2 tới `ready`; dashboard test 7/7. Chưa chạy live v2.
- `2026-10-13`: P4 phần 3. Benchmark `benchmark_p4_dino_g2` với hình học v2: v2 + suy giảm mức 1 đạt 17/21 vết, 2 báo nhầm trên 14 lượt (v1.4: 14/21, 78). Dashboard: `app.v2_files()`, `Dashboard(v2_model)`, `run_dashboard.py --v2-model`, bridge/client truyền `--surface-calibration`. Dashboard test 7/7 trong `mainenv`. Chưa chạy live v2.
- `2026-10-12`: Hình học v2. `calibrate_geometry.py` nhận offset camera cố định (`--camera-forward`, `--camera-up`); `calibration/geometry_v2.json` mới và là mặc định của `geometry.CALIBRATION_FILE`; `inventories/map_A.json` tính lại bằng v2 (người dùng duyệt); `surface_evidence.CALIBRATION_FILE` → `surface_v2.json`; harness `V2_MODELS` → thư mục `_g2`. 102 test pass với v2. Calibration bề mặt, bank v2 và benchmark đang chạy lại.
- `2026-10-12`: P4 phần 2. Bank DINOv2 thật từ 4 capture train (seed 21-24) cho hai biến thể có/không suy giảm mức 1, calibration ngưỡng pixel và ngưỡng tầng v2 trên 3 capture calibration. `live_service.above_threshold_shape()/is_diffuse()` nhận `relative_threshold` (cổng đếm hit của quy tắc bề mặt); `SurfaceCalibration.lowest_threshold()`; `calibrate_surface.py` không dùng cổng; harness thêm `V2_MODELS`, detector `dino_surface`, `dino_surface_noaug`. Benchmark `benchmark_p4_dino`: v2 bỏ được báo nhầm marine snow 3, recall cao hơn, nhưng thêm báo nhầm ở mặt trụ gần mặt nước và mối nối. Phát hiện sai số hình học khoảng 0,35 m theo chiều đứng giữa các tầng trụ. 102 test pass. Chưa chạy live v2.
- `2026-10-12`: P4 phần 1. Tải trọng số DINOv2 ViT-S/14 (85 MB, người dùng duyệt). Thêm package `auv_inspection/detector_v2/` (`features.py`, `scorer.py`, `build_bank.py`, `calibrate_pixel.py`, 7 test). `live_service.py`: `Session.scorer`, `create_session()` nhận thư mục model v2. `calibrate_surface.py`: `--model-dir`, `--thresholds`. `inventories/map_A.json`: `A_pipe_front_2` thành đoạn (người dùng duyệt, ghi trong `revisions`). Smoke trên một frame vết ống với bank tạm từ capture sạch phát triển: heatmap bám vết, khoảng 210 ms ở scale 2 (không phải số liệu đánh giá). 100 test PatchCore/robustness/v2 pass. Chưa có bank thật (chờ 4 capture seed 21-24).
- `2026-10-12`: Sửa cổng `diffuse_anomaly`: `live_service.above_threshold_shape()` mới; `is_diffuse()` dùng tỷ lệ ngoài vùng liên thông lớn nhất (> 5%), số vùng (> 6) hoặc một vùng > 25% (`DIFFUSE_MAX_REGION_SHARE`); response và `patchcore_frames.jsonl` thêm `anomaly_spread`, `largest_region_share`. Benchmark tập phát triển `benchmark_p5b_diffuse_spread`: giống v1.4 ở 12/14 lượt, abstain ít hơn; khác biệt ở độ đục 2 map A là cảnh báo trên đầu vết dài `A_pipe_front_2` ngoài bán kính nhãn điểm (đã xem ảnh). Test service quality 9 (thêm 3), 93 test PatchCore/robustness pass, dashboard 7/7. Chưa chạy live.
- `2026-10-12`: Ghi kết quả live v1.4 (`session_20261012_164927_783087`): 3/3 vết map A, 0 báo nhầm, 0 báo trùng; `patchcore_frames.jsonl` cho thấy cổng `diffuse_anomaly` abstain 12 frame khi vết `A_pipe_front_2` lớn trong tầm nhìn. Chỉ đổi tài liệu, không đổi code, model, ngưỡng hay map.
- `2026-10-12`: P5. Thêm `robustness/surface.py` (tọa độ bề mặt theo mét), `robustness/surface_evidence.py` (ô 10 cm, `frame_cells()`, `is_hit()` = ngưỡng pixel AND ngưỡng tương đối theo tầng thân ống/mối nối/mặt trụ, `SurfaceEvidence` k = 3 lượt nhìn cách ≥ 0,3 m, gộp 0,6 m, `load_calibration()`), `robustness/calibrate_surface.py` (conformal theo tầng, `data_limited`) và `calibration/surface_v1.json` từ 3 capture calibration sạch mới (seed 11/12/13). `live_service.py`: `score_request()` tách từ `analyze_request()`, `surface_step()`, `surface_evidence()` kiểm hash file ngưỡng pixel, `--alert-rule {track,surface}`, `--surface-calibration`, response `surface_alerts`. Harness: `FrameResult.more_alert_bboxes`, `Score.rearm_m` theo `rearm_distance_m` của detector, detector `patchcore_surface`. Dashboard: `PATCHCORE_ALERT_RULE = "surface"`, client truyền `--alert-rule`, bridge patch `CRACK_REARM_DISTANCE_M` về 0 cho quy tắc bề mặt (người dùng đồng ý; không sửa `run_inspection.py`), ghi `patchcore_frames.jsonl` mỗi frame, event có `surface_alerts`. Benchmark tập phát triển `benchmark_p5_surface`: 0 báo nhầm ở 12/14 lượt, marine snow 3 vẫn 19-21/100 m. Test: surface 12, service surface 3, harness 6, PatchCore/robustness liên quan pass trong `.venv-patchcore`, dashboard 7/7 trong `mainenv`. **Chưa chạy dashboard live với v1.4.**
- `2026-10-09`: Mục 7 bỏ đường dẫn ghi cứng `$env:USERPROFILE\.conda\envs\mainenv\python.exe` (14 lệnh), dùng `python` sau `conda activate mainenv`; người dùng gặp lỗi khi conda cài ở `D:\Anaconda` (và `"$env:D:\..."` bị PowerShell hiểu là biến môi trường `D`). Chỉ đổi tài liệu.
- `2026-10-09`: Ghi kết quả live v1.3 (`session_20261009_150224_114943`): 3/3 vết map A, 0 báo nhầm, 1 báo trùng vết trụ; session chưa lưu frame `diffuse_anomaly`. Chỉ đổi tài liệu, không đổi code, model, ngưỡng hay map.
- `2026-10-09`: P3. `live_service.py` thêm `interior()`, `is_diffuse()`, `DEFAULT_SCORE_MARGIN_PX` = 24, `DIFFUSE_MAX_SHARE` = 5%, `DIFFUSE_MAX_CANDIDATES` = 6; `Session`/`create_session()` có `score_margin_px`, `diffuse_gate` (mặc định giữ hành vi v1.2), CLI `--score-margin-px`, `--diffuse-gate`; trạng thái `analysis_unavailable` + `reason: diffuse_anomaly` không bước tracker; response có `quality`. Thêm `robustness/quality.py` (`measure()`, chỉ chẩn đoán; cổng theo phân vị đã thử và bỏ). Harness: `FrameResult.reason`, detector `patchcore_geo_m`/`patchcore_geo_md`, cột `diffuse_share` trong benchmark. Dashboard: `PatchCoreClient` mặc định lề 24 px + cổng, bridge gửi `analysis_reason`, app hiện "Bất thường lan rộng trên bề mặt". Benchmark tập phát triển `benchmark_p3_quality`: tổng báo nhầm 410 → 97, recall giữ ở điều kiện có nghĩa (chi tiết trong `GENERALIZATION_PLAN.md`). Test: service P3 6, quality 4 (unit PatchCore + robustness liên quan 33/33), dashboard 7/7 trong `mainenv`. **Chưa chạy dashboard live với v1.3.**
- `2026-10-09`: Ghi kết quả live P2 (`session_20261009_103800_863732`): 3/3 vết map A, 2 báo nhầm ở biên ROI (đầu ống, mép ống khi nhìn xiên lúc chuyển tiếp), 1 báo trùng vết trụ. Không đổi code.

- `2026-10-09`: P2 (ROI hình học). `geometry.py` tham số hóa (`GeometryParams`, `load_params()`, chiếu theo lô, pháp tuyến/góc tới); thêm `calibrate_geometry.py` + `calibration/geometry_v1.json` (IoU kiểm tra 0,89-1,00; mask ORB 0,87-0,97), `geometric_roi.py` (nhóm theo pose, co theo sai số pose, lọc góc tới 70°). `live_service.py` thêm `roi_mode` (mặc định `geometry`), `select_roi()`, trạng thái `no_surface_tiles`; `patchcore_client.py` truyền `--roi-mode`; `bridge.py` mở cổng PatchCore bằng `category_from_pose()` và bỏ `patchcore_category()` (test dashboard đặt AUV trước ống). Harness: `evaluate_many()` dùng chung một lần suy giảm cho mọi detector, `perceived_pose()` mô phỏng sai số định vị (D14), detector `patchcore_geo`; `benchmark.py` có `--pose-noise`. `map_A.json` chuyển `reviewed`. Hai capture P1 chuyển thành tập phát triển; P7 cần capture heldout mới. Test: geometry 10, geometric ROI 8, harness 5, service 5 (thêm 2), dashboard 7. **Chưa chạy dashboard live với ROI hình học.**

- `2026-10-08`: P1 phần 3: thêm `robustness/geometry.py`, `defect_inventory.py`, `inventories/map_A.json`, `metrics.py`, `evaluate_capture.py`, `benchmark.py` và 16 unit test (geometry 7, metrics/inventory 6, harness 3); `test_conditions.py` bỏ qua test cần `pywin32` khi chạy trong `.venv-patchcore`. Chạy benchmark baseline v1.1 (kết quả ở mục 8 và `GENERALIZATION_PLAN.md`). Trong quá trình chạy phát hiện và sửa 2 lỗi đánh giá: nhãn trụ dạng điểm chấm sai một cảnh báo nằm trên vết, thời gian xử lý tính cả frame bị bỏ qua; đã chạy lại toàn bộ và giữ bộ cũ để đối chiếu. Không đổi detector, artifact hay map.

- `2026-10-08`: Ghi kết quả 2 capture heldout với Unreal (P1 phần 2) vào mục 8: cả hai đi hết route, khoảng cách/độ sâu/yaw/đèn/lịch chụp có tác dụng; dòng chảy không đo được vì bộ điều khiển PD của HoveringAUV quá cứng (`Kp = 100`), thêm D14 vào `GENERALIZATION_PLAN.md`. Không đổi code.

- `2026-10-08`: P1 phần 2: thêm `robustness/conditions.py` (profile `train`/`heldout`, route ngẫu nhiên có kiểm tra va chạm, dòng chảy, đèn, lịch chụp) và `--randomize`/`--seed` cho `run_inspection.py`; `inspection_route.py` thêm `build_route()` có tham số, `perturb_route()`, `clearance_violations()`, `STRUCTURE_BOXES`; `enable_inspection_lights()` nhận intensity/pitch. Mặc định không đổi hành vi. Kiểm tra va chạm đã từ chối bán kính trụ heldout 2,2 m, nâng cận dưới lên 2,35 m. Tìm thấy `water_fog` cần tag `WaterPPV` mà map dự án không có, nên chưa ngẫu nhiên hóa độ đục trong mô phỏng. Test offline 57/57 (18 robustness, 10 route/gate, 29 dashboard/runtime). **Chưa chạy capture ngẫu nhiên hóa với Unreal.**

- `2026-10-08`: P1 phần 1: thêm package `auv_inspection/robustness/` với `degradation.py` (7 yếu tố × 5 mức, có seed, CLI) và 9 unit test (đạt ở `mainenv` và `.venv-patchcore`). Đã xem lưới mức nghiêm trọng trên frame thật của phiên P0 để QA trực quan; bản đầu dùng độ sâu theo ROI gây viền giả và marine snow dạng khối chữ nhật, mất 2,2 s ở mức 5, đã sửa trước khi commit. CLI chạy 14 fixture camera trong khoảng 2,8 s. Thử minh họa (không phải đánh giá) Classical từng frame trên 14 fixture × 3 seed: tỷ lệ bắt hư hại 67% ở độ đục mức 2 và 0% ở mức 5; marine snow mức 5 gây 21% frame sạch báo nhầm; nhiễu cảm biến và JPEG không ảnh hưởng. Không đổi detector, artifact hay map.

- `2026-10-08`: Ghi kết quả live P0 (`session_20261008_174818_976289`) vào mục 8 và bảng tiến độ của `GENERALIZATION_PLAN.md`: 3/3 vết map A, 1 báo nhầm ở đầu ống, 12,2 tick/s; thêm D13 (suy luận đồng bộ chặn vòng mô phỏng). Không đổi code.

- `2026-10-08`: P0 của `GENERALIZATION_PLAN.md`. `live_roi.match_roi()` bỏ nhánh ORB, giữa hai pose tham chiếu dùng giao hai mask gần nhất (thêm `nearest_references()`, `within_reference_range()`, `read_mask()`, trạng thái `roi_too_small`; `ReferenceFrame` bỏ trường `source_image`). Lựa chọn dựa trên đo 552 mask đã duyệt: co mask chỉ nâng tỷ lệ ROI nằm trên bề mặt (p10) từ 0,883 lên 0,908 với ống, còn giao hai mask lân cận nâng từ 0,79-0,97 lên 0,89-1,00, đổi lại độ phủ trụ giảm (p10 0,58-0,62). `live_service.analyze_request()` không reset tracker khi frame không đủ điều kiện. Replay chuỗi pose của phiên `session_20260927_191813_365317`: tỷ lệ frame có ROI tăng từ 28-49% lên 99,1-100%; trên trụ khoảng 40% frame chỉ có một tham chiếu cùng station (`nearest_mask`), để P2 xử lý. Unit PatchCore 15/15 (7 cũ, 8 mới) trong `.venv-patchcore`. **Chưa chạy live Unreal sau P0**; kết quả B offline cũ không còn mô tả hệ thống này (cổng hash vẫn khớp vì không hash code, xem D11).

- `2026-10-08`: Thêm `GENERALIZATION_PLAN.md`: chẩn đoán các điểm tất định (D1-D12, gồm phiên live PatchCore 2026-09-27 bỏ 47-72% frame vì thiếu ảnh tham chiếu và tracker reset), kiến trúc mới (cổng chất lượng, ROI hình học, DINOv2/Mahalanobis/loại nhiễu, ngưỡng conformal, SPRT trên bề mặt, quay lại chụp gần), ngẫu nhiên hóa điều kiện, giao thức đánh giá, lộ trình P0-P7 và tiêu chí nghiệm thu bản đầu. README gốc liên kết tới file này. Chỉ thêm tài liệu, không đổi code, artifact hay map.

- `2026-09-27`: `scripts/setup_project.ps1` thêm `Write-JsonNoBom()` để ghi `patchcore_thresholds_v1.json`/`patchcore_evaluation_B_v1.json` bằng UTF-8 không BOM. Trước đó `Set-Content -Encoding utf8` của Windows PowerShell 5.1 thêm BOM, khiến `approval_gate.approval_matches()` trả sai (dashboard mặc định Classical) và `live_service.create_session()` lỗi `JSONDecodeError` khi đọc ngưỡng. Đã chạy lại đoạn cài artifact trên máy người dùng: cổng trả PatchCore, `PatchCoreClient` khởi động service tới `ready` trên RTX 3050 trong khoảng 22 giây. Chưa chạy PatchCore live cùng Unreal. Không đổi nội dung ngưỡng, model hay map.

- `2026-09-27`: Hỗ trợ máy cài UE/conda ngoài đường dẫn mặc định. `run_inspection.find_editor()` tìm theo `--editor`, `AUV_UNREAL_EDITOR`, Epic Launcher, rồi registry `HKLM\SOFTWARE\EpicGames\Unreal Engine\5.3`, tách `launcher_engine_dir()`/`registry_engine_dir()`; thêm `tests/test_find_editor.py` (6 test). `start_dashboard.cmd` nhận `DASHBOARD_PYTHON` hoặc env conda `mainenv` đang activate. README gốc thêm yêu cầu build (.NET Framework SDK, MSVC 14.38 do lỗi C4668 với MSVC 14.40+), cách tạo `mainenv` Python 3.11+ và `.venv-patchcore`; README dashboard cập nhật tương ứng. Unit test chạy trên `mainenv` máy người dùng; lookup thật trả đúng `UnrealEditor.exe`. Chưa chạy Unreal/dashboard live sau thay đổi. Không đổi detector, route, artifact hay map.

- `2026-09-27`: Sửa `Copy-OverlayDirectory()` trong `scripts/setup_project.ps1`: `Copy-Item -LiteralPath <src>\*` không mở rộng wildcard nên bốn thư mục (map/asset AUVInspection, plugin FunplayMCP, model và dataset PatchCore) được tạo rỗng, khiến `Update-ReferenceManifest()` lỗi thiếu `manifest.jsonl`. Nay liệt kê con bằng `Get-ChildItem -LiteralPath` rồi copy, và dừng rõ lỗi nếu nguồn rỗng. Đã thử hàm trên scratchpad (572/572 file, chạy lại với `-Force` không lồng thư mục); chưa chạy lại toàn bộ script trên máy người dùng. Không đổi artifact, map hay runtime.

- `2026-09-26`: Đồng bộ tài liệu với repo đã publish: đánh dấu `auv_inspection/rebuild.py` không có trong repo và bỏ lệnh rebuild ở mục 7; thêm mô tả `create_validation_maps.py`, `finalize_validation_b.py`, `inspect_validation_assets.py` vào mục 2 và 4; tách mục 8 thành PatchCore (offline, chưa live) và Classical/runtime/dashboard; sửa số test dashboard (hiện 8) và thêm ghi chú lỗi thời cho các dòng nhật ký cũ về GitHub và `default_detector()`; `auv_inspection/README.md` bỏ lệnh `rebuild.py`, thay bằng cảnh báo generator cũ xóa chỉnh sửa thủ công. Chỉ sửa tài liệu, không chạy test, không đổi code, artifact hay map.

- `2026-09-26`: Thêm `PROJECT_STATUS_AND_ROADMAP.md` tổng hợp kiến trúc, phần đã làm, kết quả offline PatchCore, giới hạn xác minh, lộ trình xử lý nhiễu và đề xuất nghiệm thu. Không thay đổi code, artifact, detector, route hoặc map.

- `2026-09-26`: Dashboard tự giữ pose 5 giây khi runtime phát hiện hư hại, giữ lại ảnh bằng chứng đúng tick phát hiện rồi tự gửi lệnh tiếp tục. Nút Tiếp tục/Space chỉ bỏ qua thời gian chờ. Thêm countdown vào packet/UI và unit test thuần cho thời lượng; chưa chạy live Unreal cho thay đổi này. Không sửa detector, scenario, route hoặc map thủ công.

- `2026-09-26`: Chuẩn bị cấu trúc chia sẻ GitHub: thêm README, `.gitignore`, `.gitattributes` Git LFS và `scripts/setup_project.ps1`; script pin HoloOcean upstream `49e70552`, cài overlay map/asset/C++/plugin và artifact PatchCore. `worlds/`, checkout `holoocean/`, output/log, môi trường ảo và cache Unreal không được version để tránh upload 6.1 GB package và dữ liệu máy cục bộ. Chưa khởi tạo/commit/push GitHub tại thời điểm cập nhật. *(Đã lỗi thời: repo đã được publish sau đó, xem commit `a891431`.)*

- `2026-09-26`: Thêm `auv_inspection/NOISE_ROBUSTNESS_TODO.md` ghi backlog nhiễu quan sát chưa triển khai: noise/haze, nước đục, particle, bọt khí, blur, lệch pose, ánh sáng và sonar; gồm quality gate, ràng buộc xử lý thống nhất dữ liệu sạch/live và tiêu chí nghiệm thu. Không đổi runtime, model artifact, ngưỡng hay map.

- `2026-09-26`: Thêm `auv_inspection/PATCHCORE_GUIDE_VI.md` cho thành viên nhóm: mô tả dataset/ROI bốn nhóm, memory bank, fit chỉ từ ảnh sạch, calibration/test, pipeline inference, heatmap, tracker và giới hạn với hư hại mới. Không sửa runtime, model artifact, ngưỡng hay map.

- `2026-09-26`: Hoàn tất B 552 frame tại `capture_test_mixed_20260926_130548_302454`, duyệt 552 ROI và năm ID bằng ảnh raw/overlay, đánh dấu mép mờ unclear, khóa nhãn trước score. `patchcore_evaluation_B_v1.json` đạt 5/5 vết, 4/4 nhỏ/mảnh, 0 báo nhầm trên sạch test; Classical 1/4 vết ống, trụ không hỗ trợ. Đã xem bảy box sự kiện; client/service thật replay 277 frame B đều ready và khớp toàn bộ tick/box offline (`patchcore_worker_B_offline/report.json`). Unit PatchCore 7/7 và dashboard 7/7 (sau đó thêm test countdown, hiện 8 test); default_detector() trả PatchCore, chưa mở UI/live Unreal PatchCore theo yêu cầu người dùng. Thêm `auv_inspection/PATCHCORE_HANDOFF.md` với kết quả, giới hạn năm vết/mô phỏng gần tất định và hướng dẫn test dashboard. Source map A giữ hash daba22ec...; các bản riêng sạch/B đã được người dùng cho phép.

- `2026-09-26`: Hiệu chỉnh trên A3 và lượt sạch độc lập hoàn tất: ngưỡng front/back/pier0/pier1 = 61.55155/53.06446/58.91152/54.33251, phát hiện 3/3 ID A và 0 sự kiện sạch calibration; lưu `output/patchcore_thresholds_v1.json`, chưa phải kết quả test. Lượt sạch test `capture_test_clean_20260926_125649_289753` đủ 552 frame, đã score. B lần đầu dừng `stopped_by_user` sau 466 frame; không dùng làm tập test hoàn chỉnh. `run_inspection.main()/run()` thêm cờ opt-in `--ignore-global-escape` chỉ hợp lệ cho capture headless, tránh Esc ở ứng dụng khác dừng thu ảnh; Ctrl+C vẫn hoạt động, dashboard/default không đổi. Đang thu lại B tại `capture_test_mixed_20260926_130548_302454` với cờ này.
- `2026-09-26`: Hoàn tất lượt sạch calibration `capture_calibration_clean_20260926_125138_366081` (552 frame, đủ 359 waypoint). Dataset `patchcore_dataset_A3_20260926` giữ ba ID theo yêu cầu mới; chuyển nhãn/mask đã duyệt sau đối chiếu 552 frame với A cũ, tối đa 9 pixel chênh >8/frame, lưu audit, không thay dữ liệu A cũ. Dataset sạch calibration cũng khớp train sạch trong giới hạn này và chuyển mask đã duyệt; đây là lượt độc lập nhưng mô phỏng gần như tất định, chưa chứng minh tổng quát dưới thay đổi ánh sáng/góc nhìn. A3 đã score 552 frame, median 106 ms/frame khi chia sẻ GPU với capture. `inspect_validation_assets.py` đọc material domain; `finalize_validation_b.py` nạp riêng map B, đổi hướng/scale ba vết và thêm hai decal M_PipeBreak nhỏ/lớn, lưu inventory và xác minh hash A không đổi. B có năm ID, chưa xem score hay nghiệm thu. Lượt sạch test `capture_test_clean_20260926_125649_289753` và score sạch calibration đang chạy tại thời điểm cập nhật. Dashboard test vẫn dành cho người dùng.
- `2026-09-26`: Người dùng cho phép chạy lại capture và tạo bản map riêng sạch/B, giữ nguyên A gốc; dashboard test do người dùng thực hiện. `run_inspection.run()/main()` thêm `--world` giới hạn dưới `/Game/AUVInspection/Maps/`, dùng đúng asset để launch/hash và ghi world vào report. `create_validation_maps.py:create_variants()` chạy trong Unreal Python, tạo bản sao, nạp lại đúng world trước khi sửa decal, từ chối ghi đè đích và xác minh hash nguồn. Các map hợp lệ mang hậu tố `_PatchCoreClean_20260926_v3` và `_PatchCoreB_20260926_v3`; các bản thử trước v3 không dùng. Clean không còn decal; B hiện di chuyển ba decal sang vị trí khác, chưa hoàn tất kiểm tra độ đa dạng/ảnh camera. Báo cáo `output/validation_maps_20260926.json` xác nhận nguồn giữ hash `daba22ec...`. Capture A mới `capture_calibration_mixed_20260926_124619_834409` hoàn thành 359 waypoint/552 ảnh đủ bốn nhóm. Kiểm tra cú pháp Python đạt; chưa chốt ngưỡng hoặc nghiệm thu B.
- `2026-09-26`: Người dùng xác nhận bố trí A mới chỉ còn ba decal, bỏ hai vết trụ không quan sát được; giữ dữ liệu A năm vết cũ làm lịch sử, không sửa nhãn cũ thành ba vết. Map đã lưu có SHA256 `daba22ece60400aa19e5e2676a0005af51d19d105f5e03f6bce611948dc361d2`. Capture mới `capture_calibration_mixed_20260926_124137_738483` kết thúc với `stopped_by_user=true`, chỉ có 166 ảnh (106 front, 60 back, chưa có trụ), chưa hợp lệ làm A hoàn chỉnh. Sửa `threshold_candidates()` xử lý nhóm không có nhãn visible (ví dụ pier_1) mà không gây TypeError; thêm regression test, cả ba test hiệu chỉnh đạt. Người dùng sẽ tự chạy dashboard test; vẫn cần dữ liệu sạch calibration/test và bố trí B để nghiệm thu offline.
- `2026-09-26`: Mở rộng ứng viên ngưỡng PatchCore xuống dưới trung vị đỉnh ảnh sạch, có xét score vùng vết đã duyệt để không loại sớm vết mảnh yếu; vẫn đánh giá báo nhầm bằng tracker trên toàn route sạch và giữ ngân sách tối đa hai sự kiện. Unit tổng hợp hiệu chỉnh 2/2 đạt; chưa có calibration sạch độc lập hoặc A đủ năm vết để xác nhận ngưỡng thật. Map không đổi.
- `2026-09-26`: Thêm capture trung lập role/state và map hash; đăng ký 552 ảnh sạch, công cụ polygon/đề xuất/duyệt ROI và lõi PatchCore tiled bốn nhóm; cài riêng Anomalib/PyTorch CUDA và ghi phiên bản dependency. QA 552 mask bằng ảnh ghép, fit bốn bank trên GPU và dự đoán offline một frame sạch. Chuẩn bị/chấm điểm lượt A, đối chiếu với sạch và truy vấn read-only năm decal; hai decal trên trụ ở tầng giữa chưa hiện rõ trong sensor. Thêm công cụ nhãn/khóa test/hiệu chỉnh/đánh giá; tách gợi ý theo năm ID vật lý, yêu cầu nhãn đầy đủ và hash khóa, xác minh model score và bắt buộc toàn bộ vết test quan sát được để nghiệm thu; kiểm tra unit nhãn đạt. Thêm bộ chọn ROI trực tiếp và audit 552/552 frame A so với mask đã duyệt; service/client riêng môi trường khớp score offline một frame. Nối lựa chọn PatchCore/Classical với dashboard, bằng chứng PatchCore đúng tick của vòng runtime ngay cả khi reset bước camera và gate ngưỡng/test B cho mặc định; mock worker và test giới hạn báo nhầm toàn route đạt. Chấm điểm chẩn đoán 552 ảnh train sạch, thấy tracker tâm đứng yên bỏ cả hai vết ống; thay bằng tracker quỹ đạo, xác nhận lại hai vết ống và một vết trụ nhìn thấy trên A với ngưỡng thử, không dùng làm hiệu chỉnh chính thức. Chưa chạy hiệu chỉnh/nghiệm thu/live Unreal cho PatchCore; map thủ công giữ nguyên.
- `2026-09-26`: Kiểm tra lượt A chụp lại lúc 01:51: map SHA256 không đổi, 213/213 ảnh ống trùng hoàn toàn với A trước, sai khác ảnh trụ chỉ ở mức vài pixel nhiễu; hai decal trụ cao vẫn chưa có hình rõ trong sensor. Đối chiếu read-only transform/scale của ba decal trụ và giữ map nguyên trạng.
- `2026-09-26`: Thêm preview vài pose camera theo tick capture cũ để xem decal tại đúng tầng quét mà không chạy toàn route; kiểm tra unit 4/4 và chạy Unreal headless ba pose `pier_0_level_2` thành công tại `output/preview_poses_20260926_020844_407615/` (sai lệch vị trí ~0,123 m, yaw ~0,016°), thêm bốn pose hướng gần thẳng vào vị trí hai decal tại `output/preview_poses_20260926_021158_082239/`. Xác nhận thêm CLI bằng `mainenv` tại `output/preview_poses_20260926_021322_310693/`. Lượt này chỉ xác nhận công cụ preview và ảnh camera, chưa nghiệm thu PatchCore; map không bị sửa.
- `2026-09-26`: Duyệt 27 vùng thay đổi trên A hiện tại bằng ảnh ghép sạch/A và overlay nhãn; lưu `damage_labels.json` đầy đủ theo năm ID, trong đó chỉ ba ID có frame nhìn thấy và hai ID trên trụ cao vẫn không quan sát đủ. `load_labels()` đã kiểm tra cấu trúc đầy đủ; chưa dùng nhãn này để hiệu chỉnh chính thức do thiếu calibration sạch và hai decal chưa thấy.
- `2026-09-26`: Smoke thật client/service PatchCore riêng tiến trình trên 33 frame đã chụp (ống/trụ), tất cả trả `ready`, bốn cảnh báo tại đúng tick/box của tính offline, median 83,8 ms/frame; ngưỡng chỉ là chẩn đoán. Screenshot editor người dùng cho thấy ba gizmo decal bên trụ nhưng không chứng minh vết trong cảm biến; truy vấn read-only xác nhận hai decal trên vẫn chồng x/y, z lệch 10 cm và scale nhỏ hơn decal trụ thấp. Không chỉnh map.
- `2026-09-26`: Sửa preview để hiệu chỉnh offset PoseSensor ~0,123 m sau teleport; live headless một pose tick 4000 đạt sai lệch vị trí 0,0 m/yaw ~0,016° ở `output/preview_poses_20260926_022701_702185/`. Lượt capture mới ghi thêm roll/pitch/yaw từ ma trận sensor; capture cũ chưa có roll/pitch nên so sánh pixel vẫn nhiễu do hướng/ánh sáng khác. Unit capture/preview 5/5 và py_compile đạt. Map giữ nguyên.
- `2026-09-26`: Ràng buộc mặc định PatchCore với hash file ngưỡng, sáu artifact model và dataset ROI tham chiếu của chính tập B đã đánh giá; sửa `evaluate.py` ghi các hash này và dashboard dùng cổng chung. Test cổng mới cùng bốn test PatchCore cũ 5/5, dashboard 7/7, `default_detector()` hiện vẫn Classical, py_compile đạt. *(Đã lỗi thời: sau nghiệm thu B, `default_detector()` trả PatchCore.)* Hash model thật mất khoảng 0,07 giây, ROI tham chiếu khoảng 0,05 giây. Chưa tạo báo cáo B vì dữ liệu test chưa có.
- `2026-09-25`: Bổ sung `--capture-clean-structures` để thu cả bốn tầng vòng quanh mỗi trụ; phân nhóm `pipe_front`, `pipe_back`, `pier_0`, `pier_1` trong ảnh/metadata/report và giữ `--capture-clean-pipe` cho trường hợp chỉ cần ống. Cập nhật test và README, không chỉnh map/route/detector.
- `2026-09-25`: Thêm `--capture-clean-pipe`/`--capture-every-ticks` vào runtime auto để lưu frame camera gốc trên hai mặt ống vào folder riêng và bỏ qua cảnh báo; thêm metadata JSONL, báo cáo số ảnh theo mặt, README và unit test file ảnh. Giữ nguyên route, detector, scenario và map thủ công; live capture chờ người dùng chuẩn bị map sạch.
- `2026-09-23`: Bỏ ô “Ảnh gốc” trùng với camera robot khỏi hàng xử lý Tkinter, mở camera robot từ 218×184 lên 282×230 và ánh xạ `frames[1:4]` thành CLAHE/mask/kết quả. Vẫn lưu đủ bốn PNG bằng chứng. Hiệu chỉnh smoke pause từ 2 lên 3 tick theo một gói queue 12 FPS; unit 5/5 và live smoke 9/9 qua, ảnh/audit xác nhận source bảo vệ không đổi.
- `2026-09-25`: Rà soát lại source và đồng bộ inventory, luồng chạy, API, output, lệnh và trạng thái xác minh. Loại các mô tả/lệnh/bằng chứng của `auv_web_dashboard/` và `open_original_world.py` vì hai thành phần không còn trong workspace; xác định `auv_dashboard/` là dashboard duy nhất. Không sửa runtime, detector, cấu hình, route hoặc map thủ công.
- `2026-09-23`: Tạo dashboard Tkinter riêng trong `auv_dashboard/` với Unreal viewport theo AUV, camera cảm biến trực tiếp, route X/Y, bốn bước xử lý, pause/continue/stop, lưu bằng chứng và source audit. Tái sử dụng runtime bằng adapter trong worker; giữ nguyên run_inspection.py/detector/scenario/route/map. Live smoke test đạt 9/9, xem ảnh xác nhận hướng spectator và pipeline; bổ sung README/launcher và test adapter.
- `2026-09-23`: Sửa `detect_cracks()` tính nền Gaussian trước khi cắt ROI và yêu cầu lõi tương phản mạnh liên thông; loại 11 cảnh báo nhầm mặt sau của lượt người dùng, giữ 3 hư hại mặt trước. Thêm 14 fixture camera, test replay/lật ngang và `check_detection_runtime.py`; live hoàn tất cả hai phía với 3 cảnh báo trước/0 sau. Đồng bộ tài liệu với tham số đèn `2500/1000` có sẵn trong source, không chỉnh đèn.
- `2026-09-23`: Sửa `is_pipe_view()` dùng toàn bộ span `PIPE_X_MIN..PIPE_X_MAX` có margin 0,5 m thay cho `x=-13..13`; đổi cảnh báo GUI/log từ crack sang damage, thêm 3 test cổng vị trí và xác minh live camera bắt đúng lỗ ở `pipe_front_scan_004`, tick 148.
- `2026-09-23`: Thêm `_detect_large_central_hole()` để bắt vùng rỗng tối lớn nhưng yêu cầu bề mặt xung quanh còn sáng; nâng regression lên 7 test, xác minh đúng ảnh lỗ người dùng/ảnh sạch và chạy live 600 tick không phát sinh báo nhầm mới.
- `2026-09-23`: Đổi detector sang đáp ứng tối cục bộ sau Gaussian, thêm hai nhánh lọc vết nứt/hư hại lớn và loại dải vòng nối/biên ống; thêm 5 regression test, kiểm tra 10 ảnh lưu và xác minh live tại tick 497; đồng bộ cấu hình đèn hiện hành `1000/100°`.
- `2026-09-23`: Gỡ toàn bộ dashboard web, HTTP server, publisher runtime và artifact live/QA theo yêu cầu; giữ nguyên detector, luồng auto/manual và bằng chứng lượt chạy.
- `2026-09-23`: Thêm `crack_detection.py` theo pipeline bài tổng quan Mohan & Poobal (2018), tích hợp cảnh báo/giữ AUV/lưu ảnh-thời gian vào auto/manual, thêm trường report và kiểm tra live hai chế độ; cập nhật lệnh, giới hạn và cấu hình đèn hiện hành.
- `2026-09-23`: Chỉnh môi trường nước Dam trên chính map thủ công; thêm hai asset material riêng với fog theo khoảng cách và hấp thụ RGB, cân bằng ánh sáng, lưu level; bổ sung audit phạm vi và ảnh camera runtime, giữ nguyên source/config/drone/sensor/vật thể.
- `2026-09-23`: Khôi phục weighted blendable `MM_Fog_Water_Dam` cho `OriginalUnderwaterPostProcess`; ghi backup và bằng chứng transform actor không đổi.
- `2026-09-23`: Thêm plugin editor-only `FunplayMCP 0.2.0` tương thích UE 5.3 và mô tả ranh giới cấu hình/token MCP.
- `2026-09-23`: Tạo tài liệu bàn giao từ source hiện tại; thêm inventory file/hàm, call flow, config, thay đổi flashlight C++, lệnh vận hành và quy tắc tự duy trì.
- `2026-09-26`: Xóa `control_demo.py`, demo cũ sử dụng world mẫu `Dam-HoveringCamera`; không thay đổi dashboard, pipeline AUV Inspection hoặc map thủ công.