# UnderWater IMP — AUV Inspection

Mô phỏng AUV khảo sát đường ống và trụ cầu dưới nước bằng Unreal Engine 5.3, HoloOcean và dashboard Tkinter. Repository chứa source dự án, map `AUVInspection`, asset hư hại, PatchCore artifact đã đánh giá offline và một overlay cho HoloOcean upstream.

## Nội dung repository

| Đường dẫn | Nội dung |
|---|---|
| `auv_dashboard/` | Dashboard Tkinter và bridge chạy Unreal/HoloOcean |
| `auv_inspection/` | Route, runtime AUV, detector, PatchCore tools và tài liệu |
| `holoocean_overlay/` | Map, Unreal asset, plugin editor và thay đổi C++ áp dụng lên HoloOcean |
| `patchcore_artifacts/` | Model, ngưỡng và tập sạch tham chiếu dùng để chạy PatchCore |
| `scripts/setup_project.ps1` | Clone đúng HoloOcean revision và áp dụng overlay/artifact |

`holoocean/`, `worlds/`, cache Unreal, virtual environment và output runtime không được commit. Chúng quá lớn, phụ thuộc máy, hoặc có thể chứa log/token cục bộ.

## Yêu cầu

- Windows 11
- Git và Git LFS
- Unreal Engine 5.3.x, có khả năng build project HoloOcean từ source
- Python/Conda cho runtime dashboard, cùng Python 3.11 riêng cho PatchCore
- GPU CUDA là tùy chọn cho PatchCore; CPU chạy được nhưng chậm hơn

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

Script sẽ clone HoloOcean tại revision `49e70552`, chép map/asset/plugin/C++ overlay vào `holoocean/`, rồi cài artifact PatchCore vào `auv_inspection/output/`.

Nếu người dùng đã có một HoloOcean checkout riêng, truyền đường dẫn của checkout đó. Script từ chối ghi đè overlay đang tồn tại nếu không có `-Force`.

```powershell
.\scripts\setup_project.ps1 -HoloOceanPath D:\HoloOcean -Force
```

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

Artifact model, ngưỡng và ảnh sạch tham chiếu được setup script chép sẵn từ `patchcore_artifacts/`.

## Chạy dashboard

Sau khi HoloOcean đã build, từ root repository với `mainenv` đã activate:

```powershell
python -m unittest auv_dashboard.test_dashboard auv_inspection.tests.test_find_editor -v
python .\auv_dashboard\run_dashboard.py
```


## Tài liệu

- [Kế hoạch tổng quát hóa và tiến độ](GENERALIZATION_PLAN.md)
- [Hướng dẫn PatchCore](auv_inspection/PATCHCORE_GUIDE_VI.md)
- [Backlog nhiễu môi trường](auv_inspection/NOISE_ROBUSTNESS_TODO.md)
- [Bàn giao source và giới hạn](SOURCE_HANDOFF.md)
