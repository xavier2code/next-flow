"""Lightweight HTTP sidecar for skill containers.

Routes POST /tools/{tool_name} to script/{tool_name}.py's run() function.
Provides GET /health for container health checks.
"""

import importlib.util
import json
import os
import sys
from pathlib import Path

from aiohttp import web

SKILL_DIR = Path("/skill")
SCRIPT_DIR = SKILL_DIR / "script"


def load_tool_handler(tool_name: str):
    """Dynamically load run() from script/{tool_name}.py."""
    script_path = SCRIPT_DIR / f"{tool_name}.py"
    if not script_path.exists():
        return None

    spec = importlib.util.spec_from_file_location(tool_name, str(script_path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[tool_name] = module
    spec.loader.exec_module(module)

    if not hasattr(module, "run"):
        return None
    return module.run


async def handle_health(request: web.Request) -> web.Response:
    """Health check endpoint."""
    return web.Response(text="ok", status=200)


async def handle_tool(request: web.Request) -> web.Response:
    """Route tool invocation to the corresponding script."""
    tool_name = request.match_info["tool_name"]

    handler = load_tool_handler(tool_name)
    if handler is None:
        return web.json_response(
            {"error": f"Tool '{tool_name}' not found"}, status=404
        )

    try:
        body = await request.json()
    except json.JSONDecodeError:
        return web.json_response(
            {"error": "Invalid JSON body"}, status=400
        )

    try:
        result = handler(body)
        if isinstance(result, dict):
            return web.json_response(result)
        return web.json_response({"result": result})
    except Exception as e:
        return web.json_response(
            {"error": str(e)}, status=500
        )


async def handle_list_tools(request: web.Request) -> web.Response:
    """List available tools."""
    tools = []
    if SCRIPT_DIR.exists():
        for f in SCRIPT_DIR.iterdir():
            if f.suffix == ".py" and f.name != "__init__.py":
                tool_name = f.stem
                handler = load_tool_handler(tool_name)
                desc = getattr(handler, "__doc__", "") if handler else ""
                tools.append({"name": tool_name, "description": desc})
    return web.json_response(tools)


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/health", handle_health)
    app.router.add_get("/tools", handle_list_tools)
    app.router.add_post("/tools/{tool_name}", handle_tool)
    return app


if __name__ == "__main__":
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=8080)
