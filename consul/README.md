# Consul compartido

Este Compose levanta el servidor único de Consul usado por el entorno de desarrollo.
Consul mantiene el catálogo de servicios, las comprobaciones de salud y el KV. La
configuración está separada de los contenedores para que la infraestructura pueda
recrearse sin perder datos.

## Diseño

- Servidor único para desarrollo. No usar como una sola instancia en producción.
- Interfaz web disponible únicamente en `127.0.0.1:8500`.
- ACL por defecto en deny.
- Volumen persistente `proyecto-consul-data`.
- Red Docker compartida `redutn`.
- Health check sobre el estado del líder antes de crear tokens.
- Tokens separados para administración, UI, Traefik, registro de aplicaciones y
  descubrimiento del Orquestador.

Los tokens se generan una sola vez y se guardan dentro del volumen persistente,
con permisos `0600`, bajo `/consul/data/bootstrap`:

```text
management.token
ui.token
traefik.token
microservices.token
orchestrator.token
```

El token de Orquestador usa exclusivamente la política `orchestrator`, que permite
lectura de los cuatro servicios registrados y no permite escribir en el catálogo,
los agentes ni el KV:

```text
validacion-pdf
extraccion
persistencia-consultas
persistencia-actualizaciones
```

La interfaz no acepta estos archivos directamente. Hay que leer el token de UI y
pegarlo en el acceso por ACL.

## Preparación

Desde PowerShell:

```powershell
cd C:\Users\Vale\Desktop\ProyectoDesarrollo\dockers\consul
Copy-Item .env.example .env
docker network inspect redutn *> $null
if ($LASTEXITCODE -ne 0) { docker network create redutn }
docker compose up -d
```

El primer arranque crea los ACL y sus tokens. Las ejecuciones posteriores reutilizan
el estado persistente y no intentan volver a hacer bootstrap.

Leer el token de interfaz:

```powershell
docker compose exec -T consul cat /consul/data/bootstrap/ui.token
```

Abrir `http://127.0.0.1:8500/ui/` y acceder con el token leído.

Preparar en el host los archivos locales usados por los contenedores sin mostrarlos
en consola ni versionarlos:

```powershell
.\scripts\prepare-microservices-token.ps1
.\scripts\prepare-orchestrator-token.ps1
```

Los secretos quedan únicamente en `generated/microservices.token` y
`generated/orchestrator.token`. El directorio `generated/` está excluido de Git.
Los scripts comprueban el token actual en Consul antes de sincronizar el archivo,
por lo que pueden ejecutar nuevamente sin recrear el volumen persistente.

Configurar el Orquestador con el token preparado mediante un montaje de solo
lectura; no agregue el secreto al Compose versionado:

```text
CONSUL_HTTP_ADDR=http://consul:8500
CONSUL_HTTP_TOKEN_FILE=/run/secrets/consul_orchestrator_token
CONSUL_ENABLED=true
CONSUL_FALLBACK_ENABLED=false
```

El montaje real debe usar `./generated/orchestrator.token` como origen y
`/run/secrets/consul_orchestrator_token` como destino. Si el contenedor consume
otra ruta, ajuste `CONSUL_HTTP_TOKEN_FILE` a esa ruta. El token no se lee por
variables de entorno ni se imprime en los logs.

## Verificación

El líder debe tener una dirección definida:

```powershell
Invoke-RestMethod http://127.0.0.1:8500/v1/status/leader
```

El catálogo debe devolver una lista vacía antes de registrar microservicios:

```powershell
Invoke-RestMethod 'http://127.0.0.1:8500/v1/catalog/services'
```

## Persistencia

Los contenedores se pueden recrear sin perder el catálogo o los tokens:

```powershell
docker compose down
docker compose up -d
```

El volumen sí conserva los datos. Solo se borra explícitamente si se ejecuta:

```powershell
docker compose down -v
```

Ese último comando elimina el catálogo, las políticas y los tokens. La siguiente
recreación podrá volver a ejecutar el bootstrap de ACL y generará credenciales
nuevas.

## Repositorios siguientes

Este Compose todavía no registra microservicios ni cambia Traefik. Antes de avanzar,
la etapa siguiente deberá revisar:

- Si la aplicación obtiene un token limitado y nunca el token administrativo.
- Si Consul Catalog reemplaza o acompaña al provider Docker de Traefik.
- Si cada réplica recibe un identificador único.
- Si el health check usa un endpoint de readiness que no sea solo liveness.

## Pruebas locales

```powershell
python -m unittest discover -s tests -p 'test_*.py' -v
```
