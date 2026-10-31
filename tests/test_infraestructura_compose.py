import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "docker-compose.yml"


class InfraestructuraComposeTests(unittest.TestCase):
    """Primera capa del sistema en un solo compose: Consul (con su bootstrap de ACL),
    Traefik, MongoDB y Redis. Los microservicios van en un segundo compose, después."""

    def setUp(self):
        result = subprocess.run(
            ["docker", "compose", "-f", str(COMPOSE), "config", "--format", "json"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.configuration = json.loads(result.stdout)
        self.services = self.configuration["services"]

    def test_brings_up_every_infrastructure_component(self):
        self.assertEqual(self.configuration["name"], "infraestructura")
        for service in ("consul", "consul-bootstrap", "reverse-proxy", "mongodb", "redis"):
            self.assertIn(service, self.services)

    def test_traefik_starts_after_the_acl_bootstrap_left_its_token(self):
        dependency = self.services["reverse-proxy"]["depends_on"]["consul-bootstrap"]
        self.assertEqual(dependency["condition"], "service_completed_successfully")
        self.assertIn(
            "--configFile=/etc/traefik/config/traefik.generated.yml",
            self.services["reverse-proxy"]["command"],
        )

    def test_everything_shares_the_redutn_network(self):
        for name, service in self.services.items():
            self.assertIn("redutn", service["networks"], name)
        self.assertTrue(self.configuration["networks"]["redutn"]["external"])

    def test_only_traefik_and_the_local_consul_ui_publish_ports(self):
        publicados = {name for name, service in self.services.items() if service.get("ports")}
        self.assertEqual(publicados, {"reverse-proxy", "consul"})
        self.assertEqual(self.services["consul"]["ports"][0]["host_ip"], "127.0.0.1")


if __name__ == "__main__":
    unittest.main()
