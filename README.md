# Infraestructura — microservicios-pdf

Primera capa del sistema: la infraestructura compartida que se levanta **antes** que los
microservicios. Por indicación del profesor, el sistema son dos docker compose en orden:

| Orden | Compose | Qué levanta |
|---|---|---|
| 1.º | `docker-compose.yml` de este repo | Consul (con ACL), Traefik, MongoDB y Redis |
| 2.º | `docker-compose.yml` del repo `integracion` | Los cinco microservicios |

Este repo se clona con el nombre `dockers`, al lado de los demás repos del proyecto: los
composes de los microservicios buscan los tokens en `../dockers/consul/generated/`.

```bash
git clone https://github.com/vale36/infraestructura.git dockers
```

## Qué hay

| Carpeta | Componente | Para qué |
|---|---|---|
| `consul/` | Consul + `consul-bootstrap` | Descubrimiento de servicios y health checks, con ACL por defecto en *deny*. El bootstrap crea las políticas y los tokens |
| `traefik/` | Traefik | Proxy inverso por HTTPS (certificados de `*.universidad.localhost`). Publica solo al orquestador |
| `mongodb/` | MongoDB 7.0 | Una sola base para las dos persistencias. Datos en el volumen `proyecto-mongo-data` |
| `redis/` | Redis 7 | Caché de consultas y lock de actualizaciones. Sin persistencia: arranca vacío |
| `docker-compose.yml` | Todo junto | Incluye los composes de cada carpeta y fija el orden de arranque |

Cada carpeta conserva su propio compose y sus tests; el de la raíz los junta sin repetir su
definición (`include`, y `extends` para Traefik).

## Antes de la primera vez

1. Docker Desktop abierto.
2. Los certificados en `traefik/certs/cert.pem` y `traefik/certs/key.pem` (no se versionan:
   `key.pem` es una clave privada). Se generan con mkcert, ver `traefik/README.md`.
3. La red compartida, una sola vez:

   ```bash
   docker network create redutn
   ```

## Levantar

Desde esta carpeta:

```bash
docker compose up -d --wait
```

Orden de arranque, que resuelve el propio compose:

1. Consul, MongoDB y Redis, hasta quedar sanos.
2. `consul-bootstrap`: crea las ACL y los tokens (solo la primera vez; después los
   reutiliza) y deja en el host, sin mostrarlos y ignorados por Git:
   `consul/generated/microservices.token`, `consul/generated/orchestrator.token` y
   `traefik/config/traefik.generated.yml`.
3. Traefik, recién cuando el bootstrap terminó bien.

Después se levantan los microservicios desde el repo `integracion`
(`./scripts/levantar.sh`).

## Verificar

```bash
docker compose ps                     # consul, mongodb y redis "healthy"; traefik "Up"
docker compose logs consul-bootstrap  # termina con "Consul ACL infrastructure is ready"
```

- Interfaz de Consul: <http://127.0.0.1:8500/ui/>. Pide el token de interfaz, que se lee
  con `docker compose exec -T consul cat /consul/data/bootstrap/ui.token`.
- Dashboard de Traefik: <https://traefik.universidad.localhost>.

## Apagar

```bash
docker compose down        # conserva los datos de MongoDB y las ACL y registros de Consul
```

`docker compose down -v` borra también la base de datos y las ACL: el próximo arranque
genera tokens nuevos.

## Tests

Cada carpeta tiene tests de su compose (y los de la raíz prueban el compose completo). Usan
`docker compose config`, así que necesitan Docker instalado, pero no levantan nada:

```bash
python -m unittest discover -s tests -p "test_*.py"     # el compose completo
for d in consul traefik mongodb redis; do (cd $d && python -m unittest discover -s tests -p "test_*.py"); done
```

## Problemas conocidos

| Síntoma | Causa y solución |
|---|---|
| `network redutn declared as external, but could not be found` | Falta `docker network create redutn` |
| `consul-bootstrap` termina con error `Is a directory` | Una versión vieja montaba `traefik.generated.yml` como archivo y Docker creó una carpeta con ese nombre: borrar la carpeta `traefik/config/traefik.generated.yml` y volver a levantar |
| `consul-bootstrap` no puede escribir un `.token` recién borrado | Caché de las carpetas compartidas de Docker Desktop (Windows): reiniciar Docker Desktop |
| Los microservicios no arrancan con `Permission denied` sobre el token | Tokens generados por una versión vieja del bootstrap sin `chmod 644`: volver a levantar este compose |
| Traefik responde `404` para `pdf.universidad.localhost` | Todavía no se levantaron los microservicios (`integracion`) |
