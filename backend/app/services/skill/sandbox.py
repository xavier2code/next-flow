"""Docker-based sandbox for skill container management.

Per D-20, D-21, D-23 to D-28: Container lifecycle with security hardening.
- Service-type: persistent container with sidecar HTTP server
- Script-type: one-shot execution with output capture
- Stale cleanup on startup
"""

import json
import os
from dataclasses import dataclass

# Docker SDK 7.x uses nano_cpus (billionths of a CPU) instead of cpus
NANO_CPUS_PER_CORE = 1_000_000_000

import docker
import structlog

logger = structlog.get_logger()


@dataclass
class ContainerInfo:
    """Information about a running skill container."""

    container_id: str
    name: str
    url: str  # e.g., "http://localhost:PORT" or Docker network URL
    skill_name: str


class SkillSandbox:
    """Manages Docker containers for skill sandbox execution.

    Per D-20, D-21, D-23 to D-28:
    - Security hardening: cap_drop ALL, no-new-privileges, read-only fs, non-root user
    - Service-type: persistent container until explicit disable
    - Script-type: run-once with auto-remove and output capture
    """

    def __init__(self, settings) -> None:
        self._settings = settings
        self._docker = docker.from_env()
        self._network = os.environ.get("COMPOSE_NETWORK_NAME", "")

    def start_service_container(
        self,
        skill_name: str,
        extract_path: str,
        permissions: dict | None = None,
    ) -> ContainerInfo:
        """Start a persistent container for service-type skill.

        Per D-20, D-23: Persistent container with sidecar HTTP server.
        Security hardening per D-24 to D-28.

        Args:
            skill_name: Unique skill name.
            extract_path: Path to extracted skill files.
            permissions: Skill permissions dict (e.g., {"network": True}).

        Returns:
            ContainerInfo with the container's HTTP URL.
        """
        permissions = permissions or {}
        container_name = f"nextflow-skill-{skill_name}"
        use_network = permissions.get("network", False)
        network_mode = "bridge" if use_network else "none"
        # When running inside Docker Compose, connect skill containers to
        # the compose network for DNS resolution (e.g., backend -> backend:8000)
        # Only set network when using bridge mode (cannot combine with network_mode)
        network_name = self._network if (use_network and self._network) else None

        run_kwargs: dict = {
            "image": "nextflow-skill-base:latest",
            "command": ["python", "/sidecar/sidecar.py"],
            "volumes": {extract_path: {"bind": "/skill", "mode": "ro"}},
            "mem_limit": self._settings.skill_sandbox_memory,
            "nano_cpus": int(self._settings.skill_sandbox_cpus * NANO_CPUS_PER_CORE),
            "pids_limit": self._settings.skill_sandbox_pids_limit,
            "security_opt": ["no-new-privileges"],
            "cap_drop": ["ALL"],
            "network_mode": network_mode,
            "read_only": True,
            "tmpfs": {"/tmp": "size=50m"},
            "detach": True,
            "name": container_name,
            "auto_remove": False,
            "user": "1000:1000",
            "labels": {
                "nextflow.managed": "true",
                "nextflow.skill": skill_name,
            },
        }
        if network_name:
            run_kwargs["network"] = network_name

        container = self._docker.containers.run(**run_kwargs)
        # Container hostname equals container_name in Docker network
        url = f"http://{container_name}:8080"
        logger.info(
            "skill_container_started",
            skill=skill_name,
            container=container.id,
        )
        return ContainerInfo(
            container_id=container.id,
            name=container_name,
            url=url,
            skill_name=skill_name,
        )

    def stop_container(self, container_name: str) -> None:
        """Stop and remove a container by name."""
        try:
            container = self._docker.containers.get(container_name)
            container.stop(timeout=5)
            container.remove()
            logger.info("skill_container_stopped", container=container_name)
        except docker.errors.NotFound:
            logger.debug("skill_container_not_found", container=container_name)

    def run_script(
        self,
        skill_name: str,
        extract_path: str,
        tool_file: str,
        params: dict,
        timeout: float = 30.0,
    ) -> dict:
        """Run a one-shot script-type skill container.

        Per D-21: On-demand execution -- start, run, capture output, destroy.

        Args:
            skill_name: Unique skill name.
            extract_path: Path to extracted skill files.
            tool_file: Script filename (without .py extension).
            params: Parameters to pass to the script.
            timeout: Execution timeout in seconds.

        Returns:
            Parsed JSON output from the script.

        Raises:
            Exception: If script execution fails.
        """
        container_name = f"nextflow-skill-{skill_name}-{tool_file}"
        try:
            output = self._docker.containers.run(
                image="nextflow-skill-base:latest",
                command=["python", f"/skill/script/{tool_file}"],
                volumes={extract_path: {"bind": "/skill", "mode": "ro"}},
                mem_limit=self._settings.skill_sandbox_memory,
                nano_cpus=int(self._settings.skill_sandbox_cpus * NANO_CPUS_PER_CORE),
                pids_limit=self._settings.skill_sandbox_pids_limit,
                security_opt=["no-new-privileges"],
                cap_drop=["ALL"],
                network_mode="none",
                read_only=True,
                tmpfs={"/tmp": "size=50m"},
                detach=False,
                auto_remove=True,
                user="1000:1000",
                labels={"nextflow.managed": "true"},
                timeout=int(timeout),
            )
            # output is bytes from stdout
            return json.loads(output.decode("utf-8"))
        except Exception as e:
            logger.error(
                "skill_script_failed", skill=skill_name, error=str(e)
            )
            raise

    def cleanup_stale(self) -> int:
        """Remove all containers with nextflow.managed=true label.

        Per Pitfall 2: Clean up stale containers on startup.

        Returns:
            Number of containers removed.
        """
        containers = self._docker.containers.list(
            filters={"label": "nextflow.managed=true"}, all=True
        )
        count = 0
        for c in containers:
            try:
                c.remove(force=True)
                count += 1
            except Exception:
                pass
        if count:
            logger.info("skill_stale_containers_cleaned", count=count)
        return count
