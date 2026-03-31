# Phase 5: MCP Integration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in 05-CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-29
**Phase:** 05-mcp-integration
**Areas discussed:** Connection Lifecycle, Tool Discovery & Sync, Error Handling & Resilience, Admin API Design

---

## Connection Lifecycle Management

### Server connection timing

| Option | Description | Selected |
|--------|-------------|----------|
| 随应用启停 | MCPManager 在 lifespan 中连接所有已注册服务器，关闭时断开 | ✓ |
| 动态连接/断开 | 运行时动态增删，常驻运行 | |
| 懒连接（按需） | 首次调用时才建立连接 | |

**User's choice:** 随应用启停 — 简单可靠，适合服务器列表固定的场景

### Health monitoring

| Option | Description | Selected |
|--------|-------------|----------|
| 定期心跳检查 | 后台任务定期 ping，自动标记状态和重连 | ✓ |
| 被动检测 | 仅在调用失败时检测 | |
| 混合模式 | 心跳 + 失败重连 | |

**User's choice:** 定期心跳检查 — 主动发现问题，避免静默失败

### Reconnection strategy

| Option | Description | Selected |
|--------|-------------|----------|
| 指数退避重连 | 1s, 2s, 4s...max 60s，重连后自动重新同步工具 | ✓ |
| 标记失败，手动恢复 | 等待管理员操作 | |
| 固定间隔重试 | 每 30 秒固定重试 | |

**User's choice:** 指数退避重连 — 自动恢复，退避避免加重问题

### Transport selection

| Option | Description | Selected |
|--------|-------------|----------|
| 自动降级 | 优先 Streamable HTTP，失败 fallback SSE | ✓ |
| 管理员手动指定 | 按 MCPServer.transport_type 字段 | |
| 配置优先 + 自动回退 | 先按配置，失败后尝试备选 | |

**User's choice:** 自动降级 — SSE 到 Streamable HTTP 过渡期，自动适配最可用协议

### Multi-server concurrency model

| Option | Description | Selected |
|--------|-------------|----------|
| 每服务器独立实例 | dict[str, MCPClient]，隔离故障 | ✓ |
| 连接池模式 | 连接池管理，限制并发 | |
| 单队列串行 | 所有调用串行化 | |

**User's choice:** 每服务器独立实例 — 最自然的映射

### Startup behavior

| Option | Description | Selected |
|--------|-------------|----------|
| 同步启动 | 阻塞直到所有连接完成 | ✓ |
| 后台启动（非阻塞） | 应用立即接收请求，后台连接 | |

**User's choice:** 同步启动 — 确保工具就绪后才接收请求

---

## Tool Discovery & Synchronization

### Discovery timing

| Option | Description | Selected |
|--------|-------------|----------|
| 仅连接时发现 | 连接时调用 tools/list，之后不主动刷新 | ✓ |
| 连接时 + 定期刷新 | 每 N 分钟重新 tools/list | |
| 连接时 + 手动触发 | 管理员可手动触发刷新 | |

**User's choice:** 仅连接时发现 — 简单，适合工具不常变化的场景

### Namespace format

| Option | Description | Selected |
|--------|-------------|----------|
| mcp__server__tool | 双下划线分隔，ROADMAP 已锁定 | ✓ |
| server.tool（点号分隔） | 更简洁但可能冲突 | |

**User's choice:** mcp__server__tool — 确认 ROADMAP 已锁定格式

### Server disconnect/reconnect tool handling

| Option | Description | Selected |
|--------|-------------|----------|
| 重连时刷新 | 重连成功后自动 tools/list 刷新 | ✓ |
| 断开时注销 + 重连时注册 | 断开立即移除，重连重新注册 | |
| 注册后保留，不主动清理 | 断开不移除，调用时才报错 | |

**User's choice:** 重连时刷新 — 结合仅连接时发现，重连是唯一需要重新发现的时机

### Schema mapping

| Option | Description | Selected |
|--------|-------------|----------|
| 直接透传 MCP schema | MCP JSON Schema 直接注册到 ToolRegistry | ✓ |
| 转换为 OpenAI 格式 | 增加 Schema 转换层 | |

**User's choice:** 直接透传 MCP schema — 零转换，减少映射错误

---

## Error Handling & Resilience

### Tool invocation failure handling

| Option | Description | Selected |
|--------|-------------|----------|
| 错误作为 ToolMessage 返回 | 与 execute_node D-05 一致的 graceful degradation | ✓ |
| 抛出异常 | 全局异常处理器捕获 | |
| 静默失败（仅日志） | 不返回结果给 LLM | |

**User's choice:** 错误作为 ToolMessage 返回 — 与现有模式一致

### Timeout strategy

| Option | Description | Selected |
|--------|-------------|----------|
| 固定超时 | 统一 30 秒超时 | ✓ |
| 可配置超时 | 每个工具可自定义超时 | |
| 无超时 | 等待响应 | |

**User's choice:** 固定超时 — 简单可预测

### Error detail level

| Option | Description | Selected |
|--------|-------------|----------|
| 分类错误信息 | 区分连接失败/超时/协议错误/工具执行错误 | ✓ |
| 统一错误消息 | 所有错误统一格式 | |

**User's choice:** 分类错误信息 — LLM 能更精准解释问题

---

## Admin API Design

### Endpoint selection

| Option | Description | Selected |
|--------|-------------|----------|
| 注册服务器 | POST /mcp-servers | ✓ |
| 注销服务器 | DELETE /mcp-servers/{id} | ✓ |
| 查看服务器列表和状态 | GET /mcp-servers, GET /mcp-servers/{id} | ✓ |
| 更新配置 + 查看工具 | PATCH /mcp-servers/{id}, GET /mcp-servers/{id}/tools | ✓ |

**User's choice:** 全选 — 完整的 CRUD + 工具列表

### Access control

| Option | Description | Selected |
|--------|-------------|----------|
| JWT 认证即可 | 与现有端点一致 | ✓ |
| JWT + admin 角色限制 | 需实现角色检查 | |

**User's choice:** JWT 认证即可 — RBAC 未强制执行，保持一致

### Registration behavior

| Option | Description | Selected |
|--------|-------------|----------|
| 异步连接 | POST 立即返回 201，后台连接 | ✓ |
| 同步连接 | 等待连接完成再返回 | |

**User's choice:** 异步连接 — 避免长时间阻塞，客户端轮询状态

---

## Claude's Discretion

- Exact MCPClient class implementation (wrapper around mcp SDK ClientSession)
- MCPManager internal data structure and locking
- Health check interval and ping implementation
- Exact exponential backoff timing constants
- Timeout value (suggest 30 seconds)
- MCPToolHandler Protocol implementation details
- Pydantic schema definitions for Admin API request/response
- ToolRegistry.unregister(server_prefix) method signature
- Logging detail level for MCP operations

## Deferred Ideas

None — discussion stayed within phase scope
