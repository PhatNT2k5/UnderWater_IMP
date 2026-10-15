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
| P2 | ROI hình học + tọa độ bề mặt | **Xong** (live `session_20261009_103800_863732`: 3/3 vết, 2 báo nhầm ở biên ROI, 1 báo trùng) | Hiệu chỉnh hình học IoU kiểm tra 0,89-1,00; ROI hình học + lọc góc tới; frame được phân tích 100%; xem mục Kết quả P2. Tọa độ bề mặt (`surface_coordinates`) đã có, dùng ở P5 |
| P3 | Cổng chất lượng ảnh | **Xong** (live `session_20261009_150224_114943`: 3/3 vết, **0 báo nhầm**, 1 báo trùng vết trụ) | Lề chấm điểm 24 px + cổng `diffuse_anomaly`; số đo chất lượng chỉ để chẩn đoán (cổng theo phân vị bị loại). Tập phát triển: tổng báo nhầm 14 lượt chạy 410 → 97, recall giữ ở điều kiện có nghĩa; xem mục Kết quả P3 |
| P5 | Ngưỡng conformal + tích lũy bằng chứng trên bề mặt | **Xong** (live `session_20261012_164927_783087`: **3/3 vết, 0 báo nhầm, 0 báo trùng**) | Quy tắc k = 3 lượt nhìn trên ô 10 cm, hit = ngưỡng pixel AND ngưỡng tương đối theo tầng (thân ống / mối nối / mặt trụ), calibrate conformal trên 3 capture sạch train mới. Tập phát triển: 0 báo nhầm ở 12/14 lượt (v1.3: 30), marine snow 3 vẫn 19-21/100 m; xem mục Kết quả P5 |
| P4 | Detector v2: DINOv2, bank nhiều điều kiện, Mahalanobis, loại nhiễu (có ablation) | **Xong offline** (ứng viên: v2 + lề mép ảnh; P4.3 kết hợp NFAD + Mahalanobis 42/63, 17 không hơn; trước đó P4.3: NFAD 55/63 vết, 30 báo nhầm; Mahalanobis 40/63, 5 báo nhầm, xem Kết quả P4.3; phần 4: tập phát triển 6 capture, v2 + lề mép ảnh 48/63 vết, 20 báo nhầm trên 42 lượt, ngoài marine snow 93%; live `session_20261013_091452_126695`: 3/3 vết, 1 báo nhầm; Mahalanobis/NFAD/SPARC chưa làm) | `detector_v2/` (DINOv2 ViT-S/14, kNN cosine, bank coreset, calibration ngưỡng pixel v2), tích hợp vào service; DINOv2 21,5 ms (scale 1) / 114 ms (scale 2) trên RTX 3050, peak 73-120 MiB |
| P6 | Quay lại chụp gần khi bằng chứng mơ hồ | **Dừng ở mức đo** (P6.1: lợi ích tối đa 2-4/15 vết sót, chi phí 3,3-18,7 lần/100 m; lợi ích vật lý không đo được trong mô phỏng hiện tại) | Xem Kết quả P6.1 |
| P7 | Nghiệm thu đầy đủ (test kín + live), cổng hash thêm hash code | **Offline: không đạt** (recall 72,3% < 90%; báo nhầm 0,345/100 m và FPR ô 0,031% đạt). Live: map A 3/3, 0 báo nhầm; map B 4/5, 2 báo nhầm theo quy tắc (1 trong 2 nằm trên vết khi xem ảnh). Cổng hash code xong (D11) | Xem Kết quả P7 | `robustness/acceptance_preregistration.json` |
| P8 | Marine snow, báo nhầm chân trụ và rìa quầng đèn (vòng mới, đăng ký và heldout mới) | **Đang làm** (P8.1 xong; P8.2 phần 1: giới hạn trụ đạt, cổng P8 tăng recall nhưng báo nhầm ×19) | Xem Kết quả P8.1 |

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

## Kết quả P3: lề chấm điểm và cổng bất thường lan tỏa (v1.3, 2026-10-09)

Cùng tập phát triển và điều kiện như P2. Kết quả: `auv_inspection/output/benchmark_p3_quality/` (`patchcore_geo_m` = v1.2 + lề 24 px, `patchcore_geo_md` = lề + cổng). Cột v1.2 lấy từ `benchmark_p2_geometry/`.

| Điều kiện | Vết map A (v1.2 / lề / lề + cổng) | Báo nhầm/100 m map A (v1.2 / lề / lề + cổng) | Báo nhầm/100 m map sạch (v1.2 / lề / lề + cổng) | Frame bị cổng abstain (A / sạch) |
|---|---|---|---|---|
| Gốc | 2/3 / 2/3 / 2/3 | 3,94 / 0,49 / **0,49** | 0 / 0 / **0** | 0 / 0 |
| Độ đục 2 | 3/3 / 3/3 / 3/3 | 5,42 / 5,42 / 4,43 | 0,95 / 0,95 / 0,95 | 0,5% / 0,3% |
| Độ đục 4 | 2/3 / 2/3 / 2/3 | 8,37 / 4,92 / **1,48** | 2,84 / 2,84 / 1,42 | 7,7% / 1,1% |
| Marine snow 3 | 2/3 / 1/3 / 1/3 | 36,43 / 30,03 / 16,74 | 37,38 / 27,91 / 15,61 | 32% / 28% |
| Marine snow 5 | 2/3 / 2/3 / 0/3 | 39,88 / 39,39 / **0** | 40,22 / 40,22 / **0** | 100% / 99,7% |
| Đèn yếu 4 | 2/3 / 2/3 / 2/3 | 2,46 / 0,49 / **0,49** | 0 / 0 / 0 | 0 / 0 |
| Mờ chuyển động 3 | 2/3 / 2/3 / 2/3 | 13,29 / 11,82 / **4,43** | 7,10 / 6,62 / **0,95** | 19% / 14% |

- **Lề 24 px** loại gần hết báo nhầm ở biên ROI: map A gốc 8 → 1, đèn yếu 5 → 1, không mất vết nào ở điều kiện gốc.
- **Cổng lan tỏa** giảm mạnh báo nhầm ở độ đục 4, mờ chuyển động và marine snow; ở marine snow 5 hệ thống abstain gần như mọi frame thay vì phát khoảng 80 cảnh báo sai. Abstain không được tính là "sạch" (P5 không được dùng các frame này làm bằng chứng bề mặt sạch) và hiển thị cho operator.
- Tổng báo nhầm 14 lượt chạy: v1.2 **410**, lề 354, lề + cổng **97**. Recall theo vết giữ nguyên ở mọi điều kiện mà frame sạch không bị đánh dấu gần hết.
- **Recall marine snow 3 (2/3 → 1/3) không phải hồi quy có ý nghĩa:** ở điều kiện này 92-99% frame không có vết vẫn có ứng viên, nên cảnh báo "trúng" vết là trùng hợp. Cảnh báo trúng `A_pipe_front_2` của v1.2 nằm ở mép trên ống (y ≈ 211 px), vùng hạt tuyết bị lề loại.
- **Báo nhầm còn lại khi nước đục nằm trên vòng bích** (`pipe_back`, cách nhau khoảng 3 m, đúng chỗ đèn sáng nhất; đã xem ảnh tick 1741 và 2056). Vòng bích nằm sâu trong ROI và bất thường chỉ ở một chỗ, nên cả lề lẫn cổng đều không áp dụng được. Đây là lệch miền của đặc trưng → **P4** (bank nhiều điều kiện, chuẩn hóa đặc trưng); P5 có thể giảm nhờ đòi bằng chứng lặp trên cùng tọa độ bề mặt.
- **Marine snow mức vừa** (15-17/100 m) vẫn là nguồn báo nhầm lớn nhất: hạt rời rạc chưa đủ dày để vượt 5% ROI. Hạt di chuyển giữa các frame còn vết cố định trên bề mặt → **P5** (bằng chứng theo tọa độ bề mặt) là cơ chế đúng.
- **Live v1.3** (`auv_dashboard/output/session_20261009_150224_114943/`, map A, Tự động + PatchCore, điều kiện gốc): route 359/359 trong khoảng 13 phút, 4 cảnh báo. Khớp inventory bằng hình học đã hiệu chỉnh và đã xem ảnh: tick 405 `A_pipe_front_1` (cách nhãn 0,31 m), tick 654 `A_pipe_front_2` (0,39 m), tick 3657 và 3888 cùng là `A_pier_0_1` (0,22 m và 0,10 m, hai đầu vết nứt nhìn từ hai pose cách nhau hơn 2 m). So với live P2: **3/3 vết, báo nhầm 2 → 0**, báo trùng vẫn 1 (P5 gộp theo tọa độ bề mặt). Hai cảnh báo trụ có vùng nhỏ (77 và 14 px) sát mép ảnh, tức vết chỉ được thấy ở rìa tầm nhìn.
- Session live chưa ghi lại frame `diffuse_anomaly` (chỉ hiện trên UI); P5 cần lưu trạng thái từng frame phân tích để có bằng chứng bề mặt.
- Vẫn chưa đạt tiêu chí nghiệm thu: một lượt live ở điều kiện gốc trên map đã dùng để phát triển không phải bằng chứng "chưa thấy".

## Kết quả P5: bằng chứng trên bề mặt (v1.4, 2026-10-12)

Calibration (`robustness/calibration/surface_v1.json`) từ 3 capture **calibration** mới trên map sạch v3, profile train seed 11/12/13 (khoảng cách ống 2,33/1,99/2,15 m), chưa dùng cho việc gì khác: 45.591 ô, 529 m, 8.620 ô/100 m, α = 5,8×10⁻⁵ mỗi ô (ngân sách 0,5 báo nhầm/100 m). Tập phát triển không tham gia calibration, nên capture sạch dev nay là phép đo hợp lệ cho P5. Kết quả: `auv_inspection/output/benchmark_p5_surface/` (`patchcore_surface`), so với v1.3 (`patchcore_geo_md` trong `benchmark_p3_quality/`).

| Điều kiện | Vết map A (v1.3 → v1.4) | Báo nhầm map A | Báo nhầm map sạch |
|---|---|---|---|
| Gốc | 2/3 → 2/3 | 1 → **0** | 0 → 0 |
| Độ đục 2 | 3/3 → 3/3 | 9 → **0** | 2 → **0** |
| Độ đục 4 | 2/3 → 2/3 | 3 → **0** | 3 → **0** |
| Marine snow 3 | 1/3 → 1/3 | 34 → 42 | 33 → 41 |
| Marine snow 5 | 0/3 → 0/3 (abstain) | 0 → 0 | 0 → 0 |
| Đèn yếu 4 | 2/3 → 2/3 | 1 → **0** | 0 → 0 |
| Mờ chuyển động 3 | 2/3 → **1/3** | 9 → **0** | 2 → **0** |

- **0 báo nhầm ở 12/14 lượt** (v1.3: 30 báo nhầm trên cùng 12 lượt), đạt tiêu chí ≤ 1/100 m ở mọi điều kiện trừ marine snow 3. Ở điều kiện gốc chỉ có đúng 2 cảnh báo và cả hai trúng vết.
- **Recall chưa đạt** (tốt nhất 3/3 ở độ đục 2, thường 2/3). `A_pipe_front_1` yếu, ít khi đủ 3 lượt nhìn vượt ngưỡng; khi mờ chuyển động mất thêm vết trụ. Hạ k hoặc ngưỡng sẽ đổi lại báo nhầm; đây là việc của P4 (đặc trưng tốt hơn) và P6 (quay lại nhìn gần).
- **Marine snow 3 tệ hơn v1.3** (67 → 83 báo nhầm, 19-21/100 m). Phần lớn nằm trên mặt trụ, sát mép trên/dưới ảnh (vùng nhìn xiên, xa): hạt bị chấm cao ở cùng chỗ qua nhiều lượt, nên quy tắc k lượt nhìn không lọc được. Cần xử lý ở mức ảnh/đặc trưng (**P4**).
- **Mức đảm bảo thống kê:** mọi tầng `data_limited`; mặt trụ gần đạt α (5,8-6,2×10⁻⁵), thân ống 2,4×10⁻⁴, mối nối 5,0×10⁻⁴ mỗi ô. Mức này chỉ có nghĩa với điều kiện trao đổi được với lượt train; điều kiện heldout đo bằng benchmark.
- Các lựa chọn (chuẩn hóa median, dải mối nối ±0,5 m, quy tắc AND) được rút ra từ tập phát triển, nên P7 phải kiểm trên heldout mới.
- **Live v1.4** (`auv_dashboard/output/session_20261012_164927_783087/`, map A, Tự động + PatchCore, điều kiện gốc): route 359/359, 3 cảnh báo, đã xem ảnh: tick 429 `A_pipe_front_1` (cách nhãn 0,12 m), 705 `A_pipe_front_2` (0,37 m), 3666 `A_pier_0_1` (0,29 m). So với live v1.3: 3/3 vết, báo nhầm 0 → 0, **báo trùng 1 → 0** (vết trụ chỉ báo một lần). `patchcore_frames.jsonl`: 2.155 frame phân tích, median 219 ms (p90 281 ms), 18 frame không có ROI (vòng qua đầu ống), 12 frame `diffuse_anomaly`.
- **Phát hiện live: cổng `diffuse_anomaly` che vết lớn ở gần.** 12 frame abstain (tick 657-690) đều là lúc `A_pipe_front_2` trong tầm nhìn ngay trước cảnh báo ở tick 705: 5,6-8,3% ROI vượt ngưỡng nhưng chỉ 1-3 vùng. Giới hạn 5% chọn từ tập phát triển (vết tối đa 3,1% ở khoảng cách 2,77 m); live ở khoảng cách danh định gần hơn nên vết chiếm nhiều diện tích hơn. Lượt này vẫn báo được, nhưng cổng đang bỏ bằng chứng của đúng loại hư hại quan trọng nhất (vết lớn). Đã sửa ngày 2026-10-12, xem nhật ký quyết định: cổng đo độ phân tán. Benchmark tập phát triển `benchmark_p5b_diffuse_spread/`: giống v1.4 ở 12/14 lượt; tỷ lệ abstain giảm (độ đục 4 map A 7,7% → 0,3%, mờ chuyển động 19% → 14%); marine snow 3 map A 42 → 45 báo nhầm; độ đục 2 map A chuyển từ 3/3, 0 báo nhầm sang 2/3, 1 báo nhầm, nhưng đã xem ảnh: cảnh báo "nhầm" ở tick 463 (x = -7,05) nằm trên đầu trái của chính vết nứt dài `A_pipe_front_2`, cách điểm nhãn (-7,66) 0,61 m, ngay ngoài bán kính 0,6 m, và cảnh báo khớp nhãn sau đó bị gộp vào nó. Nhãn điểm không phủ hết vết dài khoảng 1 m; đề xuất đổi nhãn sang đoạn thẳng như vết trụ, chờ người dùng duyệt.

## Kết quả P4 phần 2: DINOv2 với bank nhiều điều kiện (2026-10-12, tập phát triển)

Bank: 4 capture train sạch mới (seed 21-24, khoảng cách ống 2,08-2,34 m, bán kính trụ 2,55-3,02 m), mỗi nhóm 15.000 token coreset từ 60.000 ứng viên (v1: 678-800 patch). `detector_v2_dino_s2_aug` thêm một bản suy giảm mức 1 mỗi frame, `..._noaug` không thêm. Ngưỡng pixel và ngưỡng tầng v2 calibrate trên 3 capture calibration (seed 11-13). Cả ba detector chạy với nhãn `A_pipe_front_2` mới và cổng lan tỏa đếm hit của quy tắc bề mặt (xem nhật ký quyết định). Kết quả: `auv_inspection/output/benchmark_p4_dino/`.

| Map | Điều kiện | v1.4 (`patchcore_surface`) | v2 + suy giảm mức 1 (`dino_surface`) | v2 không suy giảm |
|---|---|---|---|---|
| A | Gốc | 2/3, 0 | 2/3, 1 (*) | 2/3, 1 |
| A | Độ đục 2 | 3/3, 0 | 2/3, 4 | 3/3, 0 |
| A | Độ đục 4 | 2/3, 0 | 3/3, 0 | 3/3, 3 |
| A | Marine snow 3 | 1/3, **45** | 1/3, **0** (abstain 57%) | 0/3, 0 (abstain 100%) |
| A | Marine snow 5 | 0/3, 0 (abstain 98%) | 0/3, 0 (abstain 80%) | 0/3, 0 (abstain 100%) |
| A | Đèn yếu 4 | 2/3, 0 | 2/3, 4 | 3/3, 0 |
| A | Mờ chuyển động 3 | 1/3, 3 | **3/3**, 1 | **3/3**, 0 |
| sạch | Gốc | 0 | **7** | 5 |
| sạch | Độ đục 2 / 4 | 0 / 0 | 1 / 1 | 1 / 0 |
| sạch | Marine snow 3 | **41** | **0** (abstain 41%) | 0 (abstain 100%) |
| sạch | Marine snow 5, đèn yếu, mờ | 0 | 0 | 0 |
| | **Tổng** | 11/21 vết, 89 báo nhầm | 13/21 vết, 19 báo nhầm | 14/21 vết, 10 báo nhầm |

(*) Đã xem ảnh: cảnh báo trụ tick 2963 nằm trên vết nứt nhìn thấy, nhưng cách đoạn nhãn khoảng 0,4 m (xem phát hiện hình học bên dưới).

- **v2 xử lý được marine snow mức vừa:** 0 báo nhầm ở marine snow 3 trên cả hai map, trong khi vẫn phân tích 43-59% frame (v1.4: 41-45 báo nhầm). Bank không suy giảm thì abstain toàn bộ: an toàn nhưng không kiểm tra được gì. Đây là lợi ích rõ nhất của suy giảm mức 1 trong bank.
- **v2 tăng recall** (13-14/21 so với 11/21), rõ nhất ở mờ chuyển động (3/3 so với 1/3).
- **v2 có báo nhầm mới ở điều kiện không suy giảm:** 19 báo nhầm với bank có suy giảm, theo vùng: mặt trụ gần mặt nước (z > -2,5 m) 7, mối nối ống 5, giữa mặt trụ 5, chân trụ 1, thân ống 1. Trên map sạch gốc, 6/7 báo nhầm nằm ở z ≈ -1,0 đến -1,16 m quanh cả hai trụ: capture này có bán kính vòng trụ 3,36 m (ngoài khoảng train 2,5-3,1 m) nên nhìn thấy trụ gần mặt nước nhiều hơn dữ liệu bank.
- **Chưa đạt tiêu chí nghiệm thu** với v2 (≤ 1/100 m): map sạch gốc 3,31/100 m, map A độ đục 2 và đèn yếu 1,97/100 m.
- **Phát hiện hình học:** cùng vết nứt trụ chiếu từ tick 2963 (AUV z -9,0, yaw -58°) và tick 3478 (z -7,4, yaw -81°) cho hai đường song song lệch khoảng 0,35 m theo chiều đứng. Đây là sai số hình học giữa các tầng quan sát trụ (offset đứng của camera hoặc pitch, không xác định được ở P2 vì chỉ có một khoảng cách), làm ô bề mặt của các lượt nhìn khác tầng lệch khoảng 3 ô và làm định vị cảnh báo trụ lệch. Có thể calibrate lại bằng các capture nhiều độ sâu hiện có.
- **Độ nhiễu của phép đo:** khác biệt giữa các biến thể ở từng lượt chỉ là 1-4 cảnh báo trên 2 capture, nên nhiều so sánh nằm trong dao động ngẫu nhiên; tập phát triển nhỏ và đã được dùng cho nhiều quyết định.

## Kết quả P4 phần 3: hình học v2 (2026-10-13, tập phát triển)

Cùng dữ liệu và quy trình như phần 2, nhưng mọi thứ phụ thuộc hình học được làm lại với `geometry_v2.json`: nhãn map A, `surface_v2.json` của v1.4, bank v2 (`detector_v2_dino_s2_aug_g2`, `..._noaug_g2`) cùng ngưỡng pixel và ngưỡng tầng. Kết quả: `auv_inspection/output/benchmark_p4_dino_g2/` (vết map A, báo nhầm, tỷ lệ frame abstain).

| Map | Điều kiện | v1.4 | **v2 + suy giảm mức 1** | v2 không suy giảm |
|---|---|---|---|---|
| A | Gốc | 2/3, 0 | **3/3, 0** | 3/3, 1 |
| A | Độ đục 2 | 3/3, 0 | **3/3, 0** | 3/3, 0 |
| A | Độ đục 4 | 2/3, 0 | 3/3, 1 (9%) | 2/3, 0 |
| A | Marine snow 3 | 2/3, 37 | 1/3, **0** (35%) | 0/3, 0 (100%) |
| A | Marine snow 5 | 1/3, 1 (90%) | 1/3, **0** (42%) | 0/3, 0 (100%) |
| A | Đèn yếu 4 | 2/3, 1 | **3/3, 0** | 3/3, 0 |
| A | Mờ chuyển động 3 | 2/3, 0 | **3/3, 0** | 3/3, 1 |
| sạch | Gốc / độ đục 2 / độ đục 4 | 0 / 0 / 0 | 0 / 0 / 0 (13-16%) | 4 / 0 / 0 |
| sạch | Marine snow 3 / 5 | 39 / 0 | 0 / 1 (31-34%) | 0 / 0 (100%) |
| sạch | Đèn yếu / mờ | 0 / 0 | 0 / 0 (20% / 8%) | 0 / 0 |
| | **Tổng** | 14/21 vết, 78 báo nhầm | **17/21 vết, 2 báo nhầm** | 14/21 vết, 6 báo nhầm |

- **v2 + suy giảm mức 1 đạt ≤ 1 báo nhầm/100 m ở cả 14 lượt** (tệ nhất 0,49/100 m: một ô thân ống sau ở độ đục 4 và một ô mặt trụ ở marine snow 5). Báo nhầm vùng trụ gần mặt nước ở phần 2 biến mất khi sửa hình học, nên chúng là hệ quả của ô bề mặt lệch giữa các lượt nhìn, không phải do bản thân vùng đó.
- **Recall 17/21 = 81%** (Wilson 95% chỉ mang tính tham khảo vì 3 vết × 7 điều kiện tương quan); ngoài marine snow: 15/15. Marine snow 3/5 mỗi mức chỉ 1/3 vết. Chưa đạt mục tiêu 90%.
- **Giá phải trả:** v2 abstain 13-20% frame trên map sạch ngay cả điều kiện gốc (map A: 1-9%); bank không suy giảm thì abstain toàn bộ khi có marine snow. Chọn **v2 + suy giảm mức 1** làm ứng viên detector; v1 vẫn là mặc định dashboard tới khi chạy live và nghiệm thu.
- So với phần 2 (hình học v1): tổng báo nhầm v2 19 → 2, recall 13/21 → 17/21. Sửa hình học có tác dụng lớn hơn đổi backbone ở lượt này.
- **Live v2** (`auv_dashboard/output/session_20261013_091452_126695/`, `--v2-model detector_v2_dino_s2_aug_g2`, map A, điều kiện gốc): route 359/359, 4 cảnh báo. Tick 396 `A_pipe_front_1` (cách nhãn 0,20 m), 627 `A_pipe_front_2` (0,04 m), 3228 `A_pier_0_1` (0,02 m): **3/3 vết, định vị sát hơn hẳn** live v1.4 (0,12-0,37 m với hình học v1). Tick 6954 trụ 1 (z -6,95) là **báo nhầm** trên một vệt sẫm dọc của vân bê tông (đã xem ảnh). `patchcore_frames.jsonl`: 2.148 frame, median 256 ms (p90 317 ms) khi chạy cùng Unreal; 34 frame `diffuse_anomaly` (32 ở ống trước) đều do tiêu chí > 6 vùng (7-16 vùng nhỏ, phân tán 0,1-1%): giới hạn 6 vùng đặt cho v1, bản đồ điểm v2 mịn hơn nên nhiều vùng nhỏ hơn; cần xem lại.
- Vẫn là tập phát triển 2 capture đã dùng cho nhiều quyết định; P7 phải kiểm trên heldout mới.

## Kết quả P4 phần 4: tập phát triển 6 capture và lề ở mép ảnh (2026-10-13)

Tập phát triển mở rộng thêm 4 capture heldout (map A seed 3, 4; map sạch seed 5, 6), tổng 3 capture map A + 3 capture map sạch, 7 điều kiện, 42 lượt mỗi detector. `dino_surface_b` = v2 + suy giảm mức 1 với lề 24 px cả ở mép ảnh (calibration giữ nguyên, bảo thủ). Kết quả: `auv_inspection/output/benchmark_p4_dino_g2/` (vết map A trên 9, tổng báo nhầm, lượt tệ nhất/100 m, tỷ lệ abstain trung bình).

| Điều kiện | v1.4 | v2 | **v2 + lề mép ảnh** |
|---|---|---|---|
| Gốc | 5/9, 9 (2,95), 0% | 9/9, 9 (2,72), 7% | **9/9, 3 (0,61), 5%** |
| Độ đục 2 | 6/9, 0, 0% | 9/9, 10 (2,46), 10% | **9/9, 2 (0,98), 7%** |
| Độ đục 4 | 5/9, 2 (0,49), 0% | 8/9, 8 (0,98), 12% | 8/9, 13 (1,81), 9% |
| Marine snow 3 | 7/9, **190** (19,64), 29% | 3/9, 6 (1,81), 34% | 3/9, **0**, 33% |
| Marine snow 5 | 1/9, 18 (3,35), 85% | 3/9, 3 (0,91), 39% | 3/9, 1 (0,47), 37% |
| Đèn yếu 4 | 5/9, 7 (2,46), 0% | 9/9, 6 (1,23), 8% | **9/9, 1 (0,61), 7%** |
| Mờ chuyển động 3 | 3/9, 10 (2,87), 0% | 7/9, 0, 6% | **7/9, 0, 4%** |
| **Tổng** | 32/63 (51%), 236 | 48/63 (76%), 42 | **48/63 (76%), 20** |

- **Hai capture cũ đánh giá quá cao v2:** trên chúng v2 có 17/21 vết, 2 báo nhầm; trên 4 capture mới v2 thêm 40 báo nhầm. Báo nhầm trên capture mới tập trung ở dải ≤ 24 px quanh mép ảnh (mép dưới trên mặt trụ ở xa, nơi đèn tắt dần) và chân trụ.
- **Lề ở mép ảnh** giảm báo nhầm v2 từ 42 xuống 20 mà không mất vết nào; 2 capture sạch mới có 0 báo nhầm. Chọn làm mặc định của v2 trong dashboard.
- **Recall ngoài marine snow 42/45 (93%)**, vượt mục tiêu 90%; marine snow 3 và 5 chỉ 3/9 mỗi mức. Tổng 76% chưa đạt.
- **Báo nhầm còn lại chủ yếu ở độ đục 4** (13/20); trừ độ đục 4, mọi lượt ≤ 0,98/100 m. Giả thuyết "vùng ảnh hưởng vòng bích rộng hơn 0,5 m khi nước đục" đã bị bác bỏ (xem nhật ký quyết định 2026-10-13): ô vượt ngưỡng ở độ đục 4 rải dọc thân ống, tức lệch miền do nước đục.
- **Live v2** (lượt `session_20261013_091452_126695`, chưa có lề mép ảnh): 3/3 vết, 1 báo nhầm.

## Kết quả P4.3: NFAD và Mahalanobis (2026-10-14, tập phát triển 6 capture)

Cả hai là biến đổi tuyến tính trên bank của `detector_v2_dino_s2_aug_g2` (không dựng lại bank), có lề mép ảnh, calibration ngưỡng pixel và ngưỡng tầng riêng trên 3 capture calibration. NFAD: 8 hướng nhiễu từ chênh lệch token giữa frame capture bank và chính frame đó suy giảm mức 1 (6 yếu tố, 100 frame mỗi capture), giải thích 47-51% phương sai nhiễu theo nhóm. Mahalanobis: shrinkage 0,1. Kết quả: `auv_inspection/output/benchmark_p4_dino_g2/` (vết map A, báo nhầm, lượt tệ nhất/100 m).

| Điều kiện | v2 + lề mép ảnh | NFAD k = 8 | Mahalanobis |
|---|---|---|---|
| Gốc | 9/9, 3 (0,61) | 9/9, 5 (1,42) | 9/9, 0 |
| Độ đục 2 | 9/9, 2 (0,98) | 9/9, 5 (1,91) | 9/9, 3 (0,98) |
| Độ đục 4 | 8/9, 13 (1,81) | 8/9, **0** | 6/9, 0 |
| Marine snow 3 | 3/9, 0 | **8/9**, 16 (2,72) | 3/9, 0 |
| Marine snow 5 | 3/9, 1 (0,47) | **8/9**, 3 (0,98) | 0/9, 1 (0,45) |
| Đèn yếu 4 | 9/9, 1 (0,61) | 9/9, 1 (0,48) | 9/9, 1 (0,48) |
| Mờ chuyển động 3 | **7/9**, 0 | 4/9, 0 | 4/9, 0 |
| **Tổng** | 48/63 (76%), 20 | **55/63 (87%)**, 30 | 40/63 (63%), **5** |

- **NFAD** tăng recall mạnh ở marine snow (3/9 → 8/9 mỗi mức) và bỏ hết báo nhầm độ đục 4 (13 → 0), nhưng thêm báo nhầm ở marine snow 3 (0 → 16), gốc và độ đục 2, và **mất vết khi mờ chuyển động** (7/9 → 4/9). Đúng cảnh báo ShiftSplit-AD: một phần tín hiệu vết nứt mảnh (mờ làm vết giống thay đổi môi trường) nằm trong các hướng bị loại.
- **Mahalanobis** là biến thể duy nhất đạt **≤ 1 báo nhầm/100 m ở cả 42 lượt** (5 báo nhầm), nhưng recall giảm còn 63% (marine snow 5: 0/9, mờ: 4/9, độ đục 4: 6/9).
- Không biến thể nào đạt đồng thời cả hai tiêu chí; mỗi kỹ thuật đánh đổi một phía. Chưa đổi mặc định (dashboard vẫn v2 + lề mép ảnh).
- Thời gian xử lý trung vị: 256-326 ms/frame cho cả ba (phép biến đổi không làm chậm đáng kể).
- **NFAD rồi Mahalanobis** (`dino_nfmaha_b`: phép chiếu của `nfad8`, rồi làm trắng trên bank đã chiếu): 42/63 vết (67%), 17 báo nhầm (lượt tệ nhất 1,47/100 m). Không gộp được ưu điểm: giữ phần lớn recall marine snow 3 của NFAD (7/9) nhưng mất hết vết ở marine snow 5 như Mahalanobis (0/9) và tệ nhất khi mờ (2/9).
- **Kết luận P4.3:** không biến thể nào trội trên mọi mặt; giữ **v2 + lề mép ảnh** làm ứng viên chính (48/63, 20 báo nhầm, cân bằng nhất, mờ 7/9). NFAD ghi nhận là lựa chọn khi vùng nước nhiều marine snow (8/9 mỗi mức). SPARC chưa thử (cần frame sạch đã xác nhận tại hiện trường).

## Kết quả P6.1: vùng bằng chứng mơ hồ (2026-10-14, tập phát triển 6 capture)

Ứng viên `dino_surface_b`, 42 lượt, `auv_inspection/output/benchmark_p6_ambiguity/` (mục `ambiguity` trong mỗi kết quả). Vùng mơ hồ = ô chưa báo có 1-2 hit, gộp trong 0,6 m, đếm cuối lượt.

| Điều kiện | Vùng ≥ 1 hit /100 m | Vùng ≥ 2 hit /100 m | Vết sót | Sót trong vùng ≥ 1 hit | Sót trong vùng ≥ 2 hit |
|---|---|---|---|---|---|
| Gốc | 18,3 | 3,4 | 0 | 0 | 0 |
| Độ đục 2 | 20,8 | 5,0 | 0 | 0 | 0 |
| Độ đục 4 | 18,5 | 5,9 | 1 | 1 | 1 |
| Marine snow 3 | 22,0 | 1,3 | 6 | 1 | 0 |
| Marine snow 5 | 22,1 | 3,2 | 6 | 0 | 0 |
| Đèn yếu 4 | 16,9 | 2,3 | 0 | 0 | 0 |
| Mờ chuyển động 3 | 12,4 | 2,1 | 2 | 2 | 1 |
| **Tổng** | **18,7** | **3,3** | **15** | **4** | **2** |

- **Chi phí:** quay lại mọi vùng ≥ 1 hit là khoảng 19 lần/100 m; chỉ vùng ≥ 2 hit là 3,3 lần/100 m.
- **Lợi ích tối đa nhỏ:** 4/15 vết sót nằm trong vùng mơ hồ, 2/15 trong vùng ≥ 2 hit. Marine snow chiếm 12/15 vết sót nhưng ở đó vết gần như không đạt hit nào (cổng lan tỏa abstain 33-37% frame, điểm không qua ngưỡng): bằng chứng vắng mặt chứ không mơ hồ.
- **Lợi ích vật lý của việc tiến gần không đo được** trong hệ thống hiện tại: suy giảm được áp offline lên ảnh, không phụ thuộc khoảng cách, và Unreal của dự án không có độ đục/marine snow (`water_fog` cần tag `WaterPPV`).
- **Quyết định:** dừng P6 ở mức đo (không viết logic chèn route), chuyển P7. Làm lại P6 khi có mô phỏng độ đục/marine snow phụ thuộc khoảng cách, với quy tắc vùng ≥ 2 hit và ngân sách khoảng 3 lần/100 m.
- **Live v2 + lề mép ảnh** (`auv_dashboard/output/session_20261014_161937_404843/`, map A, điều kiện gốc): route 359/359, **3/3 vết, 0 báo nhầm** (tick 399 `A_pipe_front_1` 0,20 m; 633 `A_pipe_front_2` 0,04 m; 3237 `A_pier_0_1` 0,07 m); báo nhầm vân bê tông của lượt live v2 trước không còn. 32 frame `diffuse_anomaly` do tiêu chí > 6 vùng. Median 321 ms/frame (p90 506 ms), chạy đồng thời với benchmark P6.1 trên cùng GPU nên không phải tốc độ đơn lẻ.

## Kết quả P7: nghiệm thu offline trên dữ liệu heldout mới (2026-10-15)

Theo đúng đăng ký trước (`robustness/acceptance_preregistration.json`, code `2114d6a`, SHA256 artifact khớp, nhãn map B khóa `ecedd4f0...` trước khi chấm). 6 capture seed 101-106 (map A 101/102, map sạch 103/104, map B 105/106), 7 điều kiện, 42 lượt mỗi detector, `auv_inspection/output/benchmark_p7_acceptance/`, báo cáo `acceptance_report.json` (`acceptance.py`).

| Tiêu chí (gộp mọi điều kiện) | Ngưỡng | Ứng viên `dino_surface_b` | Đối chứng `patchcore_surface` |
|---|---|---|---|
| Recall theo vết vật lý | ≥ 90% | **72,3%** (81/112; bootstrap 95%: 63,5-79,4%) **không đạt** | 58,9% (66/112; 49,4-68,8%) không đạt |
| Báo nhầm /100 m | ≤ 1 | **0,345** (30 báo nhầm trên 8,69 km; 0,19-0,56) đạt | 2,89 (1,96-3,88) không đạt |
| FPR mức ô (cận trên Wilson 95%) | ≤ 5% | **0,031%** (138/523.525 ô) đạt | 0,150% đạt |
| **Kết luận** | | **Không đạt nghiệm thu** | Không đạt |

Recall ứng viên theo điều kiện: gốc 15/16, độ đục 2 15/16, độ đục 4 15/16, đèn yếu 4 16/16, mờ chuyển động 3 12/16, **marine snow 3 4/16, marine snow 5 4/16** (cổng lan tỏa abstain 33-36% frame). Theo map: A 33/42, B 48/70 (seed 105 27/35, seed 106 21/35).

Phân tích sau (không thay đổi kết luận, không dùng để chỉnh gì trên bộ dữ liệu này):
- Ngoài marine snow ứng viên tìm 73/80 vết (91%), gần với tập phát triển (42/45); 24/31 vết sót nằm trong marine snow. Đây là giới hạn đã biết từ P4/P6.
- Map B (lỗ thủng, chưa có trong dev) không sụp: 48/70. Vết sót ngoài marine snow đều ở seed 106 (route trụ gần 2,43 m): `B_pipe_front_hole_large` ở gốc và độ đục 2, cả 4 vết ống/trụ ở mờ chuyển động 3.
- 17/30 báo nhầm của ứng viên nằm ở chân trụ (z < -10 m), lặp lại theo điều kiện trên cùng vị trí (ví dụ (10,9; -7,2; -10,4) ở 4 điều kiện seed 101).
- Ứng viên tốt hơn đối chứng ở cả ba chỉ số; đối chứng có 154 báo nhầm riêng ở marine snow 3.

Theo quy tắc đã đăng ký, không đổi ngưỡng, bank, cổng hay nhãn sau khi xem kết quả; mọi cải tiến (marine snow, chân trụ) phải qua đăng ký mới và dữ liệu heldout mới.

**Live P7 (2026-10-15, dashboard mặc định v2 + lề mép ảnh, điều kiện gốc, route danh định 359/359):**
- Map A (`auv_dashboard/output/session_20261015_103902_679289/`): **3/3 vết, 0 báo nhầm** (tick 399 `A_pipe_front_1` 0,33 m; 645 `A_pipe_front_2` 0,17 m; 3276 `A_pier_0_1` 0,07 m).
- Map B (`session_20261015_105712_694396/`, world `AUVInspection_PatchCoreB_20260926_v3`), chấm theo quy tắc của harness (tâm box qua `locate_box`, bán kính nhãn đã khóa): **4/5 vết, 2 báo nhầm**. Khớp: tick 582 `B_pipe_front_crack_1` 0,27 m; 888 `B_pipe_front_hole_small` 0,10 m; 1158 `B_pipe_front_crack_2` 0,08 m; 1458 `B_pipe_front_hole_large` 0,25 m. Không khớp: tick 2352 `pipe_back` mép vòng bích x ≈ 9,2, ảnh không có vết (báo nhầm thật); tick 7596 `pier_1` tâm box cách `B_pier_1_crack` 0,41 m > 0,35 m, nhưng ảnh annotated cho thấy box nằm trên chính vết nứt và ô bề mặt của cảnh báo (u, v) = (-8,05; 1,15) cách đoạn nhãn khoảng 0,14 m. Theo quy tắc, ghi là 1 vết sót + 1 báo nhầm; theo xem ảnh là 5/5 vết, 1 báo nhầm. Nhãn không sửa.
- Thời gian xử lý median 296 ms (map A) / 275 ms (map B), p90 ≈ 316 ms; 79 / 94 frame `diffuse_anomaly`.
- Tiêu chí live của P7 (ít nhất 1 cảnh báo đi trọn vòng) đạt trên cả hai map; không thay đổi kết luận offline (không đạt recall).

## Kết quả P8.1: chẩn đoán lỗi của ứng viên P7 (2026-10-15, offline, không sửa gì)

Tập phát triển P8 = seed 1-6 cũ + seed 101-106 của P7 (đã xem nên không còn là heldout). Kết quả và script: `auv_inspection/output/p8_diagnosis/` (`defect_views.jsonl`, `p8_diag_views.py`, bảng ảnh báo nhầm `*_false_alerts_*.jpg`, `p8_fa_sheet.py`).

**Marine snow: vết vẫn có bằng chứng, cổng lan tỏa bỏ cả frame.** Mỗi lượt nhìn vào vết (7 capture có vết, 909 lượt nhìn × điều kiện) được chấm bằng `dino_surface_b` và ghi quyết định của cổng, ô vết tốt nhất (điểm, điểm chuẩn hóa, hai ngưỡng), median frame và tỷ lệ khối của vết bị hạt che (ảnh suy giảm trừ ảnh gốc).

| Điều kiện | Hit | Bị cổng chặn | Hit nếu bỏ cổng | Tiêu chí cổng kích hoạt | Hạt che ô vết (median) |
|---|---|---|---|---|---|
| Gốc | 240 | 25 | 265/274 | > 25% một vùng: 14, > 6 vùng: 10 | 0 |
| Marine snow 3 | 85 | 185 | 265/274 | > 6 vùng: 175 (median 14 vùng/frame) | 3% |
| Marine snow 5 | 78 | 188 | 259/274 | > 6 vùng: 183 (median 25,5) | 21% |

- Điểm của ô vết gần như không đổi dưới marine snow (tỷ lệ tuyệt đối 1,03); median frame tăng 1,15-1,77 lần nên điểm chuẩn hóa giảm, nhưng chỉ 1-5 lượt rớt vì ngưỡng tầng. **154/155 (mức 3) và 160/165 (mức 5) lượt mất hit là do cổng lan tỏa**, gần như toàn bộ qua tiêu chí > 6 vùng: hạt tạo nhiều vùng nhỏ vượt ngưỡng (frame gốc median 2 vùng).
- Ở điều kiện gốc, tiêu chí "một vùng > 25%" chặn chính vết lớn: 15/25 lượt bị chặn là `B_pipe_front_hole_large` (giải thích lỗ lớn bị sót ở seed 106 khi route đi gần).

**Báo nhầm: ba nhóm.**
- **Mặt đáy trong ROI trụ (17/30 báo nhầm P7):** `geometry.PIER_Z_RANGE` = (-12,0; 1,6) nhưng chân trụ gặp đáy ở z ≈ -10,4 (đo trên ảnh seed 101 tick 8329: -10,36 đến -10,45; hộp vật cản trong `inspection_route.py` cũng dừng ở -10,4). Mọi báo nhầm chân trụ nằm ở z -10,41 đến -10,55, ở mép dưới ảnh, tức mặt đáy và đường tiếp giáp bị coi là mặt trụ. Chỉ thấy ở khoảng cách lớn (2,7-3,0 m, seed 101 bán kính 3,59 m) vì gần hơn thì phần này ít lọt vào ảnh. Là lỗi hình học, không phải lỗi detector.
- **Rìa tối của quầng đèn trên ống:** phần lớn báo nhầm của tập phát triển cũ (12/20 ở độ đục 4, thêm đèn yếu 4), box nằm ở vùng tối hai bên hoặc mép dưới ống, nơi tín hiệu thấp.
- **Mép vòng bích mặt sau ống:** một báo nhầm live trên map B.

**Hướng P8.2 rút ra:** (1) cổng lan tỏa không đếm vùng cỡ hạt (hoặc che hạt trước khi đếm) và không chặn một vùng lớn đặc; quy tắc bề mặt k = 3 lượt nhìn đã loại nhiễu ngẫu nhiên giữa các frame, cần đo báo nhầm trên tập phát triển; (2) sửa giới hạn dưới của trụ về mặt đáy rồi calibrate lại ngưỡng; (3) sau đó mới xét mặt nạ tín hiệu thấp cho rìa quầng đèn.

## Kết quả P8.2 phần 1: cổng P8 và giới hạn dưới của trụ (2026-10-15, tập phát triển 12 capture)

12 capture (seed 1-6, 101-106) × 7 điều kiện = 84 lượt mỗi detector; `auv_inspection/output/benchmark_p8_dev/` (`dino_surface_b` chép từ P6/P7 vì code chấm điểm của nó không đổi, `dino_surface_bg`), `benchmark_p8_dev_floor/` (`dino_floor_bg`); so sánh bằng `output/p8_diagnosis/p8_compare.py`.

| Detector | Recall | Báo nhầm | /100 m | FPR ô | Frame bị cổng |
|---|---|---|---|---|---|
| `dino_surface_b` (ứng viên P7) | 129/175 (73,7%) | 50 | 0,29 | 0,026% | 14,7% |
| `dino_surface_bg` (cổng P8) | 167/175 (95,4%) | 967 | 5,63 | 0,68% | 2,4% |
| `dino_floor_bg` (cổng P8 + giới hạn trụ) | 166/175 (94,9%) | 950 | 5,54 | 0,67% | 2,4% |

| Điều kiện | b: recall / báo nhầm | bg: recall / báo nhầm |
|---|---|---|
| Gốc | 24/25 / 11 | 25/25 / 20 |
| Độ đục 2 / 4 | 24/25 / 7; 23/25 / 17 | 25/25 / 32; 24/25 / 57 |
| Marine snow 3 / 5 | 7/25 / 6; 7/25 / 4 | 25/25 / 472; 24/25 / 333 |
| Đèn yếu 4 | 25/25 / 5 | 25/25 / 32 |
| Mờ chuyển động 3 | 19/25 / 0 | 19/25 / 21 |

- **Cổng P8 không dùng được như vậy.** Nó lấy lại gần hết vết dưới marine snow (14 → 49/50) và lỗ lớn, nhưng báo nhầm tăng 19 lần (nhiều nhất ở marine snow, 805 trên thân ống, và cả ở mọi điều kiện khác). Cổng cũ hóa ra đang làm phần lớn việc chặn báo nhầm: các frame bị nó bỏ là các frame mà quy tắc bề mặt gom được hit giả qua nhiều lượt nhìn. Box báo nhầm dưới marine snow không chứa nhiều hạt hơn mức trung bình của frame (1,5% so với 1,6% pixel), nên báo nhầm không nằm trên hạt mà là do điểm của cả frame bị đẩy lên.
- **Giới hạn dưới của trụ làm đúng việc của nó:** báo nhầm "trụ dưới -10 m" 17 → 0, recall không đổi (166 so với 167, chênh 1 lượt mờ chuyển động). Có thể áp dụng độc lập với cổng.
- Vết sót ngoài marine snow gần như chỉ còn mờ chuyển động 3 (6-7 lượt).

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
| 2026-10-09 | Live P2 xác nhận nguồn báo nhầm chính là **biên ROI** (đầu ống, mép ống khi nhìn xiên): ROI giới hạn tâm đặc trưng nhưng trường nhìn của đặc trưng rộng hơn. Thêm vào **P3** một lề chấm điểm bên trong ROI theo trường nhìn của đặc trưng, đánh giá trên tập phát triển trước. Báo trùng cùng một vết (hai vị trí cách 2,08 m) để **P5** gộp theo tọa độ bề mặt |
| 2026-10-15 | **Mở P8** (người dùng duyệt kế hoạch): seed 101-106 chuyển vào tập phát triển; P8.1 chẩn đoán trước khi chọn phương án. Kết quả: mất recall dưới marine snow là do cổng lan tỏa (tiêu chí > 6 vùng), không phải điểm của vết; 17/30 báo nhầm P7 là mặt đáy lọt vào ROI trụ vì `PIER_Z_RANGE` dưới mặt đáy. Heldout P8 cần seed mới; map C đề xuất, chờ người dùng quyết |
| 2026-10-15 | **Cổng phê duyệt kiểm hash code (D11)**: `approval_gate.SCORING_CODE` (live_service và 16 module project nó nạp), hash sau khi đổi CRLF thành LF. Mặc định v2 cần `code_sha256` trong `acceptance_preregistration.json` (lấy từ chính commit đăng ký `2114d6a`, trùng working tree); cổng v1 cần `code_sha256` trong báo cáo đánh giá B. Báo cáo `patchcore_evaluation_B_v1.json` (2026-09-26) không có hash code, và code chấm điểm đã đổi nhiều từ đó (quy tắc bề mặt, hình học v2), nên cổng v1 không còn tự chọn PatchCore v1 (giao diện mặc định Classical khi tắt v2; vẫn chọn PatchCore bằng tay được). Không sửa file đánh giá hay `patchcore_artifacts/` |
| 2026-10-15 | **Dashboard mặc định dùng v2 + lề mép ảnh** (người dùng duyệt): dù không đạt nghiệm thu, ứng viên tốt hơn v1.4 ở cả ba chỉ số trên dữ liệu heldout (recall 72,3% so với 58,9%, 0,345 so với 2,89 báo nhầm/100 m). Chỉ bật khi mọi file của ứng viên còn khớp SHA256 trong `acceptance_preregistration.json`; nếu không, quay về PatchCore v1 sau cổng phê duyệt cũ; `--v1` chọn v1. Thêm `--world` để chạy live trên map B |
| 2026-10-15 | **Kết quả nghiệm thu P7 offline: ứng viên v2 + lề mép ảnh không đạt** vì recall 72,3% (bootstrap 63,5-79,4%) < 90%; báo nhầm 0,345/100 m và FPR mức ô 0,031% đạt. Đối chứng v1.4: 58,9%, 2,89/100 m. Thiếu hụt chủ yếu ở marine snow (8/32). Giữ nguyên kết luận theo đăng ký; không chỉnh gì trên dữ liệu heldout này |
| 2026-10-14 | **Khóa nhãn map B** (`robustness/inventories/map_B.json`, SHA256 `ecedd4f0...`, ghi vào `acceptance_preregistration.json` mục `map_B_labels_locked`): 5 vết (2 nứt và 2 lỗ trên mặt trước ống, 1 nứt mặt trước trụ 1), vẽ chỉ từ ảnh seed 105 (mỗi vết 2 frame, lệch ≤ 0,04 m), kiểm trên seed 106, người dùng duyệt bảng ảnh trước khi detector nào chạy trên map B. Vị trí đặt decal trong script tạo map chỉ dùng để đối chiếu |
| 2026-10-14 | **Đăng ký trước P7** (`auv_inspection/robustness/acceptance_preregistration.json`, commit code `2114d6a`, người dùng duyệt kế hoạch): ứng viên `dino_surface_b` (v2 + lề mép ảnh), đối chứng `patchcore_surface` (v1.4), SHA256 của mọi bank, ngưỡng, calibration, hình học và nhãn map A; dữ liệu heldout mới seed 101-102 (map A), 103-104 (map sạch), 105-106 (map B, chưa ai xem); 7 điều kiện, seed suy giảm 0. Tiêu chí: recall theo vết vật lý ≥ 90%, ≤ 1 báo nhầm/100 m (gộp mọi điều kiện), **FPR mức ô** ≤ 5% theo cận trên Wilson 95% (ô bề mặt sạch đã đánh giá phát cảnh báo; tỷ lệ frame có ứng viên không phải cảnh báo nên không dùng). Nhãn map B vẽ chỉ từ ảnh capture, người dùng duyệt và khóa trước khi chấm. Không đổi gì sau đăng ký; mọi thay đổi cần đăng ký và dữ liệu heldout mới |
| 2026-10-14 | **Dừng P6 sau P6.1** (đo offline, không viết logic chèn route). Vết bị sót trên tập phát triển chủ yếu ở marine snow, nơi bằng chứng vắng mặt chứ không mơ hồ; lợi ích tối đa của quay lại theo vùng mơ hồ là 2-4/15 vết; lợi ích vật lý của tiến gần (cột nước ngắn hơn) không mô phỏng được vì suy giảm offline không phụ thuộc khoảng cách và Unreal không có độ đục/marine snow. Chuyển P7 |
| 2026-10-14 | Kết thúc P4: ứng viên detector là **v2 (DINOv2 + bank suy giảm mức 1) + lề 24 px cả ở mép ảnh**, cân bằng nhất trên tập phát triển 6 capture (48/63 vết, 20 báo nhầm). Ablation P4.3: NFAD tăng recall marine snow nhưng mất vết khi mờ và thêm báo nhầm; Mahalanobis giảm báo nhầm nhưng mất recall; kết hợp hai cái kém cả ứng viên. Không thử thêm biến thể trên cùng tập phát triển để tránh khớp quá; P7 kiểm ứng viên trên heldout mới |
| 2026-10-13 | **Giữ dải mối nối ±0,5 m** (không nới theo báo nhầm độ đục 4). Đo số ô sạch sẽ báo nếu áp ngưỡng thân ống, theo khoảng cách tới vòng bích gần nhất, với v2 + lề mép ảnh: 3 capture calibration gần như 0 ở mọi khoảng cách; tập phát triển điều kiện gốc 39 ô trong 0-0,2 m (đã nằm trong dải và bị ngưỡng mối nối chặn), 1 ô ở 0,3-0,5 m, 1 ô ngoài 1 m; độ đục 4: 31 ô trong 0-0,2 m, 4 ở 0,3-0,5 m, 15 ở 0,5-1,0 m, 7 ngoài 1 m. Ở độ đục 4 các ô rải dọc thân ống chứ không dồn ngay ngoài mép dải, nên nguyên nhân là ngoại hình thân ống thay đổi khi nước đục (lệch miền), không phải vòng bích; nới dải sẽ là tinh chỉnh theo tập phát triển mà ít tác dụng. Log: `auv_inspection/output/joint_profile_v2.log` |
| 2026-10-13 | Tập phát triển mở rộng 4 capture heldout (map A seed 3, 4; map sạch seed 5, 6), người dùng chạy. v2 dùng **lề 24 px cả ở mép ảnh** (`--border-margin`, mặc định tắt cho v1): báo nhầm v2 trên các capture mới tập trung sát mép ảnh; trên 6 capture lề này giảm báo nhầm 42 → 20 mà không mất vết. Chọn sau khi đo trên tập phát triển, P7 kiểm lại |
| 2026-10-12 | **Hình học v2** (người dùng duyệt): `camera_forward_m` = 0,41 m, `camera_up_m` = 0,09 m cố định theo vị trí `CameraLeftSocket` so với `IMUSocket` (PoseSensor) đo trên hình socket của HoveringAUV trong tài liệu HoloOcean, tỷ lệ lấy từ vị trí thruster trong client (±0,25 m, ±0,22 m); 5 tham số còn lại fit lại trên 552 mask như P2. Lý do: cùng vết nứt trụ nhìn từ hai tầng lệch 0,35 m với v1; dò từng tham số cho thấy chỉ offset tiến (khoảng 0,3 m) hoặc nửa cạnh trụ 1,2 m (mâu thuẫn silhouette) khử được, còn pitch và offset đứng thì không. v2: lệch hai lượt 0,030 m, hai lượt vết ống 0,015 m (v1: 0,057), pitch 0,005° (AUV luôn cân bằng theo roll/pitch ghi trong capture; v1 3,92° là bù sai), trục ống -10,294 (hằng số route -10,3); IoU kiểm tra trên mask và mask ORB tương đương v1 (mask một khoảng cách không phân biệt được). Nhãn map A tính lại từ đúng nguồn ảnh cũ với v2; mọi calibration bề mặt, bank v2 và benchmark P4 làm lại; `geometry_v1.json`, `surface_v1.json` và model v2 cũ giữ để đối chiếu |
| 2026-10-12 | P4: **cổng lan tỏa đếm hit của quy tắc bề mặt** (điểm ≥ ngưỡng pixel AND điểm ≥ ngưỡng tầng thấp nhất của nhóm × median frame) khi có quy tắc bề mặt. Lý do: ngưỡng pixel v2 (calibrate theo ô) thấp ở mức pixel, cổng chỉ dùng ngưỡng tuyệt đối abstain 19-52% frame của v2 ở điều kiện gốc và độ đục 2 (lưu `benchmark_p4_dino_abs_gate_superseded/`). Hệ quả với v1.4: ở mờ chuyển động 3 abstain 14% → 0,5% và có 3 báo nhầm (trước là 0). `calibrate_surface.py` từ nay chấm mọi frame sạch, không qua cổng (cổng phụ thuộc chính ngưỡng được calibrate; thêm dữ liệu chỉ làm ngưỡng cao hơn hoặc bằng); `surface_v1.json` của v1 không đổi vì không frame calibration nào bị abstain |
| 2026-10-12 | P4 bắt đầu, người dùng duyệt: (1) tải trọng số `timm/vit_small_patch14_dinov2.lvd142m` (85 MB, Hugging Face); (2) 4 capture **bank** sạch mới, profile train, seed 21-24 (`--dataset-role train`); (3) **ranh giới suy giảm chốt trước**: bank chỉ thêm suy giảm offline mức 1 (mỗi frame một bản, một yếu tố ngẫu nhiên), benchmark dùng mức 2-5 nên vẫn là điều kiện chưa thấy; (4) nhãn `A_pipe_front_2` đổi từ điểm sang đoạn. Phân chia dữ liệu: bank = seed 21-24 train; calibration ngưỡng = seed 11-13; phát triển = heldout seed 1-2; nghiệm thu P7 = heldout mới + map B. v2 có ngưỡng pixel riêng (conformal trên capture calibration, cùng thống kê với quy tắc bề mặt) vì không gian đặc trưng mới; model, ngưỡng v1 và `patchcore_artifacts/` giữ nguyên |
| 2026-10-12 | Sửa nhãn `A_pipe_front_2` (người dùng duyệt): từ điểm (-7,66; 0,5; -10,3) bán kính 0,6 m sang đoạn (-7,07; 0,533; -10,6) → (-7,93; 0,50; -10,375) bán kính 0,35 m, vẽ theo hai đầu mút vết nứt ở frame tick 463 và 478 của capture phát triển map A (hai lượt nhìn lệch ≤ 0,07 m). Nguyên nhân: vết dài khoảng 0,9 m, cảnh báo trên đầu trái vết bị tính là báo nhầm. Benchmark trước ngày này dùng nhãn cũ; so sánh P4 chạy lại baseline với nhãn mới |
| 2026-10-12 | Sửa cổng `diffuse_anomaly` (P3) sau live P5: "lan tỏa" đo bằng **độ phân tán** = tỷ lệ ROI vượt ngưỡng **ngoài vùng liên thông lớn nhất** > 5%, hoặc > 6 vùng ứng viên, hoặc **một vùng > 25% ROI** (bất thường diện rộng, vẫn báo operator). Lý do: live P5 abstain 12 frame khi vết `A_pipe_front_2` lớn ở gần (5,6-8,3% ROI trong 1-3 vùng). Đo trên tập phát triển trước khi đổi: frame có vết ≤ 2,4% ngoài vùng lớn nhất (tổng tới 5,0% vì lề 24 px làm ROI nhỏ đi), vùng lớn nhất ≤ 7%; frame mờ/marine snow 5 có mảng liền 44-57% nên cần điều kiện vùng đơn lẻ; 25% chọn gấp khoảng 3 lần vết lớn nhất đã thấy (8,3%). Không cần calibrate lại quy tắc bề mặt: không frame calibration nào bị abstain ở cả hai cổng |
| 2026-10-12 | P5: **thay SPRT/e-value bằng quy tắc k = 3 lượt nhìn trên ô bề mặt 10 cm** (camera dời ≥ 0,3 m giữa hai lượt được tính, gộp cảnh báo trong 0,6 m). Lý do: SPRT cần phân phối p-value của hư hại (tham số `a`) mà không có dữ liệu để ước lượng; quy tắc k-trên-n là dạng trực tuyến của "lượt cao thứ k ≥ ngưỡng", calibrate được chỉ bằng dữ liệu sạch. Đo trên tập phát triển trước khi chọn: đếm hit nhị phân ở ngưỡng cũ không tách được vết với marine snow (834 ô sạch có ≥ 3 hit), median/lượt cao thứ k của điểm thô bị dịch chuyển toàn cục và vòng bích lấn át |
| 2026-10-12 | P5: **chuẩn hóa điểm ô theo median điểm của frame** và **tầng Mondrian thân ống / mối nối / mặt trụ**. Ô sạch điểm cao nhất quán nằm ở vòng bích mỗi 3 m (xác nhận bằng ảnh tại x = -9, 3, 15) và mặt trụ gần mặt nước; mối nối được hiệu chỉnh riêng thay vì bỏ (vết ở mối nối là hư hại thật). Dải mối nối ±0,5 m theo đo ô sạch quanh vòng bích ở 2,77 m |
| 2026-10-12 | P5: **hit = ngưỡng pixel đã khóa AND ngưỡng tương đối theo tầng, hai ngưỡng calibrate riêng.** Chỉ ngưỡng tương đối: vòng bích ở 2,77 m (ngoài khoảng train 1,8-2,4 m) vượt ngưỡng mối nối, 10 báo nhầm map A gốc (lưu `benchmark_p5_surface_norm_only_superseded/`). Calibrate thống kê kết hợp: không ô sạch nào đạt 3 hit theo ngưỡng pixel nên mọi ngưỡng tầng = 0, quy tắc lùi về chỉ ngưỡng pixel (mô phỏng 11-32 báo nhầm khi độ đục/mờ; lưu `benchmark_p5_surface_abs_degenerate_superseded/`). Mỗi ngưỡng giữ mức α riêng nên AND cũng giữ |
| 2026-10-12 | P5: dashboard bỏ **khóa re-arm 2 m** của runtime khi dùng quy tắc bề mặt (người dùng đồng ý), bằng `patch.object(run_inspection, "CRACK_REARM_DISTANCE_M", 0.0)` trong bridge, không sửa `run_inspection.py`. Khóa này che cảnh báo vết thật đứng sau một báo nhầm trong vòng 2 m; quy tắc bề mặt đã gộp trùng theo vùng. Harness mô phỏng giống vậy (detector khai `rearm_distance_m`) |
| 2026-10-12 | P5: 3 capture **calibration** sạch mới (map sạch v3, profile train seed 11/12/13) dành riêng cho calibration bề mặt. Map B (`AUVInspection_PatchCoreB_20260926_v3`, 5 vết) **giữ chưa xem** cho nghiệm thu P7 |
| 2026-10-09 | P3: **bỏ cổng chất lượng theo phân vị** (mục 3.1 ban đầu). Ngưỡng phân vị 1/99 của frame sạch mô phỏng loại 65-100% frame ngay ở mức suy giảm nhẹ nhất (độ đục, đèn yếu, mờ), vì frame sạch gần như tất định nên khoảng "bình thường" rất hẹp; cổng biến thành bộ phát hiện ngoài phân phối. Nhiễu cảm biến còn kích hoạt bộ đếm hạt trong khi marine snow 3 phần lớn không. Thay bằng: (a) **lề chấm điểm 24 px** theo trường nhìn của descriptor (lân cận 3×3 layer2 stride 8 + layer3 stride 16), chọn trước khi đo; (b) **cổng `diffuse_anomaly`**: abstain khi hơn 5% ROI vượt ngưỡng hoặc hơn 6 vùng ứng viên. Giới hạn chọn từ đo trên 160 frame tập phát triển (33 có vết trong tầm nhìn): frame có vết tối đa 3,1% ROI và 5 vùng, frame sạch 0,3% và 1 vùng. Vì chọn trên tập phát triển, P7 phải kiểm lại trên heldout mới. Số đo chất lượng (`robustness/quality.py`) giữ làm chẩn đoán, để P5 quyết định frame nào đủ tốt làm bằng chứng sạch. Mặc định dashboard: lề + cổng |
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
| D11 | Cổng hash không hash code | `approval_gate.py` | Sửa logic xong vẫn hiện "đã nghiệm thu". **Đã sửa 2026-10-15:** cổng kiểm thêm SHA256 của 17 file code chấm điểm (`SCORING_CODE`) |
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

> **Sửa đổi 2026-10-09 (P3):** cổng theo phân vị dưới đây đã thử và bị loại; xem nhật ký quyết định và mục Kết quả P3. Bản thực hiện: lề chấm điểm + cổng `diffuse_anomaly`; các chỉ số dưới đây chỉ được đo và báo cáo.

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

> **Sửa đổi 2026-10-12 (P5):** bản thực hiện dùng quy tắc k = 3 lượt nhìn trên ô 10 cm với hit = ngưỡng pixel AND ngưỡng tương đối theo tầng, thay cho SPRT/e-value dưới đây; xem nhật ký quyết định và mục Kết quả P5.

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

> **Thiết kế thực hiện (P6, 2026-10-14):**
> - **Vùng mơ hồ:** các ô bề mặt chưa có cảnh báo, có 1 đến k-1 = 2 lượt nhìn đạt hit (ngưỡng pixel AND ngưỡng tầng), gộp trong 0,6 m (`SurfaceEvidence.ambiguous_regions()`). Quay lại chỉ có ích ở đây: ô có 0 hit là sạch theo bằng chứng hiện có, ô đủ 3 hit đã báo.
> - **Cơ chế chèn route:** runtime đọc route từ danh sách Python và bridge đã bọc `advance_station`, nên bridge có thể chèn điểm quay lại vào danh sách đang chạy mà không sửa `run_inspection.py`. Điểm quay lại: hướng thẳng vào tâm vùng, khoảng cách camera-bề mặt không nhỏ hơn khoảng bank/calibration đã thấy (khoảng 1,6 m), qua `clearance_violations()`, rồi trở lại route.
> - **Chi phí là rủi ro chính:** marine snow tạo nhiều ô 1 hit ngẫu nhiên. P6.1 đo offline trên tập phát triển số vùng mơ hồ/100 m (chi phí) và vết bị bỏ sót có nằm trong vùng mơ hồ hay không (lợi ích tối đa), để chọn ngưỡng kích hoạt (ví dụ chỉ vùng có 2 hit) và ngân sách (số lần quay lại/100 m) **trước** khi viết logic chèn route (P6.2), rồi chạy live.

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
| P3 | Cổng chất lượng 3.1 với mã lý do (thực hiện: lề chấm điểm + cổng `diffuse_anomaly`, xem nhật ký quyết định) | Frame xấu không tạo báo nhầm; tỷ lệ từ chối báo cáo theo yếu tố | 1 ngày |
| P5 | Ngưỡng conformal + SPRT trên bề mặt; thay `calibrate.py`, `alerts.py` (thực hiện: quy tắc k lượt nhìn trên ô bề mặt, xem nhật ký quyết định 2026-10-12) | FPR thực tế ≤ α (Wilson); đường PoD được báo cáo | 1,5-2 ngày |
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
