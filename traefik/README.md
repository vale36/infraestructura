# Traefik
Traefik es un proxy inverso y balanceador de carga, nativo de la nube y de código abierto que facilita la implementación de microservicios.

![Traefik](https://doc.traefik.io/traefik/assets/img/traefik-architecture.png)
## Estructura de Traefik
```
carpeta_del_usuario
├── traefik
│   └── certs 
│   └── config  # Carpeta de configuración de traefik
│   └── docker-compose.yml
```

## Proveedores: Consul Catalog y archivos

Traefik tiene dos proveedores y ninguno más:

| Proveedor | De dónde saca las rutas | Qué publica |
|---|---|---|
| `consulCatalog` | Los servicios registrados en Consul con el tag `traefik.enable=true`, etiquetas `traefik.*` y health check en `passing` | El orquestador (contrato 1.6.0) |
| `file` | `config/config.yml` | El panel (`traefik.universidad.localhost`) y los certificados |

No tiene el proveedor Docker ni monta `/var/run/docker.sock`: nadie se publicaba con
labels, y con el socket montado (aunque sea `:ro`) un Traefik comprometido controla Docker
y el host.

Consul debe estar iniciado en la red externa `redutn` antes que Traefik. Lo normal es
levantar todo con el `docker-compose.yml` de la raíz, que arranca Traefik recién cuando el
bootstrap de Consul terminó:

```powershell
cd dockers
docker compose up -d --wait
```

El bootstrap lee el token `traefik` y lo inserta en `config/traefik.generated.yml`; nunca
lo muestra por consola. Ese archivo está ignorado por Git y es el único que monta Traefik
en lugar del archivo base. Si se regeneran los tokens borrando el volumen de Consul, el
próximo `docker compose up` lo vuelve a escribir.

En Consul, el token de Traefik solo puede leer servicios y nodos. No tiene permisos
para registrar servicios, modificar KV ni administrar ACL. El Orquestador se publica
por Consul Catalog (contrato 1.6.0): se registra en Consul con los tags de Traefik
(`Host(pdf.universidad.localhost)`, HTTPS, cortocircuito y límite de tasa), que vienen
de su configuración en el KV.

El panel sale solo por su router HTTPS de `config.yml`: `api.insecure` está en `false`,
así que el puerto 8080 (la API sin router) queda cerrado. No pide usuario ni contraseña
(desarrollo). `sendAnonymousUsage` también está en `false`.

Solo se publican los puertos 80 y 443. Antes también el 6379 y el 27017 como
entrypoints TCP para Redis y MongoDB, pero ninguno tenía router: los servicios los usan
por nombre dentro de `redutn` y no hacía falta exponerlos.

Traefik monta la carpeta `config` completa y arranca con
`--configFile=/etc/traefik/config/traefik.generated.yml`. Se monta la carpeta y no el
archivo porque, si `traefik.generated.yml` todavía no existe cuando Docker crea el
contenedor, montar el archivo suelto hace que Docker cree una carpeta con ese nombre.

Para comprobar la conexión, revisar los logs de Traefik:

```powershell
docker compose logs --tail 100 reverse-proxy
```

Los microservicios se registran en Consul sin etiquetas `traefik.*`, así que Consul
Catalog no publica ninguno: son internos.

# Utilidad para generar Certificados
Para generar e instalar certificados para desarrollo se puede utilizar **mkcert** 
1. Descargar mkcert https://github.com/FiloSottile/mkcert/tags

2. Generar certificados:
```
mkcert -cert-file certs/cert.pem -key-file certs/key.pem "universidad.localhost" "*.universidad.localhost" 127.0.0.1 ::1
```
3. Instalar certificados
```
mkcert -install
```
Los archivos *key.pem* y *cert.pem* deben copiarse en la carpeta **certs** de traefik

## Documentación
- [mkcert](https://github.com/FiloSottile/mkcert)
- [traefik](https://doc.traefik.io/traefik/)
