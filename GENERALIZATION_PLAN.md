# Kế hoạch tổng quát hóa hệ thống phát hiện hư hại

> Tài liệu sống của nhóm. Cập nhật bảng **Tiến độ** và **Nhật ký quyết định** mỗi khi xong một phase hoặc đổi quyết định.
>
> Tạo: **2026-10-08**. Liên quan: `SOURCE_HANDOFF.md` (nguồn sự thật về code), `PROJECT_STATUS_AND_ROADMAP.md` (hiện trạng trước kế hoạch này), `auv_inspection/NOISE_ROBUSTNESS_TODO.md` (backlog nhiễu, được kế hoạch này thay thế dần).

## Mục tiêu

Hệ thống phải hoạt động tốt hoặc chấp nhận được trong **nhiều điều kiện nước thực tế khác nhau**, xử lý được các tình huống **chưa gặp trong thử nghiệm**, giải thích được và có bằng chứng rõ ràng. Kết quả trong mô phỏng chỉ có giá trị khi được đo trên **điều kiện chưa thấy**.

## Tiến độ

| Phase | Nội dung | Trạng thái | Bằng chứng |
|---|---|---|---|
| P0 | Gỡ chặn live: tracker không reset khi frame không đủ điều kiện; ROI dùng mask gần nhất với dung sai | **Xong** (baseline v1.1) | Unit 15/15; replay pose: ROI có ở 99,1-100% frame (trước 28-49%). Live `session_20261008_174818_976289` map A: **3/3 vết** (2 ống, 1 trụ 0), **1 báo nhầm** ở đầu ống (`nearest_mask` lệch 27 cm), route 359/359, 12,2 tick/s |
| P1 | Hạ tầng đánh giá + ngẫu nhiên hóa điều kiện; đo lại baseline v1 trên điều kiện chưa thấy | **Xong** (xem mục Baseline v1.1). Phần 3: `geometry.py`, `defect_inventory.py` + `inventories/map_A.json`, `metrics.py`, `evaluate_capture.py`, `benchmark.py`, 16 unit test; benchmark 28 tổ hợp | Phần 1: `robustness/degradation.py`, 7 yếu tố × 5 mức, 9 unit test. Phần 2: `--randomize train\|heldout --seed`, 9 unit test; Unreal: `capture_test_mixed_20261008_190916_184618` (map A, heldout seed 1, 598 ảnh) và `capture_test_clean_20261008_191432_831527` (map sạch v3, heldout seed 2, 635 ảnh), cả hai đi hết route; khoảng cách ống, lệch độ sâu/yaw, đèn, lịch chụp có tác dụng; dòng chảy không đo được (D14). Phần 3 (bộ chỉ số, đo baseline) chưa làm |
| P2 | ROI hình học + tọa độ bề mặt | **Xong offline** (chờ live dashboard) | Hiệu chỉnh hình học IoU kiểm tra 0,89-1,00; ROI hình học + lọc góc tới; frame được phân tích 100%; xem mục Kết quả P2. Tọa độ bề mặt (`surface_coordinates`) đã có, dùng ở P5 |
| P3 | Cổng chất lượng ảnh | Chưa làm | |
| P5 | Ngưỡng conformal + tích lũy bằng chứng SPRT trên bề mặt | Chưa làm | |
| P4 | Detector v2: DINOv2, bank nhiều điều kiện, Mahalanobis, loại nhiễu (có ablation) | Chưa làm | |
| P6 | Quay lại chụp gần khi bằng chứng mơ hồ | Chưa làm | |
| P7 | Nghiệm thu đầy đủ (test kín + live), cổng hash thêm hash code | Chưa làm | |

Thứ tự thực hiện đã chốt: **P0 → P1 → P2 → P3 → P5 → P4 → P6 → P7**. P1 phải đi trước P4 vì thiếu bài đo đúng thì không chứng minh được đổi model có lợi; P5 đi trước P4 vì sửa lỗi tracker và ngưỡng cho mọi backbone.

## Baseline v1.1 trên điều kiện chưa thấy (P1, 2026-10-08)

Hai capture heldout (mục 4): map A có 3 vết (`capture_test_mixed_20261008_190916_184618`, cách ống 2,77 m, bán kính trụ 3,19 m) và map sạch (`capture_test_clean_20261008_191432_831527`, 1,62 m, 3,36 m). Chấm theo vết vật lý bằng `auv_inspection/robustness/benchmark.py`; kết quả đầy đủ ở `auv_inspection/output/benchmark_p1_baseline_v1_1/summary.md`.

| Điều kiện | Classical: vết map A | Classical: báo nhầm/100 m (sạch) | PatchCore: vết map A | PatchCore: báo nhầm/100 m (sạch) | PatchCore: frame sạch có ứng viên |
|---|---|---|---|---|---|
| Gốc | 0/3 | 0 | 1/3 | 1,42 | 12% |
| Độ đục 2 | 0/3 | 0 | 1/3 | 1,89 | 28% |
| Độ đục 4 | 0/3 | 0 | 1/3 | 4,73 | 46% |
| Marine snow 3 | 0/3 | 0 | 0/3 | 11,35 | 99% |
| Marine snow 5 | 0/3 | 0 | 0/3 | 13,25 | 100% |
| Đèn yếu 4 | 0/3 | 0 | 1/3 | 0,95 | 10% |
| Mờ chuyển động 3 | 0/3 | 0 | 1/3 | 6,62 | 61% |

- **So với tiêu chí:** recall 0-33% (mục tiêu ≥ 90%); PatchCore báo nhầm 1,42/100 m ngay ở điều kiện gốc (mục tiêu ≤ 1); tỷ lệ frame sạch có ứng viên 12% (mục tiêu FPR ≤ 5%). **Chưa đạt tiêu chí nào.**
- **Classical** không tạo ứng viên nào trên các frame thấy rõ vết nứt ở khoảng cách 2,77 m: ngưỡng chỉnh tay cho 2 m không ngoại suy được. Giữ làm baseline, không đầu tư thêm.
- **PatchCore** mất khả năng phân tích khi pose xa ảnh tham chiếu: ống 0% frame ở 2,77 m, trụ 1% ở bán kính 3,36 m (ROI theo station/pose, D2/D5) → **P2**. Vết duy nhất bắt được là vết trụ (tick 3478).
- Marine snow làm gần như mọi frame sạch vượt ngưỡng (bank chỉ học bề mặt không có hạt); độ đục và mờ chuyển động tăng báo nhầm; 3 báo nhầm gốc nằm ở mặt sau ống khi AUV gần hơn train (1,62 m so với 2,06 m) → **P3** (cổng chất lượng), **P5** (bằng chứng trên bề mặt lọc hạt di chuyển), **P4** (bank nhiều điều kiện, loại không gian nhiễu).
- PatchCore khoảng 200-250 ms/frame trên RTX 3050 khi chạy offline một mình (D13).
- Lưu ý: 1 lượt mỗi loại map, 3 vết; khả năng quan sát vết tính theo hình học, không theo ánh sáng; frame liên tiếp tương quan. Đây là baseline để so sánh, không phải ước lượng chính xác hiệu năng.

## Kết quả P2: ROI hình học (v1.2, 2026-10-09)

Cùng hai capture (nay là **tập phát triển**, xem nhật ký quyết định), cùng hình học đã hiệu chỉnh cho mọi detector. Kết quả: `auv_inspection/output/benchmark_p2_geometry/` (v1.2 có lọc góc tới 70°), `.../pose_noise/`, và `benchmark_p2_geometry_no_incidence/` (v1.2 chưa lọc, để so sánh).

| Điều kiện | v1.1: vết map A | v1.2: vết map A | v1.1: báo nhầm/100 m (A / sạch) | v1.2: báo nhầm/100 m (A / sạch) |
|---|---|---|---|---|
| Gốc | 1/3 | 2/3 | 0 / 1,42 | 3,94 / **0** |
| Độ đục 2 | 1/3 | **3/3** | 0 / 1,89 | 5,42 / 0,95 |
| Độ đục 4 | 1/3 | 2/3 | 0 / 4,73 | 8,37 / 2,84 |
| Marine snow 5 | 0/3 | 2/3 | 5,42 / 13,25 | 39,88 / 40,22 |
| Đèn yếu 4 | 1/3 | 2/3 | 0 / 0,95 | 2,46 / **0** |
| Mờ chuyển động 3 | 1/3 | 2/3 | 0 / 6,62 | 13,29 / 7,10 |
| Nhiễu pose 0,1 m/2° | | 2/3 | | 0,98 / 0 |
| Nhiễu pose 0,25 m/5° | | 1/3 | | 0 / 0 |

- **Tỷ lệ frame được phân tích 28-33% → 100%**; recall vết vật lý tăng ở mọi điều kiện; trên map sạch báo nhầm giảm ở gốc, độ đục và đèn yếu. Đạt tiêu chí P2: IoU ≥ 0,85 (kiểm tra 0,89-1,00) và chịu được sai số pose.
- **Báo nhầm v1.2 trên map A** nằm ở dải mép ống/vòng bích (đã xem ảnh). Lọc góc tới 70° giảm 4,92 → 3,94/100 m ở điều kiện gốc; nhiễu pose 0,1 m/2° làm ROI co thêm và còn 0,98/100 m. Nguồn báo nhầm chính là **vùng biên ROI**, cần P3/P5.
- **Nhiễu pose 0,25 m/5°:** ROI co khoảng 70 px; ở 2,77 m dải ống còn quá mỏng nên 93-96% frame ống trả `no_surface_tiles` (không kết luận) thay vì báo nhầm. Suy giảm an toàn nhưng mất recall ống: trên AUV thật cần định vị tốt hơn hoặc lại gần (P6).
- **Marine snow** vẫn gần 100% frame vượt ngưỡng; v1.2 phân tích nhiều frame hơn nên báo nhầm còn tăng. Đây là việc của P3 (cổng chất lượng) và P5 (bằng chứng trên bề mặt).
- Vẫn chưa đạt tiêu chí nghiệm thu (recall ≥ 90%, ≤ 1 báo nhầm/100 m). Chưa chạy dashboard live với v1.2.

## Tiêu chí nghiệm thu (bản đầu)

Đo trên **điều kiện môi trường chưa từng dùng** để train hay chọn ngưỡng:

| Chỉ số | Mục tiêu |
|---|---|
| Recall theo ID vết vật lý | ≥ 90% |
| Báo nhầm | ≤ 1 trên 100 m bề mặt đã khảo sát |
| FPR tại ngưỡng | ≤ 5% với độ tin cậy 95% (δ = 5%) |

Đây là mức khởi đầu; nhóm sẽ siết hoặc nới sau khi có số liệu P1. Mọi tiêu chí phải được chốt **trước** khi chạy tập test.

## Nhật ký quyết định

| Ngày | Quyết định |
|---|---|
| 2026-10-08 | Chấp nhận kế hoạch, thứ tự phase và tiêu chí nghiệm thu bản đầu ở trên |
| 2026-10-08 | Đồng ý thêm dependency DINOv2 (qua `torch.hub` hoặc `timm`) vào `.venv-patchcore` cho P4 |
| 2026-10-09 | **Hai capture heldout P1 (`capture_test_mixed_20261008_190916_184618`, `capture_test_clean_20261008_191432_831527`) chuyển thành tập phát triển.** Đã dùng ảnh và kết quả của chúng để tìm lỗi (nhãn trụ, báo nhầm ở mép ống), nên không còn là bằng chứng "chưa thấy". Nghiệm thu P7 phải dùng capture heldout mới với seed khác, chưa ai xem trước |
| 2026-10-09 | P2: ROI hình học bỏ pixel có góc tới > 70°. Lý do vật lý (diện tích mỗi pixel gấp 1/cos θ, khoảng 3 lần; thiếu sáng; lẫn nền và mép vòng bích) chọn trước khi đo; nhu cầu phát hiện khi xem các báo nhầm v1.2 nằm trên dải mép ống ở `capture_test_mixed` (tập phát triển). Giữ kết quả không lọc ở `benchmark_p2_geometry_no_incidence` để so sánh |
| 2026-10-09 | P2: hiệu chỉnh hình học khớp 5 tham số (bán kính ống, độ cao trục, nửa cạnh trụ, offset ngang, pitch); offset tiến/đứng giữ 0 vì không xác định được với một khoảng cách duy nhất. Nhãn map A chuyển `reviewed` theo xác nhận của người dùng |
| 2026-10-08 | P1 phần 3: chấm theo **vết vật lý**, định vị cảnh báo bằng hình học camera chưa hiệu chỉnh (IoU 0,81-0,87 so với 552 mask đã duyệt), dung sai khớp 0,6 m (vết ống) và đoạn thẳng + 0,35 m (vết nứt dài trên trụ). Nhãn trụ được đổi từ điểm sang đoạn sau khi ảnh cho thấy một cảnh báo PatchCore nằm trên vết nhưng ngoài bán kính điểm; sửa theo ảnh, không theo kết quả detector, ghi trong `revisions` của `map_A.json`. Nhãn map A vẫn ở trạng thái `proposed` chờ người dùng xác nhận |
| 2026-10-08 | Giữ dòng chảy trong `RunConditions` (lực vật lý đúng, có tác dụng khi gần bão hòa bộ điều khiển) nhưng **không coi là nguồn sai lệch pose**. Sai số pose thực tế (DVL/INS) sẽ mô phỏng ở P2 bằng nhiễu trên pose đưa cho khối nhận thức, vì đó mới là cái detector thấy trên AUV thật |
| 2026-10-08 | P1 phần 2: profile `heldout` lấy **mọi** yếu tố ngoài khoảng `train` (ngoại suy), có test bảo đảm không mẫu nào lọt vào khoảng train. Route ngẫu nhiên phải qua `clearance_violations()`; bán kính trụ heldout tối thiểu 2,35 m (2,2 m bị từ chối vì góc hộp an toàn trụ vuông ở khoảng 2,26 m) |
| 2026-10-08 | Không ngẫu nhiên hóa độ đục trong mô phỏng ở P1: `water_fog` cần tag `WaterPPV` mà map dự án không có. Muốn bật cần thêm tag vào **bản sao** map (người dùng quyết định); trước mắt độ đục dùng suy giảm offline |
| 2026-10-08 | P1 phần 1: suy giảm offline dùng **khoảng cách đồng nhất 2 m** cho tới P2. Mô hình tách công trình/nền theo ROI bị loại vì đáy gần nằm ngoài ROI, bị xóa trắng và tạo viền giả. Hệ số độ đục là bộ mức nghiêm trọng, chưa khớp với nước Jerlov thật |
| 2026-10-08 | Chốt baseline v1.1 từ live P0: 3/3 vết map A, 1 báo nhầm ở đầu ống. Không vá riêng báo nhầm này (ví dụ siết dung sai `nearest_mask`) vì sẽ làm mất cả vết trụ (lệch 19 cm); nguyên nhân là ROI không biết ống kết thúc ở đâu, P2 xử lý tận gốc |
| 2026-10-08 | P0: ROI giữa hai pose tham chiếu dùng **giao hai mask** thay vì co mask hay ORB. Lý do: trên 552 mask đã duyệt, co mask gần như không cải thiện tỷ lệ ROI nằm trên bề mặt, còn giao hai mask nâng p10 lên 0,89-1,00 (đổi lại độ phủ trụ giảm); ORB chưa từng được đánh giá và cần ảnh gốc không có trong repo |

---

## 1. Chẩn đoán hiện trạng

Hệ thống hiện tại không hỏng ở model mà ở **cách đặt bài toán**: ROI, nhóm bề mặt, tracker và ngưỡng đều gắn với một lần chạy tất định, nên đánh giá offline chỉ đo khả năng nhận lại chính dữ liệu đó.

| # | Vấn đề | Bằng chứng | Hệ quả khi ra thực tế |
|---|---|---|---|
| D1 | Train, calibration và test cùng route, cùng lưới 10 tick, cùng nước, cùng đèn | Hai lượt A trùng 213/213 ảnh ống từng pixel | Test 5/5 chỉ đo khả năng "nhận lại" |
| D2 | ROI cần ảnh tham chiếu trùng pose (≤7 cm/1°), lệch hơn phải căn ORB | Phiên live 2026-09-27: 47-72% frame bị bỏ; nhánh ORB chưa từng được đánh giá; repo không kèm ảnh gốc | AUV thật không đi lại đúng pose cũ |
| D3 | Tracker bị `reset()` mỗi khi frame không phân tích được | Phiên live: 0 cảnh báo | Nhiễu ngắt quãng xóa sạch bằng chứng |
| D4 | Tracker so khớp trong pixel với hằng số 13 px/tick, 60 px | `alerts.py` | Đổi tốc độ, khoảng cách hay FPS là sai |
| D5 | Nhóm bề mặt suy từ tên station | `bridge.patchcore_category()` | Manual, route khác hay AUV thật không có tên station |
| D6 | 4 ngưỡng chọn từ 3 vết + 1 lượt sạch với ràng buộc "tổng báo nhầm ≤ 2" | `calibrate.py` | Không có bảo đảm thống kê; điểm khoảng cách trôi khi nước đổi (MVTec AD 2) |
| D7 | Backbone WRN50 học có giám sát trên ImageNet, khoảng cách Euclid | `patchcore_model_v1/config.json` | DINOv2 cho recall cao hơn hẳn ở cùng mức báo nhầm (mục 3.3) |
| D8 | Không có khái niệm chất lượng ảnh | `live_service.py` | Frame mờ hay đục vẫn bị chấm điểm |
| D9 | Pose lấy đúng tuyệt đối từ mô phỏng | `PoseSensor` | AUV thật có sai số DVL/INS và trôi theo thời gian |
| D10 | Đánh giá 5 vết, 1 bố trí, 1 seed, không khoảng tin cậy | `patchcore_evaluation_B_v1.json` | Không biết độ bất định |
| D11 | Cổng hash không hash code | `approval_gate.py` | Sửa logic xong vẫn hiện "đã nghiệm thu" |
| D13 | Suy luận PatchCore chạy đồng bộ trong vòng mô phỏng | Live P0: 130-243 ms/frame trên RTX 3050 dùng chung với Unreal; mô phỏng còn 12,2 tick/s (Classical 23,5) | Trên AUV thật, suy luận chậm sẽ chặn vòng điều khiển; cần tách bất đồng bộ (bỏ frame cũ). Xử lý ở P4 |
| D14 | Bộ điều khiển vị trí HoveringAUV quá cứng: `Kp = 100 s⁻²`, gia tốc tối đa 1 m/s² | Capture heldout với dòng chảy 0,35-0,45 m/s: sai lệch ngang giống hệt lượt không dòng chảy (khoảng 6 cm, là độ lệch socket PoseSensor); lực cản khoảng 24 N trên AUV 31 kg chỉ gây lệch khoảng 0,8 cm | AUV thật giữ vị trí kém hơn nhiều và còn sai số định vị (ước lượng pose khác pose thật). Dòng chảy trong mô phỏng không đại diện được điều này; sai số pose sẽ được mô phỏng bằng cách làm nhiễu **pose đưa cho khối nhận thức** ở P2 |
| D12 | Độ phân giải chưa gắn với yêu cầu kiểm định | 640×480, FOV 80° nên f ≈ 381 px; ở 2 m mỗi pixel ≈ 5,2 mm | Vết mảnh hơn vài mm không thể thấy về mặt vật lý |

## 2. Nguyên tắc thiết kế

1. Tách nhiễu khỏi hư hại ở mọi tầng: ảnh (cổng chất lượng), đặc trưng (loại không gian nhiễu), thời gian và không gian (bằng chứng bám trên bề mặt công trình).
2. Thiếu dữ liệu tốt thì không kết luận gì: frame kém không cập nhật bằng chứng, không kết luận "sạch", không xóa bằng chứng đã có.
3. Quyết định theo đơn vị vật lý (cm trên bề mặt, m đã khảo sát), không theo tick hay pixel.
4. Ngưỡng phải có phát biểu thống kê: báo nhầm ≤ α với độ tin cậy 1-δ, kèm số mẫu cần có.
5. Đánh giá trên điều kiện chưa thấy, chốt tiêu chí trước, báo cáo kèm khoảng tin cậy.
6. Mỗi thành phần phải có đường ra thực tế (dữ liệu lấy từ đâu trên AUV thật).

## 3. Kiến trúc mới và cơ sở toán học

```text
Camera + pose (có sai số)
 └─ [3.1] Cổng chất lượng ─── kém ──> "không đủ điều kiện" (không cập nhật bằng chứng)
 └─ [3.2] ROI hình học + khoảng cách từng pixel + tọa độ bề mặt (s, θ)
 └─ [3.3] Đặc trưng DINOv2 -> làm trắng Mahalanobis -> loại không gian nhiễu
 └─ [3.4] kNN với memory bank nhiều điều kiện -> điểm bất thường
 └─ [3.5] p-value conformal theo nhóm bề mặt và mức chất lượng
 └─ [3.6] Tích lũy bằng chứng trên lưới bề mặt (log-odds / SPRT)
 └─ [3.7] Vùng còn mơ hồ -> quay lại chụp gần -> cảnh báo và báo cáo
```

### 3.1 Cổng chất lượng ảnh

Chỉ số mỗi frame: phương sai Laplacian (độ nét), RMS contrast trong ROI, tỷ lệ pixel cháy sáng hoặc quá tối, mật độ đốm sáng nhỏ sau top-hat (marine snow), độ phủ ROI, độ bất định pose. Ngưỡng lấy theo phân vị trên dữ liệu sạch nhiều điều kiện rồi kiểm trên tập calibration, không chỉnh tay. Đầu ra là mã lý do: `blurred`, `low_visibility`, `occluded`, `particles`, `pose_uncertain`.

### 3.2 ROI hình học

Mô hình pinhole: `f = (W/2) / tan(FOV/2) = 320 / tan 40° ≈ 381,4 px`. Mỗi pixel bắn một tia và giao với hình trụ của ống hoặc trụ cầu (tọa độ trong `inspection_route.py`), cho ra:

1. Mask ROI.
2. Khoảng cách z(x) tới bề mặt ở từng pixel, dùng cho mô hình ảnh dưới nước (3.8) và cho `GSD = z/f` (mm/pixel).
3. Tọa độ bề mặt: ống (s dọc trục, θ quanh chu vi), trụ (h, θ). Nhóm bề mặt suy từ công trình mà tia chạm vào, thay cho tên station.

Sai số pose σ được lan truyền qua Jacobian của phép chiếu thành biên độ lệch pixel; mask được co tương ứng, và frame có ROI còn lại quá nhỏ bị đánh dấu `pose_uncertain`.

Cơ sở: PatchCore và AnomalyDINO không dùng vị trí patch khi chấm điểm, nên ROI chỉ cần tách công trình khỏi nền. Đo trên 552 mask đã duyệt: hai mask cách nhau khoảng 30 cm có IoU median 1,0 trên ống và 0,93-0,94 trên trụ.

Đường ra thực tế: hình học từ bản vẽ hoàn công hoặc sonar/stereo. Dự phòng: tách vật thể không cần học bằng thành phần PCA đầu tiên của đặc trưng DINOv2 (AnomalyDINO).

### 3.3 Đặc trưng và loại nhiễu

**a) Backbone DINOv2 ViT-S/14**, giữ WRN50 làm baseline. AnomalyDINO: DINOv2 vượt ViT học trên ImageNet ít nhất +4% AUROC, khoảng 60 ms/ảnh với ViT-S ở 448 px. Deng (2026), cùng mức báo nhầm đã hiệu chỉnh: recall 70,7% với DINOv2 so với 26,3% với PatchCore-WRN50. Cần đo FPS thật trên RTX 3050 4 GB khi chạy cùng Unreal.

**b) Làm trắng Mahalanobis** (Mahalanobis PatchCore, 2026):

```text
z(u) = L⁻¹ (R(u) − μ),   Σ_reg = LLᵀ
a(u) = min_{m∈M} ‖z(u) − m‖²
```

Bù cho việc đặc trưng sâu có hướng và tương quan. Trên tập công nghiệp của paper: AUROC 0,981 → 0,986 so với Euclid; peak RAM 37,4 GB → 8,2 GB.

**c) Loại không gian nhiễu** (NFAD, 2026). Tạo biến thể ảnh sạch chỉ đổi môi trường (đèn, độ đục, màu nước) bằng mô hình 3.8, rồi:

```text
Σ_nui = E[Δz Δzᵀ],   V = top-k vector riêng của Σ_nui
z' = z − γ(x) · V Vᵀ z
```

`γ(x)` giảm khi phản hồi bất thường tập trung tại chỗ. Trên AeBAD-S: I-AUROC 86,7% → 90,5%.

Cảnh báo (ShiftSplit-AD, 2026): tín hiệu hư hại cũng nằm một phần trong không gian nhiễu; lọc mạnh làm AUROC loại "breakdown" giảm 0,889 → 0,780. Bước (c) chỉ được giữ khi ablation trên điều kiện chưa thấy chứng minh có lợi, và phải báo cáo theo từng loại hư hại.

**d) Thích nghi tại hiện trường** (SPARC, 2026). Trước khi khảo sát, chụp k ≤ 8 frame sạch đã xác nhận; mỗi ô không gian ước lượng không gian bất đồng bằng SVD hạng k-1 rồi chiếu loại bỏ. Không dùng gradient; trên MVTec AD 2 và AeBAD-S, Image AUROC tăng trung bình +13,8 điểm phần trăm.

### 3.4 Memory bank nhiều điều kiện

Ảnh sạch thu dưới nhiều điều kiện (mục 4), coreset k-center phân tầng theo điều kiện. Ảnh cho bank chỉ lấy từ map đã xác nhận sạch, không bao giờ dùng frame có decal ("When more references hurt", 2026). Lưu ý patch bình thường sát vùng hư hại có thể bị thiếu ("What remains normal?", 2026).

### 3.5 Ngưỡng thống kê

p-value conformal (Bates và cộng sự, Annals of Statistics 2023), với m điểm calibration sạch cùng nhóm bề mặt và cùng mức chất lượng:

```text
p(s) = (1 + #{i : s_i ≥ s}) / (m + 1)
```

Số mẫu cần để khẳng định FPR ≤ α với độ tin cậy 1-δ (Wilks 1941; Deng 2026):

```text
m_min = ⌈ log δ / log(1 − α) ⌉
α = 5%, δ = 5%  →  m ≥ 59
α = 1%, δ = 5%  →  m ≥ 299
```

m phải là số đơn vị **độc lập**: 552 frame liên tiếp của một lượt không phải 552 mẫu độc lập. Đơn vị calibration là đoạn khảo sát hoặc lượt chạy độc lập dưới điều kiện ngẫu nhiên, hoặc dùng p-value theo khối. Hiệu chỉnh theo tầng (Mondrian) cho từng tổ hợp nhóm bề mặt × mức chất lượng. Khi môi trường trôi trong lúc khảo sát: theo dõi phân bố điểm của frame sạch và yêu cầu hiệu chỉnh lại khi phát hiện thay đổi (hướng tham khảo: conformal test martingale, 2026).

### 3.6 Tích lũy bằng chứng trên bề mặt công trình

Lưới ô c (ví dụ 5×5 cm theo (s, θ)). Mỗi frame hợp lệ cho mỗi ô nó phủ một p-value p_c,t:

```text
L_c ← L_c + log LR(p_c,t)        (frame "không đủ điều kiện": KHÔNG cập nhật)
LR(p) = a · p^(a−1),  0 < a < 1
```

`LR` là calibrator p sang e-value (Vovk & Wang, Annals of Statistics 2021), đồng thời là tỷ số hợp lý khi p-value vùng hư hại phân bố Beta(a, 1); `a` ước lượng trên validation có hư hại tổng hợp. Quyết định theo SPRT của Wald:

```text
L_c ≥ A = ln((1−β)/α)   → cảnh báo        (α = 1%, β = 5%  →  A ≈ 4,55)
L_c ≤ B = ln(β/(1−α))   → kết luận sạch   (B ≈ −2,99)
B < L_c < A             → chưa đủ bằng chứng → 3.7
```

Hư hại đứng yên trên bề mặt, còn hạt phù du, bọt khí và đốm phản sáng di chuyển theo tọa độ bề mặt, nên cộng dồn theo ô tự lọc nhiễu thoáng qua mà không cần hằng số pixel. Báo cáo có vị trí vật lý (ví dụ "ống, s = 12,4 m, θ = 35°"). Các frame liên tiếp có tương quan: chỉ cộng quan sát cách nhau một khoảng dịch chuyển tối thiểu và giới hạn mức cộng mỗi ô; cần kiểm chứng trên dữ liệu.

### 3.7 Quay lại quan sát gần

Ô ở vùng B < L < A kích hoạt lập lại kế hoạch: giữ vị trí, tiến gần, đổi góc nhìn. Lợi ích tính trước theo mô hình suy hao:

```text
t(z) = e^(−β z)      β = 0,5 m⁻¹ (nước ven bờ khá đục)
z: 2,0 m → 1,2 m   ⇒   t: 0,37 → 0,55  (tín hiệu ×1,49)
GSD: 5,2 → 3,1 mm/px
```

### 3.8 Mô hình ảnh dưới nước (để tạo dữ liệu)

```text
I(x) = J(x)·e^(−β_D z) + [J(x)·(e^(−G z) − e^(−β z))] * H_z  +  B∞·(1 − e^(−β_B z))
         truyền thẳng            tán xạ thuận (mờ theo z)              tán xạ ngược
```

(Akkaynak & Treibitz 2018; bổ sung tán xạ thuận và môi trường không đồng nhất bằng trường ngẫu nhiên Gaussian: Ismiroglou và cộng sự 2025, được chọn là thực hơn trong 82,5% đánh giá ở nước ven bờ.) z(x) lấy chính xác từ 3.2. Bổ sung hệ số nước Jerlov (Solonenko & Mobley 2015), marine snow theo bộ MSRB, nhiễu cảm biến Poisson-Gaussian.

Không áp mô hình này làm tiền xử lý chỉ cho frame live. Dùng cho: biến thể của memory bank và không gian nhiễu, các mức nghiêm trọng cho test, dữ liệu thích nghi.

## 4. Ngẫu nhiên hóa có kiểm soát

Mỗi lượt chạy có `seed` và ghi lại toàn bộ tham số: tái lập được nhưng các lượt khác nhau (domain randomization, Tobin và cộng sự 2017).

| Yếu tố | Khoảng đề xuất | Cách tạo | Trạng thái |
|---|---|---|---|
| Dòng chảy (lệch pose) | 0-0,5 m/s, đổi hướng | `env.set_ocean_currents()` | Có API |
| Khoảng cách tới công trình | 1,2-3,0 m | Tham số hóa `build_route()` | Cần code |
| Độ sâu, yaw | ±0,3 m, ±10° | Nhiễu trên waypoint | Cần code |
| Tốc độ, thời điểm chụp | 0,3-1,2 m/s; khoảng chụp ngẫu nhiên | Thay lưới 10 tick | Cần code |
| Đèn | Cường độ ±50%, góc chùm, pitch, nhiệt màu | `env.turn_on_flashlight()` | Có API |
| Độ đục, màu nước | Loại nước Jerlov I-9C | `env.water_fog()` (chưa rõ tác dụng trên material Dam riêng của map) + mô hình 3.8 offline | Cần kiểm tra |
| Hạt nhiễu, bọt khí | 5 mức | Mô hình marine snow, offline | Cần code |
| Camera | Exposure, motion blur, nhiễu, JPEG | `scenario.json` + offline | Có sẵn một phần |
| Bề mặt công trình | Bám bẩn, texture, độ nhám | Bản sao map mới (không đụng map gốc) | Cần editor |
| Hư hại | Loại, kích thước, hướng, tương phản, vị trí | Script Unreal Python theo mẫu `create_validation_maps.py` | Cần editor |

Chia dữ liệu theo điều kiện:

- **Train:** điều kiện nhóm X, map sạch.
- **Calibration:** điều kiện nhóm X, lượt độc lập, map sạch.
- **Validation:** điều kiện X + hư hại tổng hợp (ước lượng `a` ở 3.6).
- **Test:** điều kiện Y chưa từng thấy (ví dụ nước 7C/9C, dòng chảy mạnh, đèn yếu), bố trí hư hại mới, nhãn khóa trước khi chấm; thêm leave-one-factor-out.
- **Thang mức nghiêm trọng** kiểu ImageNet-C: 5 mức mỗi yếu tố.

## 5. Giao thức đánh giá

| Chỉ số | Ý nghĩa |
|---|---|
| Recall theo ID vết vật lý + đường PoD theo kích thước và độ tương phản (kiểu ASTM E2862) | Vết nhỏ nhất còn bắt được ở từng điều kiện |
| Báo nhầm trên 100 m bề mặt | Chỉ số vận hành |
| FPR tại ngưỡng + khoảng Wilson 95% | Kiểm tra lời hứa α |
| Tỷ lệ "không đủ điều kiện" theo yếu tố | Tránh hệ thống "an toàn" vì không phân tích |
| Sai số vị trí trên bề mặt (cm) | Cho báo cáo kiểm định |
| Quãng đường hoặc thời gian tới phát hiện | Đánh giá 3.6 và 3.7 |
| FPS và độ trễ trên RTX 3050 cùng Unreal | Khả năng chạy thật |

- Độ bất định: bootstrap theo lượt chạy (lượt là cụm), nhiều seed, khoảng tin cậy 95%.
- Ablation: bật/tắt từng thành phần 3.1-3.7 trên điều kiện chưa thấy; không cải thiện thì bỏ.
- Kiểm tra định vị: so tỷ lệ trùng của cặp (bản đồ điểm, mask đúng ảnh) với cặp tráo mask ảnh khác (Deng 2026).
- Bằng chứng gần thực tế: dữ liệu dưới nước thật không có hư hại (BUCKET, MSRB) để đo báo nhầm; ảnh vết nứt bê tông dưới nước đã công bố để kiểm tra ngoại hình vết; tùy chọn mạnh nhất là thử trong bể với ống bê tông có vết nứt thật và đo độ đục NTU.

## 6. Lộ trình chi tiết

Quy tắc chung: map gốc không đổi (chỉ tạo bản sao); artifact v1 giữ làm baseline, artifact mới là v2 đặt cạnh; cập nhật `SOURCE_HANDOFF.md` trong cùng task; tách bạch offline và live.

| Phase | Nội dung | Tiêu chí xong | Ước lượng |
|---|---|---|---|
| P0 | Tracker bỏ qua frame không đủ điều kiện thay vì reset; ROI dùng mask gần nhất với dung sai 0,5 m/3° | Chạy live có số liệu baseline v1.1 (chỉ là baseline, không phải nghiệm thu) | 0,5 ngày |
| P1 | Capture có `--seed` và các yếu tố mục 4; thư viện mô hình 3.8 + marine snow; chia dữ liệu theo điều kiện; bộ chỉ số mục 5 | Đo lại baseline v1 trên điều kiện chưa thấy | 2 ngày |
| P2 | ROI hình học, tọa độ bề mặt; thay `live_roi` và `patchcore_category` | IoU ≥ 0,85 so với 552 mask đã duyệt; chịu được sai số pose mô phỏng | 1-1,5 ngày |
| P3 | Cổng chất lượng 3.1 với mã lý do | Frame xấu không tạo báo nhầm; tỷ lệ từ chối báo cáo theo yếu tố | 1 ngày |
| P5 | Ngưỡng conformal + SPRT trên bề mặt; thay `calibrate.py`, `alerts.py` | FPR thực tế ≤ α (Wilson); đường PoD được báo cáo | 1,5-2 ngày |
| P4 | DINOv2 + bank nhiều điều kiện + Mahalanobis; NFAD và SPARC có gate bằng ablation | v2 hơn v1 có ý nghĩa thống kê trên điều kiện chưa thấy | 2-3 ngày |
| P6 | Lập lại kế hoạch quay lại chụp gần | Giảm bỏ sót ở mức nhiễu cao; báo cáo chi phí quãng đường | 1-2 ngày |
| P7 | Test kín + live dashboard; cổng hash thêm hash code | Báo cáo có khoảng tin cậy; live có ít nhất 1 cảnh báo đi trọn vòng | 1-2 ngày |

## 7. Giới hạn

- Mô phỏng không thay được dữ liệu thật. Bằng chứng mạnh nhất trong dự án: mô phỏng ngẫu nhiên hóa + dữ liệu nhiễu thật không có hư hại + (nếu được) thử trong bể.
- Độ phân giải giới hạn kích thước vết nhỏ nhất (D12); báo cáo phải ghi dạng "phát hiện vết rộng từ X mm ở khoảng cách Y m".
- Nước quá đục thì camera RGB mất tác dụng; kết hợp sonar (Sonar-MASt3R 2026, opti-acoustic 2025) là bước sau, ngoài phạm vi.
- Luật thi: code phải viết trong ngày thi. Tài liệu này là thiết kế; phần nào code trong ngày thi phải ghi rõ là phần làm mới.

## Tài liệu tham khảo

- Roth và cộng sự, *Towards Total Recall in Industrial Anomaly Detection* (PatchCore), CVPR 2022.
- Damm và cộng sự, *AnomalyDINO*, WACV 2025. https://www.alphaxiv.org/abs/2405.14529
- Ferrari và cộng sự, *Mahalanobis PatchCore*, 2026. https://www.alphaxiv.org/abs/2605.27748
- Cao và cộng sự, *NFAD: Nuisance-Filtered Anomaly Detection Under Distribution Shift*, 2026. https://www.alphaxiv.org/abs/2608.29112
- Han và cộng sự, *SPARC*, 2026. https://www.alphaxiv.org/abs/2608.18585
- *ShiftSplit-AD*, 2026. https://www.alphaxiv.org/abs/2608.27610
- Deng, *Distribution-free false-alarm calibration and chance-corrected spatial evaluation for industrial anomaly detection*, 2026. https://www.alphaxiv.org/abs/2608.15090
- *What Remains Normal?*, 2026. https://www.alphaxiv.org/abs/2608.23299
- *Contamination-Aware DINOv2 Memory Banks*, 2026. https://www.alphaxiv.org/abs/2608.22082
- Bates, Candès và cộng sự, *Testing for outliers with conformal p-values*, Annals of Statistics 2023.
- Vovk & Wang, *E-values: calibration, combination and applications*, Annals of Statistics 2021.
- *Change detection with conformal martingales*, 2026. https://www.alphaxiv.org/abs/2609.27179
- Ismiroglou và cộng sự, *Sea-ing Through Scattered Rays*, 2025. https://www.alphaxiv.org/abs/2509.15011
- Akkaynak & Treibitz, *A Revised Underwater Image Formation Model*, CVPR 2018; Solonenko & Mobley, *Inherent optical properties of Jerlov water types*, Applied Optics 2015.
- *Marine Snow Removal Benchmarking Dataset* (2021-2024). https://arxiv.org/abs/2103.14249
- Orinaitė và cộng sự, Applied Sciences 2023 (vết nứt bê tông dưới nước). https://doaj.org/article/b45eae0c92db4217a3e2b8fbf7c8bba2
- Lv và cộng sự, Journal of Zhejiang University 2025 (sinh ảnh vết nứt trụ cầu). https://www.zjujournals.com/eng/EN/abstract/abstract46988.shtml
- *A research on detecting and recognizing bridge cracks in complex underwater conditions*. https://fracturae.com/index.php/fis/article/view/1332
- *Sonar-MASt3R*, 2026. https://www.alphaxiv.org/abs/2603.13585; *Opti-Acoustic Scene Reconstruction in Highly Turbid Underwater Environments*, 2025. https://www.alphaxiv.org/abs/2508.03408
- Tobin và cộng sự, *Domain Randomization for Transferring Deep Neural Networks from Simulation to the Real World*, IROS 2017.
- Wilks, *Determination of sample sizes for setting tolerance limits*, Annals of Mathematical Statistics 1941.
