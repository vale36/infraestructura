# Contrato 1.6.0: lo usa consul-config, del compose de integración, para cargar en el KV
# la configuración de cada microservicio (config/<servicio>/). No registra servicios.
key_prefix "config/" {
  policy = "write"
}
