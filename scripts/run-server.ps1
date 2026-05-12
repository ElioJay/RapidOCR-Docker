param(
    [string]$ImageName = "rapidocr-docker",
    [string]$Tag = "1.0.0",
    [int]$Port = 8000,
    [int]$HostPort = $Port,
    [string]$ContainerName = "rapidocr-docker"
)

$ErrorActionPreference = "Stop"

# The container listens on APP_PORT, and Docker maps it to HostPort.
$Image = "${ImageName}:${Tag}"
docker run --rm `
    --name $ContainerName `
    -e "APP_HOST=0.0.0.0" `
    -e "APP_PORT=$Port" `
    -p "${HostPort}:${Port}" `
    $Image server
