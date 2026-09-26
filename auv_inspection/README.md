# AUV Inspection simulation

Map thử nghiệm cho đề xuất giám sát công trình ngầm bằng AUV, trên HoloOcean / Unreal Engine 5.3.2.

## Nội dung

- Map: `/Game/AUVInspection/Maps/AUVInspection`.
- Map đã được sửa thủ công: đáy biển 70 x 60 m, tuyến ống hiện dài khoảng 33 m, hai trụ cầu và dầm nối.
- Tái sử dụng material cát, bê tông, nước và mô hình HoveringAUV có trong project.
- `scene.json` và `scene_manifest.json` mô tả bản dựng cũ; không phản ánh đầy đủ những thay đổi thủ công trong map hiện tại.
- AUV có vật lý HoloOcean, bộ điều khiển vị trí/hướng `control_scheme=1`, camera, pose, velocity, depth và IMU; tự động bám hai bên đường ống rồi đi quanh từng trụ cầu.
- Có hai chế độ: tự động khảo sát công trình hoặc người dùng tự điều khiển.
- Xem camera trực tiếp, phân tích vùng ống trong từng frame và lưu ảnh/thời gian khi có cảnh báo nghi vấn vết nứt.

## Chạy demo

Từ thư mục `UnderwaterDemo`, dùng môi trường Python đã có HoloOcean, NumPy, OpenCV và pywin32:

```powershell
& "$env:USERPROFILE\.conda\envs\mainenv\python.exe" .\auv_inspection\run_inspection.py
```

Chương trình tự tìm UE 5.3 qua manifest Epic Launcher, mở map dạng `-game` và khởi tạo AUV. Khi phát hiện nghi vấn nứt hoặc thủng, AUV giữ vị trí, cửa sổ camera hiện cảnh báo `POSSIBLE DAMAGE` và tự lưu ảnh; nhấn `Space` để tiếp tục khảo sát hoặc `ESC` để thoát. Chạy offscreen:

```powershell
& "$env:USERPROFILE\.conda\envs\mainenv\python.exe" .\auv_inspection\run_inspection.py --headless --steps 60000
```

Chế độ mặc định `auto` dùng tuyến trong `inspection_route.py`: đi dọc hai bên toàn bộ ống ở `z=-10.3 m`, cách tim ống `2 m`, camera quay vào ống. AUV vòng ngoài đầu ống để đổi bên, sau đó khảo sát trụ trái rồi trụ phải bằng bốn vòng quanh mỗi trụ ở `z=-9.2, -6.8, -4.4, -2 m`, bán kính `2.8 m`; camera quay về tâm trụ. Target được giữ trước AUV khoảng `1.2 m` để chuyển động liên tục qua các waypoint; chỉ điểm cuối mới giữ sai số vị trí dưới `0.25 m` và yaw dưới `8°` trong 15 tick.

## Thu ảnh công trình sạch cho phát hiện bất thường

Sau khi **tự chuẩn bị và lưu map sạch** (không có lỗ/vết nứt), chạy từ root project:

```powershell
& "$env:USERPROFILE\.conda\envs\mainenv\python.exe" .\auv_inspection\run_inspection.py --capture-clean-structures --headless --steps 60000
```

Bỏ `--headless` nếu muốn xem camera khi AUV chạy. Chế độ này chỉ dùng route `auto`, bỏ qua detector và không dừng vì cảnh báo. Cứ mỗi 10 tick đủ điều kiện (đổi bằng `--capture-every-ticks 5`), chương trình lưu **frame BGR gốc từ `InspectionCamera`**, không có chữ hoặc bounding box. Ảnh được lấy ở đoạn quét hai mặt ống và các vòng quay quanh cả hai trụ (`pier_0`, `pier_1`, bốn tầng mỗi trụ). Bỏ qua các đoạn di chuyển giữa công trình; 30 tick đầu chờ camera/đèn ổn định. Lệnh không chỉnh sửa hay lưu map. Nếu chỉ muốn thu ống, dùng `--capture-clean-pipe` thay cho `--capture-clean-structures`.

Mỗi lần chạy tạo thư mục riêng `auv_inspection/output/clean_structures_<timestamp>/`: `images/pipe_front/`, `images/pipe_back/`, `images/pier_0/`, `images/pier_1/`, `frames.jsonl` (một dòng JSON cho mỗi ảnh: tick, station, loại công trình, nhóm ảnh, pose, kích thước, thời gian), `telemetry.json`, `report.json` và `unreal.log`. `report.json` ghi tổng số ảnh từng nhóm và `route_completed`. Tùy chọn cũ `--capture-clean-pipe` vẫn tạo `clean_pipe_<timestamp>/` và chỉ có hai nhóm ống. Nếu thoát sớm hoặc gặp lỗi, ảnh và `frames.jsonl` đã ghi vẫn còn; kiểm tra report trước khi dùng làm dataset. Code **không thể xác nhận map thật sự sạch**: cần xem mẫu ảnh của cả bốn nhóm và loại ảnh còn hư hại trước khi huấn luyện PatchCore. Nên tách dữ liệu ống và trụ khi xây bộ nhớ bề mặt bình thường.

Đây là tuyến cố định theo tọa độ map đã lưu và kiểm kê ngày 22/09/2026, không phải tự phát hiện công trình hay tự tránh chướng ngại. Nếu di chuyển ống/trụ trong editor, cần cập nhật tuyến. Kiểm tra hình học không thay thế chạy thử vật lý/camera. Code điều hướng không rebuild hay lưu map. Để tự điều khiển:

```powershell
& "$env:USERPROFILE\.conda\envs\mainenv\python.exe" .\auv_inspection\run_inspection.py --mode manual
```

Phím điều khiển manual: `W/S` tiến/lùi theo hướng AUV, `A/D` đi ngang, `R/F` lên/xuống, `Q/E` xoay yaw và `ESC` để thoát. Có thể đổi tốc độ bằng `--move-speed` (m/s) và `--yaw-speed` (độ/s).

Ở chế độ manual, cảnh báo cũng tạm giữ AUV và lưu bằng chứng; nhấn `Space` để lấy lại quyền điều khiển. Chế độ `--headless` chỉ hỗ trợ auto: sau cảnh báo đầu tiên, chương trình lưu bằng chứng rồi kết thúc lượt chạy với `stopped_for_damage: true` vì không có cửa sổ để nhận phím tiếp tục.

Hai đèn trước của AUV tự bật ở cả chế độ auto/manual, chiếu thẳng theo camera. Tham số người dùng đã chỉnh trong `enable_inspection_lights()` của `run_inspection.py` hiện là `intensity=2500`, `beam_width=1000`; lần sửa detector mặt sau giữ nguyên cấu hình này. Module HoloOcean đã sửa và biên dịch để tạo Blueprint điều khiển đèn tạm thời nếu map chỉ có manager C++; không lưu actor đó vào map. Khi mang source sang máy khác cần build lại module để có bản sửa này.

Có thể chỉ định `--editor 'G:\UnrealEngine\UE_5.3\Engine\Binaries\Win64\UnrealEditor.exe'` nếu cần.

Đây là map chạy trực tiếp qua bản Unreal đã cài; **chưa đóng gói thành bộ world/exe standalone**. Không chạy map mới bằng package `Ocean` đã đóng gói sẵn vì package đó không chứa map này.

## Thu ảnh và chuẩn bị PatchCore

Để thu ảnh khi map có hư hại, dùng chế độ trung lập về nhãn:

```powershell
& "$env:USERPROFILE\.conda\envs\mainenv\python.exe" .\auv_inspection\run_inspection.py --capture-structures --dataset-role calibration --scene-state mixed --headless --steps 60000
```

Đổi `calibration` thành `test` cho lượt giữ riêng; trên map sạch đổi `mixed` thành `clean`. Mỗi lượt tạo `output/capture_<role>_<state>_<timestamp>/`, lưu ảnh gốc/`frames.jsonl` và SHA256 của `.umap` trong report. `mixed` chỉ cho biết phiên có hư hại, không gán nhãn từng ảnh. Map không bị lưu/chỉnh bởi lệnh thu ảnh. Cần giữ riêng lượt sạch hiệu chỉnh, bố trí A hiệu chỉnh, lượt sạch đánh giá và bố trí B đánh giá.

Có thể thêm `--world /Game/AUVInspection/Maps/AUVInspection_PatchCoreClean_20260926_v3` vào lệnh capture để thu trên bản map sạch riêng; mặc định vẫn là map A gốc. Report ghi world và hash của map thực sự được chạy. Bản B nháp là `AUVInspection_PatchCoreB_20260926_v3`, chưa được nghiệm thu. `create_validation_maps.py` chạy trong Unreal Python để tạo các bản sao này theo quyền người dùng, không ghi đè đích đã có; không chạy lại nếu chỉ cần thu ảnh.

Khi thu ảnh headless trong lúc dùng ứng dụng khác, thêm `--ignore-global-escape` để Esc trên desktop không dừng capture. Ctrl+C trong terminal vẫn dừng được. Cờ chỉ hợp lệ với capture headless; điều khiển dashboard không đổi.

Để xem nhanh một vị trí đã biết sau khi chỉnh decal, không cần chạy toàn route. Ví dụ hai decal trụ 0 gần tầng quét 2:

```powershell
& "$env:USERPROFILE\.conda\envs\mainenv\python.exe" .\auv_inspection\run_inspection.py --preview-source .\auv_inspection\output\capture_calibration_mixed_20260926_015105_231742 --preview-ticks 3990,4000,4010,4020 --headless
```

Lệnh mở map **đã lưu**, đưa AUV đến bốn pose camera trong `frames.jsonl`, rồi lưu `preview_<tick>.png` và `compare_<tick>.png` (trái: ảnh nguồn, phải: map hiện tại) trong `output/preview_poses_<timestamp>/`. `report.json` ghi station, sai lệch pose và hash map. Preview hiệu chỉnh vị trí agent theo PoseSensor; capture mới còn ghi roll/pitch/yaw để tái tạo đầy đủ hướng camera. Capture cũ chỉ có yaw nên ảnh hai bên có thể khác texture/ánh sáng ngay cả khi map không đổi: dùng để xem vết bằng mắt, không lấy chênh lệch pixel làm nhãn tự động. Đây là công cụ kiểm tra vị trí/độ rõ, không thay thế bốn lượt hiệu chỉnh và đánh giá. Sau khi đã huấn luyện/hiệu chỉnh xong, thêm vết hư hại mới không cần thêm vào tập train hoặc chụp lại route mỗi lần; nếu thay bề mặt công trình, camera, ánh sáng hoặc route thì cần kiểm tra/cập nhật ảnh sạch tham chiếu cho phần bị ảnh hưởng.

Môi trường `.venv-patchcore` dùng Python 3.11, Anomalib 2.6.2, PyTorch 2.14.0+cu130, torchvision 0.29.0+cu130 và OpenCV có GUI; các phiên bản chính được ghi trong `patchcore_data/requirements-patchcore.txt`. Môi trường này tách khỏi `mainenv` của HoloOcean/dashboard. Xác nhận GPU:

```powershell
& .\.venv-patchcore\Scripts\python.exe -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

Ảnh sạch đã đăng ký tại `output/patchcore_dataset_clean_20260925/`: 552 frame, bốn nhóm và 60 ảnh đại diện; xem `review.html`. Các lệnh công cụ dữ liệu:

```powershell
& .\.venv-patchcore\Scripts\python.exe -m auv_inspection.patchcore_data.prepare <capture_folder> <new_dataset_folder>
& .\.venv-patchcore\Scripts\python.exe -m auv_inspection.patchcore_data.roi_seed .\auv_inspection\output\patchcore_dataset_clean_20260925
& .\.venv-patchcore\Scripts\python.exe -m auv_inspection.patchcore_data.roi_editor .\auv_inspection\output\patchcore_dataset_clean_20260925
& .\.venv-patchcore\Scripts\python.exe -m auv_inspection.patchcore_data.roi_propagate .\auv_inspection\output\patchcore_dataset_clean_20260925
& .\.venv-patchcore\Scripts\python.exe -m auv_inspection.patchcore_data.roi_audit .\auv_inspection\output\patchcore_dataset_clean_20260925
& .\.venv-patchcore\Scripts\python.exe -m auv_inspection.patchcore_data.roi_review .\auv_inspection\output\patchcore_dataset_clean_20260925
& .\.venv-patchcore\Scripts\python.exe -m auv_inspection.patchcore_data.train .\auv_inspection\output\patchcore_dataset_clean_20260925 .\auv_inspection\output\patchcore_model_v1
```

ROI editor: nhấp trái thêm điểm, nhấp phải xóa điểm cuối, `S` lưu polygon, `N` bỏ qua, `R` xóa điểm, `Q` thoát. `roi_seed` tạo gợi ý và ảnh ghép để xem, không tự phê duyệt. `roi_propagate` dùng căn chỉnh đặc trưng và dự phòng hình học khi cần; `roi_audit` tạo ảnh ghép toàn route. ROI review dùng `A` duyệt, `X` loại frame không đủ bề mặt, `N` để sau, `Q` thoát. Huấn luyện từ chối ảnh chưa duyệt và ảnh calibration/test; frame bị loại không đi vào bộ nhớ. PatchCore dùng bốn bộ nhớ riêng, ô 256×256 bước 128 và không thu nhỏ nguyên frame. Bộ nhớ baseline `output/patchcore_model_v1/` đã fit trên 552 ảnh sạch; chưa có ngưỡng hiệu chỉnh, nên score không phải xác suất hư hại. Dashboard đã có lựa chọn PatchCore nhưng không khởi động nhánh đó khi thiếu file ngưỡng.

Với lượt capture mới, dùng `roi_propagate <new_dataset_folder> --reference-dataset .\auv_inspection\output\patchcore_dataset_clean_20260925`, rồi duyệt mask và chạy `python -m auv_inspection.patchcore_data.score_dataset <new_dataset_folder> .\auv_inspection\output\patchcore_model_v1 <new_score_folder>`. Lệnh `predict <dataset_folder> <model_folder> <image_relative_path> <new_output_folder>` lưu từng frame kèm heatmap để kiểm tra thủ công.

`live_roi` đối chiếu frame với ảnh sạch cùng nhóm/station và pose, dùng mask đã duyệt hoặc căn chỉnh ORB khi pose lệch nhẹ; trả trạng thái thiếu tham chiếu/căn chỉnh lỗi thay vì coi frame là bình thường. Audit offline: `python -m auv_inspection.patchcore_data.live_roi <clean_reference_dataset> <target_dataset> <report.json>`. Trên lượt A hiện tại, 552/552 frame có ROI, IoU median 1,0 và thấp nhất 0,888 so với mask A đã duyệt; cả hai route cùng pose nên chưa chứng minh nhánh căn chỉnh khi route đổi. Dashboard đã gọi bộ chọn này qua service khi chọn PatchCore và có ngưỡng; chưa thử live với Unreal.

`live_service` trong môi trường PatchCore và `auv_dashboard/patchcore_client.py` đã trao đổi frame/ROI/heatmap qua JSON-lines trong kiểm tra offline; một frame A cho score đúng bằng file offline cùng tick. Dashboard đã nối nhánh PatchCore cho quét auto ống/trụ, mỗi ba tick, nhưng client yêu cầu `output/patchcore_thresholds_v1.json`; chưa có ngưỡng/test B và chưa thử live cùng Unreal.

Sau khi có capture `mixed`, tạo dataset mới bằng `prepare`, truyền mask bằng `roi_propagate --reference-dataset <clean_dataset>`, xem `roi_audit` và duyệt mask. Dùng `python -m auv_inspection.patchcore_data.label_damage <dataset_folder> <defect_id> --category pipe_front --size-class thin` cho từng vết vật lý, đổi category phù hợp. Trong cửa sổ nhãn: `B` vẽ box bằng kéo chuột, `L` chọn đường tâm bằng các điểm nhấp, `C` sao chép nhãn frame trước để sửa/duyệt, `A` chấp nhận nhãn đề xuất đã có hình hợp lệ, `S` ghi vết nhìn thấy, `U` không đủ rõ, `N` không thấy, `P` quay lại và `Q` lưu/thoát. ID giữ nguyên xuyên suốt route. `compare_clean` và `label_from_difference` có thể đề xuất vùng thay đổi khi hai route căn khớp, nhưng phải xác nhận đúng từng vết vật lý; không dùng cho inference. Tập test cần chạy `python -m auv_inspection.patchcore_data.lock_labels <dataset_folder>` trước khi đánh giá.

CLI `calibrate` chọn kết hợp bốn ngưỡng từ **lượt calibration sạch độc lập** và lượt A có đủ nhãn đã duyệt cho từng ID/frame, từ chối bất kỳ vết vật lý nào chưa hiện trong ảnh A, giới hạn tổng hai báo nhầm cho cả route và ưu tiên vết nhỏ/mảnh; lưu ở `output/patchcore_thresholds_v1.json` để dashboard đọc. `evaluate` chỉ đọc lượt test sạch/B, xác minh hash nhãn đã khóa và ngưỡng đã chốt, đồng thời replay Classical trên ảnh ống; lưu ở `output/patchcore_evaluation_B_v1.json` để bật PatchCore mặc định khi `acceptance.passed=true`. Cả hai CLI yêu cầu score cùng model, nằm trong `auv_inspection.patchcore_data` và có `--help`. Chưa chạy hiệu chỉnh/nghiệm thu do chưa có đủ lượt sạch/B; dashboard vẫn mặc định Classical.

Lượt A ngày 26/09 (`output/patchcore_dataset_calibration_A_20260926/`) có 5 decal trong map theo truy vấn Unreal chỉ đọc. Hai vết trên mặt trước ống và một trên trụ 0 xuất hiện rõ trong ảnh camera; hai decal nhỏ hơn gần UE `(-1100, 650, -530/-520)` trên trụ 0 chưa hiện thành đường nứt liên tục trong frame camera tầng quét tương ứng. Xem `damage_inventory_A.json`, `output/patchcore_changes_A_20260926/` và score offline ở `output/patchcore_scores_calibration_A_20260926/`. Nhãn `damage_labels.json` đã duyệt bằng overlay so sánh ảnh sạch/A: 8 frame nhìn thấy cho mỗi ID ống, 9 frame cho ID trụ thấp; hai ID trụ cao không có frame nhìn thấy, giữ `unclear` trong khoảng quét liên quan. File `damage_label_proposals.json` vẫn là gợi ý ban đầu, không dùng để hiệu chỉnh. Cần người dùng chỉnh map để hai vết cuối có tín hiệu nhìn thấy rồi thu A mới; code không chỉnh/sửa map.

Chẩn đoán tracker trên chính 552 ảnh train sạch và A cũ: điều kiện tâm đứng yên 35 px bỏ cả hai vết ống vì chúng chạy khoảng 90 px qua ảnh mỗi 10 tick. Tracker quỹ đạo mới xác nhận hai sự kiện ống tick 420/490 và vết trụ tick 2930/3390 ở hai vòng quét, không báo trên ảnh train sạch tại các ngưỡng thử (`output/patchcore_diagnostic_A_20260926.json`). **Đây không phải hiệu chỉnh/nghiệm thu**: ảnh train sạch không độc lập và hai vết trụ cao còn chưa nhìn thấy.

## Xem và chỉnh map

Mở `holoocean/engine/Holodeck.uproject`, tìm `Content/AUVInspection/Maps/AUVInspection` trong Content Browser. Actor `AUV_EditorPreview_RuntimeSpawnedByPython` chỉ giúp bố trí trong editor; AUV vật lý thật được Python sinh khi chạy demo.

Để dựng lại, đóng map trong editor trước, sửa `scene.json` rồi chạy:

```powershell
& "$env:USERPROFILE\.conda\envs\mainenv\python.exe" .\auv_inspection\rebuild.py
```

Script chỉ dựng lại map `AUVInspection`. Bản `.umap` trước đó được chép vào `output/backups/`. Chỉnh sửa thủ công trong map này sẽ bị thay thế khi rebuild; map mẫu `ExampleLevel`/`TestWorld` được giữ nguyên. Không đổi cấu hình mặc định hay mã C++ của HoloOcean.

## Kết quả và giới hạn

Tuyến bám công trình đã chạy offscreen hoàn tất 359/359 waypoint trên map sửa thủ công; xem `ROUTE_VALIDATION.md` cho bằng chứng và giới hạn. `VALIDATION.md` ghi nhận bản cũ ngày 19/09.

Mỗi `output/run_.../` chứa `telemetry.json`, `report.json` và `unreal.log`. Khi có cảnh báo, thư mục `damage_events/event_001/` chứa `camera.png` (ảnh gốc), `preprocessed.png`, `mask.png`, `annotated.png` và `event.json` (thời gian theo múi giờ máy, tick, tọa độ, vùng nghi vấn). `report.json` chứa `damage_event_count`, `damage_events` và `stopped_for_damage`. Camera được phân tích từng tick khi nhìn ống; telemetry lấy mỗi 3 tick (10 Hz). Ở chế độ auto, chỉ khi `route_completed: true` mới coi là đi hết tuyến. Chạy giới hạn ít bước hoặc dừng vì vết nứt sẽ không hoàn thành tuyến. Ảnh trong các lượt chạy cũ không bị xóa.

`scene_manifest.json` chứa nhãn thực tế do scene định nghĩa: loại lỗi, mức độ đặt trước, vị trí và stencil ID. Tọa độ client tính bằng mét: `[UE.x / 100, -UE.y / 100, UE.z / 100]`. Các ID stencil được chuẩn bị cho pipeline nhãn sau này; hiện chưa xuất segmentation mask hay bounding box ground truth.

`crack_detection.py` hiện thực chuỗi xử lý theo bài tổng quan Mohan & Poobal (2018): camera → CLAHE → hai nhánh phát hiện → lọc hình học → xác nhận qua 3 frame liên tiếp. Nhánh vết nứt dùng Gaussian giảm texture rồi đo vùng tối so với nền cục bộ. Nhánh lỗ thủng tìm vùng tối lớn nối qua tâm ảnh nhưng chỉ chấp nhận khi vùng xung quanh vẫn đủ sáng, vì vậy ảnh thiếu sáng toàn cục không bị gọi là lỗ. Bộ lọc cũng loại các đốm phản sáng, dải vòng nối đứng và biên ống ngang. Detector bắt đầu sau 30 tick để camera/đèn ổn định. Bộ lọc được hiệu chỉnh theo ống trong map hiện tại và chạy trên toàn chiều dài đã đo của ống (`x=-18.51..15.61 m`, `|y|<=3.5 m`, `z=-12..-8.5 m`); auto chỉ xét các đoạn `pipe_front_scan`/`pipe_back_scan`. Đây là heuristic phát hiện **nghi vấn**, có thể báo nhầm hoặc bỏ sót; bounding box đánh dấu vùng tín hiệu, không phân loại mức độ hư hỏng và chưa có đánh giá accuracy trên tập nhãn độc lập.

Chưa triển khai toàn bộ capstone: dataset ảnh sạch/nhiễu đồng bộ, huấn luyện enhancement/segmentation, đánh giá model, dòng chảy thay đổi, dashboard và cảnh báo bảo trì. Geometry hỏng hóc hiện là bản mẫu phục vụ khảo sát/camera, chưa phải asset hư hỏng photorealistic hoặc mô phỏng cơ học phá hủy.

Để giảm báo nhầm ở mặt sau, detector tính nền ánh sáng trên toàn frame trước khi cắt vùng quan sát. Một vùng nghi vấn phải có lõi tối đậm nối liền; các đốm texture hoặc bóng nhạt sát vòng nối không đủ để cảnh báo. Quy tắc này áp dụng chung cho cả hai phía ống. Các vết rất mảnh hoặc tương phản yếu vẫn có thể bị bỏ sót.

Kiểm tra hồi quy từ root project (14 ảnh camera thật được giữ trong `tests/data/pipe_views/`):

```powershell
& "$env:USERPROFILE\.conda\envs\mainenv\python.exe" -m unittest auv_inspection.tests.test_crack_detection auv_inspection.tests.test_camera_regression -v
```

QA live cả hai phía ống, tự tiếp tục sau mỗi cảnh báo và lưu frame cảm biến:

```powershell
& "$env:USERPROFILE\.conda\envs\mainenv\python.exe" .\auv_inspection\check_detection_runtime.py
```

Harness QA dùng controller/sensor/detector hiện tại, chạy offscreen và kết thúc sau mặt sau ống. File `output/detector_qa_*/summary.json` ghi tổng frame/cảnh báo và liên kết report; không dùng lượt QA này để xác nhận đã khảo sát các trụ cầu.
