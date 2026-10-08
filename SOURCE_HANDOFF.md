# Source handoff — UnderwaterDemo

> Tài liệu bàn giao dành cho AI/agent và thành viên mới. Hãy đọc file này trước khi sửa source.
>
> Cập nhật gần nhất: **2026-10-08** - P0 đã chạy live (3/3 vết map A, 1 báo nhầm); P1 phần 1: thư viện suy giảm ảnh `auv_inspection/robustness/`; không chỉnh map thủ công.

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
- `build_route() -> list[Waypoint]`
  - Dùng helper cục bộ `append(...)` để nội suy đoạn dài thành bước tối đa khoảng `0.8 m` và nội suy yaw theo đường ngắn nhất.
  - Đi mặt trước ống, vòng ngoài đầu ống, quay lại mặt sau, rồi thực hiện bốn vòng đủ quanh mỗi trụ.
  - Camera luôn được hướng vào bề mặt cần quan sát.
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
- `enable_inspection_lights(env) -> None`
  - Bật `flashlight1` và `flashlight2`; tham số hiện có trong source là intensity `2500`, beam_width `1000`, pitch/yaw `0`. Task sửa detector mặt sau giữ nguyên các giá trị người dùng đã chỉnh này.
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
- `main() -> None`
  - Parse `--editor`, `--steps`, `--headless`, `--mode`, `--move-speed`, `--yaw-speed`, ba chế độ capture và `--preview-source` loại trừ nhau, `--preview-ticks`, `--dataset-role`, `--scene-state`, `--capture-every-ticks`.
  - Validate số dương, cấm `manual + headless` và yêu cầu `auto` khi thu ảnh sạch; sau đó cấu hình logging và gọi `run()`.

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
- `live_service.py`: `create_session()` kiểm tra ngưỡng cùng model, nạp backbone chung và bốn bank trong môi trường PatchCore; `analyze_request()` nhận PNG/tick/nhóm/station/pose, tìm ROI, chấm điểm, xác nhận cảnh báo ba frame và trả ROI/heatmap/mask/annotation cùng trạng thái lỗi rõ; frame `analysis_unavailable` **không reset tracker** (từ P0), track cũ chỉ bị bỏ theo `max_gap_ticks`; ma trận score nén chỉ gửi khi có alert hoặc yêu cầu chẩn đoán; `serve()` xử lý JSON-lines stdin/stdout; `main()` cung cấp CLI. Dashboard đã có nhánh chọn đã có ngưỡng hiệu chỉnh, chưa test UI live.
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
- `approval_gate.py`: `file_sha256()` hash file; `fingerprint()` hash danh sách file theo tên tương đối và nội dung; `model_fingerprint()` buộc backbone/config/bốn bank; `reference_fingerprint()` buộc manifest/summary/trạng thái ROI/toàn bộ mask; `approval_matches()` chỉ cho dashboard mặc định PatchCore khi báo cáo B đạt đủ bốn điều kiện và khớp đường dẫn/hash ngưỡng, model, tham chiếu.
- `calibrate.py`: `load_scored()` kiểm tra role/state và manifest; `load_maps()` nạp score; `detect_events()` áp dụng tracker; `load_labels()` yêu cầu đủ nhãn đã duyệt, nhóm hợp lệ và hình của mọi vết visible trên tất cả frame liên quan, xác minh hash khi test đã khóa; `label_box()` và `detected_defects()` đối chiếu vị trí; `visible_ids()` xác định ID nhìn thấy; `threshold_candidates()` thử cả vùng dưới trung vị đỉnh ảnh sạch, lấy thêm điểm đỉnh trong vùng vết visible đã duyệt và giữ lưới tối đa 64 mức để xét vết yếu; `calibrate()` từ chối ID vật lý chưa thấy trong bất kỳ frame A, xác minh hai score cùng model rồi chọn kết hợp bốn ngưỡng bằng quy hoạch động với **tổng** tối đa hai báo nhầm trên toàn route sạch, ưu tiên vết nhỏ/mảnh; `main()` cung cấp CLI. Đã chạy trên A3 ba ID và lượt sạch calibration độc lập; 3/3 ID và 0 báo nhầm sạch, ngưỡng lưu ở patchcore_thresholds_v1.json.
- `lock_labels.py`: `lock()` dùng kiểm tra nhãn đầy đủ của `load_labels()`, khóa nhãn test và ghi SHA256; `main()` cung cấp CLI.
- `evaluate.py`: `classical_events()` replay detector Classical trên hai mặt ống; `evaluate()` xác minh hai score test và ngưỡng cùng model, dùng ngưỡng đã chốt trên tập test sạch/B có nhãn khóa, báo recall theo vết nhìn thấy, vết không đủ quan sát, báo nhầm, độ trễ và so sánh Classical; `acceptance.passed` cũng yêu cầu mọi ID trong inventory nhìn thấy được. Report ghi SHA256 ngưỡng và fingerprint model/tham chiếu cho cổng mặc định dashboard; `main()` cung cấp CLI. Đã chạy trên B khóa nhãn: 5/5 ID, 4/4 nhỏ/mảnh, 0 báo nhầm sạch; xem PATCHCORE_HANDOFF.md về giới hạn.
- `tests/test_approval_gate.py`: Tạo artifact thử và xác nhận cổng mặc định từ chối khi ngưỡng, bank model, ROI mask hoặc điều kiện nghiệm thu bị đổi sau đánh giá.
- `tests/test_label_integrity.py`: Kiểm tra nhãn visible thiếu hình bị từ chối và nhãn test thay đổi sau khóa bị phát hiện.
- `tests/test_live_roi.py`: Dataset mask giả trong thư mục tạm; kiểm tra `pose_match`, giao hai mask khi ở giữa hai tham chiếu, `nearest_mask` khi chỉ có một tham chiếu, `reference_unavailable` khi lệch quá 0,5 m và `roi_too_small` khi hai mask không giao. Không cần ảnh camera.
- `tests/test_live_service_unavailable.py`: `analyze_request()` với frame không có ROI không đổi trạng thái tracker; tracker vẫn xác nhận vết khi frame tốt xen kẽ frame bị bỏ (mẫu phiên live 2026-09-27) và vẫn bỏ track sau khoảng trống quá `max_gap_ticks`.
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

`robustness/tests/test_degradation.py`: 9 test trên ảnh tổng hợp có vết nứt: tái lập theo seed, giữ kích thước/kiểu, từ chối yêu cầu sai, độ tương phản giảm đơn điệu theo độ đục và giảm theo khoảng cách, độ nét giảm theo mất nét/mờ chuyển động, độ sáng giảm theo đèn yếu, sai khác tăng theo nhiễu/hạt/JPEG, CLI ghi tham số và không ghi đè.

### `auv_inspection/test_inspection_route.py`

`InspectionRouteTests` chỉ kiểm tra hình học, không mở Unreal:

- `test_station_advances_without_waiting_at_each_point()`
  - Xác nhận lookahead bỏ qua waypoint gần nhưng không bỏ qua điểm cuối.
- `test_short_steps_and_unique_names()`
  - Xác nhận tên waypoint duy nhất và khoảng cách giữa hai điểm liên tiếp không quá `0.80001 m`.
- `test_segments_clear_structure_bounds()`
  - Lấy mẫu các đoạn tuyến và xác nhận không cắt AABB của ống/trụ/móng đã cộng biên an toàn `0.65 m`.
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

- `main()`: đọc `--autostart`, `--steps` (mặc định 60000, số dương), `--smoke-test`; thiết lập DPI, tạo Tk/`Dashboard`, chạy mainloop. Smoke test kiểm tra kết quả sau khi đóng và trả lỗi nếu không đạt.
- Entry point gọi `multiprocessing.freeze_support()` để tương thích spawn trên Windows.
- `start_dashboard.cmd`: chọn Python theo thứ tự `DASHBOARD_PYTHON`, `%USERPROFILE%\.conda\envs\mainenv\python.exe`, rồi `%CONDA_PREFIX%\python.exe` khi env conda đang activate là `mainenv`; báo lỗi hướng dẫn nếu không thấy, truyền tiếp tham số, giữ console khi có lỗi. `__init__.py` đánh dấu package, không có side effect.

### `auv_dashboard/bridge.py`

| Hàm / class | Trách nhiệm |
|---|---|
| `source_hashes()` | SHA-256 runtime, detector, scenario, route và map trước/sau phiên |
| `patchcore_category()` | Chọn một trong bốn nhóm ống/trụ từ station quét tự động; bỏ qua đoạn chuyển tiếp |
| `prepare_session_scenario()` | Copy `scenario.json` vào phiên dashboard, không ghi file cấu hình gốc |
| `publish_latest()` | Queue preview giới hạn, không block khi UI chậm; chỉ bỏ ảnh cũ |
| `encode_frame()` | JPEG với quality truyền vào (mặc định 87) cho ảnh màu/xám; PNG lossless cho mask |
| `viewport_pose()` | Vị trí spectator sau/trên AUV; bù phép `ConvertAngularVector` của TeleportCameraCommand hiện tại bằng đảo vector nhìn; không thay pose AUV |
| `run_worker()` | Tạo log/copy scenario, mở PatchCoreClient riêng môi trường nếu được chọn và có ngưỡng, gắn adapter theo process, gọi `run`, ghi detector vào report, gửi report/lỗi, ghi source audit và đóng feeder preview |
| `DashboardEnvironment.step()` (class cục bộ) | Gọi nguyên `step`, đọc camera/pose/yaw/speed/tick và xóa trạng thái phân tích cũ; nhánh viewport capture còn trong bridge nhưng UI Tkinter hiện hành không kích hoạt |
| `read_commands()` | Nhận stop, pause, continue, follow và danh sách phím đang giữ |
| `launch_engine()` | Gọi Popen gốc, gửi PID và output cho UI |
| `advance()`, `gate()`, `analyze()` | Classical gọi hàm gốc; PatchCore mở gate cho bốn nhóm, gửi một frame mỗi ba tick thật của vòng `run()` đến service và lưu kết quả có tick phân tích cho preview |
| `PatchCoreTracker.update()/reset()` | Adapter dùng sự kiện ba frame đã xác nhận từ service; không xác nhận lại trong runtime |
| `draw()` | Classical gọi hàm gốc; PatchCore trả annotation đúng frame của service |
| `damage_pause_remaining()` | Tính số giây còn lại trong khoảng giữ AUV sau cảnh báo, mặc định 5 giây |
| `save_event()` | Classical gọi lưu event gốc; PatchCore lưu camera/ROI/heatmap/mask/annotation/score và model/ngưỡng/tick/pose, sau đó giữ đúng ba ô bằng chứng, bắt đầu mốc 5 giây và gửi sự kiện tin cậy |
| `is_key_pressed()` | Thay đọc phím toàn hệ thống bằng trạng thái lệnh riêng của dashboard; ở auto PatchCore, lần kiểm tra Escape đầu mỗi vòng ghi tick của `run()` nên không lệch khi `reset()` bước camera trước vòng |
| `preview()` | Gửi viewport Unreal JPEG quality 78 và ảnh robot theo `preview_fps`; chỉ mã hóa pipeline theo `pipeline_fps` hoặc khi có bằng chứng mới; gửi pose/waypoint/candidate count, detector, trạng thái và tick phân tích qua queue |
| `resume_damage_pause()`, `wait_key()` | Xử lý pause/stop; khi hết 5 giây, trả Space cho runtime để tiếp tục tự động; nút/Space của UI vẫn có thể bỏ qua chờ; gửi trạng thái resume và giới hạn nhịp 30 Hz |

`PROTECTED_FILES` gồm năm file được audit. Không đưa dữ liệu dashboard vào `auv_inspection/output/`. Dashboard sao chép nguyên scenario và nhận đủ bốn stage trong mọi preview; tham số flashlight vẫn do runtime gốc thực hiện.

### `auv_dashboard/patchcore_client.py`

`PatchCoreClient.__init__()` mở Python riêng từ `.venv-patchcore`, ghi stderr vào `patchcore_worker.log`, đọc stdout JSON-lines bằng thread và chờ thông điệp ready có timeout; bắt buộc file ngưỡng đã hiệu chỉnh. `_read_responses()` và `_receive()` chuyển lỗi/timeout/worker exit thành lỗi rõ; `analyze()` gửi PNG cùng tick/nhóm/station/pose, xác minh tick/nhóm trả về; `close()` dừng và thu hồi subprocess; `decode_image()` giải mã ảnh stage. Client đã được smoke offline với một frame A và đóng sạch. Bridge/app gọi nhánh này khi người dùng chọn PatchCore và có ngưỡng, nhưng chưa chạy thử cùng Unreal.

### `auv_dashboard/viewport.py`

`UnrealViewport.__init__()` giữ Tk host và handle; `attach()` tìm đúng cửa sổ Unreal theo PID, lưu style rồi SetParent vào host; `_area()` chọn cửa sổ có client area lớn nhất; `resize()` theo kích thước host; `detach()` khôi phục style/parent nếu cửa sổ còn sống. Không tìm hoặc điều khiển editor/cửa sổ của phiên khác.

### `auv_dashboard/widgets.py`

- `CameraTile.__init__()` tạo canvas placeholder; `set_frame()` đọc bytes ảnh vào Pillow; `render()` fit giữ tỷ lệ, giữ tham chiếu PhotoImage; `clear()` trả về placeholder.
- `project_3d()` là phép chiếu thuần từ XYZ qua yaw/pitch/scale sang tọa độ Canvas; test không cần mở Tk/Unreal.
- `RouteMap.__init__()` giữ đầy đủ XYZ của 359 waypoint, trail, marker hư hại và trạng thái orbit/zoom. `begin_orbit()`, `orbit()`, `wheel_zoom()`, `reset_view()` xử lý kéo/cuộn/đặt lại; `clear_run()` xóa dữ liệu phiên nhưng giữ góc nhìn; `add_alert()` đánh số tọa độ hư hại; `update_position()` thêm trail 3D và hướng AUV.
- `projection()`, `project()`, `line()`, `render()` tự fit theo kích thước Canvas rồi vẽ lưới đáy, ống, trụ theo chiều cao, tuyến kế hoạch, trail thực, marker và AUV. Đây là sơ đồ dựa geometry/tọa độ route đã biết, không phải cảm biến dựng bản đồ.

### `auv_dashboard/app.py`

`default_detector()` gọi `approval_gate.approval_matches()`; chỉ chọn PatchCore mặc định khi báo cáo B đạt đủ điều kiện và hash của ngưỡng, backbone/bốn bank/config, dataset ROI tham chiếu vẫn khớp bản đã đánh giá; hiện trả PatchCore sau khi B offline đạt. Chế độ `--smoke-test` luôn chọn Classical để giữ hợp đồng QA cũ. Đường dẫn model/dataset/ngưỡng/đánh giá là các hằng số ở đầu file.

| Thành viên `Dashboard` | Trách nhiệm |
|---|---|
| `__init__()`, `_configure()`, `_build()` | Khởi tạo trạng thái, Tk/ttk theme, bố cục theo sketch, bind phím/focus và vòng poll |
| `label()`, `button()` | Tạo widget cùng typography/màu |
| `send()`, `start()` | Gửi lệnh, kiểm tra PatchCore chỉ chạy auto và có ngưỡng, đổi nhãn ba stage, tạo session/queues và spawn worker với detector/chế độ/follow đã chọn |
| `toggle_pause()`, `continue_run()`, `set_follow()`, `stop()` | Điều khiển phiên qua queue; stop lưu thời điểm cho timeout cleanup |
| `key_down()`, `key_up()`, `release_keys()` | W/S/A/D/R/F/Q/E, Space, Esc; nhả phím khi Tk mất focus |
| `open_output()`, `open_alert()` | Mở folder phiên hoặc annotated.png của event chọn |
| `handle_event()` | Nhận PID, cảnh báo, resume tự động/thủ công, trạng thái, traceback, report; cập nhật nút/danh sách và thêm marker XYZ vào route khi có hư hại |
| `render_packet()` | Đưa `frames[1:4]` vào ba ô tương ứng Classical hoặc PatchCore vì ảnh gốc đã có ở camera robot; cập nhật route/trail XYZ, telemetry, tiến độ, FPS/latency, countdown tự tiếp tục, tick phân tích và trạng thái ROI/cảnh báo |
| `poll()` | Drain event/latest frame, nhúng Unreal, quản lý worker và cleanup chỉ tiến trình sở hữu sau timeout 12 giây |
| `save_ui_session()`, `close()`, `finish_close()` | Ghi ui_session.json khi worker kết thúc hoặc đóng UI, dừng/detach và đóng queues/Tk; giữ tóm tắt phiên trước nếu chạy lại |
| `snapshot()`, `qa_tick()`, `validate_smoke_test()` | Chụp vùng UI có DirectX, tự pause/continue/stop và xác minh chín điều kiện QA live; pause cho phép tối đa 3 tick đã nằm trong queue preview 12 FPS |

### `auv_dashboard/test_dashboard.py`

`DashboardBridgeTests` có tám test: countdown giữ 5 giây rồi hết; phân nhóm đúng scan ống/trụ và bỏ transition; mock worker xác minh PatchCore dùng tick của vòng runtime ngay cả khi `reset()` bước camera; queue không tăng khi UI chậm và giữ frame mới nhất; PNG giữ mask chính xác; JPEG giữ kích thước/kênh ảnh robot; phép chiếu route phân biệt độ sâu/chiều cao; spectator nhìn về AUV sau phép đổi trục thực tế của upstream ở năm góc yaw và không sửa mảng vị trí đầu vào. Đây là test không mở Unreal, tách với live smoke test.

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

Từ root `UnderwaterDemo`:

```powershell
# Chạy tuyến tự động có camera preview
& "$env:USERPROFILE\.conda\envs\mainenv\python.exe" .\auv_inspection\run_inspection.py

# Dashboard Tkinter hiện hành; cũng có thể nhấp đúp auv_dashboard/start_dashboard.cmd
& "$env:USERPROFILE\.conda\envs\mainenv\python.exe" .\auv_dashboard\run_dashboard.py --autostart

# Test adapter không mở Unreal / kiểm thử dashboard với Unreal thật
& "$env:USERPROFILE\.conda\envs\mainenv\python.exe" -m unittest auv_dashboard.test_dashboard -v
& "$env:USERPROFILE\.conda\envs\mainenv\python.exe" .\auv_dashboard\run_dashboard.py --smoke-test

# Chạy headless với giới hạn tick
& "$env:USERPROFILE\.conda\envs\mainenv\python.exe" .\auv_inspection\run_inspection.py --headless --steps 60000

# Sau khi người dùng tự chuẩn bị map sạch: thu PNG camera gốc của ống và trụ
& "$env:USERPROFILE\.conda\envs\mainenv\python.exe" .\auv_inspection\run_inspection.py --capture-clean-structures --headless --steps 60000

# Điều khiển thủ công
& "$env:USERPROFILE\.conda\envs\mainenv\python.exe" .\auv_inspection\run_inspection.py --mode manual

# Khi hiện cảnh báo vết nứt trong cửa sổ camera: Space để tiếp tục, Esc để thoát

# Unit test hình học (không mở Unreal)
& "$env:USERPROFILE\.conda\envs\mainenv\python.exe" .\auv_inspection\test_inspection_route.py

# Regression ảnh tổng hợp + 14 frame InspectionCamera thật (chạy từ root)
& "$env:USERPROFILE\.conda\envs\mainenv\python.exe" -m unittest auv_inspection.tests.test_crack_detection auv_inspection.tests.test_camera_regression -v

# Tạo bản suy giảm có seed của một thư mục PNG (P1); không ghi đè thư mục đích
& "$env:USERPROFILE\.conda\envs\mainenv\python.exe" -m auv_inspection.robustness.degradation <thu_muc_png> <thu_muc_moi> --degradation turbidity:3 --degradation marine_snow:2 --seed 0
& "$env:USERPROFILE\.conda\envs\mainenv\python.exe" -m unittest auv_inspection.robustness.tests.test_degradation -v

# QA live cả hai mặt ống, tự tiếp tục cảnh báo, không mở cửa sổ
& "$env:USERPROFILE\.conda\envs\mainenv\python.exe" .\auv_inspection\check_detection_runtime.py
```

Không có lệnh rebuild map: `auv_inspection/rebuild.py` không có trong repo (xem mục 4).

## 8. Trạng thái đã xác minh và giới hạn

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