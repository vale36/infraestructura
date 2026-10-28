#!/bin/sh
set -e

BOOTSTRAP_DIR=/consul/data/bootstrap
MANAGEMENT_TOKEN_FILE=$BOOTSTRAP_DIR/management.token
UI_TOKEN_FILE=$BOOTSTRAP_DIR/ui.token
TRAEFIK_TOKEN_FILE=$BOOTSTRAP_DIR/traefik.token
MICROSERVICES_TOKEN_FILE=$BOOTSTRAP_DIR/microservices.token

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
  fi
}

ensure_token() {
  token_file=$1
  token_description=$2
  policy_name=$3

  if [ -f "$token_file" ]; then
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
ensure_token "$TRAEFIK_TOKEN_FILE" "Read-only catalog token for Traefik" traefik
ensure_token "$MICROSERVICES_TOKEN_FILE" "Service registration token for microservices" microservices

umask 077
printf '%s\n' "$management_token" > "$UI_TOKEN_FILE"

printf '%s\n' "Consul ACL infrastructure is ready; tokens are stored in $BOOTSTRAP_DIR"
