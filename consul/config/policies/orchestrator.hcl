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
