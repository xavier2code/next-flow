"""Smoke test: verify MCP server routes are registered in the v1 router."""

from fastapi.routing import APIRoute

from app.api.v1.router import router


def test_mcp_servers_router_included():
    """The mcp-servers router is registered under /api/v1."""
    routes = [
        (r.path, list(r.methods or []))
        for r in router.routes
        if isinstance(r, APIRoute)
    ]
    mcp_routes = [(p, m) for p, m in routes if "/mcp-servers" in p]
    assert len(mcp_routes) >= 6, f"Expected >=6 mcp-servers routes, got {len(mcp_routes)}: {mcp_routes}"


def test_mcp_server_routes_have_expected_paths():
    """All 6 MCP server endpoint paths exist in the router."""
    routes = [
        r.path
        for r in router.routes
        if isinstance(r, APIRoute)
    ]
    # Router has prefix="/api/v1", so paths are fully qualified
    assert "/api/v1/mcp-servers" in routes
    assert "/api/v1/mcp-servers/{server_id}" in routes
    assert "/api/v1/mcp-servers/{server_id}/tools" in routes
