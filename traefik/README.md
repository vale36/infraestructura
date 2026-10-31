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
│   └── scripts
```

## Consul Catalog (desarrollo)

Traefik conserva el provider Docker para las aplicaciones existentes y habilita
Consul Catalog como fuente adicional de servicios. El provider Consul solo acepta
servicios con el tag `traefik.enable=true`, etiquetas `traefik.*` y comprobaciones
en estado `passing`.

Consul debe estar iniciado en la red externa `redutn` antes que Traefik. Preparar
la configuración local ignorada que agrega a Traefik su token de solo lectura:

```powershell
cd dockers\consul
docker compose up -d --wait

cd ..\traefik
.\scripts\prepare-consul-token.ps1
docker compose config --quiet
docker compose up -d
```

El script lee el token `traefik` desde el volumen persistente de Consul y lo inserta
en `config\traefik.generated.yml`; nunca lo muestra por consola. Ese archivo está
ignorado por Git y es el único que monta Traefik en lugar del archivo base. Si se
regeneran los tokens borrando el volumen de Consul, volver a ejecutar el script antes
de recrear Traefik.

En Consul, el token de Traefik solo puede leer servicios y nodos. No tiene permisos
para registrar servicios, modificar KV ni administrar ACL. El provider Docker sigue
activo: el Orquestador se publica con labels Docker (`pdf.universidad.localhost`).

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
