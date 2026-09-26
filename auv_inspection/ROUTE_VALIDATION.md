# Kiểm tra tuyến bám công trình — 2026-09-22

## Bổ sung: chuyển động liên tục và camera 30 Hz

- Bỏ thời gian chờ 15 tick tại mỗi waypoint trung gian. Target tự động được giữ trước AUV khoảng 1.2 m; chỉ điểm cuối cần giữ đúng vị trí/hướng trong 15 tick.
- Camera `InspectionCamera` tăng từ 10 Hz lên 30 Hz; cửa sổ preview cập nhật mỗi tick. Telemetry vẫn ghi 10 Hz và không lưu ảnh.
- Lượt thử: `output/run_20260922_224853_923255/`, chạy 3000 tick, exit code 0, 1000 mẫu telemetry.
- Tốc độ trung bình 0.893 m/s, trung vị 0.915 m/s, cực đại 1.215 m/s. Chỉ 1/999 khoảng lấy mẫu dưới 0.05 m/s (0.1%), xác nhận không còn dừng ở từng waypoint.
- Lượt thử có giới hạn 3000 tick nên `route_completed=false` là dự kiến; AUV đã đi hết hai bên ống và bắt đầu vòng quanh trụ thứ nhất.
- Folder lượt thử chỉ có `report.json`, `telemetry.json`, `unreal.log`; không tạo ảnh.

## Bổ sung: đèn AUV

- `run_inspection.py` tự bật `flashlight1` và `flashlight2` với cường độ 25000 mỗi đèn, beam 70°, pitch/yaw 0°.
- Sửa `TurnOnFlashlightCommand.cpp` để khởi tạo `/Game/FlashlightManager.FlashlightManager_C` dưới dạng actor transient khi thiếu. Blueprint AUV yêu cầu class này; manager C++ thuần trong map không đủ. Đã build `HolodeckEditor Win64 Development` thành công.
- Kiểm tra đối chứng bằng `check_flashlight_runtime.py`: giữ cùng vị trí backscan `[10, -2, -10.3]`, yaw 90°, tắt đèn 180 tick rồi bật 180 tick. Run `output/run_20260922_223829_096630/`, exit code 0, 24 ảnh.
- Ảnh tắt: `frame_00150.png`; ảnh bật: `frame_00330.png`. Đã xem ảnh: ánh đèn làm rõ vùng giữa thân ống; vùng ngoài chùm sáng vẫn tối. Log không còn lỗi `Accessed None`/mảng manager rỗng.
- Bài kiểm tra đèn cố ý dừng sau 360 tick, không chạy hết tuyến nên `route_completed=false` là dự kiến. Bằng chứng chạy đủ tuyến bên dưới được ghi trước thay đổi đèn.
- SHA-256 map sau kiểm tra đèn vẫn trùng hash bên dưới.

## Tuyến đầy đủ (trước bổ sung đèn)

- Tuyến: `inspection_route.py`, được gọi từ `run_inspection.py`.
- Chạy thực tế: `run_inspection.py --headless --steps 60000`, exit code 0.
- Kết quả: [report.json](output/run_20260922_222053_514387/report.json), `route_completed=true`, 359/359 waypoint, `stopped_by_user=false`.
- 1.191 ảnh 640 × 480; đã kiểm tra mọi file được tham chiếu trong telemetry đều tồn tại. Tick ảnh cuối: 17.850 (khoảng 595 giây mô phỏng ở 30 Hz).
- Đã chạy hết hai mặt bên đường ống, vòng ngoài đầu ống, rồi bốn vòng quanh mỗi trụ ở các độ sâu -9.2, -6.8, -4.4 và -2 m.
- Đã xem ảnh thực tế ở mặt trước/mặt sau ống và cả hai trụ: hướng camera quan sát đúng công trình. Mặt sau ống tối do ánh sáng map; không thay đổi ánh sáng, material hay actor.
- Bốn kiểm tra hình học đạt: bước tuyến ngắn/tên duy nhất; đoạn nối không cắt bounds ống/trụ/móng đã mở rộng 0.65 m; hướng camera quay vào công trình; hai đầu ống và các vòng trụ đầy đủ.
- SHA-256 map trước/sau: `858727A7A9A096671F10A42240EE5C2D58CA4DA59A9FAE0C1CB24A2DFE657D6B`. Không rebuild hoặc lưu map.

## Giới hạn

- Đây là tuyến cố định dựa trên tọa độ bản map đã kiểm kê; di chuyển công trình cần sửa tuyến. Không có tránh vật cản bằng cảm biến.
- Tiêu chí đến waypoint: sai số vị trí <0.25 m và yaw <8° trong 15 tick. Khi đang chuyển waypoint, sai số có thể lớn hơn các ngưỡng này.
- Không khẳng định đã chụp toàn bộ diện tích bề mặt hoặc phát hiện mọi hư hại; chưa đánh giá độ phủ ảnh/độ chính xác detector.
- Log có D3D12 `Handled ensure: SwapChain4.GetReference()` lúc khởi động offscreen; tiến trình vẫn hoàn thành tuyến và thoát thành công.
- `VALIDATION.md` ngày 19/09 là kết quả bản map/tuyến cũ, không dùng để xác nhận tuyến hiện tại.
