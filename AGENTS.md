# AGENTS.md — UnderwaterDemo

## Bắt đầu task

- Đọc `SOURCE_HANDOFF.md` trước khi phân tích hoặc sửa source của project.
- Phân biệt source project (`auv_inspection/`, các script root, asset/map riêng) với framework upstream trong `holoocean/`.
- Map `holoocean/engine/Content/AUVInspection/Maps/AUVInspection.umap` có chỉnh sửa thủ công. Không chạy `auv_inspection/rebuild.py`, không ghi đè hoặc lưu map nếu người dùng chưa yêu cầu rõ ràng.

## Đồng bộ tài liệu bắt buộc

Khi sửa code, config, asset hành vi, cấu trúc file, CLI, output schema, map/route hoặc Unreal C++, phải cập nhật `SOURCE_HANDOFF.md` trong cùng task:

- Cập nhật mô tả file và từng hàm/class bị ảnh hưởng.
- Cập nhật luồng chạy, lệnh sử dụng, dependency và giới hạn nếu thay đổi.
- Đổi ngày “Cập nhật gần nhất” và thêm một dòng vào “Nhật ký cập nhật tài liệu”.
- Không ghi kết quả compile/unit test thành live Unreal validation.
- Nếu không cần sửa `SOURCE_HANDOFF.md`, khi bàn giao phải nêu ngắn gọn lý do tài liệu vẫn đúng.

## An toàn dữ liệu

- Không xóa `auv_inspection/output/backups/` hoặc các run đang được tài liệu validation tham chiếu nếu chưa được phép.
- `scene.json`/`scene_manifest.json` thuộc bản generator cũ và không phản ánh đầy đủ map thủ công hiện tại.
- Giữ nguyên thay đổi người dùng và file unrelated trong nested Git checkout `holoocean/`.
