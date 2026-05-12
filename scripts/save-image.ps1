param(
    [string]$ImageName = "rapidocr-docker",
    [string]$Tag = "1.0.0",
    [string]$Output = "dist\rapidocr-docker-1.0.0.tar"
)

$ErrorActionPreference = "Stop"

# Save the built image as a tar file for offline deployment.
$Image = "${ImageName}:${Tag}"
$OutputPath = [System.IO.Path]::GetFullPath($Output)
$OutputDir = Split-Path -Parent $OutputPath

if ($OutputDir -and -not (Test-Path -LiteralPath $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
}

docker save -o $OutputPath $Image
Write-Output "Saved image $Image to $OutputPath"
