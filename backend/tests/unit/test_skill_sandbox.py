"""Unit tests for SkillSandbox Docker container management.

Per D-20, D-21, D-23 to D-28: Docker container lifecycle with security hardening.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.services.skill.sandbox import ContainerInfo, SkillSandbox


class MockSettings:
    """Minimal settings mock for sandbox tests."""

    skill_sandbox_memory = "256m"
    skill_sandbox_cpus = 1.0
    skill_sandbox_pids_limit = 100


@pytest.fixture
def mock_docker():
    """Create a mocked Docker client."""
    with patch("app.services.skill.sandbox.docker") as mock_docker_mod:
        mock_client = MagicMock()
        mock_docker_mod.from_env.return_value = mock_client
        mock_docker_mod.errors.NotFound = Exception
        yield mock_client


@pytest.fixture
def sandbox(mock_docker):
    """Create a SkillSandbox with mocked Docker."""
    return SkillSandbox(MockSettings())


class TestStartServiceContainer:
    """Test service-type container creation with security hardening."""

    def test_creates_container_with_correct_options(self, sandbox, mock_docker):
        """Per D-20, D-23: Service container has security hardening."""
        mock_container = MagicMock()
        mock_container.id = "abc123"
        mock_docker.containers.run.return_value = mock_container

        result = sandbox.start_service_container(
            skill_name="weather-query",
            extract_path="/tmp/nextflow/skills/weather-query",
            permissions={"network": True},
        )

        # Verify container was created
        mock_docker.containers.run.assert_called_once()
        call_kwargs = mock_docker.containers.run.call_args[1]

        # Container naming (per D-20)
        assert call_kwargs["name"] == "nextflow-skill-weather-query"
        assert call_kwargs["image"] == "nextflow-skill-base:latest"

        # Security hardening (per D-23 to D-28)
        assert call_kwargs["cap_drop"] == ["ALL"]
        assert call_kwargs["security_opt"] == ["no-new-privileges"]
        assert call_kwargs["read_only"] is True
        assert call_kwargs["user"] == "1000:1000"
        assert call_kwargs["mem_limit"] == "256m"
        assert call_kwargs["cpus"] == 1.0
        assert call_kwargs["pids_limit"] == 100

        # Network mode: bridge when network permission granted
        assert call_kwargs["network_mode"] == "bridge"

        # Volume mount: skill files read-only
        assert call_kwargs["volumes"] == {
            "/tmp/nextflow/skills/weather-query": {"bind": "/skill", "mode": "ro"}
        }

        # Tmpfs for writable temp space
        assert call_kwargs["tmpfs"] == {"/tmp": "size=50m"}

        # Service container is detached and NOT auto-removed
        assert call_kwargs["detach"] is True
        assert call_kwargs["auto_remove"] is False

        # Labels for management
        assert call_kwargs["labels"]["nextflow.managed"] == "true"
        assert call_kwargs["labels"]["nextflow.skill"] == "weather-query"

        # Command runs sidecar
        assert call_kwargs["command"] == ["python", "/sidecar/sidecar.py"]

        # Return value is ContainerInfo
        assert isinstance(result, ContainerInfo)
        assert result.container_id == "abc123"
        assert result.name == "nextflow-skill-weather-query"
        assert result.skill_name == "weather-query"

    def test_network_mode_none_when_no_network_permission(
        self, sandbox, mock_docker
    ):
        """Per D-23: No network access by default."""
        mock_container = MagicMock()
        mock_container.id = "def456"
        mock_docker.containers.run.return_value = mock_container

        sandbox.start_service_container(
            skill_name="isolated-skill",
            extract_path="/tmp/test",
            permissions={"network": False},
        )

        call_kwargs = mock_docker.containers.run.call_args[1]
        assert call_kwargs["network_mode"] == "none"

    def test_network_mode_none_when_no_permissions(self, sandbox, mock_docker):
        """Per D-23: Default is no network."""
        mock_container = MagicMock()
        mock_container.id = "def456"
        mock_docker.containers.run.return_value = mock_container

        sandbox.start_service_container(
            skill_name="no-perm-skill",
            extract_path="/tmp/test",
        )

        call_kwargs = mock_docker.containers.run.call_args[1]
        assert call_kwargs["network_mode"] == "none"


class TestStopContainer:
    """Test container stop and removal."""

    def test_stops_and_removes_container(self, sandbox, mock_docker):
        """Stop container stops then removes."""
        mock_container = MagicMock()
        mock_docker.containers.get.return_value = mock_container

        sandbox.stop_container("nextflow-skill-weather-query")

        mock_docker.containers.get.assert_called_once_with(
            "nextflow-skill-weather-query"
        )
        mock_container.stop.assert_called_once_with(timeout=5)
        mock_container.remove.assert_called_once()

    def test_handles_not_found_gracefully(self, sandbox, mock_docker):
        """No error if container already gone."""
        mock_docker.containers.get.side_effect = Exception("Not found")

        # Should not raise
        sandbox.stop_container("nextflow-skill-nonexistent")


class TestRunScript:
    """Test one-shot script-type container execution."""

    def test_runs_script_and_captures_output(self, sandbox, mock_docker):
        """Per D-21: Script runs once, captures output, auto-removes."""
        import json

        expected_output = {"result": "sunny", "temp": 72}
        mock_docker.containers.run.return_value = json.dumps(
            expected_output
        ).encode("utf-8")

        result = sandbox.run_script(
            skill_name="weather-query",
            extract_path="/tmp/nextflow/skills/weather-query",
            tool_file="get_weather",
            params={"city": "NYC"},
            timeout=30.0,
        )

        mock_docker.containers.run.assert_called_once()
        call_kwargs = mock_docker.containers.run.call_args[1]

        # Script container runs the specific tool file
        assert call_kwargs["command"] == ["python", "/skill/script/get_weather"]

        # Security hardening
        assert call_kwargs["cap_drop"] == ["ALL"]
        assert call_kwargs["security_opt"] == ["no-new-privileges"]
        assert call_kwargs["read_only"] is True
        assert call_kwargs["user"] == "1000:1000"

        # Script container is auto-removed and NOT detached
        assert call_kwargs["auto_remove"] is True
        assert call_kwargs["detach"] is False

        # Script containers never have network
        assert call_kwargs["network_mode"] == "none"

        # Returns parsed JSON output
        assert result == expected_output

    def test_raises_on_script_failure(self, sandbox, mock_docker):
        """Script failure propagates exception."""
        mock_docker.containers.run.side_effect = Exception("Script crashed")

        with pytest.raises(Exception, match="Script crashed"):
            sandbox.run_script(
                skill_name="bad-skill",
                extract_path="/tmp/test",
                tool_file="fail",
                params={},
            )


class TestCleanupStale:
    """Test stale container cleanup."""

    def test_removes_stale_containers(self, sandbox, mock_docker):
        """Per Pitfall 2: Remove all nextflow.managed containers on startup."""
        mock_c1 = MagicMock()
        mock_c2 = MagicMock()
        mock_docker.containers.list.return_value = [mock_c1, mock_c2]

        count = sandbox.cleanup_stale()

        mock_docker.containers.list.assert_called_once_with(
            filters={"label": "nextflow.managed=true"}, all=True
        )
        assert count == 2
        mock_c1.remove.assert_called_once_with(force=True)
        mock_c2.remove.assert_called_once_with(force=True)

    def test_handles_removal_failure(self, sandbox, mock_docker):
        """Gracefully handles individual container removal failures."""
        mock_c1 = MagicMock()
        mock_c1.remove.side_effect = Exception("Cannot remove")
        mock_docker.containers.list.return_value = [mock_c1]

        count = sandbox.cleanup_stale()
        assert count == 0

    def test_returns_zero_when_no_stale(self, sandbox, mock_docker):
        """No stale containers returns 0."""
        mock_docker.containers.list.return_value = []

        count = sandbox.cleanup_stale()
        assert count == 0
