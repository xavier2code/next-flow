"""TDD tests for SKILL.md validator, ZIP validator, and skill type inference.

Tests cover:
- parse_skill_manifest: YAML frontmatter parsing and validation
- validate_skill_zip: ZIP structure, path safety, tool-script matching
- infer_skill_type: knowledge/script/service type inference
"""
import io
import zipfile

import pytest

from app.services.skill.errors import SkillValidationError


# ---------------------------------------------------------------------------
# Helpers to build in-memory ZIP archives
# ---------------------------------------------------------------------------

def _make_zip(files: dict[str, str]) -> bytes:
    """Create a ZIP archive in memory. ``files`` maps path -> content."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, content in files.items():
            zf.writestr(path, content)
    buf.seek(0)
    return buf.read()


VALID_SKILL_MD = """\
---
name: weather
version: "1.0.0"
description: A weather skill
tools:
  - name: get_weather
    description: Get current weather
    parameters:
      type: object
      properties:
        city:
          type: string
      required:
        - city
permissions:
  network: true
---

# Weather Skill

This skill fetches weather data.
"""

VALID_SKILL_MD_NO_TOOLS = """\
---
name: docs
version: "1.0.0"
description: Documentation skill
---

# Docs Skill
"""


# ---------------------------------------------------------------------------
# parse_skill_manifest tests
# ---------------------------------------------------------------------------

class TestParseSkillManifest:
    """Tests for parse_skill_manifest."""

    def test_valid_manifest_returns_tuple(self):
        from app.services.skill.validator import parse_skill_manifest

        metadata, body = parse_skill_manifest(VALID_SKILL_MD)
        assert metadata["name"] == "weather"
        assert metadata["version"] == "1.0.0"
        assert metadata["description"] == "A weather skill"
        assert "# Weather Skill" in body

    def test_missing_name_raises(self):
        from app.services.skill.validator import parse_skill_manifest

        content = "---\nversion: '1.0'\ndescription: test\n---\nBody"
        with pytest.raises(SkillValidationError, match="name"):
            parse_skill_manifest(content)

    def test_missing_version_raises(self):
        from app.services.skill.validator import parse_skill_manifest

        content = "---\nname: test\ndescription: test\n---\nBody"
        with pytest.raises(SkillValidationError, match="version"):
            parse_skill_manifest(content)

    def test_missing_description_raises(self):
        from app.services.skill.validator import parse_skill_manifest

        content = "---\nname: test\nversion: '1.0'\n---\nBody"
        with pytest.raises(SkillValidationError, match="description"):
            parse_skill_manifest(content)

    def test_invalid_tool_missing_name_raises(self):
        from app.services.skill.validator import parse_skill_manifest

        content = """\
---
name: test
version: '1.0'
description: test
tools:
  - description: missing name field
---
Body"""
        with pytest.raises(SkillValidationError, match="[Tt]ool.*name"):
            parse_skill_manifest(content)

    def test_invalid_tool_missing_description_raises(self):
        from app.services.skill.validator import parse_skill_manifest

        content = """\
---
name: test
version: '1.0'
description: test
tools:
  - name: my_tool
---
Body"""
        with pytest.raises(SkillValidationError, match="[Tt]ool.*description"):
            parse_skill_manifest(content)

    def test_parameters_not_dict_raises(self):
        from app.services.skill.validator import parse_skill_manifest

        content = """\
---
name: test
version: '1.0'
description: test
tools:
  - name: t
    description: d
    parameters: "not a dict"
---
Body"""
        with pytest.raises(SkillValidationError, match="parameters"):
            parse_skill_manifest(content)

    def test_valid_manifest_with_tools(self):
        from app.services.skill.validator import parse_skill_manifest

        metadata, body = parse_skill_manifest(VALID_SKILL_MD)
        assert len(metadata["tools"]) == 1
        tool = metadata["tools"][0]
        assert tool["name"] == "get_weather"
        assert tool["description"] == "Get current weather"

    def test_valid_manifest_no_tools(self):
        from app.services.skill.validator import parse_skill_manifest

        metadata, body = parse_skill_manifest(VALID_SKILL_MD_NO_TOOLS)
        assert metadata["name"] == "docs"
        assert "tools" not in metadata or metadata.get("tools") is None


# ---------------------------------------------------------------------------
# validate_skill_zip tests
# ---------------------------------------------------------------------------

class TestValidateSkillZip:
    """Tests for validate_skill_zip."""

    def test_valid_zip_returns_metadata(self, tmp_path):
        from app.services.skill.validator import validate_skill_zip

        zip_data = _make_zip({
            "SKILL.md": VALID_SKILL_MD,
            "script/get_weather.py": "def run(): pass",
        })
        zip_path = tmp_path / "test.zip"
        zip_path.write_bytes(zip_data)

        result = validate_skill_zip(str(zip_path))
        assert "metadata" in result
        assert "body" in result
        assert "skill_type" in result
        assert result["metadata"]["name"] == "weather"

    def test_missing_skill_md_raises(self, tmp_path):
        from app.services.skill.validator import validate_skill_zip

        zip_data = _make_zip({"readme.txt": "hello"})
        zip_path = tmp_path / "test.zip"
        zip_path.write_bytes(zip_data)

        with pytest.raises(SkillValidationError, match="SKILL.md"):
            validate_skill_zip(str(zip_path))

    def test_path_traversal_raises(self, tmp_path):
        from app.services.skill.validator import validate_skill_zip

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("SKILL.md", VALID_SKILL_MD)
            zf.writestr("../etc/passwd", "malicious")
        buf.seek(0)
        zip_path = tmp_path / "evil.zip"
        zip_path.write_bytes(buf.getvalue())

        with pytest.raises(SkillValidationError, match="[Pp]ath"):
            validate_skill_zip(str(zip_path))

    def test_tool_script_mismatch_missing_script_raises(self, tmp_path):
        from app.services.skill.validator import validate_skill_zip

        zip_data = _make_zip({"SKILL.md": VALID_SKILL_MD})
        zip_path = tmp_path / "test.zip"
        zip_path.write_bytes(zip_data)

        with pytest.raises(SkillValidationError, match="script.*get_weather"):
            validate_skill_zip(str(zip_path))

    def test_extra_script_not_in_tools_raises(self, tmp_path):
        from app.services.skill.validator import validate_skill_zip

        zip_data = _make_zip({
            "SKILL.md": VALID_SKILL_MD,
            "script/get_weather.py": "def run(): pass",
            "script/rogue.py": "def run(): pass",
        })
        zip_path = tmp_path / "test.zip"
        zip_path.write_bytes(zip_data)

        with pytest.raises(SkillValidationError, match="rogue"):
            validate_skill_zip(str(zip_path))

    def test_knowledge_zip_no_script_dir(self, tmp_path):
        from app.services.skill.validator import validate_skill_zip

        zip_data = _make_zip({
            "SKILL.md": VALID_SKILL_MD_NO_TOOLS,
            "data/info.txt": "some knowledge",
        })
        zip_path = tmp_path / "test.zip"
        zip_path.write_bytes(zip_data)

        result = validate_skill_zip(str(zip_path))
        assert result["skill_type"] == "knowledge"


# ---------------------------------------------------------------------------
# infer_skill_type tests
# ---------------------------------------------------------------------------

class TestInferSkillType:
    """Tests for infer_skill_type."""

    def test_knowledge_no_script(self):
        from app.services.skill.validator import infer_skill_type

        result = infer_skill_type({}, has_script_dir=False)
        assert result == "knowledge"

    def test_service_script_with_tools(self):
        from app.services.skill.validator import infer_skill_type

        metadata = {"tools": [{"name": "t", "description": "d"}]}
        result = infer_skill_type(metadata, has_script_dir=True)
        assert result == "service"

    def test_script_no_tools(self):
        from app.services.skill.validator import infer_skill_type

        result = infer_skill_type({}, has_script_dir=True)
        assert result == "script"

    def test_service_empty_tools_list_treated_as_script(self):
        from app.services.skill.validator import infer_skill_type

        # Empty tools list means no tools declared
        result = infer_skill_type({"tools": []}, has_script_dir=True)
        assert result == "script"
