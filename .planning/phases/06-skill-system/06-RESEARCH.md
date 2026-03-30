# Phase 6: Skill System - Research

**Researched:** 2026-03-30
**Domain:** Skill package management, Docker sandbox execution, MinIO object storage, Tool Registry integration
**Confidence:** HIGH

## Summary

Phase 6 implements the Skill System -- the platform's plugin architecture for extending Agent capabilities. Skills are ZIP packages containing a SKILL.md manifest (YAML frontmatter + Agent instructions), optional script/ directory with executable tools, and optional reference/ materials. Three skill types are auto-inferred from package structure: knowledge (SKILL.md only, no container), service (script/ with persistent Docker container and HTTP sidecar), and script (script/ with one-shot Docker execution). This phase builds on the Tool Registry, ToolHandler Protocol, and MCP Manager patterns established in Phases 2 and 5.

The implementation follows the MCP Manager pattern exactly: SkillManager mirrors MCPManager lifecycle (connect_all/disconnect_all in lifespan), SkillToolHandler mirrors MCPToolHandler (duck-typed ToolHandler with classified errors and timeout), and the CRUD API mirrors MCPServerService/routes. The key new components are MinIO integration for ZIP storage, Docker SDK for sandbox container management, and YAML frontmatter parsing for SKILL.md manifests.

**Primary recommendation:** Replicate the MCP Manager lifecycle pattern verbatim for SkillManager. Use python-frontmatter (1.1.0) for SKILL.md parsing, minio (7.2.x) for package storage, and Docker SDK (7.1.x) for sandbox execution. Add MinIO service to docker-compose.yml as the first task.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** SKILL.md is the single source of truth, using YAML frontmatter to merge manifest metadata with Agent instructions (Jekyll/Hugo-style). No separate manifest.yaml
- **D-02:** SKILL.md frontmatter fields: name (required, globally unique), version, description, tools (list of {name, description, parameters JSON Schema}), permissions ({network: bool}). Body is Agent-facing instructions in Markdown
- **D-03:** Fixed ZIP structure: SKILL.md (required) + script/ (optional) + reference/ (optional) + requirements.txt (optional for service-type only)
- **D-04:** Tools are fully statically declared in SKILL.md frontmatter. No runtime introspection needed
- **D-05:** Each tool maps to a file in script/ directory. Filename matches tool name, contains `async def run(params: dict) -> dict`. One file per tool
- **D-06:** Pure knowledge Skills allowed (no script/, no tool registration). Agent acts on SKILL.md instructions using existing built-in/MCP tools
- **D-07:** Single version per Skill name. Re-uploading same-name Skill overwrites the old version. No multi-version coexistence in v1
- **D-08:** Python-only Skills in v1
- **D-09:** reference/ directory serves dual purpose: Agent-retrievable reference materials AND runtime resources for script/ code
- **D-10:** Size-based split: small files (<N tokens) injected directly into Agent context, large files go through RAG vector retrieval. Threshold at Claude's discretion
- **D-11:** Tools registered to ToolRegistry on Skill enable, unregistered on disable. Follows MCP Manager connect/disconnect pattern
- **D-12:** Namespace format `skill__{skill_name}__{tool_name}`. Bulk unregister via `unregister("skill__{name}__")` prefix
- **D-13:** Pure knowledge Skills do NOT register any tools in ToolRegistry
- **D-14:** All tools globally shared across all Agents in v1
- **D-15:** Skill names must be globally unique. Upload rejects duplicate names
- **D-16:** When Skills are enabled, comma-separated summary list (name + brief description) injected as part of Agent SystemMessage
- **D-17:** Full SKILL.md content loaded on-demand via built-in `load_skill(name)` tool
- **D-18:** load_skill registered as built-in tool in ToolRegistry. Returns full SKILL.md markdown body
- **D-19:** Platform auto-infers Skill type from structure: no script/ = knowledge, script/ + tools declared = service, script/ + no tools = script
- **D-20:** Service type: persistent Docker container with sidecar HTTP server. Container stays running until disable
- **D-21:** Script type: on-demand execution -- platform starts container, runs script, captures output, destroys container
- **D-22:** Knowledge type: no container at all. SKILL.md instructions injected via load_skill tool
- **D-23:** HTTP API communication between SkillToolHandler and container sidecar
- **D-24:** Unified base image + volume mount for Skill files. No per-Skill image builds
- **D-25:** Base image sidecar: single HTTP port with path-based routing to script/{tool_name}.py
- **D-26:** Global uniform resource limits via Settings. No per-Skill customization in v1
- **D-27:** Health check + auto-restart for service-type containers
- **D-28:** Script-type Skills can only use pre-installed libraries from base image. Service-type may use requirements.txt
- **D-29:** Upload validates: SKILL.md exists, frontmatter parses, required fields present, tools JSON Schema valid, script/ files match declared tools one-to-one
- **D-30:** ZIP stored as-is in MinIO. Metadata parsed into Skill DB model. Container mounts extracted files via volume
- **D-31:** Hot-update: synchronous stop-then-start. Disable old, replace ZIP in MinIO, re-enable
- **D-32:** Platform restart recovery: read enabled Skills from DB, pull ZIPs from MinIO, re-extract, re-start containers, re-register tools
- **D-33:** Extend existing Skill DB model: add version (str), permissions (JSON), package_url (str, MinIO key), skill_type (str, auto-inferred)
- **D-34:** Admin API: POST /skills (upload), GET /skills (list), GET /skills/{id} (detail), PATCH /skills/{id} (update metadata), DELETE /skills/{id} (delete), POST /skills/{id}/enable, POST /skills/{id}/disable

### Claude's Discretion
- Exact SKILL.md frontmatter schema (additional optional fields beyond name/version/description/tools/permissions)
- Base image contents (which pre-installed libraries to include)
- Resource limit default values (suggest: memory=256MB, CPU=1 core, timeout=30s)
- Health check interval for service-type containers (suggest: 30s)
- Size threshold for reference file direct-inject vs RAG (suggest: 500 tokens)
- Sidecar HTTP server implementation details
- Exact load_skill tool response format
- Error handling and fallback behavior when sandbox is unavailable
- SkillToolHandler Protocol implementation details (similar to MCPToolHandler)
- Logging detail level for skill operations

### Deferred Ideas (OUT OF SCOPE)
- Per-agent skill binding -- v2, after RBAC is implemented
- Multi-version skill coexistence -- v2, when marketplace (MKT-01) is built
- Skill marketplace with review system -- v2 MKT-01
- Custom per-skill resource limits -- v2
- SDK pip package for enhanced developer experience -- evaluate if sidecar proves limiting
- Celery integration for async skill packaging/unpackaging -- if synchronous processing becomes a bottleneck
- Git repository import for skills -- future enhancement
- Online skill editor -- future enhancement
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SKIL-01 | Skill package format definition with manifest (name, description, permissions, tools) | SKILL.md YAML frontmatter format (D-01 to D-06), python-frontmatter library for parsing, ZIP validation logic (D-29) |
| SKIL-02 | MinIO integration for skill package storage | minio Python SDK 7.2.x, docker-compose MinIO service addition, bucket management, presigned URL considerations |
| SKIL-03 | Docker-based sandbox executor with resource limits and timeout enforcement | Docker SDK 7.1.x container run API, resource limits (mem_limit, cpu_count, pids_limit), security hardening (cap_drop, read_only, network_mode), sidecar HTTP architecture (D-20, D-23 to D-28) |
| SKIL-04 | Skill lifecycle management (upload, validate, enable, disable, hot-update) | SkillService CRUD pattern (mirrors MCPServerService), SkillManager lifecycle (mirrors MCPManager), platform restart recovery (D-32) |
| SKIL-05 | Skill tool registration into unified Tool Registry | SkillToolHandler (mirrors MCPToolHandler), namespace convention skill__{name}__{tool} (D-12), unregister prefix pattern, load_skill built-in tool (D-17, D-18) |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| minio | 7.2.x | S3-compatible object storage client | Storing/retrieving Skill ZIP packages. S3-compatible API means migration to AWS S3 is trivial. Latest stable: 7.2.20 |
| docker | 7.1.x | Docker SDK for Python | Container lifecycle management for skill sandbox execution. Resource limit enforcement. Latest stable: 7.1.0 |
| python-frontmatter | 1.1.0 | YAML frontmatter parser for SKILL.md | Parse Jekyll/Hugo-style SKILL.md files with YAML metadata + markdown body. Well-maintained, simple API. Latest: 1.1.0 |
| PyYAML | 6.0.x | YAML parsing (dependency of python-frontmatter) | Already installed in backend venv (6.0.3). Required for frontmatter parsing |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| httpx | 0.28+ (already installed) | Async HTTP client for sandbox sidecar communication | SkillToolHandler sends HTTP POST to container sidecar. Already in project dependencies |
| zipfile | stdlib | ZIP extraction and validation | Validate uploaded ZIP structure, extract for container mounting |
| asyncio | stdlib | Timeout enforcement, background health checks | asyncio.wait_for for tool timeouts, asyncio.create_task for health check loop |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| python-frontmatter | Custom PyYAML + split("---") | Custom parsing is error-prone with edge cases (frontmatter at EOF, missing closing ---, BOM). python-frontmatter handles these. Only worth custom if adding a dependency is unacceptable |
| Docker SDK | subprocess + docker CLI | Docker SDK provides typed API, proper error handling, and streaming logs. subprocess is fragile and hard to test |
| MinIO | AWS S3 direct | MinIO is self-hosted, avoids cloud lock-in. S3-compatible API means code works with both. Use MinIO for dev/self-hosted, S3 for cloud deployments |

**Installation:**
```bash
pip install minio>=7.2.0 docker>=7.1.0 python-frontmatter>=1.1.0
```

**Version verification:**
- minio: 7.2.20 (verified via pip index, 2026-03-30)
- docker: 7.1.0 (verified via pip index, 2026-03-30)
- python-frontmatter: 1.1.0 (verified via pip index, 2026-03-30)
- PyYAML: 6.0.3 (already installed in backend venv)

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
├── services/
│   ├── skill/                      # New: Skill domain service module
│   │   ├── __init__.py             # Exports SkillManager
│   │   ├── manager.py              # SkillManager: lifecycle, container management
│   │   ├── handler.py              # SkillToolHandler: ToolHandler Protocol impl
│   │   ├── validator.py            # ZIP validation, frontmatter parsing
│   │   ├── sandbox.py              # Docker sandbox execution, container lifecycle
│   │   └── errors.py               # Classified skill errors (mirrors mcp/errors.py)
│   ├── skill_service.py            # CRUD service (mirrors mcp_server_service.py)
│   ├── tool_registry/
│   │   ├── builtins.py             # Add load_skill built-in tool here
│   │   ├── registry.py             # ToolRegistry (already has unregister prefix)
│   │   └── handlers.py             # ToolHandler Protocol (unchanged)
│   └── mcp/                        # Existing: reference pattern
├── models/
│   └── skill.py                    # Extend with version, permissions, package_url, skill_type
├── schemas/
│   └── skill.py                    # New: Pydantic schemas (mirrors mcp_server.py)
├── api/
│   ├── v1/
│   │   ├── skills.py               # New: REST endpoints (mirrors mcp_servers.py)
│   │   └── router.py               # Add skills router
│   └── deps.py                     # Add get_skill_manager dependency
├── core/
│   └── config.py                   # Add MinIO + sandbox settings
└── main.py                         # Add MinIO client + SkillManager to lifespan

# Sidecar base image (separate Dockerfile)
sandbox/
├── Dockerfile                      # Base image with Python runtime + sidecar
├── sidecar.py                      # HTTP server: routes to script/{tool}.py run()
└── requirements.txt                # Pre-installed libraries for script-type skills
```

### Pattern 1: SkillManager Lifecycle (mirrors MCPManager)
**What:** SkillManager holds dict of running containers keyed by skill name, manages enable/disable lifecycle, runs health checks for service-type containers.
**When to use:** All skill container lifecycle management.
**Example:**
```python
class SkillManager:
    def __init__(
        self,
        tool_registry: ToolRegistry,
        session_factory: async_sessionmaker[AsyncSession],
        minio_client: Minio,
        docker_client: docker.DockerClient,
        settings: SkillSandboxSettings,
    ) -> None:
        self._registry = tool_registry
        self._session_factory = session_factory
        self._minio = minio_client
        self._docker = docker_client
        self._settings = settings
        self.containers: dict[str, ContainerInfo] = {}
        self._health_task: asyncio.Task | None = None

    async def enable_all(self) -> None:
        """Enable all Skills with status='enabled' from DB (mirrors MCPManager.connect_all)."""
        async with self._session_factory() as db:
            result = await db.execute(
                select(Skill).where(Skill.status == "enabled")
            )
            skills = list(result.scalars().all())
        await asyncio.gather(*[self._enable_one(s) for s in skills])

    async def disable_all(self) -> None:
        """Stop all containers, unregister all tools (mirrors MCPManager.disconnect_all)."""
        for name in list(self.containers.keys()):
            await self.disable_skill(name)
```

### Pattern 2: SkillToolHandler (mirrors MCPToolHandler)
**What:** Duck-typed ToolHandler that sends HTTP POST to sandbox container sidecar.
**When to use:** All skill tool invocations.
**Example:**
```python
class SkillToolHandler:
    """ToolHandler that routes to skill sandbox via HTTP."""

    def __init__(self, container_url: str, tool_name: str, timeout: float = 30.0):
        self._url = f"{container_url}/tools/{tool_name}"
        self._tool_name = tool_name
        self._timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)

    async def invoke(self, params: dict) -> Any:
        try:
            resp = await self._client.post(self._url, json=params)
            resp.raise_for_status()
            return resp.json()
        except httpx.TimeoutException:
            raise SkillToolTimeoutError(self._tool_name, self._timeout)
        except httpx.ConnectError as e:
            raise SkillToolConnectionError(self._tool_name, str(e))
        except Exception as e:
            raise SkillToolExecutionError(self._tool_name, str(e))
```

### Pattern 3: SKILL.md Frontmatter Parsing
**What:** Parse YAML frontmatter from SKILL.md using python-frontmatter, validate required fields.
**When to use:** On skill upload/validation.
**Example:**
```python
import frontmatter

def parse_skill_manifest(skill_md_content: str) -> tuple[dict, str]:
    """Parse SKILL.md into frontmatter metadata and markdown body."""
    post = frontmatter.loads(skill_md_content)

    # Validate required fields
    required = ["name", "version", "description"]
    for field in required:
        if field not in post.metadata:
            raise ValidationError(f"Missing required field: {field}")

    # Validate tools structure if present
    tools = post.metadata.get("tools", [])
    for tool in tools:
        if "name" not in tool or "description" not in tool:
            raise ValidationError("Each tool must have name and description")

    return post.metadata, post.content
```

### Pattern 4: Docker Sandbox Container Configuration
**What:** Security-hardened container configuration with resource limits.
**When to use:** Creating service-type and script-type skill containers.
**Example:**
```python
container = docker_client.containers.run(
    image="nextflow-skill-base:latest",
    command=["python", "/sidecar/sidecar.py"],
    volumes={extract_path: {"bind": "/skill", "mode": "ro"}},
    mem_limit="256m",
    cpus=1.0,
    pids_limit=100,
    security_opt=["no-new-privileges"],
    cap_drop=["ALL"],
    network_mode="none" if not permissions.get("network") else "bridge",
    read_only=True,
    tmpfs={"/tmp": "size=50m"},
    detach=True,
    name=f"nextflow-skill-{skill_name}",
    auto_remove=False,
    user="1000:1000",  # non-root
)
```

### Anti-Patterns to Avoid
- **Running skill code in-process:** Never import or exec skill code in the FastAPI process. Always use Docker containers for isolation. In-process execution is the #1 security risk (Pitfall 9 in PITFALLS.md)
- **Per-skill Docker image builds:** Do NOT build a Docker image per skill. Use a single base image + volume mount for skill files (D-24). Building images is slow (30-120s) and creates image sprawl
- **Synchronous ZIP download during request handling:** Downloading from MinIO is I/O. Always use async operations. For hot-update, the synchronous stop-then-start is acceptable because it is an admin action, but MinIO operations should still use async wrappers
- **Flat tool namespace without source prefix:** All skill tools must use `skill__{name}__{tool}` prefix. Without it, tool name collisions between skills and MCP servers are inevitable
- **Missing container cleanup on crash:** If the FastAPI process crashes, Docker containers continue running. SkillManager must track container names and clean up stale containers on startup

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| YAML frontmatter parsing | Custom split("---") + yaml.safe_load | python-frontmatter | Edge cases: BOM, missing closing delimiter, empty frontmatter, nested YAML with --- in content |
| S3-compatible object storage | Local filesystem storage or custom HTTP upload | MinIO + minio SDK | Handles concurrent access, bucket policies, presigned URLs, automatic multipart upload for large packages |
| Container resource isolation | Process-level sandboxing with resource limits | Docker SDK with security opts | Docker provides kernel-level isolation (namespaces, cgroups, seccomp). Process-level is insufficient for untrusted code |
| Tool invocation routing | Manual if/else dispatch in execute node | ToolRegistry + ToolHandler Protocol | Already built. Just register SkillToolHandler instances. Follows established MCP pattern |
| ZIP validation | Custom ZIP parsing | zipfile stdlib + path traversal checks | zipfile handles ZIP64, encoding issues. Must add security checks for path traversal (e.g., "../" in filenames) |

**Key insight:** The MCP integration in Phase 5 already established every pattern this phase needs. SkillManager = MCPManager, SkillToolHandler = MCPToolHandler, SkillService = MCPServerService. The only genuinely new components are MinIO storage, Docker sandbox execution, and SKILL.md parsing.

## Common Pitfalls

### Pitfall 1: ZIP Path Traversal Attack
**What goes wrong:** A malicious ZIP contains entries like `../../../etc/passwd` or `../../app/main.py`. When extracted, these overwrite application files.
**Why it happens:** Python's zipfile module extracts member filenames as-is without sanitization by default. This is a well-known security vulnerability.
**How to avoid:** Validate every member path before extraction. Reject entries with absolute paths, paths containing `..`, or paths that escape the target directory.
```python
import os

def safe_extract(zip_path: str, target_dir: str) -> None:
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.namelist():
            # Reject absolute paths and path traversal
            if member.startswith("/") or ".." in member:
                raise ValidationError(f"Unsafe path in ZIP: {member}")
            target = os.path.realpath(os.path.join(target_dir, member))
            if not target.startswith(os.path.realpath(target_dir)):
                raise ValidationError(f"Path traversal in ZIP: {member}")
        zf.extractall(target_dir)
```
**Warning signs:** Any ZIP extraction without path validation.

### Pitfall 2: Docker Container Leaks on Process Crash
**What goes wrong:** FastAPI process crashes or restarts, but Docker containers started by SkillManager continue running indefinitely. On restart, SkillManager creates new containers alongside the leaked ones, consuming resources and causing port conflicts.
**Why it happens:** Docker containers are managed by the Docker daemon, not the Python process. When the Python process dies, the daemon has no instruction to stop them.
**How to avoid:** (1) Use a consistent container naming pattern (`nextflow-skill-{name}`) so stale containers can be identified. (2) On SkillManager startup, before enable_all, remove any containers matching the naming pattern. (3) Set a container label like `nextflow.managed=true` for reliable filtering.
**Warning signs:** `docker ps` shows containers from previous sessions. Memory usage grows after multiple restarts.

### Pitfall 3: MinIO Connection in Test Environment
**What goes wrong:** Tests that touch SkillService or SkillManager require a running MinIO instance. CI pipeline fails because MinIO is not available.
**Why it happens:** Unlike PostgreSQL and Redis which are already in docker-compose for testing, MinIO is new and not yet in the test setup.
**How to avoid:** Add MinIO to docker-compose.yml. For unit tests, mock the MinIO client. For integration tests, use docker-compose MinIO. Consider a lightweight fake for unit tests that stores files in /tmp.
**Warning signs:** Tests that skip or mock MinIO but never validate real upload/download behavior.

### Pitfall 4: Sidecar HTTP Port Conflicts
**What goes wrong:** Multiple service-type skills each need a container with a sidecar HTTP server. If ports are hardcoded or randomly assigned without tracking, containers fail to start due to port conflicts.
**Why it happens:** Docker's port mapping requires explicit host port assignment. Two containers cannot bind to the same host port.
**How to avoid:** Use Docker's internal networking. Containers communicate via Docker network, not host port mapping. Each container's sidecar listens on port 8080 internally, and the SkillToolHandler uses Docker network DNS or container IP to reach it. Alternatively, assign ports from a pool (e.g., 9000-9999) and track allocations.
**Warning signs:** Second service-type skill fails to enable with "port already in use" error.

### Pitfall 5: SKILL.md Encoding Issues
**What goes wrong:** SKILL.md files uploaded by users may have non-UTF-8 encoding, BOM markers, or mixed line endings. Frontmatter parsing fails or produces garbled metadata.
**Why it happens:** ZIP files from Windows may include files with CRLF line endings or GBK encoding. python-frontmatter expects UTF-8.
**How to avoid:** Explicitly decode SKILL.md content as UTF-8 during extraction. Normalize line endings. Catch UnicodeDecodeError and return a clear validation error.
**Warning signs:** Users uploading skills from Windows get "invalid frontmatter" errors. Chinese characters in SKILL.md descriptions are garbled.

### Pitfall 6: Orphaned Tools After Container Death
**What goes wrong:** A service-type skill's Docker container dies (OOM, segfault, Docker restart). The tools remain registered in ToolRegistry but invocations fail. No health check detects this.
**Why it happens:** ToolRegistry is in-memory. Tool registration and container lifecycle are separate concerns. Without health checks, stale registrations persist.
**How to avoid:** Implement periodic health checks for service-type containers (D-27). On health check failure, unregister tools, attempt container restart, re-register on success. Mirrors MCPManager health check pattern exactly.
**Warning signs:** Agent calls a skill tool and gets a connection error. No automatic recovery occurs.

### Pitfall 7: Resource Exhaustion from Concurrent Skill Executions
**What goes wrong:** Multiple script-type skills execute simultaneously, each starting a Docker container. With 10+ concurrent executions, host CPU/memory is exhausted.
**Why it happens:** Each script-type invocation starts a new container. Without concurrency limits, N concurrent invocations create N containers.
**How to avoid:** Implement a semaphore limiting concurrent script-type executions (e.g., max 5). Queue excess invocations. This is at Claude's discretion for v1 but essential for production.
**Warning signs:** System becomes unresponsive when multiple users trigger script-type skills simultaneously.

## Code Examples

### SKILL.md Example (Valid Package)
```markdown
---
name: weather-query
version: "1.0.0"
description: "Query weather data for any city worldwide"
tools:
  - name: get_weather
    description: "Get current weather for a city"
    parameters:
      type: object
      properties:
        city:
          type: string
          description: "City name"
        unit:
          type: string
          enum: ["celsius", "fahrenheit"]
          description: "Temperature unit"
      required: ["city"]
permissions:
  network: true
---

# Weather Query Skill

When the user asks about weather:
1. Call get_weather with the city name
2. Format the response in a user-friendly way
3. Include temperature, conditions, and a 3-day outlook if available

Always specify the unit based on the user's location (celsius for non-US, fahrenheit for US).
```

### MinIO Client Initialization
```python
from minio import Minio

def create_minio_client(endpoint: str, access_key: str, secret_key: str, secure: bool = False) -> Minio:
    """Create MinIO client and ensure skill-packages bucket exists."""
    client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)
    bucket_name = "skill-packages"
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)
    return client
```

### SkillService CRUD (mirrors MCPServerService)
```python
class SkillService:
    @staticmethod
    async def create(db: AsyncSession, tenant_id: str, name: str,
                     version: str, description: str, skill_type: str,
                     permissions: dict, package_url: str, manifest: dict) -> Skill:
        skill = Skill(
            tenant_id=tenant_id,
            name=name,
            version=version,
            description=description,
            skill_type=skill_type,
            permissions=permissions,
            package_url=package_url,
            manifest=manifest,
            status="inactive",
        )
        db.add(skill)
        await db.flush()
        await db.refresh(skill)
        return skill

    @staticmethod
    async def get_by_name(db: AsyncSession, name: str) -> Skill | None:
        result = await db.execute(select(Skill).where(Skill.name == name))
        return result.scalar_one_or_none()
```

### Enable Skill Flow (mirrors MCPManager.connect_server)
```python
async def enable_skill(self, skill: Skill) -> None:
    """Enable a skill: start container (if needed), register tools."""
    if skill.skill_type == "knowledge":
        # No container needed. Tools already available via load_skill.
        pass
    elif skill.skill_type == "service":
        # Start persistent container
        container_info = await self._start_service_container(skill)
        self.containers[skill.name] = container_info
    elif skill.skill_type == "script":
        # No persistent container. Script runs on-demand.
        pass

    # Register tools in ToolRegistry
    prefix = f"skill__{skill.name}__"
    self._registry.unregister(prefix)  # Clean slate

    tools = skill.manifest.get("tools", [])
    for tool in tools:
        tool_name = f"skill__{skill.name}__{tool['name']}"
        handler = self._create_handler(skill, tool)
        self._registry.register(
            name=tool_name,
            schema=tool.get("parameters", {"type": "object"}),
            handler=handler,
        )

    # Update status
    await self._update_skill_status(skill.id, "enabled")
```

### Classified Skill Errors (mirrors mcp/errors.py)
```python
class SkillToolError(Exception):
    def __init__(self, tool_name: str, message: str) -> None:
        self.tool_name = tool_name
        super().__init__(message)

class SkillToolTimeoutError(SkillToolError):
    def __init__(self, tool_name: str, timeout: float) -> None:
        super().__init__(tool_name,
            f"Skill tool '{tool_name}' timed out after {timeout}s. "
            f"The sandbox may be overloaded.")

class SkillToolConnectionError(SkillToolError):
    def __init__(self, tool_name: str, detail: str) -> None:
        super().__init__(tool_name,
            f"Skill tool '{tool_name}' failed: sandbox unreachable. {detail}")

class SkillToolExecutionError(SkillToolError):
    def __init__(self, tool_name: str, detail: str) -> None:
        super().__init__(tool_name,
            f"Skill tool '{tool_name}' execution error: {detail}")
```

### load_skill Built-in Tool Registration
```python
# In builtins.py, add to register_builtin_tools():

@registry.register(
    name="load_skill",
    schema={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "The skill name to load full instructions for",
            },
        },
        "required": ["name"],
    },
)
async def load_skill(params: dict) -> str:
    """Load full SKILL.md content for a specific skill."""
    # Implementation needs access to SkillManager or a skill content store.
    # Use module-level setter pattern (like memory_service in Phase 4).
    ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Docker SDK 6.x | Docker SDK 7.x | 2024 | Async-compatible, modern API. 7.1.0 is current |
| MinIO SDK 6.x/7.0 | MinIO SDK 7.2.x | 2024-2025 | Improved presigned URL handling, S3 compatibility |
| python-frontmatter 0.x | python-frontmatter 1.x | 2024 | Stable API, better error handling |
| Custom sandbox (subprocess) | Docker-based sandbox with security opts | Standard practice | Kernel-level isolation vs. easily-escaped process isolation |
| Per-skill Docker images | Single base image + volume mount | Industry trend | Eliminates image build time, reduces storage |

**Deprecated/outdated:**
- subprocess-based sandboxing: insufficient isolation for untrusted code
- pickle-based manifest format: insecure (arbitrary code execution on deserialization). YAML frontmatter is safe when using yaml.safe_load (which python-frontmatter uses)

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker daemon | Sandbox execution | YES | 29.3.1 | -- |
| Python 3.12+ venv | Backend runtime | YES | 3.12.13 | -- |
| PyYAML | SKILL.md parsing | YES | 6.0.3 | -- |
| minio SDK | Package storage | NO | -- | Must install (pip install minio) |
| docker SDK | Container management | NO | -- | Must install (pip install docker) |
| python-frontmatter | Frontmatter parsing | NO | -- | Must install (pip install python-frontmatter) |
| MinIO service | Object storage backend | NO | -- | Must add to docker-compose.yml |
| PostgreSQL | Skill model persistence | YES | Running via docker-compose | -- |
| Redis | Cache, sessions | YES | Running via docker-compose | -- |
| httpx | Sandbox HTTP communication | YES | 0.28+ | -- |

**Missing dependencies with no fallback:**
- minio SDK: Must be installed in backend venv. Add to pyproject.toml
- docker SDK: Must be installed in backend venv. Add to pyproject.toml
- python-frontmatter: Must be installed in backend venv. Add to pyproject.toml
- MinIO service: Must be added to docker-compose.yml. Port 9000 (API) + 9001 (Console)

**Missing dependencies with fallback:**
- None. All missing items are required for this phase.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | backend/pyproject.toml (asyncio_mode = "auto") |
| Quick run command | `cd backend && python -m pytest tests/ -x -q` |
| Full suite command | `cd backend && python -m pytest tests/ -v --tb=short` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SKIL-01 | SKILL.md frontmatter parsing validates required fields | unit | `python -m pytest tests/unit/test_skill_validator.py -x` | NO -- Wave 0 |
| SKIL-01 | ZIP structure validation (required files, path safety) | unit | `python -m pytest tests/unit/test_skill_validator.py -x` | NO -- Wave 0 |
| SKIL-02 | MinIO upload and download of skill packages | integration | `python -m pytest tests/unit/test_skill_minio.py -x` | NO -- Wave 0 |
| SKIL-03 | Docker container starts with resource limits | integration | `python -m pytest tests/unit/test_skill_sandbox.py -x` | NO -- Wave 0 |
| SKIL-03 | Container timeout enforcement | unit | `python -m pytest tests/unit/test_skill_handler.py -x` | NO -- Wave 0 |
| SKIL-04 | Skill lifecycle: upload, enable, disable, hot-update | integration | `python -m pytest tests/test_skills.py -x` | NO -- Wave 0 |
| SKIL-05 | Tool registration in ToolRegistry on enable | unit | `python -m pytest tests/unit/test_skill_registry.py -x` | NO -- Wave 0 |
| SKIL-05 | Tool unregistration on disable | unit | `python -m pytest tests/unit/test_skill_registry.py -x` | NO -- Wave 0 |
| SKIL-05 | load_skill built-in tool returns SKILL.md content | unit | `python -m pytest tests/unit/test_skill_builtins.py -x` | NO -- Wave 0 |
| SKIL-05 | SkillToolHandler classified errors | unit | `python -m pytest tests/unit/test_skill_handler.py -x` | NO -- Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/ -x -q`
- **Per wave merge:** `cd backend && python -m pytest tests/ -v --tb=short`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/test_skill_validator.py` -- SKILL.md parsing, ZIP validation, path traversal prevention
- [ ] `tests/unit/test_skill_handler.py` -- SkillToolHandler timeout, connection, execution errors
- [ ] `tests/unit/test_skill_registry.py` -- Tool registration/unregistration with skill namespace prefix
- [ ] `tests/unit/test_skill_builtins.py` -- load_skill built-in tool
- [ ] `tests/unit/test_skill_sandbox.py` -- Docker container lifecycle (requires Docker daemon)
- [ ] `tests/test_skills.py` -- Integration tests for Skill CRUD API endpoints
- [ ] `tests/conftest.py` -- Add MinIO mock fixture, SkillManager fixture

## Open Questions

1. **Sidecar HTTP server implementation**
   - What we know: D-25 specifies single HTTP port with path-based routing. Must auto-discover `run()` functions in script/ directory.
   - What's unclear: Whether the sidecar uses a lightweight framework (aiohttp, starlette) or raw asyncio HTTP. The sidecar runs inside the Docker container, so framework choice is contained.
   - Recommendation: Use a minimal approach -- aiohttp or even raw asyncio.start_server. The sidecar should be tiny. A single Python file (~100 lines). Avoid FastAPI/Starlette inside the container to keep the base image small.

2. **Script-type execution trigger mechanism**
   - What we know: D-21 specifies on-demand execution -- start container, run script, capture output, destroy. Script-type Skills have no tools in frontmatter.
   - What's unclear: How the Agent actually triggers script execution. Since there are no tools registered, the Agent cannot invoke via ToolRegistry. Perhaps the script is triggered via a built-in tool like `run_skill_script(name, params)`.
   - Recommendation: Register a built-in tool `run_skill_script` that takes a skill name and params, starts a one-shot container, and returns output. This aligns with the load_skill pattern.

3. **Volume mount strategy for container file access**
   - What we know: D-30 says ZIP stored in MinIO, container mounts extracted files via volume. D-24 says unified base image + volume mount.
   - What's unclear: Where extracted files live on the host filesystem. Docker bind mounts require a host path. Options: (1) extract to a temp dir, (2) extract to a persistent directory, (3) use Docker named volumes.
   - Recommendation: Extract to a persistent directory (e.g., `/tmp/nextflow/skills/{name}/`) on enable, clean up on disable. Use bind mount. This is simple and debuggable.

4. **Skill summary injection into Agent SystemMessage**
   - What we know: D-16 specifies injecting a comma-separated summary list of enabled skills into the Agent's SystemMessage.
   - What's unclear: The exact injection point and format. The analyze node builds the system message. Need to query enabled skills and format the summary.
   - Recommendation: Query all enabled skills from DB (or cache in SkillManager), format as "Available skills: weather-query (weather lookup), doc-search (document search)...", append to system message in analyze node.

## Sources

### Primary (HIGH confidence)
- Project CLAUDE.md -- Full tech stack specification, MinIO 7.x, Docker 7.x SDK, python-frontmatter recommendations
- `.planning/CONTEXT.md` (06-CONTEXT.md) -- All locked decisions D-01 through D-34
- `.planning/research/ARCHITECTURE.md` -- Skill Manager component, Sandbox Executor component, Tool Registry Pattern 5
- `.planning/research/PITFALLS.md` -- Pitfall 9 (Skill Sandbox Escapes), Pitfall 19 (MinIO Presigned URL), Security Mistakes table
- `.planning/research/STACK.md` -- MinIO 7.x, Docker 7.x SDK entries

### Secondary (MEDIUM confidence)
- PyPI registry -- minio 7.2.20, docker 7.1.0, python-frontmatter 1.1.0 version verification
- Docker SDK documentation (training knowledge) -- containers.run API, resource limits, security options
- MinIO Python SDK documentation (training knowledge) -- bucket operations, put_object, get_object, fget_object

### Tertiary (LOW confidence)
- Docker security best practices (training knowledge) -- cap_drop, security_opt, seccomp profiles. Not verified against 2026 docs. Flag: verify specific security_opt values work on macOS Docker Desktop
- Sidecar auto-discovery pattern -- custom design, no external reference. Validated only by architectural reasoning

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all versions verified against PyPI registry, libraries are well-established with years of production use
- Architecture: HIGH -- every pattern has a working reference implementation in the codebase (MCPManager, MCPToolHandler, MCPServerService)
- Pitfalls: HIGH -- based on well-documented Docker security practices and common ZIP handling vulnerabilities. STATE.md specifically flags Docker sandbox security as needing investigation
- Test infrastructure: HIGH -- pytest + pytest-asyncio already configured, conftest.py pattern established

**Research date:** 2026-03-30
**Valid until:** 2026-04-30 (stable libraries, unlikely to change significantly)
