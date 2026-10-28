datacenter = "dc1"
data_dir = "/consul/data"
node_name = "consul-server-dev"
server = true
bootstrap_expect = 1

bind_addr = "0.0.0.0"
client_addr = "0.0.0.0"

ui_config {
  enabled = true
}

ports {
  dns = 8600
  http = 8500
  https = -1
  grpc = -1
}

acl {
  enabled = true
  default_policy = "deny"
  enable_token_persistence = true
  down_policy = "extend-cache"
}

log_level = "INFO"
