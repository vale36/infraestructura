service_prefix "validacion-pdf" {
  policy = "read"
}

service_prefix "extraccion" {
  policy = "read"
}

service_prefix "persistencia-consultas" {
  policy = "read"
}

service_prefix "persistencia-actualizaciones" {
  policy = "read"
}

# Consul exige leer el nodo asociado para responder Health/Catalog con el servicio.
node_prefix "" {
  policy = "read"
}

# Contrato 1.6.0: se registra a sí mismo, con los tags de Traefik que lo publican...
service "orquestador" {
  policy = "write"
}

# ...y lee solo su configuración del KV.
key_prefix "config/orquestador/" {
  policy = "read"
}
