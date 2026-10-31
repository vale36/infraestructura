import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "docker-compose.yml"


class MongoComposeTests(unittest.TestCase):
    """MongoDB compartida por las dos persistencias (primera capa: infraestructura)."""

    def setUp(self):
        result = subprocess.run(
            ["docker", "compose", "-f", str(COMPOSE), "config", "--format", "json"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.configuration = json.loads(result.stdout)
        self.service = self.configuration["services"]["mongodb"]

    def test_the_service_is_reachable_as_mongodb_in_redutn(self):
        self.assertIn("redutn", self.service["networks"])
        self.assertTrue(self.configuration["networks"]["redutn"]["external"])
        self.assertEqual(self.service["container_name"], "mongodb")

    def test_data_survives_in_a_named_volume(self):
        volume = next(v for v in self.service["volumes"] if v["target"] == "/data/db")
        self.assertEqual(volume["type"], "volume")
        self.assertEqual(
            self.configuration["volumes"][volume["source"]]["name"],
            "proyecto-mongo-data",
        )

    def test_it_does_not_publish_ports_on_the_host(self):
        # Traefik ya usa 27017 como entrypoint TCP; los servicios llegan por la red.
        self.assertNotIn("ports", self.service)

    def test_it_has_a_real_healthcheck(self):
        command = " ".join(self.service["healthcheck"]["test"])
        self.assertIn("ping", command)

    def test_it_uses_the_same_image_as_the_rest_of_the_project(self):
        self.assertEqual(self.service["image"], "mongo:7.0")


if __name__ == "__main__":
    unittest.main()
