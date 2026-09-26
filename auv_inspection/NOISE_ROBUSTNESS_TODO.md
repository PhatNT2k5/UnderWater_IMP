# TODO — Độ bền PatchCore trước nhiễu môi trường

**Trạng thái:** Chưa triển khai. Pipeline PatchCore hiện học và suy luận trên ảnh RGB camera trong mô phỏng, với RGB ImageNet normalization và ROI đã duyệt. Các mục dưới đây là backlog, không phải khả năng đã được xác minh.

## Mục tiêu

Giảm báo nhầm và bỏ sót khi môi trường quan sát thay đổi, đồng thời không phải thêm từng loại hư hại vào tập train. Cần duy trì nguyên tắc: PatchCore học **bề mặt sạch**, không học danh sách decal hư hại.

## Các loại nhiễu cần xử lý

| Nhiễu / thay đổi | Rủi ro với PatchCore | Hướng xử lý đề xuất |
|---|---|---|
| Shot noise, thermal noise | Texture hạt lạ trên toàn frame, tăng score và báo nhầm | Denoising nhẹ; đo độ nhiễu; bỏ frame vượt ngưỡng chất lượng |
| Speckle-like haze | Che chi tiết mảnh và tạo texture giả | Denoising hoặc khử haze có kiểm soát; đánh giá giữ được vết mảnh |
| Nước đục, giảm tầm nhìn | Giảm tương phản, đổi màu và làm ROI không ổn định | Quality gate theo contrast/visibility; enhancement nhẹ hoặc yêu cầu chụp lại |
| Phù sa, bụi nước | Nhiều đốm chuyển động có thể thành candidate | Loại frame có mật độ particle cao; xác nhận theo thời gian và quỹ đạo |
| Bọt khí, che khuất tạm thời | Vùng anomaly lớn nhưng không phải hư hại | Occlusion detector; trả `analysis_unavailable`, chờ frame tiếp theo |
| Rung camera, motion blur | Mất cạnh vết nứt và có thể bỏ sót | Blur quality gate; không kết luận trên frame mờ; tăng số frame quan sát nếu cần |
| Dòng chảy làm AUV lệch | Sai station/pose, ROI tham chiếu không khớp | Pose-aware ROI alignment; báo unavailable nếu sai lệch vượt giới hạn |
| Thay đổi đèn/độ sâu | Dịch phân bố brightness và color | Chuẩn hóa color/illumination thống nhất giữa dữ liệu sạch và live |
| Imaging sonar | Ảnh sonar có texture và physics khác RGB camera | Pipeline/model/memory bank PatchCore riêng cho sonar; không dùng chung bank RGB |

## Thiết kế pipeline mục tiêu

```text
Camera RGB
  -> quality gate (blur, visibility, occlusion, noise)
  -> correction nhẹ và xác định được trạng thái
  -> ROI alignment theo pose/tham chiếu
  -> PatchCore
  -> ngưỡng theo category
  -> candidate + tracker nhiều frame
  -> alert hoặc analysis_unavailable
```

`analysis_unavailable` là kết quả an toàn khi ảnh không đủ chất lượng. Nó không được hiểu là bề mặt bình thường và không tạo alert hư hại.

## Ràng buộc dữ liệu

Không được chỉ áp dụng tiền xử lý cho frame live. Nếu thêm một bước như khử noise, cân bằng ánh sáng hoặc khử haze, cùng bước đó phải được áp dụng cho:

1. Ảnh sạch dùng làm train/memory bank.
2. Ảnh calibration dùng chọn ngưỡng.
3. Ảnh test dùng đánh giá.
4. Frame camera live.

Nếu các ảnh sạch gốc vẫn phù hợp, không cần chạy lại route để chụp ảnh mới. Có thể xử lý lại ảnh sạch hiện có và fit lại memory bank. Nếu vật liệu, ánh sáng, camera hoặc route đổi đáng kể, cần thu sạch lại phần bề mặt bị ảnh hưởng.

## Thứ tự triển khai đề xuất

1. Ghi và hiển thị quality metrics: blur, contrast, brightness, tỉ lệ ROI, tỉ lệ pixel che khuất.
2. Thêm quality gate và trạng thái `analysis_unavailable`; kiểm tra không tạo báo nhầm khi frame xấu.
3. Bổ sung nhiễu tổng hợp có kiểm soát vào tập đánh giá, không đưa ảnh hư hại vào train.
4. So sánh baseline với denoising/illumination normalization nhẹ.
5. Chọn pipeline tiền xử lý duy nhất, áp dụng lại cho tập sạch/calibration/test và fit artifact PatchCore mới.
6. Đánh giá riêng từng loại nhiễu bằng recall, false alerts, tỷ lệ unavailable và thời gian xử lý.
7. Chỉ sau khi RGB ổn định mới thiết kế pipeline sonar riêng.

## Tiêu chí nghiệm thu cần đặt trước khi triển khai

- Không làm giảm recall với vết nhỏ/mảnh so với baseline đã chốt.
- False alert được đo trên route sạch có nhiễu.
- Frame quá xấu được đánh dấu unavailable thay vì bị coi là sạch.
- Thời gian suy luận vẫn đáp ứng tốc độ dashboard.
- Kết quả phải có test offline độc lập và chạy thử live Unreal; hai loại bằng chứng này không thay thế nhau.
