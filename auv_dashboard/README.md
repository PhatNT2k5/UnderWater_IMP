# AUV Observatory — dashboard realtime

Dashboard **Tkinter**, chạy Unreal/HoloOcean thật và dùng trực tiếp `InspectionCamera` của robot. Toàn bộ source và kết quả dashboard nằm trong folder này. `auv_inspection/run_inspection.py`, detector, scenario, tuyến và map được giữ nguyên.

## Chạy

Nhấp đúp **`start_dashboard.cmd`**, rồi nhấn **Bắt đầu khảo sát**. Launcher dùng Python `mainenv` hiện có.

Hoặc chạy từ root `UnderwaterDemo`:

```powershell
& "$env:USERPROFILE\.conda\envs\mainenv\python.exe" .\auv_dashboard\run_dashboard.py

# Mở giao diện và bắt đầu ngay
& "$env:USERPROFILE\.conda\envs\mainenv\python.exe" .\auv_dashboard\run_dashboard.py --autostart
```

Dashboard tự mở một phiên Unreal riêng. Không cần chạy thêm `run_inspection.py`. Lần khởi động đầu có thể mất khoảng 10–30 giây.

## Các phần trên giao diện

- **Góc nhìn thứ ba:** cửa sổ Unreal thật được nhúng vào UI, camera quan sát đi theo AUV. Bỏ chọn **Theo AUV** để giữ vị trí camera quan sát. Camera này tách biệt với cảm biến robot.
- **Camera robot:** ảnh cảm biến `InspectionCamera` trực tiếp, không lấy ảnh từ góc nhìn thứ ba.
- **Lộ trình khảo sát 3D:** dùng đủ X/Y/Z của tuyến và `PoseSensor` để vẽ tuyến dự kiến, vệt đã đi, hướng AUV, ống, hai trụ và vị trí hư hại được đánh số. Kéo chuột để xoay, cuộn để zoom, nhấp đúp hoặc nút `↻` để đặt lại góc nhìn. Đây là sơ đồ từ tọa độ đã biết, không phải map 3D tái dựng từ sensor.
- **Ba bước xử lý:** Classical hiển thị ảnh xám/CLAHE → mask vùng nghi vấn → kết quả khoanh vùng; PatchCore hiển thị ROI bề mặt → heatmap bất thường → kết quả đánh dấu. Ảnh gốc không lặp lại ở đây vì đã có trong ô **Camera robot** lớn phía trên. Classical phân tích quét ống; PatchCore phân tích cả ống và hai trụ khi đã có ngưỡng.
- **Phát hiện hư hại:** danh sách cảnh báo cùng tọa độ X; nhấp đúp để mở ảnh bằng chứng đầy đủ.

Khi có cảnh báo, AUV giữ vị trí theo đúng logic gốc. **Ba ô xử lý giữ ảnh tại tick phát hiện**, có nhãn ghi rõ thời điểm; ô camera robot vẫn chạy trực tiếp. Classical lưu `camera.png`, `preprocessed.png`, `mask.png`, `annotated.png`; PatchCore lưu `camera.png`, `roi.png`, `heatmap.png`, `mask.png`, `annotated.png`, `scores.npz` và metadata model/ngưỡng/tick/pose. Nhấn **Tiếp tục sau cảnh báo** hoặc **Space** để quét tiếp và đưa ba ô về ảnh hiện tại.

## Điều khiển

| Điều khiển | Tác dụng |
|---|---|
| Tự động / Thủ công | Chọn trước khi bắt đầu |
| Classical / PatchCore | Chọn detector trước khi bắt đầu; PatchCore hiện chỉ hỗ trợ tuyến tự động và cần ngưỡng đã hiệu chỉnh |
| Tạm dừng / Chạy tiếp | Tạm ngừng bước mô phỏng / chạy tiếp |
| Tiếp tục sau cảnh báo / Space | Rời trạng thái giữ vị trí sau phát hiện |
| Dừng / Esc | Kết thúc phiên và lưu report |
| Mở kết quả | Mở folder kết quả của phiên hiện tại |
| Kéo / cuộn trên lộ trình | Xoay / thu phóng sơ đồ 3D |
| Nhấp đúp lộ trình / `↻` | Đặt lại góc nhìn 3D |
| W/S, A/D | Tiến/lùi, ngang trái/phải trong chế độ thủ công |
| R/F, Q/E | Lên/xuống, xoay trái/phải trong chế độ thủ công |

Các phím điều khiển được nhận khi phần giao diện Tkinter có focus. Nhấp vào tiêu đề hoặc vùng trống của dashboard nếu vừa nhấp vào cảnh Unreal. Khi dashboard mất focus, các phím đang giữ được nhả để tránh robot tiếp tục di chuyển ngoài ý muốn.

## Kiến trúc và dữ liệu

`app.py` chạy UI ở luồng chính. `bridge.py` mở một worker bằng `multiprocessing.spawn`, import `run_inspection.py`, gọi lại `run()` với adapter **chỉ trong bộ nhớ của worker**. Adapter chuyển preview/phím qua queue và chuyển đầu ra vào folder phiên. Không ghi đè hoặc sao chép lại logic detector/controller.

`patchcore_client.py` mở `auv_inspection.patchcore_data.live_service` bằng Python riêng của `.venv-patchcore`, trao đổi PNG/tick/nhóm/station/pose qua JSON-lines và báo lỗi/timeout rõ. UI đã có lựa chọn **Classical / PatchCore**. PatchCore chỉ chạy trên tuyến tự động, cần `auv_inspection/output/patchcore_thresholds_v1.json`, dùng `patchcore_model_v1` và ảnh sạch tham chiếu; khi thiếu ngưỡng, UI báo rõ và không khởi động phiên. PatchCore là mặc định hiện tại sau khi B offline đạt. UI chỉ tự chọn PatchCore khi báo cáo B đạt đủ điều kiện và SHA256 ngưỡng/model/ROI tham chiếu còn khớp bản đã đánh giá; thay một artifact phải đánh giá lại. Client/service đã xử lý thử 33 frame đã chụp với kết quả khớp offline, **chưa chạy PatchCore live cùng Unreal**.

Queue preview có tối đa hai gói; nếu UI chậm thì bỏ ảnh preview cũ. Cảnh báo và trạng thái dùng queue riêng để không mất sự kiện. Camera UI tối đa 12 fps; mô phỏng được giới hạn theo thời gian thực ở 30 tick/s hiện hành. Tốc độ thực tế phụ thuộc Unreal/GPU; đây là dữ liệu đang chạy, không phải phát lại log.

```text
auv_dashboard/
├── run_dashboard.py          # CLI / khởi tạo Tkinter
├── start_dashboard.cmd       # Launcher nhấp đúp dùng mainenv
├── app.py                    # UI, điều khiển, tiến độ, vòng đọc queue
├── bridge.py                 # Worker tái sử dụng runtime, truyền ảnh/telemetry
├── patchcore_client.py       # Client subprocess PatchCore riêng môi trường
├── viewport.py               # Nhúng đúng cửa sổ Unreal thuộc phiên này
├── widgets.py                # Camera tile và sơ đồ tuyến XYZ 3D tương tác
├── test_dashboard.py         # Kiểm tra codec, queue và chuyển trục camera
└── output/session_*/
    ├── scenario.json         # Bản sao nguyên trạng cấu hình khi bắt đầu
    ├── worker.log
    ├── source_audit.json     # SHA-256 năm file bảo vệ trước/sau
    ├── ui_session.json       # Tóm tắt UI, trạng thái dừng/lỗi
    └── output/run_*/
        ├── telemetry.json
        ├── report.json
        ├── unreal.log
        └── damage_events/event_*/
            ├── camera.png
            ├── preprocessed.png       # Classical; PatchCore dùng roi.png
            ├── heatmap.png            # PatchCore
            ├── mask.png
            ├── annotated.png
            ├── scores.npz             # PatchCore, ma trận điểm gốc
            └── event.json
```

## Dependency và giới hạn

- Windows, Python có Tkinter, `numpy`, `opencv-python`, `Pillow`, `pywin32`, HoloOcean client và Unreal 5.3 của project. Tất cả đã có trong môi trường `mainenv`; task này không cài dependency mới.
- Phần nhúng cửa sổ dùng Win32 nên không chạy nguyên trạng trên Linux/macOS. UI khuyến nghị màn hình từ 1440×900; kích thước tối thiểu 1080×700.
- Camera quan sát bù phép đổi trục của `TeleportCameraCommand` trong checkout HoloOcean hiện tại. Cần kiểm tra lại khi nâng framework.
- Bản đồ nhỏ lấy tuyến hiện hành; nếu chỉnh geometry trong Unreal thì cần cập nhật tuyến riêng. Dashboard không tự dò vật cản.
- Classical là heuristic hiện có. PatchCore cho điểm bất thường từ model học máy đã đạt kiểm tra offline trên năm vết B (5/5, sạch test 0 báo nhầm), chưa test live cùng Unreal; không tự kết luận mức độ hư hỏng hay coi điểm là xác suất.
- Đóng UI sẽ gửi lệnh dừng và đợi worker lưu kết quả. Nếu worker không đáp ứng sau 12 giây, chỉ tiến trình của phiên này bị kết thúc; tình huống đó được ghi `forced_shutdown`, có thể không có report đầy đủ.

## Kiểm thử

```powershell
# Không mở Unreal
& "$env:USERPROFILE\.conda\envs\mainenv\python.exe" -m unittest auv_dashboard.test_dashboard -v

# Mở dashboard và Unreal thật, tự kiểm tra pause / phát hiện / continue / stop
& "$env:USERPROFILE\.conda\envs\mainenv\python.exe" .\auv_dashboard\run_dashboard.py --smoke-test
```

Smoke test cố định dùng Classical để giữ hợp đồng kiểm thử cũ ngay cả khi PatchCore trở thành mặc định. Nó lưu ảnh UI và `qa_checks.json`; trả lỗi nếu nhúng cửa sổ, truyền ảnh, tạm dừng, tiếp tục sau cảnh báo, cập nhật tuyến, dừng hoặc kiểm tra bảo toàn source thất bại. Ảnh QA chụp vùng dashboard đang hiển thị để lấy được child DirectX; tránh che cửa sổ trong lúc kiểm thử. PatchCore cần lượt live riêng sau khi có ngưỡng.

Phiên live `output/session_20260923_220549_429030/` đạt 9/9 kiểm tra: camera robot được mở rộng 282×230, ba ô lần lượt hiển thị CLAHE/mask/kết quả, Unreal nhúng trực tiếp, route và marker cảnh báo cập nhật, pause/continue/stop hoạt động, worker thoát mã 0 và source audit không đổi. `dashboard_alert.png` đã được xem trực tiếp. Năm unit test đều đạt. Lượt ngắn này chưa xác nhận toàn bộ 359 waypoint; chế độ thủ công chưa được thao tác đầy đủ bằng tay.

## Bàn giao PatchCore 26/09/2026

Xem `../auv_inspection/PATCHCORE_HANDOFF.md` để biết kết quả và các bước người dùng test dashboard. Worker replay 277 frame B khớp toàn bộ bảy sự kiện offline. Phần kiểm thử UI/live dành cho người dùng; không coi kết quả offline là xác nhận FPS hoặc pause/continue thực tế.
