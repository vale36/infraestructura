$ErrorActionPreference = "Stop"

$traefikDirectory = Split-Path -Parent $PSScriptRoot
$consulComposeFile = Join-Path $traefikDirectory "..\consul\docker-compose.yml"
$consulComposeFile = [System.IO.Path]::GetFullPath($consulComposeFile)
$sourceConfig = Join-Path $traefikDirectory "config\traefik.yml"
$generatedConfig = Join-Path $traefikDirectory "config\traefik.generated.yml"

$tokenLines = & docker compose -f $consulComposeFile exec -T consul cat /consul/data/bootstrap/traefik.token
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo leer el token de Traefik. Comprueba que Consul este iniciado y que el bootstrap ACL haya terminado."
}

$token = ($tokenLines | Out-String).Trim()
if ([string]::IsNullOrWhiteSpace($token) -or $token -match "\s") {
    throw "Consul devolvio un token vacio o invalido."
}

$content = [System.IO.File]::ReadAllText($sourceConfig)
$anchor = '      datacenter: "dc1"'
if (-not $content.Contains($anchor)) {
    throw "No se encontro la configuracion del datacenter de Consul en traefik.yml."
}

$content = $content.Replace($anchor, "$anchor`r`n      token: `"$token`"")
$encoding = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($generatedConfig, $content, $encoding)

Write-Host "Configuracion Consul de Traefik preparada; el valor del token no se muestra."
