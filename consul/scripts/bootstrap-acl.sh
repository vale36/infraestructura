#!/bin/sh
set -e

BOOTSTRAP_DIR=/consul/data/bootstrap
MANAGEMENT_TOKEN_FILE=$BOOTSTRAP_DIR/management.token
UI_TOKEN_FILE=$BOOTSTRAP_DIR/ui.token
TRAEFIK_TOKEN_FILE=$BOOTSTRAP_DIR/traefik.token
MICROSERVICES_TOKEN_FILE=$BOOTSTRAP_DIR/microservices.token
ORCHESTRATOR_TOKEN_FILE=$BOOTSTRAP_DIR/orchestrator.token
AGENT_TOKEN_FILE=$BOOTSTRAP_DIR/consul-agent.token
AGENT_CONFIG_FILE=/consul/generated-config/consul-agent.hcl

mkdir -p "$BOOTSTRAP_DIR"
chmod 700 "$BOOTSTRAP_DIR"

if [ -f "$MANAGEMENT_TOKEN_FILE" ]; then
  management_token=$(cat "$MANAGEMENT_TOKEN_FILE")
else
  management_json=$(consul acl bootstrap -http-addr="$CONSUL_HTTP_ADDR" -format=json)
  management_token=$(printf '%s' "$management_json" | sed -n 's/.*"SecretID"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n 1)

  if [ -z "$management_token" ]; then
    echo "Consul ACL bootstrap did not return a management token" >&2
    exit 1
  fi

  umask 077
  printf '%s\n' "$management_token" > "$MANAGEMENT_TOKEN_FILE"
fi

ensure_policy() {
  policy_name=$1
  policy_file=$2

  if ! consul acl policy read \
    -http-addr="$CONSUL_HTTP_ADDR" \
    -token="$management_token" \
    -name="$policy_name" >/dev/null 2>&1; then
    consul acl policy create \
      -http-addr="$CONSUL_HTTP_ADDR" \
      -token="$management_token" \
      -name="$policy_name" \
      -rules="@$policy_file" >/dev/null
  else
    consul acl policy update \
      -http-addr="$CONSUL_HTTP_ADDR" \
      -token="$management_token" \
      -name="$policy_name" \
      -rules="@$policy_file" >/dev/null
  fi
}

ensure_token() {
  token_file=$1
  token_description=$2
  policy_name=$3

  if [ -f "$token_file" ] && consul acl token read \
    -http-addr="$CONSUL_HTTP_ADDR" \
    -token="$(cat "$token_file")" \
    -self >/dev/null 2>&1; then
    return
  fi

  token_json=$(consul acl token create \
    -http-addr="$CONSUL_HTTP_ADDR" \
    -token="$management_token" \
    -description="$token_description" \
    -policy-name="$policy_name" \
    -format=json)
  token=$(printf '%s' "$token_json" | sed -n 's/.*"SecretID"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n 1)

  if [ -z "$token" ]; then
    echo "Could not create the $policy_name ACL token" >&2
    exit 1
  fi

  umask 077
  printf '%s\n' "$token" > "$token_file"
}

ensure_policy traefik /consul/policies/traefik.hcl
ensure_policy microservices /consul/policies/microservices.hcl
ensure_policy orchestrator /consul/policies/orchestrator.hcl
ensure_policy consul-agent /consul/policies/consul-agent.hcl
ensure_token "$TRAEFIK_TOKEN_FILE" "Read-only catalog token for Traefik" traefik
ensure_token "$MICROSERVICES_TOKEN_FILE" "Service registration token for microservices" microservices
ensure_token "$ORCHESTRATOR_TOKEN_FILE" "Read-only discovery token for the Orchestrator" orchestrator
ensure_token "$AGENT_TOKEN_FILE" "Agent reconciliation token for Consul" consul-agent

agent_token=$(cat "$AGENT_TOKEN_FILE")
acl_config=$(printf 'acl {\n  tokens {\n    agent = "%s"\n  }\n}\n' "$agent_token")
if [ ! -f "$AGENT_CONFIG_FILE" ] || [ "$(cat "$AGENT_CONFIG_FILE")" != "$(printf '%b' "$acl_config")" ]; then
  umask 077
  printf '%b' "$acl_config" > "$AGENT_CONFIG_FILE"
fi
chown consul:consul "$AGENT_CONFIG_FILE"
consul reload -http-addr="$CONSUL_HTTP_ADDR" -token="$management_token" >/dev/null

umask 077
printf '%s\n' "$management_token" > "$UI_TOKEN_FILE"

# Archivos para el host, sin mostrar los valores: los microservicios y el Orquestador
# reciben su token como Docker secret y Traefik lee su configuración generada. Hace lo
# mismo que los scripts prepare-*.ps1, para que la infraestructura se levante con un
# solo `docker compose up`.
if [ -d /consul/host-generated ]; then
  # cat y no cp: sobre las carpetas compartidas de Docker Desktop (Windows) cp falla con
  # "File exists" cuando el archivo se borró hace poco desde el host.
  cat "$MICROSERVICES_TOKEN_FILE" > /consul/host-generated/microservices.token
  cat "$ORCHESTRATOR_TOKEN_FILE" > /consul/host-generated/orchestrator.token
  chmod 644 /consul/host-generated/microservices.token /consul/host-generated/orchestrator.token
fi
if [ -f /traefik-config/traefik.yml ]; then
  traefik_token=$(cat "$TRAEFIK_TOKEN_FILE")
  awk -v token="$traefik_token" '
    { print }
    /^      datacenter: "dc1"/ { print "      token: \"" token "\"" }
  ' /traefik-config/traefik.yml > /traefik-config/traefik.generated.yml
fi

printf '%s\n' "Consul ACL infrastructure is ready; tokens are stored in $BOOTSTRAP_DIR"
