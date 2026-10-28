$ErrorActionPreference = "Stop"

$consulDirectory = Split-Path -Parent $PSScriptRoot
$consulComposeFile = Join-Path $consulDirectory "docker-compose.yml"
$generatedDirectory = Join-Path $consulDirectory "generated"
$generatedToken = Join-Path $generatedDirectory "orchestrator.token"

$tokenLines = & docker compose -f $consulComposeFile exec -T consul cat /consul/data/bootstrap/orchestrator.token
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo leer el token del Orquestador. Comprueba que Consul este iniciado y que el bootstrap ACL haya terminado."
}

$token = ($tokenLines | Out-String).Trim()
if ([string]::IsNullOrWhiteSpace($token) -or $token -match "\s") {
    throw "Consul devolvio un token del Orquestador vacio o invalido."
}

& docker compose -f $consulComposeFile exec -T consul sh -c `
    'token=$(cat "$1"); consul acl token read -http-addr=http://127.0.0.1:8500 -token="$token" -self >/dev/null' `
    sh /consul/data/bootstrap/orchestrator.token 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "El token del Orquestador no pertenece al servidor Consul actual."
}

New-Item -ItemType Directory -Path $generatedDirectory -Force | Out-Null
[System.IO.File]::WriteAllText($generatedToken, $token, [System.Text.UTF8Encoding]::new($false))
Write-Host "Token exclusivo del Orquestador preparado; el valor no se muestra."
