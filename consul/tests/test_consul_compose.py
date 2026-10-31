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
            "orchestrator.token",
        ):
            self.assertIn(token_name, script)

    def test_consul_server_configuration_enables_ui_and_acl(self):
        configuration = (ROOT / "config/consul.hcl").read_text(encoding="utf-8")
        self.assertIn('server = true', configuration)
        self.assertIn('enabled = true', configuration)
        self.assertIn('default_policy = "deny"', configuration)
        self.assertIn('ui_config', configuration)

    def test_microservices_acl_policy_is_limited_to_services_and_reads(self):
        policy = (ROOT / "config/policies/microservices.hcl").read_text(encoding="utf-8")
        self.assertNotIn('node_prefix "consul-server-dev"', policy)
        self.assertIn('service_prefix ""', policy)
        self.assertIn('key_prefix "config/"', policy)

    def test_orchestrator_acl_policy_only_reads_registered_microservices(self):
        policy_path = ROOT / "config/policies/orchestrator.hcl"
        policy = policy_path.read_text(encoding="utf-8")
        for service_name in (
            "validacion-pdf",
            "extraccion",
            "persistencia-consultas",
            "persistencia-actualizaciones",
        ):
            self.assertIn(f'service_prefix "{service_name}"', policy)
        self.assertIn('policy = "read"', policy)
        self.assertNotIn("write", policy.replace('policy = "read"', ""))
        self.assertIn('node_prefix ""', policy)
        self.assertIn('policy = "read"', policy)
        self.assertNotIn("key_prefix", policy)

    def test_readme_documents_orchestrator_token_and_real_service_names(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("orchestrator.token", readme)
        self.assertIn("prepare-orchestrator-token.ps1", readme)
        self.assertIn("extraccion", readme)
        self.assertNotIn("extraccion-texto", readme)

    def test_token_preparation_scripts_verify_and_prepare_from_live_consul(self):
        for script_name in (
            "prepare-microservices-token.ps1",
            "prepare-orchestrator-token.ps1",
        ):
            script = (ROOT / "scripts" / script_name).read_text(encoding="utf-8")
            self.assertIn("acl token read", script)
            self.assertIn("-self", script)
            self.assertIn("generated", script)

    def test_agent_token_policy_and_persisted_generated_config_are_present(self):
        policy = (ROOT / "config/policies/consul-agent.hcl").read_text(encoding="utf-8")
        script = (ROOT / "scripts/bootstrap-acl.sh").read_text(encoding="utf-8")
        ignore = (ROOT / "config/.gitignore").read_text(encoding="utf-8")
        self.assertIn('node_prefix "consul-server-dev"', policy)
        self.assertIn('agent_prefix "consul-server-dev"', policy)
        self.assertIn("/consul/generated-config/consul-agent.hcl", script)
        self.assertIn("generated/", ignore)

    def test_acl_bootstrap_updates_policy_changes_for_existing_tokens(self):
        script = (ROOT / "scripts/bootstrap-acl.sh").read_text(encoding="utf-8")
        self.assertIn("consul acl policy update", script)

    def test_acl_bootstrap_can_persist_agent_config_for_consul(self):
        volumes = self.services["consul-bootstrap"]["volumes"]
        generated_mount = next(
            volume
            for volume in volumes
            if volume.get("target") == "/consul/generated-config"
        )
        self.assertEqual(generated_mount["type"], "volume")
        self.assertEqual(generated_mount["source"], "consul_generated_config")
        self.assertFalse(generated_mount.get("read_only", False))


    def test_bootstrap_leaves_the_host_files_ready_without_extra_scripts(self):
        # Con un solo `docker compose up` de la infraestructura: el bootstrap deja los
        # tokens de microservicios y Orquestador (Docker secrets) y la configuración de
        # Traefik con su token, como hacen los scripts prepare-*.ps1.
        targets = {
            volume["target"]: volume
            for volume in self.services["consul-bootstrap"]["volumes"]
        }
        self.assertEqual(targets["/consul/host-generated"]["type"], "bind")
        self.assertTrue(
            targets["/consul/host-generated"]["source"].replace("\\", "/").endswith("consul/generated")
        )
        self.assertEqual(targets["/traefik-config"]["type"], "bind")
        self.assertTrue(
            targets["/traefik-config"]["source"].replace("\\", "/").endswith("traefik/config")
        )

        script = (ROOT / "scripts/bootstrap-acl.sh").read_text(encoding="utf-8")
        self.assertIn("host-generated/microservices.token", script)
        self.assertIn("host-generated/orchestrator.token", script)
        self.assertIn("traefik.generated.yml", script)
        self.assertNotIn("echo \"$traefik_token", script)

    def test_host_token_files_are_readable_by_the_services_unprivileged_user(self):
        # Los microservicios corren como appuser y reciben el archivo como Docker secret:
        # con el umask 077 del bootstrap no lo podrían leer y no arrancarían.
        script = (ROOT / "scripts/bootstrap-acl.sh").read_text(encoding="utf-8")
        self.assertIn(
            "chmod 644 /consul/host-generated/microservices.token "
            "/consul/host-generated/orchestrator.token",
            script,
        )

if __name__ == "__main__":
    unittest.main()
