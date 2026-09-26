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

## Chạy dashboard

Sau khi HoloOcean đã build và Python runtime được cài theo tài liệu `auv_inspection/README.md`:

```powershell
python .\auv_dashboard\run_dashboard.py
```

PatchCore cần `.venv-patchcore` theo `auv_inspection/patchcore_data/requirements-patchcore.txt`. Artifact model, ngưỡng và ảnh sạch tham chiếu được setup script chép sẵn từ `patchcore_artifacts/`.


## Tài liệu

- [Hướng dẫn PatchCore](auv_inspection/PATCHCORE_GUIDE_VI.md)
- [Backlog nhiễu môi trường](auv_inspection/NOISE_ROBUSTNESS_TODO.md)
- [Bàn giao source và giới hạn](SOURCE_HANDOFF.md)
