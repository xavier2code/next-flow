"""SKILL.md frontmatter parser, ZIP structure validator, and skill type inference.

Per design decisions:
- D-01: SKILL.md uses YAML frontmatter with required fields
- D-02: Required fields are name, version, description
- D-03: ZIP must contain SKILL.md at root
- D-04: Tools must have name and description
- D-05: Path safety -- reject traversal attacks
- D-19: Skill type inferred from ZIP structure
- D-29: One-to-one tool-script matching
"""
import zipfile

import frontmatter

from app.services.skill.errors import SkillValidationError

REQUIRED_FIELDS = ("name", "version", "description")


def parse_skill_manifest(skill_md_content: str) -> tuple[dict, str]:
    """Parse SKILL.md content and validate required frontmatter fields.

    Args:
        skill_md_content: Raw SKILL.md file content with YAML frontmatter.

    Returns:
        Tuple of (metadata dict, markdown body string).

    Raises:
        SkillValidationError: If required fields are missing or tools are invalid.
    """
    try:
        post = frontmatter.loads(skill_md_content)
    except Exception as exc:
        raise SkillValidationError(f"Failed to parse SKILL.md: {exc}") from exc

    metadata = dict(post.metadata)

    # Validate required fields
    for field in REQUIRED_FIELDS:
        if field not in metadata or not metadata[field]:
            raise SkillValidationError(
                f"SKILL.md missing required field: '{field}'"
            )

    # Validate tools if present
    tools = metadata.get("tools")
    if tools is not None:
        if not isinstance(tools, list):
            raise SkillValidationError("'tools' must be a list")
        for i, tool in enumerate(tools):
            if not isinstance(tool, dict):
                raise SkillValidationError(f"Tool entry {i} must be a dict")
            if "name" not in tool or not tool["name"]:
                raise SkillValidationError(
                    f"Tool entry {i} missing required field: 'name'"
                )
            if "description" not in tool or not tool["description"]:
                raise SkillValidationError(
                    f"Tool entry {i} missing required field: 'description'"
                )
            # Validate parameters if present
            params = tool.get("parameters")
            if params is not None:
                if not isinstance(params, dict):
                    raise SkillValidationError(
                        f"Tool '{tool['name']}' parameters must be a dict"
                    )

    return metadata, post.content


def validate_skill_zip(
    zip_path: str,
    target_dir: str | None = None,
) -> dict:
    """Validate a skill ZIP package structure and contents.

    Checks:
    - SKILL.md exists at root
    - No path traversal in filenames
    - Declared tools have matching script files
    - No extra script files without tool declarations

    Args:
        zip_path: Path to the ZIP file.
        target_dir: Optional extraction target directory (for path resolution).

    Returns:
        Dict with keys: metadata, body, skill_type.

    Raises:
        SkillValidationError: If validation fails.
    """
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()

            # Check SKILL.md exists at root
            if "SKILL.md" not in names:
                raise SkillValidationError(
                    "ZIP must contain SKILL.md at root level"
                )

            # Check path safety: reject traversal and absolute paths
            for name in names:
                if name.startswith("/") or ".." in name.split("/"):
                    raise SkillValidationError(
                        f"Path traversal detected in ZIP entry: '{name}'"
                    )

            # Parse SKILL.md from ZIP
            skill_md_content = zf.read("SKILL.md").decode("utf-8")
            metadata, body = parse_skill_manifest(skill_md_content)

            # Check for script/ directory presence
            script_files = [
                n for n in names if n.startswith("script/") and n.endswith(".py")
            ]
            has_script_dir = len(script_files) > 0

            # Validate tool-script one-to-one match if tools declared and scripts exist
            tools = metadata.get("tools") or []
            if tools or has_script_dir:
                # Get tool names from manifest
                tool_names = {t["name"] for t in tools}
                # Get script file names (without extension and script/ prefix)
                script_names = {
                    n[len("script/"):-len(".py")]
                    for n in script_files
                }

                # Each declared tool must have a matching .py file
                missing_scripts = tool_names - script_names
                if missing_scripts:
                    raise SkillValidationError(
                        f"Declared tools missing script files: "
                        f"{', '.join(f'script/{s}.py' for s in sorted(missing_scripts))}"
                    )

                # Each script file must be declared as a tool
                extra_scripts = script_names - tool_names
                if extra_scripts:
                    raise SkillValidationError(
                        f"Script files not declared in tools: "
                        f"{', '.join(sorted(extra_scripts))}"
                    )

            skill_type = infer_skill_type(metadata, has_script_dir)

            return {
                "metadata": metadata,
                "body": body,
                "skill_type": skill_type,
            }
    except SkillValidationError:
        raise
    except zipfile.BadZipFile as exc:
        raise SkillValidationError(f"Invalid ZIP file: {exc}") from exc
    except Exception as exc:
        raise SkillValidationError(f"ZIP validation failed: {exc}") from exc


def infer_skill_type(metadata: dict, has_script_dir: bool) -> str:
    """Infer skill type from ZIP structure.

    Per D-19:
    - No script/ directory -> "knowledge"
    - script/ + tools declared -> "service"
    - script/ + no tools declared -> "script"

    Args:
        metadata: Parsed SKILL.md metadata dict.
        has_script_dir: Whether the ZIP contains a script/ directory with .py files.

    Returns:
        One of: "knowledge", "service", "script".
    """
    tools = metadata.get("tools") or []
    has_tools = len(tools) > 0

    if not has_script_dir:
        return "knowledge"
    if has_tools:
        return "service"
    return "script"
