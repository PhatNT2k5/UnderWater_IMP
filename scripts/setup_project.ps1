[CmdletBinding()]
param(
    [string]$HoloOceanPath = (Join-Path $PSScriptRoot "..\holoocean"),
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$overlayRoot = Join-Path $repositoryRoot "holoocean_overlay"
$artifactRoot = Join-Path $repositoryRoot "patchcore_artifacts"
$holoOceanRevision = "49e70552"
$holoOceanPath = [System.IO.Path]::GetFullPath($HoloOceanPath)
$createdHoloOcean = $false

function Copy-OverlayDirectory {
    param([string]$Source, [string]$Destination)

    if ((Test-Path -LiteralPath $Destination) -and -not $Force) {
        throw "Destination overlay already exists: $Destination. Review it first, then rerun with -Force."
    }
    # -LiteralPath does not expand "*", so enumerate children explicitly.
    $items = @(Get-ChildItem -LiteralPath $Source -Force)
    if ($items.Count -eq 0) {
        throw "Overlay source is empty: $Source. Run 'git lfs pull' and retry."
    }
    New-Item -ItemType Directory -Force -Path $Destination | Out-Null
    $items | Copy-Item -Destination $Destination -Recurse -Force
}

function Update-ReferenceManifest {
    param([string]$DatasetPath)

    $manifestPath = Join-Path $DatasetPath "manifest.jsonl"
    $rows = Get-Content -LiteralPath $manifestPath | ForEach-Object {
        $row = $_ | ConvertFrom-Json
        $row.source_image = Join-Path $DatasetPath $row.image
        $row | ConvertTo-Json -Compress
    }
    [System.IO.File]::WriteAllLines($manifestPath, [string[]]$rows)
}

function Get-ReferenceFingerprint {
    param([string]$DatasetPath)

    $paths = @(
        (Join-Path $DatasetPath "summary.json"),
        (Join-Path $DatasetPath "manifest.jsonl"),
        (Join-Path $DatasetPath "roi_approved.json")
    ) + @(Get-ChildItem -LiteralPath (Join-Path $DatasetPath "roi_masks") -Filter "*.png" | Sort-Object FullName | ForEach-Object FullName)
    $digest = [System.Security.Cryptography.SHA256]::Create()
    try {
        foreach ($path in $paths) {
            $relative = $path.Substring($DatasetPath.Length).TrimStart("\", "/").Replace("\", "/")
            $relativeBytes = [System.Text.Encoding]::UTF8.GetBytes($relative)
            [void]$digest.TransformBlock($relativeBytes, 0, $relativeBytes.Length, $relativeBytes, 0)
            $zero = [byte[]](0)
            [void]$digest.TransformBlock($zero, 0, 1, $zero, 0)
            $fileDigest = [System.Security.Cryptography.SHA256]::Create()
            try { $fileHash = $fileDigest.ComputeHash([System.IO.File]::ReadAllBytes($path)) }
            finally { $fileDigest.Dispose() }
            [void]$digest.TransformBlock($fileHash, 0, $fileHash.Length, $fileHash, 0)
        }
        [void]$digest.TransformFinalBlock([byte[]]@(), 0, 0)
        return ([System.BitConverter]::ToString($digest.Hash)).Replace("-", "").ToLowerInvariant()
    }
    finally { $digest.Dispose() }
}
function Assert-CanWriteFile {
    param([string]$Path)

    if ((Test-Path -LiteralPath $Path) -and -not $Force) {
        throw "Destination file already exists: $Path. Rerun with -Force after reviewing its changes."
    }
}

if (-not (Test-Path -LiteralPath $holoOceanPath)) {
    & git clone https://github.com/byu-holoocean/HoloOcean.git $holoOceanPath
    if ($LASTEXITCODE -ne 0) { throw "Could not clone HoloOcean." }
    Push-Location $holoOceanPath
    try {
        & git checkout $holoOceanRevision
        if ($LASTEXITCODE -ne 0) { throw "Could not checkout HoloOcean revision $holoOceanRevision." }
    }
    finally { Pop-Location }
    $createdHoloOcean = $true
}

$enginePath = Join-Path $holoOceanPath "engine"
if (-not (Test-Path -LiteralPath (Join-Path $enginePath "Holodeck.uproject"))) {
    throw "Holodeck.uproject was not found under $enginePath. Supply a valid HoloOcean checkout path."
}

Copy-OverlayDirectory (Join-Path $overlayRoot "engine\Content\AUVInspection") (Join-Path $enginePath "Content\AUVInspection")

foreach ($relativePath in @(
    "engine\Holodeck.uproject",
    "engine\Source\Holodeck\ClientCommands\Private\TurnOnFlashlightCommand.cpp"
)) {
    $source = Join-Path $overlayRoot $relativePath
    $destination = Join-Path $holoOceanPath $relativePath
    if ((Test-Path -LiteralPath $destination) -and -not ($Force -or $createdHoloOcean)) {
        throw "Destination file already exists: $destination. Rerun with -Force after reviewing its changes."
    }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
    Copy-Item -LiteralPath $source -Destination $destination -Force
}

Copy-OverlayDirectory (Join-Path $overlayRoot "engine\Plugins\FunplayMCP") (Join-Path $enginePath "Plugins\FunplayMCP")

foreach ($artifact in @("patchcore_model_v1", "patchcore_dataset_clean_20260925")) {
    $source = Join-Path $artifactRoot $artifact
    $destination = Join-Path $repositoryRoot "auv_inspection\output\$artifact"
    if (-not (Test-Path -LiteralPath $source)) {
        throw "Missing PatchCore artifact: $source. Run 'git lfs pull' and retry."
    }
    Copy-OverlayDirectory $source $destination
}

$referenceDestination = Join-Path $repositoryRoot "auv_inspection\output\patchcore_dataset_clean_20260925"
Update-ReferenceManifest $referenceDestination

$thresholdDestination = Join-Path $repositoryRoot "auv_inspection\output\patchcore_thresholds_v1.json"
Assert-CanWriteFile $thresholdDestination
Copy-Item -LiteralPath (Join-Path $artifactRoot "patchcore_thresholds_v1.json") -Destination $thresholdDestination -Force
$thresholds = Get-Content -LiteralPath $thresholdDestination -Raw | ConvertFrom-Json
$thresholds.model_dir = Join-Path $repositoryRoot "auv_inspection\output\patchcore_model_v1"
$thresholds | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $thresholdDestination -Encoding utf8

$evaluationDestination = Join-Path $repositoryRoot "auv_inspection\output\patchcore_evaluation_B_v1.json"
Assert-CanWriteFile $evaluationDestination
Copy-Item -LiteralPath (Join-Path $artifactRoot "patchcore_evaluation_B_v1.json") -Destination $evaluationDestination -Force
$evaluation = Get-Content -LiteralPath $evaluationDestination -Raw | ConvertFrom-Json
$evaluation.model_dir = $thresholds.model_dir
$evaluation.reference_dataset = $referenceDestination
$evaluation.thresholds = $thresholdDestination
$evaluation.reference_sha256 = Get-ReferenceFingerprint $referenceDestination
$evaluation.thresholds_sha256 = (Get-FileHash -LiteralPath $thresholdDestination -Algorithm SHA256).Hash.ToLowerInvariant()
$evaluation | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $evaluationDestination -Encoding utf8

Write-Host "Overlay installed. Open $enginePath\Holodeck.uproject with Unreal Engine 5.3, build if requested, then run auv_dashboard\run_dashboard.py."
