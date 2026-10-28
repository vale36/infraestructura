$ErrorActionPreference = "Stop"

$consulDirectory = Split-Path -Parent $PSScriptRoot
$consulComposeFile = Join-Path $consulDirectory "docker-compose.yml"
$generatedDirectory = Join-Path $consulDirectory "generated"
$generatedToken = Join-Path $generatedDirectory "microservices.token"

$tokenLines = & docker compose -f $consulComposeFile exec -T consul cat /consul/data/bootstrap/microservices.token
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo leer el token de microservicios. Comprueba que Consul este iniciado y que el bootstrap ACL haya terminado."
}

$token = ($tokenLines | Out-String).Trim()
if ([string]::IsNullOrWhiteSpace($token) -or $token -match "\s") {
    throw "Consul devolvio un token vacio o invalido."
}

New-Item -ItemType Directory -Path $generatedDirectory -Force | Out-Null
[System.IO.File]::WriteAllText($generatedToken, $token, [System.Text.UTF8Encoding]::new($false))
Write-Host "Token de registro de microservicios preparado; el valor no se muestra."
