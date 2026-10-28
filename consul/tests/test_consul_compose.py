import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "docker-compose.yml"


class ConsulComposeTests(unittest.TestCase):
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

    def test_consul_is_the_only_exposed_service(self):
        consul_ports = self.services["consul"]["ports"]
        self.assertEqual(consul_ports[0]["target"], 8500)
        self.assertEqual(consul_ports[0]["published"], "8500")
        self.assertEqual(consul_ports[0]["host_ip"], "127.0.0.1")
        self.assertNotIn("ports", self.services["consul-bootstrap"])

    def test_consul_uses_persistent_shared_data_and_network(self):
        service = self.services["consul"]
        volume_sources = {volume["source"] for volume in service["volumes"]}
        self.assertIn("consul_data", volume_sources)
        self.assertIn("redutn", service["networks"])
        self.assertTrue(self.configuration["networks"]["redutn"]["external"])
        self.assertEqual(
            self.configuration["volumes"]["consul_data"]["name"],
            "proyecto-consul-data",
        )

    def test_consul_has_a_real_healthcheck(self):
        healthcheck = self.services["consul"]["healthcheck"]
        command = healthcheck["test"]
        self.assertIn("/v1/status/leader", " ".join(command))

    def test_acl_bootstrap_is_healthy_before_token_creation(self):
        bootstrap = self.services["consul-bootstrap"]
        dependency = bootstrap["depends_on"]["consul"]
        self.assertEqual(dependency["condition"], "service_healthy")

        script = (ROOT / "scripts/bootstrap-acl.sh").read_text(encoding="utf-8")
        for token_name in (
            "management.token",
            "ui.token",
            "traefik.token",
            "microservices.token",
        ):
            self.assertIn(token_name, script)

    def test_consul_server_configuration_enables_ui_and_acl(self):
        configuration = (ROOT / "config/consul.hcl").read_text(encoding="utf-8")
        self.assertIn('server = true', configuration)
        self.assertIn('enabled = true', configuration)
        self.assertIn('default_policy = "deny"', configuration)
        self.assertIn('ui_config', configuration)


if __name__ == "__main__":
    unittest.main()
