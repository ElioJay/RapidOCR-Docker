param(
    [Parameter(Mandatory = $true)]
    [string]$InputFile,
    [string]$OutputFile = "",
    [string]$ImageName = "rapidocr-docker",
    [string]$Tag = "1.0.0",
    [int]$RenderDpi = 200,
    [switch]$ReturnWordBox,
    [switch]$Pretty
)

$ErrorActionPreference = "Stop"

# Mount only the input directory and optional output directory into the container.
$InputPath = (Resolve-Path -LiteralPath $InputFile).Path
$InputDir = Split-Path -Parent $InputPath
$InputName = Split-Path -Leaf $InputPath
$Image = "${ImageName}:${Tag}"

$DockerArgs = @("run", "--rm", "-v", "${InputDir}:/input:ro")

if ($OutputFile) {
    $OutputPath = [System.IO.Path]::GetFullPath($OutputFile)
    $OutputDir = Split-Path -Parent $OutputPath
    $OutputName = Split-Path -Leaf $OutputPath

    if ($OutputDir -and -not (Test-Path -LiteralPath $OutputDir)) {
        New-Item -ItemType Directory -Path $OutputDir | Out-Null
    }

    $DockerArgs += @("-v", "${OutputDir}:/output")
}

$DockerArgs += @($Image, "ocr", "/input/$InputName", "--render-dpi", "$RenderDpi")

if ($ReturnWordBox) {
    $DockerArgs += "--return-word-box"
}

if ($Pretty) {
    $DockerArgs += "--pretty"
}

if ($OutputFile) {
    $DockerArgs += @("--output", "/output/$OutputName")
}

docker @DockerArgs
