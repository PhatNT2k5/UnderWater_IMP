# Báo cáo hiện trạng và lộ trình tiếp theo

**Dự án:** UnderwaterDemo — AUV kiểm tra đường ống và trụ dưới nước<br>
**Cập nhật:** 26/09/2026
**Mục đích:** Giúp thành viên nhóm nắm được hệ thống hiện có, kết quả đã kiểm chứng, giới hạn và thứ tự triển khai tiếp theo.

## 1. Tóm tắt dự án

Dự án mô phỏng một AUV dùng camera để khảo sát đường ống và trụ cầu trong HoloOcean/Unreal Engine 5.3. AUV chạy theo route tự động hoặc điều khiển thủ công. Dashboard Tkinter hiển thị mô phỏng, camera robot, route, kết quả xử lý ảnh và bằng chứng cảnh báo.

Hệ thống có hai hướng phát hiện:

- **Classical:** các bước xử lý ảnh và luật hình học được viết riêng cho những kiểu hư hại nhìn thấy trong cảnh mô phỏng.
- **PatchCore:** học đặc trưng bề mặt bình thường từ ảnh sạch; vùng khác thường được chấm điểm và theo dõi qua nhiều frame. Cách này không cần thêm từng loại vết nứt vào train, nhưng vẫn phụ thuộc vào việc vết có thể nhìn thấy và khác đủ rõ với bề mặt sạch.

Một phần quan trọng của lộ trình tiếp theo là kiểm tra khả năng hoạt động khi camera gặp nhiễu môi trường. Các biện pháp khử nhiễu, quality gate và đánh giá robustness trong báo cáo này **mới là đề xuất, chưa được triển khai**.

## 2. Kiến trúc và luồng xử lý hiện tại

```text
Unreal map AUVInspection + HoloOcean
                 │
       run_inspection.py / route
                 │ camera, pose, telemetry
                 ▼
       auv_dashboard.bridge worker
        ┌────────┴─────────┐
        │                  │
    Classical           PatchCore
        │                  │
        └────────┬─────────┘
                 ▼
 Dashboard Tkinter + ảnh sự kiện + report
```

- Map project là `holoocean/engine/Content/AUVInspection/Maps/AUVInspection.umap`. Đây là map được chỉnh thủ công; tránh chạy công cụ dựng map có thể ghi đè map.
- Runtime chính nằm trong `auv_inspection/`; dashboard hiện hành nằm trong `auv_dashboard/`.
- Dashboard chạy runtime trong worker riêng. Nó nhận camera/telemetry qua queue và lưu kết quả trong `auv_dashboard/output/session_*/`.
- Khi có cảnh báo trên dashboard, worker lưu ảnh bằng chứng ở tick phát hiện, giữ AUV ở pose đó khoảng 5 giây rồi tự tiếp tục. Nút **Tiếp tục sau cảnh báo** hoặc phím **Space** có thể bỏ qua thời gian đợi.
- Thay đổi tự tiếp tục mới được kiểm tra cú pháp và unit test adapter; chưa được xác nhận qua một lượt Unreal/dashboard live.

## 3. Những phần đã hoàn thành

### 3.1 Map, route và mô phỏng

- Có map AUVInspection với đường ống, hai trụ, AUV và các vị trí hư hại dùng trong thử nghiệm.
- Có route auto để quét hai mặt ống và khảo sát các tầng quanh hai trụ; runtime cũng hỗ trợ điều khiển manual.
- Có telemetry, report, log Unreal và thư mục bằng chứng cho mỗi lần chạy.
- Có chế độ chụp ảnh cấu trúc sạch để thu dữ liệu camera theo nhóm `pipe_front`, `pipe_back`, `pier_0`, `pier_1`.
- Có các bản map riêng phục vụ calibration/test PatchCore. Map A gốc đã được giữ nguyên trong quá trình tạo các bản này.

### 3.2 Classical detector

- Dùng tiền xử lý ảnh và heuristic để tìm một số vùng tối/khác thường trên ống; áp dụng bộ lọc vùng và xác nhận ứng viên qua nhiều frame.
- Có regression tests và harness kiểm tra camera/route.
- Detector này chuyên biệt hơn PatchCore. Trong đánh giá B hiện có, Classical phát hiện 1/4 hư hại ống được so sánh; detector này không xử lý trụ.

### 3.3 PatchCore

- Đã tạo dữ liệu tham chiếu sạch cho bốn nhóm bề mặt, mỗi nhóm có ROI mask đã duyệt.
- Backbone hiện dùng `wide_resnet50_2` pretrained; trích đặc trưng từ `layer2`/`layer3`, chia frame thành tile 256×256 với bước trượt 128 px; memory bank được rút gọn bằng K-Center Greedy.
- Train dùng **552 ảnh sạch**. Hư hại không được đưa vào train để tránh học chúng như bình thường.
- Calibration/test được tách riêng theo lượt chạy. Tập test B có 552 ảnh và năm ID hư hại ở bố trí khác với calibration; nhãn được khóa trước khi chấm.
- Báo cáo offline B hiện ghi nhận **5/5 ID hư hại nhìn thấy được phát hiện**, **4/4 vết nhỏ hoặc mảnh**, và **0 cảnh báo trên route sạch test**. Nhiều box có thể thuộc cùng một vết vật lý nên số event không đồng nghĩa số hư hại.
- Ngưỡng hiện tại theo nhóm `pipe_front / pipe_back / pier_0 / pier_1`: `61.55155 / 53.06446 / 58.91152 / 54.33251`.
- Có ROI tham chiếu theo nhóm/station/pose. Nếu không tìm/căn chỉnh được ROI, service trả `analysis_unavailable`; trạng thái này không được coi là kết luận bề mặt sạch.
- Không cần train lại chỉ vì thêm một decal hư hại. Cần kiểm tra vết mới có xuất hiện trong ROI/camera và có vượt ngưỡng ổn định qua tracker hay không. Thay camera, ánh sáng, route hoặc bề mặt sạch có thể cần cập nhật tham chiếu/ngưỡng và đánh giá lại.

### 3.4 Dashboard và handoff

- Có dashboard Tkinter với lựa chọn auto/manual và Classical/PatchCore, Unreal viewport nhúng, camera robot, route XYZ, telemetry, danh sách cảnh báo, ảnh pipeline và thư mục output.
- Nút Pause/Continue/Stop và mở ảnh bằng chứng đã được nối với worker.
- PatchCore được dùng mặc định khi hash model, threshold, tham chiếu và báo cáo đánh giá vẫn khớp cổng chấp thuận.
- Có README, `SOURCE_HANDOFF.md`, hướng dẫn PatchCore, báo cáo kết quả, hướng dẫn thiết lập repo và Git LFS cho artifact lớn.

## 4. Kết quả đã kiểm chứng và giới hạn

### Đã kiểm chứng offline

- PatchCore: 5/5 vết B nhìn thấy, 4/4 nhóm nhỏ/mảnh, 0 alert trên route sạch test theo bộ dữ liệu và cách chấm hiện tại.
- Replay client/service PatchCore trên frame đã chụp cho kết quả khớp sự kiện/tick offline trong đợt bàn giao.
- Dashboard adapter: 8/8 unit test sau khi thêm countdown giữ pose 5 giây; kiểm tra cú pháp Python đạt.
- Dashboard từng có một lần live smoke test 9/9 cho giao diện và luồng pause/continue/stop cũ. Đây không phải bằng chứng live cho PatchCore hoặc thay đổi tự tiếp tục mới.

### Chưa được xác nhận

- Chưa chạy một lượt dashboard + Unreal live để xác nhận PatchCore nhận vết và tự tiếp tục đúng sau 5 giây trong cùng phiên.
- Bộ test PatchCore mới có năm ID hư hại, trên vật liệu và môi phỏng mô phỏng hiện tại. Không thể suy rộng thành cam kết phát hiện mọi loại vết mới.
- Các lượt ảnh sạch gần như tất định và chỉ khác nhau rất ít pixel. Chưa chứng minh tổng quát với nhiều mức chiếu sáng, camera, texture, nhiễu hoặc hình học khác.
- Chưa đo recall hư hại riêng đầy đủ cho mọi category; trong B có category chỉ được kiểm tra sạch.
- Kết quả PatchCore đánh dấu vùng bất thường, không phân loại loại hư hại, mức độ nghiêm trọng hoặc biên chính xác của vết.
- Pipeline chống nhiễu trong mục 5 chưa được triển khai hay nghiệm thu.

## 5. Nhiễu môi trường: vấn đề và hướng giải quyết

Nhiễu có thể tạo ra hai lỗi: **báo nhầm** nếu nhiễu giống bất thường, hoặc **bỏ sót** nếu nhiễu che mất dấu hiệu vết nứt. Không nên xử lý bằng một bộ lọc mạnh áp lên riêng frame live. Nếu đổi tiền xử lý, cùng phiên bản phải chạy trên dữ liệu train sạch, calibration, test và live; nếu không, phân bố đặc trưng và ngưỡng sẽ lệch nhau.

| Hiện tượng | Tác động thường gặp | Hướng xử lý để thử |
|---|---|---|
| Shot noise/thermal noise | Hạt sáng tối rải khắp ảnh, làm tăng điểm bất thường | Đo noise; thử denoise nhẹ như median/bilateral/NLM ở mức bảo toàn cạnh; đánh giá vết mảnh sau lọc |
| Speckle/haze | Texture giả hoặc tương phản thấp, che cạnh mảnh | Chấm chất lượng visibility/contrast; thử enhancement nhẹ; tránh sharpen mạnh tạo cạnh giả |
| Nước đục, giảm tầm nhìn | Màu và tương phản đổi, ROI alignment yếu | Chuẩn hóa sáng/màu có giới hạn; nếu visibility thấp thì đánh dấu frame không đủ chất lượng |
| Phù sa/hạt bụi nước | Đốm chuyển động tạo candidate nhưng thường chỉ tồn tại ngắn | Theo dõi candidate qua frame; dùng chuyển động/tính tồn tại để giảm nhiễu hạt, không xóa mọi vùng nhỏ |
| Bọt khí/vật thể che khuất | Vùng lớn bất thường tạm thời hoặc che đúng vị trí vết | Đo mức che khuất; đợi frame kế tiếp nếu chỉ che thoáng qua; không diễn giải vùng bị che là sạch |
| Rung/motion blur | Làm mờ cạnh, mất vết nứt mảnh | Đo blur; đánh dấu không đủ chất lượng hoặc giảm tốc/giữ quan sát thêm khi blur kéo dài |
| AUV lệch do dòng chảy | ROI/reference sai pose, scoring nền sai | Kiểm tra pose và độ tin cậy alignment; trả `analysis_unavailable` khi lệch vượt giới hạn |
| Thay đổi cường độ/độ sâu | Dịch brightness/color so với ảnh train | Đo brightness/contrast; thử illumination normalization nhất quán trên mọi tập dữ liệu |
| Nhiễu imaging sonar | Kiểu tín hiệu khác RGB, memory bank RGB không phù hợp | Xây pipeline và memory bank sonar riêng; không gộp thẳng sonar với bank RGB |

### Nguyên tắc thiết kế

1. **Tách chất lượng ảnh khỏi bất thường bề mặt.** Trước PatchCore, ước lượng blur, sáng/tối, tương phản, visibility, che khuất và độ tin cậy ROI/alignment.
2. **Trả trạng thái rõ ràng khi không đủ chất lượng.** Không biến frame mờ/che khuất thành kết luận “sạch”. Dùng `analysis_unavailable` kèm lý do và tiếp tục quan sát hoặc yêu cầu AUV giữ/điều chỉnh theo chính sách đã chọn.
3. **Ưu tiên xử lý nhẹ và có thể kiểm tra.** Bắt đầu với denoise cạnh bảo toàn, chuẩn hóa sáng/màu có giới hạn và căn chỉnh ROI. Dehaze/sharpen mạnh có thể tạo texture/cạnh không có thật.
4. **Dùng thông tin thời gian.** Vết hư hại thường bám trên bề mặt qua nhiều frame; hạt, bọt và che khuất thường biến đổi. Tracker hỗ trợ loại nhiễu tạm thời nhưng không được đặt điều kiện diện tích lớn đến mức bỏ mất vết nhỏ.
5. **Không đưa hư hại vào memory bank sạch.** Nếu cần thích nghi với noise nền, đánh giá riêng việc bổ sung ảnh bề mặt sạch trong điều kiện mới; không học frame có decal/hư hại như ảnh sạch.
6. **Giữ baseline để so sánh.** Chạy detector gốc và phiên bản mới trên cùng frame/nhãn; lưu preprocessing version, tham số, model/threshold hash và chất lượng đầu vào theo từng kết quả.

## 6. Lộ trình triển khai đề xuất

### Giai đoạn 0 — Chốt baseline và bộ dữ liệu đánh giá

- Giữ nguyên artifact PatchCore hiện tại làm baseline có thể quay lại.
- Lấy ảnh sạch và ảnh B/A đã có; kiểm tra manifest, ROI, nhãn và không trộn các frame liền kề giữa calibration/test.
- Tạo bộ đánh giá offline có bản sạch gốc và bản nhiễu tổng hợp theo từng mức độ. Giữ một tập test kín không dùng chọn tham số.
- Đặt sẵn cách tính recall theo ID/vết, false alert theo lượt hoặc mỗi số frame, alert latency, tỷ lệ `analysis_unavailable`, thời gian inference và khả năng giữ vết nhỏ/mảnh.

### Giai đoạn 1 — Gắn đo chất lượng ảnh, chưa thay detector

- Tính blur, brightness, contrast, vùng bão hòa/cháy sáng, visibility đơn giản, tỷ lệ che khuất và ROI alignment confidence.
- Ghi các chỉ số vào log/report; hiển thị lý do khi frame kém chất lượng.
- Chạy trên dữ liệu hiện tại để chọn ngưỡng chất lượng ban đầu, tránh đặt ngưỡng chỉ bằng cảm tính.

### Giai đoạn 2 — Mô phỏng nhiễu và đo độ nhạy

- Thêm từng loại nhiễu riêng: Gaussian/shot noise, speckle, haze/contrast loss, particle, bubble/occlusion, blur, lệch pose và thay đổi ánh sáng.
- Tạo nhiều mức nhẹ/vừa/nặng với seed xác định để kết quả tái lập; không lấy các bản nhiễu làm ảnh hư hại.
- Đo baseline PatchCore và Classical trước khi chỉnh thuật toán. Phân tích loại nào gây báo nhầm hoặc bỏ sót nhiều nhất.
- Giữ kiểm tra ảnh raw, ROI, heatmap, mask và event; heatmap đỏ tự nó chưa có nghĩa là cảnh báo.

### Giai đoạn 3 — Bổ sung quality gate và trạng thái không đủ điều kiện

- Chặn phân tích/kết luận khi frame quá mờ, ROI lệch, tầm nhìn thấp hoặc bị che đáng kể.
- Trả `analysis_unavailable` kèm mã lý do như `blurred`, `low_visibility`, `occluded`, `roi_misaligned`.
- Quy định hành vi AUV: nhiễu ngắn thì chờ/chụp frame mới; lỗi kéo dài thì báo dashboard và giữ an toàn hoặc tiếp tục theo quyết định vận hành. Chỉ chuyển sang trạng thái “đã khảo sát” khi có ảnh đủ chất lượng.

### Giai đoạn 4 — So sánh tiền xử lý

- So sánh baseline với các lựa chọn nhẹ: denoise bảo toàn cạnh, chuẩn hóa illumination/color, CLAHE có giới hạn trên ROI và xử lý mờ/chói.
- Chọn riêng cấu hình tối thiểu đạt hiệu quả; không ghép nhiều filter trước khi biết tác dụng từng filter.
- Kiểm tra trực tiếp rằng vết nứt nhỏ/mảnh vẫn còn nhìn thấy trong ảnh sau xử lý.

### Giai đoạn 5 — Tạo pipeline/artifact đã hiệu chỉnh

- Chọn một pipeline tiền xử lý thống nhất và gắn version cho nó.
- Chạy lại pipeline đó trên ảnh sạch hiện có, calibration và test; nếu ảnh sạch vẫn đại diện cho bề mặt bình thường, không cần chạy lại route chỉ vì thêm loại noise tổng hợp.
- Nếu xử lý làm thay đổi embedding hoặc điều kiện sạch thực tế đã đổi nhiều, tạo memory bank/model và ngưỡng mới. Giữ artifact cũ để rollback.
- Chỉ dùng calibration để chọn ngưỡng. Không nhìn test rồi sửa ngưỡng; nếu dùng test để điều chỉnh thì cần một test set mới.

### Giai đoạn 6 — Kiểm thử tích hợp và live

- Chạy offline trên từng loại/mức nhiễu và báo cáo kết quả theo category, không chỉ một điểm tổng.
- Chạy dashboard + Unreal live với map thử nghiệm; xác nhận detector, `analysis_unavailable`, alert, lưu ảnh, giữ 5 giây và tự chạy tiếp.
- Kiểm tra tải CPU/GPU, thời gian mỗi frame, tốc độ camera và backlog queue khi inference chậm.
- Ghi rõ test offline và live là hai bằng chứng riêng.

### Giai đoạn 7 — Sonar và domain khác (sau RGB)

- Chỉ triển khai sonar khi có sensor/data/nhãn phù hợp. Sonar cần ROI, tiền xử lý, memory bank và threshold riêng.
- Không khẳng định kết quả RGB camera đại diện cho sonar hoặc camera thật ngoài môi trường mô phỏng.

## 7. Tiêu chí nghiệm thu đề xuất

Trước khi bắt đầu tối ưu, nhóm cần chốt baseline và ngưỡng chấp nhận bằng số. Bộ tiêu chí nên gồm:

- Recall theo từng ID hư hại và theo nhóm bề mặt; báo cáo riêng vết nhỏ/mảnh.
- False alert trên route sạch cho từng loại và mức nhiễu.
- Tỷ lệ frame bị `analysis_unavailable`, có phân loại nguyên nhân.
- Thời gian từ frame đầu nhìn rõ đến cảnh báo; thời gian inference và tốc độ preview.
- Chất lượng localization: vùng heatmap/mask có bám vết thực tế hay không.
- Kiểm tra ảnh sau tiền xử lý không xóa/biến dạng các vết nhỏ.
- Reproducibility: seed, dataset version, preprocessing version, model/threshold hash và lệnh chạy được lưu cùng báo cáo.
- Dashboard live xử lý được ít nhất một cảnh báo từ đầu tới cuối, bao gồm ảnh bằng chứng và tự tiếp tục 5 giây.

Không chọn một ngưỡng chất lượng ảnh hoặc một phương pháp enhancement cho mọi môi trường trước khi xem trade-off false alert/recall trên bộ đánh giá.

## 8. Việc ưu tiên kế tiếp

1. Người dùng chạy dashboard chọn **Auto + PatchCore** và xác nhận luồng cảnh báo mới giữ 5 giây, lưu đúng ảnh và tự chạy lại.
2. Tạo bộ benchmark nhiễu offline từ frame hiện có; trước tiên đo tác động, chưa sửa model.
3. Thêm logging quality metrics để xác định noise nào thực sự là nguyên nhân chính.
4. Triển khai quality gate cho blur/occlusion/ROI alignment và xác nhận `analysis_unavailable` không tạo báo hư hại giả.
5. Thử từng tiền xử lý nhẹ, so sánh bằng tiêu chí ở mục 7.
6. Chỉ cập nhật memory bank/threshold sau khi chọn pipeline bằng calibration; giữ tập test độc lập.
7. Sau khi offline đạt, kiểm tra live dashboard/Unreal và bổ sung báo cáo kết quả.

## 9. Tài liệu liên quan

- `SOURCE_HANDOFF.md`: cấu trúc, API, luồng chạy, lệnh và ranh giới bảo vệ map.
- `auv_inspection/PATCHCORE_GUIDE_VI.md`: dữ liệu, memory bank, suy luận và giới hạn PatchCore.
- `auv_inspection/PATCHCORE_HANDOFF.md`: số liệu calibration/test B, artifact và cách kiểm tra dashboard.
- `auv_inspection/NOISE_ROBUSTNESS_TODO.md`: checklist kỹ thuật tập trung về độ bền trước nhiễu.
- `auv_dashboard/README.md`: chạy dashboard và điều khiển.

---

**Lưu ý trạng thái:** Các số liệu PatchCore trong báo cáo là kết quả offline trên bộ dữ liệu mô phỏng hiện có. Hướng xử lý noise là roadmap gợi ý; chưa có bằng chứng chúng đã hoạt động trong runtime.