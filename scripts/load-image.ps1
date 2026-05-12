param(
    [Parameter(Mandatory = $true)]
    [string]$ImageTar
)

$ErrorActionPreference = "Stop"

# Load a Docker image tar on an offline deployment machine.
$TarPath = (Resolve-Path -LiteralPath $ImageTar).Path
docker load -i $TarPath
