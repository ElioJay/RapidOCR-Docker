param(
    [string]$ImageName = "rapidocr-docker",
    [string]$Tag = "1.0.0",
    [switch]$NoCache
)

$ErrorActionPreference = "Stop"

# Build from the project root so Docker can find Dockerfile and src/.
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$Image = "${ImageName}:${Tag}"

$BuildArgs = @("build", "-t", $Image)
if ($NoCache) {
    $BuildArgs += "--no-cache"
}
$BuildArgs += $ProjectRoot

docker @BuildArgs
