"""SkillManager: lifecycle management with tool registration.

Per D-11, D-12, D-16, D-20, D-21, D-22, D-27, D-32:
Enable/disable skills, register/unregister tools in ToolRegistry,
parse SKILL.md body, store descriptions, health check loop.
"""

from __future__ import annotations

import asyncio
import io
import os
import tempfile
import zipfile
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.skill import Skill
from app.services.skill.handler import SkillToolHandler
from app.services.skill.sandbox import ContainerInfo, SkillSandbox
from app.services.skill.storage import SkillStorage
from app.services.skill.validator import parse_skill_manifest
from app.services.tool_registry import ToolRegistry

logger = structlog.get_logger()


class SkillManager:
    """Manages skill lifecycle: enable/disable, container management, tool registration.

    Per D-11, D-32: Mirrors MCPManager pattern.
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        session_factory: async_sessionmaker[AsyncSession],
        skill_storage: SkillStorage,
        skill_sandbox: SkillSandbox,
        skill_content: dict[str, str],  # {skill_name: SKILL.md body}
        timeout: float = 30.0,
        health_check_interval: float = 30.0,
    ) -> None:
        self._registry = tool_registry
        self._session_factory = session_factory
        self._storage = skill_storage
        self._sandbox = skill_sandbox
        self._skill_content = skill_content  # In-memory cache of SKILL.md bodies
        self._skill_descriptions: dict[str, str] = {}  # {skill_name: description}
        self._timeout = timeout
        self._health_check_interval = health_check_interval
        self.containers: dict[str, ContainerInfo] = {}
        self._health_task: asyncio.Task | None = None

    async def enable_all(self) -> None:
        """Enable all Skills with status='enabled' from DB.

        Per D-32: Platform restart recovery -- read enabled skills, pull ZIPs,
        re-extract, re-start containers, re-register tools.
        """
        self._sandbox.cleanup_stale()
        async with self._session_factory() as db:
            result = await db.execute(
                select(Skill).where(Skill.status == "enabled")
            )
            skills = list(result.scalars().all())
        if not skills:
            logger.info("skill_no_enabled_skills")
            return
        logger.info("skill_enabling_all", count=len(skills))
        for skill in skills:
            try:
                await self._enable_one(skill)
            except Exception as e:
                logger.error(
                    "skill_enable_failed", skill=skill.name, error=str(e)
                )

    async def _enable_one(self, skill: Skill) -> None:
        """Enable a single skill: extract from MinIO, start container, register tools.

        Parses SKILL.md body and stores in _skill_content dict for load_skill tool.
        Stores description in _skill_descriptions for summaries.
        """
        # Download and extract ZIP from MinIO
        zip_data = self._storage.get_package(skill.name, skill.version)
        extract_path = os.path.join(
            tempfile.gettempdir(), "nextflow", "skills", skill.name
        )
        os.makedirs(extract_path, exist_ok=True)

        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
            # Safe extraction (validator already validated this ZIP)
            zf.extractall(extract_path)

            # Parse SKILL.md body and store for load_skill tool
            skill_md_path = os.path.join(extract_path, "SKILL.md")
            if os.path.exists(skill_md_path):
                with open(skill_md_path, "r", encoding="utf-8") as f:
                    skill_md_content = f.read()
                _, body = parse_skill_manifest(skill_md_content)
                self._skill_content[skill.name] = body
                logger.debug(
                    "skill_content_stored",
                    skill=skill.name,
                    body_len=len(body),
                )

        # Store description for get_enabled_skill_summaries (per D-16)
        if skill.description:
            self._skill_descriptions[skill.name] = skill.description

        if skill.skill_type == "service":
            # Start persistent container (per D-20)
            container_info = self._sandbox.start_service_container(
                skill_name=skill.name,
                extract_path=extract_path,
                permissions=skill.permissions or {},
            )
            self.containers[skill.name] = container_info

        elif skill.skill_type == "script":
            # No persistent container -- runs on demand (per D-21)
            pass

        elif skill.skill_type == "knowledge":
            # No container, no tools (per D-22, D-13)
            pass

        # Register tools in ToolRegistry (per D-11, D-12)
        # Knowledge-type and script-type (no tools declared) skip this
        tools = (skill.manifest or {}).get("tools", [])
        prefix = f"skill__{skill.name}__"
        self._registry.unregister(prefix)  # Clean slate

        for tool in tools:
            tool_name = f"skill__{skill.name}__{tool['name']}"
            if skill.skill_type == "service":
                handler: Any = SkillToolHandler(
                    container_url=self.containers[skill.name].url,
                    tool_name=tool["name"],
                    timeout=self._timeout,
                )
            else:
                # For script/knowledge with tools declared (shouldn't happen per D-19)
                continue
            self._registry.register(
                name=tool_name,
                schema=tool.get("parameters", {"type": "object"}),
                handler=handler,
            )
            logger.info("skill_tool_registered", tool=tool_name)

        # Update status
        await self._update_skill_status(skill.id, "enabled")
        logger.info(
            "skill_enabled", skill=skill.name, type=skill.skill_type
        )

    async def disable_skill(self, skill_name: str) -> None:
        """Disable a skill: stop container, unregister tools, clean caches."""
        # Unregister tools
        prefix = f"skill__{skill_name}__"
        removed = self._registry.unregister(prefix)
        logger.info(
            "skill_tools_unregistered", skill=skill_name, count=removed
        )

        # Stop container if running
        container_info = self.containers.pop(skill_name, None)
        if container_info:
            self._sandbox.stop_container(container_info.name)

        # Clean caches
        self._skill_content.pop(skill_name, None)
        self._skill_descriptions.pop(skill_name, None)

        # Update status
        await self._update_skill_status_by_name(skill_name, "disabled")
        logger.info("skill_disabled", skill=skill_name)

    async def disable_all(self) -> None:
        """Stop all containers, unregister all tools."""
        skill_names = list(self.containers.keys())
        # Also unregister any knowledge-type skills (no containers but may need cleanup)
        for tool in self._registry.list_tools():
            if tool["name"].startswith("skill__"):
                skill_name = tool["name"].split("__")[1]
                if skill_name not in skill_names:
                    skill_names.append(skill_name)
        for name in skill_names:
            await self.disable_skill(name)
        logger.info("skill_all_disabled")

    async def start_health_check(self) -> None:
        """Start background health check for service-type containers (per D-27)."""
        self._health_task = asyncio.create_task(self._health_check_loop())
        logger.info(
            "skill_health_check_started",
            interval=self._health_check_interval,
        )

    async def stop_health_check(self) -> None:
        """Stop the background health check task."""
        if self._health_task is not None:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
            self._health_task = None

    async def _health_check_loop(self) -> None:
        """Background loop: check service-type container health."""
        while True:
            try:
                await asyncio.sleep(self._health_check_interval)
                await self._check_all_containers()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error("skill_health_check_error", error=str(e))

    async def _check_all_containers(self) -> None:
        """Check health of all service-type containers."""
        import httpx

        for skill_name, info in list(self.containers.items()):
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(f"{info.url}/health")
                    if resp.status_code != 200:
                        raise Exception(
                            f"Health check returned {resp.status_code}"
                        )
            except Exception as e:
                logger.warning(
                    "skill_health_check_failed",
                    skill=skill_name,
                    error=str(e),
                )
                await self._handle_container_failure(skill_name)

    async def _handle_container_failure(self, skill_name: str) -> None:
        """Handle container failure: attempt restart."""
        logger.info("skill_restarting", skill=skill_name)
        try:
            # Get skill from DB
            async with self._session_factory() as db:
                result = await db.execute(
                    select(Skill).where(Skill.name == skill_name)
                )
                skill = result.scalar_one_or_none()
            if skill and skill.skill_type == "service":
                await self.disable_skill(skill_name)
                await self._enable_one(skill)
                logger.info("skill_restarted", skill=skill_name)
        except Exception as e:
            logger.error(
                "skill_restart_failed", skill=skill_name, error=str(e)
            )

    async def _update_skill_status(
        self, skill_id: Any, status: str
    ) -> None:
        """Update skill status in DB by ID."""
        try:
            async with self._session_factory() as db:
                result = await db.execute(
                    select(Skill).where(Skill.id == skill_id)
                )
                skill = result.scalar_one_or_none()
                if skill:
                    skill.status = status
                    await db.commit()
        except Exception as e:
            logger.error(
                "skill_status_update_failed",
                skill_id=str(skill_id),
                error=str(e),
            )

    async def _update_skill_status_by_name(
        self, skill_name: str, status: str
    ) -> None:
        """Update skill status in DB by name."""
        try:
            async with self._session_factory() as db:
                result = await db.execute(
                    select(Skill).where(Skill.name == skill_name)
                )
                skill = result.scalar_one_or_none()
                if skill:
                    skill.status = status
                    await db.commit()
        except Exception as e:
            logger.error(
                "skill_status_update_failed",
                skill_name=skill_name,
                error=str(e),
            )

    def get_skill_content(self, skill_name: str) -> str | None:
        """Get SKILL.md body for a skill (used by load_skill built-in tool)."""
        return self._skill_content.get(skill_name)

    def get_enabled_skill_summaries(self) -> list[dict]:
        """Get summary list of enabled skills for Agent context injection.

        Per D-16: Returns list of dicts with "name" AND "description" keys.
        """
        summaries = []
        for tool in self._registry.list_tools():
            name = tool["name"]
            if name.startswith("skill__"):
                parts = name.split("__")
                if len(parts) >= 3:
                    skill_name = parts[1]
                    summaries.append(
                        {
                            "name": skill_name,
                            "description": self._skill_descriptions.get(
                                skill_name, ""
                            ),
                        }
                    )
        # Deduplicate by skill name
        seen: set[str] = set()
        unique: list[dict] = []
        for s in summaries:
            if s["name"] not in seen:
                seen.add(s["name"])
                unique.append(s)
        return unique
