# PatchCore — bàn giao ngày 26/09/2026

## Kết quả đã xác minh

| Phần | Kết quả |
|---|---|
| Train | 552 ảnh sạch, bốn memory bank, ảnh gốc 640×480 chia ô 256×256 |
| Calibration sạch | 552 ảnh từ lượt riêng, đủ route |
| Calibration A | 552 ảnh, ba vết còn lại do người dùng xác nhận |
| Test sạch | 552 ảnh từ lượt riêng, không dùng chọn ngưỡng |
| Test B | 552 ảnh, năm vết ở vị trí/hướng/kích thước mới; nhãn khóa trước chấm điểm |
| PatchCore trên B | 5/5 vết, 4/4 nhóm nhỏ/mảnh, 0 báo nhầm trên route sạch test |
| Classical trên cùng ảnh ống | 1/4 vết; 0 báo nhầm sạch; không hỗ trợ trụ |
| Unit test | PatchCore 7/7; dashboard 7/7, không mở UI |
| Dashboard + Unreal trực tiếp | Người dùng tự test; chưa xác nhận trong đợt bàn giao này |

Ngưỡng front/back/pier0/pier1: **61.55155 / 53.06446 / 58.91152 / 54.33251**.
Calibration phát hiện 3/3 vết A và 0 báo nhầm sạch. Không dùng B để thay đổi các ngưỡng này.
Kết quả B có 7 sự kiện cho 5 vết vật lý: một vùng lớn có hai box và vết trụ được thấy ở hai tầng quét. Không tính các sự kiện lặp thành vết độc lập.
Độ trễ trên ảnh lấy mỗi 10 tick: 20–40 tick từ frame đầu nhìn rõ đến cảnh báo. Median suy luận offline B khoảng 61 ms/ảnh; chưa phải tốc độ khi dashboard và Unreal cùng chạy.

## Giới hạn của kết quả

- Chỉ có năm vết test, cùng vật liệu mô phỏng và route auto hiện tại. Đây là kết quả trên bộ test này, không phải bảo đảm 100% với mọi vết mới.
- Các lượt sạch được thu riêng nhưng gần như tất định: khác nhau tối đa vài pixel. Chưa đánh giá thay đổi mạnh về ánh sáng, camera, texture hoặc hình học.
- B có hư hại ở mặt trước ống và trụ 1; mặt sau ống và trụ 0 chỉ có kiểm tra sạch trong B. Chưa đo recall hư hại riêng cho mọi nhóm.
- Box chỉ vùng bất thường, không phải biên chính xác toàn bộ vết hoặc phân loại mức độ hỏng.
- Phạm vi triển khai là auto; chưa xác nhận PatchCore ở điều khiển manual.

## Bạn test dashboard

1. Từ thư mục project, chạy `auv_dashboard/start_dashboard.cmd`.
2. Chọn **Auto** và **PatchCore**. Khi hash model/ngưỡng/tham chiếu và báo cáo đạt khớp nhau, PatchCore được chọn mặc định.
3. Nhấn **Bắt đầu khảo sát**. Dashboard vẫn mở map A gốc có ba vết của bạn.
4. Khi có cảnh báo, kiểm tra camera, ROI, heatmap và box; nhấn **Tiếp tục sau cảnh báo** để đi tiếp.
5. Thử Pause/Continue và Stop; kiểm tra phiên có report và ảnh bằng chứng.
6. Gửi folder `auv_dashboard/output/session_...` nếu bỏ sót, báo nhầm, worker lỗi hoặc thao tác không hoạt động đúng.

Không dùng `--smoke-test` để nghiệm thu PatchCore: chế độ đó cố định Classical.
Không phải chụp lại train mỗi lần thêm decal mới. Nếu thay camera, route hoặc bề mặt thì cần kiểm tra/cập nhật dữ liệu tham chiếu phần bị ảnh hưởng.

## Artifact chính

- Model: `output/patchcore_model_v1/`
- ROI train: `output/patchcore_dataset_clean_20260925/`
- Ngưỡng: `output/patchcore_thresholds_v1.json`
- Báo cáo test: `output/patchcore_evaluation_B_v1.json`
- Ảnh box kết quả: `output/patchcore_B_events_review.jpg`
- Dataset A mới: `output/patchcore_dataset_A3_20260926/`
- Dataset sạch calibration/test: `output/patchcore_dataset_calibration_clean_20260926/`, `output/patchcore_dataset_test_clean_20260926/`
- Dataset B và nhãn khóa: `output/patchcore_dataset_B_20260926/`
- Bản map riêng hợp lệ: `AUVInspection_PatchCoreClean_20260926_v3`, `AUVInspection_PatchCoreB_20260926_v3`.
- Map A gốc giữ SHA256 `daba22ece60400aa19e5e2676a0005af51d19d105f5e03f6bce611948dc361d2`; backup ở `output/backups/patchcore_before_variants_20260926/`.

Các capture bị ngắt và bản map thử trước v3 được giữ làm lịch sử, không tham gia nghiệm thu.
