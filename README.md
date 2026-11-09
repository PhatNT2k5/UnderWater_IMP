# UnderWater IMP — AUV Inspection

Mô phỏng AUV khảo sát đường ống và trụ cầu dưới nước bằng Unreal Engine 5.3, HoloOcean và dashboard Tkinter. Repository chứa source dự án, map `AUVInspection`, asset hư hại, PatchCore artifact đã đánh giá offline và một overlay cho HoloOcean upstream.

## Nội dung repository

| Đường dẫn | Nội dung |
|---|---|
| `auv_dashboard/` | Dashboard Tkinter và bridge chạy Unreal/HoloOcean |
| `auv_inspection/` | Route, runtime AUV, detector, PatchCore tools và tài liệu |
| `holoocean_overlay/` | Map, Unreal asset, plugin editor và thay đổi C++ áp dụng lên HoloOcean |
| `patchcore_artifacts/` | Model, ngưỡng và tập sạch tham chiếu: PatchCore v1 và bộ phát hiện P8 (DINOv2, `detector_v2_*`) |
| `scripts/setup_project.ps1` | Clone đúng HoloOcean revision và áp dụng overlay/artifact |

`holoocean/`, `worlds/`, cache Unreal, virtual environment và output runtime không được commit. Chúng quá lớn, phụ thuộc máy, hoặc có thể chứa log/token cục bộ.

## Yêu cầu

- Windows 11
- Git và Git LFS
- Unreal Engine 5.3.x, có khả năng build project HoloOcean từ source
- Python/Conda cho runtime dashboard, cùng Python 3.11 riêng cho PatchCore
- GPU CUDA là tùy chọn cho PatchCore; CPU chạy được nhưng chậm hơn
- Internet ở lần chạy đầu: bộ phát hiện P8 tải trọng số DINOv2 `vit_small_patch14_dinov2.lvd142m` (khoảng 85 MB) từ Hugging Face qua `timm`, lưu vào cache `%USERPROFILE%\.cache\huggingface`

Sau khi clone, tải LFS trước khi setup:

```powershell
git lfs install
git lfs pull
```

## Setup một máy mới

Từ thư mục root repository, chạy:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup_project.ps1
```

Script sẽ clone HoloOcean tại revision `49e70552`, chép map/asset/plugin/C++ overlay vào `holoocean/` (gồm map A, B, C và các map sạch), rồi cài artifact vào `auv_inspection/output/`: PatchCore v1 và bộ phát hiện P8 (`detector_v2_dino_s2_aug_g2`, `detector_v2_dino_s2_aug_g2_floor`).

Nếu người dùng đã có một HoloOcean checkout riêng, truyền đường dẫn của checkout đó. Script từ chối ghi đè overlay đang tồn tại nếu không có `-Force`.

```powershell
.\scripts\setup_project.ps1 -HoloOceanPath D:\HoloOcean -Force
```

### Cập nhật một máy đã setup trước đây

Máy đã chạy `setup_project.ps1` trước bản P8 chỉ cần lấy code, LFS và chép thêm model P8 cùng map C (không cần chạy lại toàn bộ script):

```powershell
git checkout main
git pull
git lfs pull
Copy-Item -Recurse -Force .\patchcore_artifacts\detector_v2_dino_s2_aug_g2 .\auv_inspection\output\
Copy-Item -Recurse -Force .\patchcore_artifacts\detector_v2_dino_s2_aug_g2_floor .\auv_inspection\output\
Copy-Item -Force .\holoocean_overlay\engine\Content\AUVInspection\Maps\AUVInspection_PatchCoreC_20261016_v1.umap .\holoocean\engine\Content\AUVInspection\Maps\
```

Nếu `holoocean` nằm ở chỗ khác, thay đường dẫn đích ở lệnh cuối. Sau đó kiểm tra như mục "Kiểm tra bộ phát hiện P8" bên dưới.

Sau đó mở `holoocean\engine\Holodeck.uproject` trong Unreal Engine 5.3 và build `HolodeckEditor` nếu Unreal yêu cầu. Map nằm tại:

```text
Content/AUVInspection/Maps/AUVInspection.umap
```

Build lần đầu cần Visual Studio 2022 (workload C++), **.NET Framework SDK 4.6+** và toolset **MSVC v14.38**. MSVC 14.40 trở lên báo lỗi `C4668 '__has_feature'` trong header UE 5.3; khi đó chỉ định 14.38 trong `%APPDATA%\Unreal Engine\UnrealBuildTool\BuildConfiguration.xml` (`<WindowsPlatform><CompilerVersion>14.38.xxxxx</CompilerVersion></WindowsPlatform>`, lấy đúng số thư mục trong `VC\Tools\MSVC\`).

Runtime tìm `UnrealEditor.exe` theo thứ tự: `--editor`, biến môi trường `AUV_UNREAL_EDITOR`, manifest Epic Launcher, rồi registry `HKLM\SOFTWARE\EpicGames\Unreal Engine\5.3` (`InstalledDirectory`). Nếu UE cài ngoài Launcher, đặt một trong hai giá trị cuối để dashboard chạy được.

## Môi trường Python

`mainenv` cho Unreal/HoloOcean/dashboard cần **Python 3.11+** (`approval_gate` dùng `hashlib.file_digest`):

```powershell
conda create -n mainenv python=3.11 -y
conda activate mainenv
pip install numpy scipy matplotlib pywin32 opencv-python pillow
```

HoloOcean client được import trực tiếp từ `holoocean/client/src`, không cần `pip install`. Nếu conda không nằm ở `%USERPROFILE%\.conda`, các lệnh dạng `& "$env:USERPROFILE\.conda\envs\mainenv\python.exe"` trong tài liệu con được thay bằng `python` sau `conda activate mainenv`.

PatchCore chạy trong venv riêng tại `.venv-patchcore` (dashboard gọi đúng `.venv-patchcore\Scripts\python.exe`), tạo bằng Python 3.11:

```powershell
python -m venv .venv-patchcore
.\.venv-patchcore\Scripts\python.exe -m pip install -r .\auv_inspection\patchcore_data\requirements-patchcore.txt
```

Artifact model, ngưỡng và ảnh sạch tham chiếu được setup script chép sẵn từ `patchcore_artifacts/`. Lần đầu bộ phát hiện P8 chạy, `timm` tải trọng số DINOv2 từ Hugging Face (cần Internet một lần).

## Chạy dashboard

Sau khi HoloOcean đã build, từ root repository với `mainenv` đã activate:

```powershell
python -m unittest auv_dashboard.test_dashboard auv_inspection.tests.test_find_editor -v
python .\auv_dashboard\run_dashboard.py
```

Dashboard mặc định dùng **bộ phát hiện P8** (DINOv2, ứng viên đã đạt nghiệm thu) khi mọi file model và mã chấm điểm còn khớp mã băm đã đăng ký trong `auv_inspection/robustness/acceptance_preregistration_p8.json`. Nếu không khớp, dashboard lùi về bộ phát hiện cũ hơn. Một số tùy chọn:

| Lệnh | Tác dụng |
|---|---|
| `python .\auv_dashboard\run_dashboard.py` | Map A, bộ phát hiện P8 |
| `... --world /Game/AUVInspection/Maps/AUVInspection_PatchCoreC_20261016_v1` | Map C (6 vết, có vết mặt sau ống và trụ) |
| `... --world /Game/AUVInspection/Maps/AUVInspection_PatchCoreB_20260926_v3` | Map B (5 vết, có lỗ thủng) |
| `... --v1` | PatchCore v1 cũ, để so sánh |

### Kiểm tra bộ phát hiện P8

Với `mainenv` đã activate, từ root repository:

```powershell
python -c "from pathlib import Path; from auv_inspection.patchcore_data.approval_gate import registered_candidate_matches as ok; print(ok(Path('auv_inspection/output/detector_v2_dino_s2_aug_g2_floor'), Path('auv_inspection/robustness/acceptance_preregistration_p8.json'), Path('.')))"
```

`True` nghĩa là dashboard sẽ dùng P8. `False` thường do thiếu `git lfs pull` (file bank `.pt` khi đó chỉ là con trỏ LFS vài trăm byte), chưa chép `patchcore_artifacts/detector_v2_*` vào `auv_inspection/output/`, hoặc đã sửa file JSON của model. Các file JSON này và `auv_inspection/robustness/calibration/geometry_v3.json` được `.gitattributes` checkout với xuống dòng CRLF để mã băm khớp trên mọi máy; không mở rồi lưu lại chúng bằng editor đổi kiểu xuống dòng.

Test của bộ phát hiện chạy trong `.venv-patchcore`:

```powershell
.\.venv-patchcore\Scripts\python.exe -m unittest discover -s auv_inspection\patchcore_data\tests
.\.venv-patchcore\Scripts\python.exe -m unittest discover -s auv_inspection\detector_v2\tests
.\.venv-patchcore\Scripts\python.exe -m unittest discover -s auv_inspection\robustness\tests
```


## Tài liệu

- [Kế hoạch tổng quát hóa và tiến độ](GENERALIZATION_PLAN.md)
- [Hướng dẫn PatchCore](auv_inspection/PATCHCORE_GUIDE_VI.md)
- [Backlog nhiễu môi trường](auv_inspection/NOISE_ROBUSTNESS_TODO.md)
- [Bàn giao source và giới hạn](SOURCE_HANDOFF.md)
