# Kiểm tra thực thi - 2026-09-19

## Bản nghiệm thu

- Unreal Engine 5.3.2; project `holoocean/engine/Holodeck.uproject`.
- `rebuild.py`: exit code 0, commandlet báo 0 errors / 14 warnings; 202 actor được lưu vào map.
- Map mới: `holoocean/engine/Content/AUVInspection/Maps/AUVInspection.umap`.
- Có 7 điểm lỗi trong `scene_manifest.json`, thuộc hai loại công trình.
- Lượt chạy cuối: `output/run_20260919_133429_853804/`.
- `run_inspection.py --headless --steps 6000`: exit code 0.
- `report.json`: `route_completed=true`, đủ 9/9 waypoint, 163 ảnh camera 640 x 480.
- Đã xem ảnh camera trực tiếp để sửa trục xoay ống, độ phơi sáng và vị trí vết lỗi tránh mặt bích.
- Đã kiểm tra baseline với ảnh xám không có lỗi, mảng màu gỉ và mảng màu xanh tổng hợp: ba kiểm tra đều đạt. Đây là kiểm tra logic, không đo độ chính xác nhận diện thực tế.
- Git status của checkout HoloOcean: chỉ thêm `engine/Content/AUVInspection/`; các thay đổi sẵn có trong Saved/Config và UpgradeLog vẫn còn. Không chỉnh source C++ hoặc map mẫu.

## Giới hạn và cảnh báo

- Asset lỗi còn đơn giản; gỉ và biofouling dùng các mảng geometry có màu, không phải texture hư hỏng thực tế.
- Baseline chỉ tìm màu gỉ/biofouling, có false positive ở nền và ánh sáng. Chưa có trained crack/deformation detector, chưa đo mAP.
- Mức độ và loại lỗi trong manifest là ground truth của scene, không phải kết quả AI suy luận.
- Chưa xuất dataset ảnh sạch/nhiễu, segmentation masks; chưa đóng gói standalone executable.
- Chế độ `-RenderOffScreen` trên máy này có Unreal D3D12 `Handled ensure: SwapChain4.GetReference()` khi khởi động. Đây là cảnh báo runtime đã quan sát: tiến trình vẫn chạy và hoàn thành toàn tuyến; không được hiểu là log hoàn toàn sạch.
- Bản build dùng API viewport đã deprecated trong UE 5.3 và có warning mặc định của HoloOcean. Build hoàn tất không lỗi.
- Các lượt `run_...` trước là thử nghiệm hình học/phơi sáng; dùng đúng lượt cuối ở trên làm bằng chứng cho bản hiện tại.
