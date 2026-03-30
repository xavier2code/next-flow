"""Task 1 TDD tests: Infrastructure setup -- dependencies, MinIO, config, Skill model.

These tests verify that the skill infrastructure is properly configured:
- Skill model has all required extended fields
- Settings has MinIO and sandbox configuration attributes
- docker-compose.yml includes MinIO service
- pyproject.toml includes required dependencies
"""
import pathlib

import pytest


class TestSkillModel:
    """Test 1: Skill model has all required fields."""

    def test_skill_has_version_field(self):
        from app.models.skill import Skill

        col = Skill.__table__.c.version
        assert col is not None

    def test_skill_has_permissions_field(self):
        from app.models.skill import Skill

        col = Skill.__table__.c.permissions
        assert col is not None

    def test_skill_has_package_url_field(self):
        from app.models.skill import Skill

        col = Skill.__table__.c.package_url
        assert col is not None

    def test_skill_has_skill_type_field(self):
        from app.models.skill import Skill

        col = Skill.__table__.c.skill_type
        assert col is not None

    def test_skill_type_default_is_knowledge(self):
        from app.models.skill import Skill

        col = Skill.__table__.c.skill_type
        assert col.default.arg == "knowledge"


class TestSettings:
    """Test 2: Settings has minio_* and skill_sandbox_* attributes."""

    def test_minio_endpoint(self):
        from app.core.config import Settings

        fields = Settings.model_fields
        assert "minio_endpoint" in fields

    def test_minio_access_key(self):
        from app.core.config import Settings

        fields = Settings.model_fields
        assert "minio_access_key" in fields

    def test_minio_secret_key(self):
        from app.core.config import Settings

        fields = Settings.model_fields
        assert "minio_secret_key" in fields

    def test_minio_secure(self):
        from app.core.config import Settings

        fields = Settings.model_fields
        assert "minio_secure" in fields

    def test_minio_bucket(self):
        from app.core.config import Settings

        fields = Settings.model_fields
        assert "minio_bucket" in fields

    def test_skill_sandbox_memory(self):
        from app.core.config import Settings

        fields = Settings.model_fields
        assert "skill_sandbox_memory" in fields

    def test_skill_sandbox_cpus(self):
        from app.core.config import Settings

        fields = Settings.model_fields
        assert "skill_sandbox_cpus" in fields

    def test_skill_sandbox_timeout(self):
        from app.core.config import Settings

        fields = Settings.model_fields
        assert "skill_sandbox_timeout" in fields

    def test_skill_sandbox_pids_limit(self):
        from app.core.config import Settings

        fields = Settings.model_fields
        assert "skill_sandbox_pids_limit" in fields

    def test_skill_health_check_interval(self):
        from app.core.config import Settings

        fields = Settings.model_fields
        assert "skill_health_check_interval" in fields


class TestDockerCompose:
    """Test 3: docker-compose.yml contains minio service."""

    def test_minio_service_exists(self):
        import yaml

        project_root = pathlib.Path(__file__).resolve().parent.parent.parent.parent
        actual = project_root / "docker-compose.yml"
        with open(actual) as f:
            data = yaml.safe_load(f)
        assert "minio" in data.get("services", {})

    def test_minio_ports(self):
        import yaml

        project_root = pathlib.Path(__file__).resolve().parent.parent.parent.parent
        actual = project_root / "docker-compose.yml"
        with open(actual) as f:
            data = yaml.safe_load(f)
        minio = data["services"]["minio"]
        ports = minio.get("ports", [])
        port_nums = []
        for p in ports:
            if isinstance(p, str):
                port_nums.append(int(p.split(":")[0]))
            elif isinstance(p, int):
                port_nums.append(p)
        assert 9000 in port_nums
        assert 9001 in port_nums


class TestDependencies:
    """Test 4: pyproject.toml contains minio, docker, python-frontmatter."""

    def test_minio_dependency(self):
        pyproject = pathlib.Path(__file__).resolve().parent.parent.parent / "pyproject.toml"
        content = pyproject.read_text()
        assert "minio" in content.lower()

    def test_docker_dependency(self):
        pyproject = pathlib.Path(__file__).resolve().parent.parent.parent / "pyproject.toml"
        content = pyproject.read_text()
        # Match "docker" as a dependency line, not just the word appearing elsewhere
        lines = content.split("\n")
        dep_lines = [l for l in lines if "docker" in l.lower() and ("=" in l or ">=" in l)]
        assert len(dep_lines) > 0, "docker dependency not found in pyproject.toml"

    def test_python_frontmatter_dependency(self):
        pyproject = pathlib.Path(__file__).resolve().parent.parent.parent / "pyproject.toml"
        content = pyproject.read_text()
        assert "python-frontmatter" in content.lower()
