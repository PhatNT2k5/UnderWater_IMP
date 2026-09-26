# Hướng dẫn PatchCore cho dự án AUV Inspection

Tài liệu này giải thích pipeline PatchCore đang chạy trong project. Mục tiêu là để thành viên nhóm hiểu dữ liệu nào được dùng, model học gì và vì sao một vùng có thể hiện đỏ trên heatmap nhưng chưa tạo cảnh báo.

## 1. PatchCore dùng để làm gì?

PatchCore là thuật toán phát hiện bất thường từ **ảnh bề mặt sạch**. Nó không học từng loại decal, tên asset, vết nứt hay lỗ thủng cụ thể.

Thay vào đó, nó tạo một bộ nhớ về đặc trưng của bề mặt bình thường. Khi ảnh mới có một vùng khác đủ nhiều với bộ nhớ này, vùng đó có điểm bất thường cao.

```text
frame camera
  -> ROI chỉ chứa bề mặt cần kiểm tra
  -> các tile 256 x 256 chồng lấp
  -> Wide ResNet50-2 trích đặc trưng
  -> so sánh với memory bank ảnh sạch
  -> heatmap điểm bất thường
  -> ngưỡng + vùng liên thông + theo dõi qua frame
  -> cảnh báo hư hại
```

## 2. Dữ liệu

Dataset sạch hiện được tổ chức theo bốn nhóm bề mặt:

```text
patchcore_dataset_clean_20260925/
├── images/
│   ├── pipe_front/
│   ├── pipe_back/
│   ├── pier_0/
│   └── pier_1/
├── manifest.jsonl
├── roi_masks/
└── roi_approved.json
```

Mỗi frame camera là ảnh BGR 640 x 480 và có một record trong `manifest.jsonl`. Record giữ đường dẫn ảnh, tick, thời gian, nhóm bề mặt, station route, pose AUV, yaw, kích thước ảnh, vai trò dữ liệu (`train`, `calibration` hoặc `test`) và trạng thái scene (`clean` hoặc `mixed`).

Mỗi ảnh có một ROI mask đã duyệt. ROI chỉ giữ phần thân ống hoặc mặt trụ. Nước, nền, sàn, biên ảnh và vùng ngoài công trình không được đưa vào tính điểm.

## 3. Ba tập dữ liệu có vai trò khác nhau

| Tập | Nội dung | Dùng để làm gì |
|---|---|---|
| Train | Chỉ ảnh sạch | Xây memory bank của bề mặt bình thường |
| Calibration | Ảnh sạch độc lập và map A có nhãn hư hại | Chọn ngưỡng cảnh báo |
| Test | Ảnh sạch độc lập và map B có bố trí hư hại khác | Đánh giá cuối cùng |

Ảnh có hư hại **không được đưa vào train**. Nếu đưa chúng vào, PatchCore có thể coi chính hư hại đó là bình thường.

## 4. Quá trình fit memory bank

Backbone hiện tại là `wide_resnet50_2`, dùng các layer `layer2` và `layer3`, với trọng số pretrained. Project không fine tune lại toàn bộ backbone.

Mỗi frame được chia thành tile 256 x 256, bước trượt 128 pixel. Cách làm này giữ chi tiết vết mảnh tốt hơn resize cả frame về một kích thước nhỏ.

Với từng tile, model trích vector đặc trưng. Chỉ các vị trí nằm chắc trong ROI mới được giữ. Các vector sạch được gom vào memory bank của đúng nhóm bề mặt. Sau đó K-Center Greedy chọn một coreset đa dạng để giảm dung lượng mà vẫn giữ các kiểu texture/ánh sáng sạch đại diện.

Artifact `output/patchcore_model_v1/` hiện có bốn bank:

| Nhóm | Số vector coreset |
|---|---:|
| `pipe_front` | 678 |
| `pipe_back` | 684 |
| `pier_0` | 800 |
| `pier_1` | 800 |

## 5. Xử lý một ảnh khi dashboard chạy

1. Dashboard gửi frame camera, category, station, vị trí và yaw sang PatchCore worker.
2. Worker tìm ROI từ ảnh sạch tham chiếu của cùng category và station. Nếu không tìm/align được ROI, nó trả `analysis_unavailable`, không tự coi frame là sạch.
3. Frame được chia tile và trích đặc trưng theo cùng cách với train.
4. Mỗi đặc trưng được so với vector gần nhất trong memory bank của category đó.
5. Khoảng cách đến vector sạch gần nhất trở thành anomaly score; các score được ghép lại thành heatmap ở độ phân giải ảnh gốc.
6. Pixel có score lớn hơn ngưỡng category tạo binary mask.
7. Các pixel mask liền nhau thành candidate. Candidate từ 2 pixel trở lên vẫn được giữ để không loại vết mảnh.
8. Một candidate chỉ thành alert nếu xuất hiện theo quỹ đạo hợp lý trong 3 frame đã phân tích, tối đa cách nhau 15 tick.

Ngưỡng hiện tại là khác nhau cho từng category vì texture và ánh sáng của ống/trụ khác nhau. Heatmap hiển thị được scale theo percentile 5 đến 99 của **frame hiện tại** để dễ nhìn. Vì vậy màu đỏ trên heatmap chỉ cho thấy vùng tương đối cao trong frame; nó không tự chứng minh vùng đó vượt ngưỡng alert.

## 6. Vì sao phát hiện được vết hư hại?

Vết nứt, lỗ, vùng bong hoặc hư hại khác thường thay đổi texture, cạnh, độ tối, hình dạng hoặc phản xạ. Nếu đặc trưng của vùng đó không giống đủ với bất kỳ đặc trưng sạch nào trong memory bank, khoảng cách tăng lên. Khi vùng vượt ngưỡng và tồn tại ổn định qua ba frame, dashboard phát cảnh báo.

Đánh giá offline trên bố trí B, khác bố trí dùng calibration, đã có 5/5 hư hại nhìn thấy được phát hiện; trong đó có 4/4 hư hại nhỏ hoặc mảnh, và 0 cảnh báo trên route sạch test. Đây là bằng chứng offline; không thay thế kiểm tra live trong Unreal/dashboard.

## 7. Có cần train lại khi thêm hư hại mới không?

Thông thường **không cần**. Vì PatchCore học bề mặt sạch, một hư hại mới vẫn có thể được phát hiện nếu nó tạo khác biệt đủ rõ trong ảnh camera.

Khả năng bỏ sót tăng khi:

- Vết quá nhỏ, quá mảnh hoặc tương phản quá thấp so với ảnh 640 x 480.
- Vết nằm ngoài ROI, ngoài góc camera hoặc route không đi qua vị trí đó.
- Vết bị chói đèn, bóng tối, phản xạ hoặc texture nền che mất.
- Hư hại có đặc trưng gần với texture sạch trong memory bank.
- Vết chỉ xuất hiện rõ dưới ba frame nên tracker chưa xác nhận.
- Vật liệu, camera, route, góc nhìn, exposure hoặc ánh sáng thay đổi đáng kể so với dữ liệu sạch.

Khi thêm hư hại mới, nên chạy route và kiểm tra ảnh raw, ROI, heatmap, mask và alert. Chỉ cần chụp lại dữ liệu sạch hoặc fit lại memory bank khi bề mặt bình thường hay điều kiện quan sát đã thay đổi đáng kể.

## 8. Giới hạn cần nhớ

- Score không phải xác suất hư hại.
- PatchCore phát hiện bất thường, không phân loại loại hư hại hoặc mức độ nghiêm trọng.
- Một vùng đỏ có thể chưa vượt ngưỡng hoặc chưa đủ ba frame xác nhận.
- Kết quả trên simulation gần như tất định chưa chứng minh khả năng tổng quát với ánh sáng, nhiễu hay camera thực tế khác.
