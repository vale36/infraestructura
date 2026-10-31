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

    def test_existing_docker_provider_and_ports_are_preserved(self):
        service = self.configuration["services"]["reverse-proxy"]
        docker_socket = next(
            volume
            for volume in service["volumes"]
            if volume["target"] == "/var/run/docker.sock"
        )
        self.assertEqual(docker_socket["source"], "/var/run/docker.sock")
        self.assertTrue(docker_socket["read_only"])
        self.assertEqual(
            {port["published"] for port in service["ports"]},
            {"80", "443", "6379", "27017"},
        )
        self.assertEqual(service["labels"]["traefik.enable"], "true")
        self.assertEqual(service["labels"]["traefik.http.routers.traefik"], "true")

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

        preparation_script = (ROOT / "scripts/prepare-consul-token.ps1").read_text(
            encoding="utf-8"
        )
        self.assertIn("traefik.token", preparation_script)
        self.assertIn("traefik.generated.yml", preparation_script)

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
