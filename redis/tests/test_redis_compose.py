import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "docker-compose.yml"


class RedisComposeTests(unittest.TestCase):
    """Redis compartido por las dos persistencias: solo caché y lock (contrato 1.2.0)."""

    def setUp(self):
        result = subprocess.run(
            ["docker", "compose", "-f", str(COMPOSE), "config", "--format", "json"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.configuration = json.loads(result.stdout)
        self.service = self.configuration["services"]["redis"]

    def test_the_service_is_reachable_as_redis_in_redutn(self):
        self.assertIn("redutn", self.service["networks"])
        self.assertTrue(self.configuration["networks"]["redutn"]["external"])
        self.assertEqual(self.service["container_name"], "redis")

    def test_it_runs_without_snapshot_or_append_only_file(self):
        command = self.service["command"]
        self.assertEqual(command[command.index("--save") + 1], "")
        self.assertEqual(command[command.index("--appendonly") + 1], "no")

    def test_it_has_no_volume_so_it_starts_empty(self):
        self.assertNotIn("volumes", self.service)

    def test_it_does_not_publish_ports_on_the_host(self):
        # Traefik ya usa 6379 como entrypoint TCP; los servicios llegan por la red.
        self.assertNotIn("ports", self.service)

    def test_it_has_a_real_healthcheck(self):
        command = " ".join(self.service["healthcheck"]["test"])
        self.assertIn("ping", command)


if __name__ == "__main__":
    unittest.main()
