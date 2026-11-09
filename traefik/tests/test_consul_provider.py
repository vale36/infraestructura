import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "docker-compose.yml"


class ConsulProviderTests(unittest.TestCase):
    def setUp(self):
        result = subprocess.run(
            ["docker", "compose", "-f", str(COMPOSE), "config", "--format", "json"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.configuration = json.loads(result.stdout)

    def test_without_docker_provider_nor_docker_socket(self):
        # Nadie se publica con labels: el orquestador llega por Consul Catalog y el panel
        # por config.yml. Con el socket montado (aunque sea :ro), un Traefik comprometido
        # le puede pedir cualquier cosa a Docker y controlar el host.
        service = self.configuration["services"]["reverse-proxy"]
        self.assertNotIn(
            "/var/run/docker.sock",
            [volume["target"] for volume in service["volumes"]],
        )
        self.assertFalse(service.get("labels"))
        static_configuration = (ROOT / "config/traefik.yml").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("docker:", static_configuration)
        self.assertNotIn("docker.sock", static_configuration)

    def test_only_http_and_https_are_published(self):
        service = self.configuration["services"]["reverse-proxy"]
        # Solo HTTP y HTTPS: MongoDB y Redis no se publican por Traefik (nadie los
        # usaba; los servicios los llaman por nombre dentro de redutn).
        self.assertEqual(
            {port["published"] for port in service["ports"]},
            {"80", "443"},
        )
        static_configuration = (ROOT / "config/traefik.yml").read_text(
            encoding="utf-8"
        )
        self.assertNotIn(":6379", static_configuration)
        self.assertNotIn(":27017", static_configuration)

    def test_consul_catalog_token_is_loaded_from_generated_config(self):
        service = self.configuration["services"]["reverse-proxy"]
        # Se monta la carpeta y no el archivo: si traefik.generated.yml todavía no
        # existe cuando Docker crea el contenedor, montar el archivo suelto hace que
        # Docker cree una carpeta con ese nombre y el bootstrap ya no puede escribirlo.
        config_dir = next(
            volume
            for volume in service["volumes"]
            if volume["target"] == "/etc/traefik/config"
        )
        self.assertEqual(config_dir["source"], str(ROOT / "config"))
        self.assertTrue(config_dir["read_only"])
        self.assertIn(
            "--configFile=/etc/traefik/config/traefik.generated.yml", service["command"]
        )

        static_configuration = (ROOT / "config/traefik.yml").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("token:", static_configuration)

    def test_dashboard_only_through_its_https_router_and_without_telemetry(self):
        # api.insecure abre la API y el panel en el puerto 8080 sin pasar por ningún
        # router; sin él, el panel sale solo por el router de config.yml (HTTPS).
        static_configuration = (ROOT / "config/traefik.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("insecure: false", static_configuration)
        self.assertIn("sendAnonymousUsage: false", static_configuration)
        dynamic_configuration = (ROOT / "config/config.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn('service: "api@internal"', dynamic_configuration)

    def test_consul_catalog_uses_shared_network_and_minimal_provider_scope(self):
        service = self.configuration["services"]["reverse-proxy"]
        self.assertIn("redutn", service["networks"])

        static_configuration = (ROOT / "config/traefik.yml").read_text(
            encoding="utf-8"
        )
        for expected in (
            "consulCatalog:",
            'address: "consul:8500"',
            'scheme: "http"',
            'exposedByDefault: false',
            '- "passing"',
        ):
            self.assertIn(expected, static_configuration)


if __name__ == "__main__":
    unittest.main()
