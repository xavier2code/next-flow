# Phase 6: Skill System - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-30
**Phase:** 06-skill-system
**Areas discussed:** Skill 包格式, 工具发现与注册, 沙箱执行模型, 生命周期管理

---

## Skill 包格式

| Option | Description | Selected |
|--------|-------------|----------|
| YAML manifest + Python 代码 | manifest.yaml 声明元数据 + main.py 入口 + 依赖文件 | |
| JSON manifest + 多语言支持 | manifest.json + 任意语言入口 | |
| 极简 JSON | 仅 name/version/entry | |

**User's choice:** YAML manifest + Python 代码 → **Updated to:** SKILL.md with YAML frontmatter (merged manifest into SKILL.md)

| Option | Description | Selected |
|--------|-------------|----------|
| 全静态声明 | manifest/frontmatter 声明工具的 name/description/parameters JSON Schema | ✓ |
| 运行时动态注册 | 技能启动后通过 HTTP API 注册工具 | |
| 混合模式 | manifest 声明基本信息，运行时补充 | |

**User's choice:** 全静态声明

| Option | Description | Selected |
|--------|-------------|----------|
| ZIP 包上传 | 用户上传 ZIP，平台自动解压验证存储 | ✓ |
| Git 仓库导入 | 通过 Git URL 拉取构建 | |
| 在线编辑器 | 平台上在线编辑代码 | |

**User's choice:** ZIP 包上传

| Option | Description | Selected |
|--------|-------------|----------|
| 仅 Python | 入口固定为 Python 异步函数 | ✓ |
| Python + Node.js | 双语言支持 | |
| 任意语言 | 只要能启动 HTTP 服务 | |

**User's choice:** 仅 Python

| Option | Description | Selected |
|--------|-------------|----------|
| SDK 包模式 | 提供 nextflow-skill-sdk pip 包 | |
| 纯函数模式 | 入口接收 dict 返回 dict | |
| HTTP 服务模式 | 技能实现 HTTP 接口 | |

**User's choice:** 基础镜像 sidecar（开发者无需 import 任何东西，只需遵循 async def run(params) -> dict 约定）

| Option | Description | Selected |
|--------|-------------|----------|
| 一个函数一个工具 | script/ 每个文件对应一个工具 | ✓ |
| 单入口路由分发 | 一个函数根据 tool_name 参数分发 | |
| 装饰器注册 | @skill.tool() 装饰器 | |

**User's choice:** 一个函数一个工具（script/ 一个文件对应一个工具）

| Option | Description | Selected |
|--------|-------------|----------|
| 仅网络权限 | 仅声明网络出站权限 | ✓ |
| 多维度权限 | 网络+文件系统+环境变量 | |
| 默认无权限 | 全部禁止 | |

**User's choice:** 仅网络权限

**User clarification:** Skills 是一种特殊 AI 能力，每个 Skill 都有 SKILL.md，可能包含 script/ 和 reference/ 文件夹。

| Option | Description | Selected |
|--------|-------------|----------|
| SKILL.md 是 Agent 指南 | 给 Agent 看的使用指令 | ✓ |
| SKILL.md 是人类文档 | 给人看的文档 | |
| 双层文档 | 上半 Agent 指令，下半人类文档 | |

**User's choice:** SKILL.md 是 Agent 指南

| Option | Description | Selected |
|--------|-------------|----------|
| 两者并存 | SKILL.md + manifest.yaml | |
| SKILL.md 合并 manifest | frontmatter 替代 manifest | ✓ |

**User's choice:** SKILL.md 合并 manifest（frontmatter 即 manifest）

| Option | Description | Selected |
|--------|-------------|----------|
| 标准 requirements.txt | Skill 根目录下，平台构建时 pip install | ✓ |
| manifest 中声明依赖 | frontmatter 中声明 | |
| 无自定义依赖 | 仅预装库 | |

**User's choice:** 标准 requirements.txt

| Option | Description | Selected |
|--------|-------------|----------|
| 严格固定结构 | SKILL.md + main.py + requirements.txt | ✓ |
| 自由结构 + 入口指定 | 任意目录，frontmatter 指定入口 | |

**User's choice:** 严格固定结构（SKILL.md 必需，script/ 和 reference/ 可选）

| Option | Description | Selected |
|--------|-------------|----------|
| SystemMessage 注入 | SKILL.md 正文作为 SystemMessage | ✓ |
| 混合注入 + RAG 检索 | 区分必知和可选参考 | |
| 纯 RAG 检索 | 按需获取 | |

**User's choice:** SystemMessage 注入

| Option | Description | Selected |
|--------|-------------|----------|
| SKILL.md 必需，其余可选 | 纯知识型可以没有 script/ | ✓ |
| SKILL.md + script/ 必需 | 必须有可执行工具 | |
| 完全灵活 | 由作者决定 | |

**User's choice:** SKILL.md 必需，其余可选

| Option | Description | Selected |
|--------|-------------|----------|
| 允许纯知识型 | 无工具的 Skill 仍然有效 | ✓ |
| 必须有工具 | 否则不算技能 | |

**User's choice:** 允许纯知识型

| Option | Description | Selected |
|--------|-------------|----------|
| 直接注入上下文 | reference 文件全部注入 | |
| RAG 向量检索 | 按需检索 | |
| 大小分流处理 | 小文件注入，大文件走 RAG | ✓ |

**User's choice:** 大小分流处理

| Option | Description | Selected |
|--------|-------------|----------|
| 单版本覆盖 | 同名覆盖，无多版本 | ✓ |
| 多版本 + 默认最新 | 保留历史版本 | |
| 版本绑定到 Agent | 每个 Agent 指定版本 | |

**User's choice:** 单版本覆盖

---

## 工具发现与注册

| Option | Description | Selected |
|--------|-------------|----------|
| enable 时注册 | 上传验证但不注册，enable 时注册到 ToolRegistry | ✓ |
| 上传即注册 | 上传后立即注册 | |
| 按需懒加载 | Agent 调用时加载 | |

**User's choice:** enable 时注册

| Option | Description | Selected |
|--------|-------------|----------|
| 复用 unregister(prefix) | 批量注销，与 MCP 一致 | ✓ |
| 单工具注销 | 逐个注销 | |

**User's choice:** 复用 unregister(prefix)（Skill 级别批量注销）

| Option | Description | Selected |
|--------|-------------|----------|
| 平台注入 Agent 上下文 | SKILL.md 作为 SystemMessage 注入 | ✓ |
| Agent 主动查询 | Agent 调用 list_tools 接口 | |
| 工具描述中包含指南 | tool schema 的 description 字段 | |

**User's choice:** 平台注入 Agent 上下文

| Option | Description | Selected |
|--------|-------------|----------|
| 全部注入 | 所有已启用 Skill 的 SKILL.md 拼接 | |
| 按相关性筛选注入 | 根据用户消息筛选 | |
| 摘要 + 按需加载 | 注入摘要列表，Agent 通过 load_skill 按需加载 | ✓ |

**User's choice:** 摘要 + 按需加载

| Option | Description | Selected |
|--------|-------------|----------|
| 内置 load_skill 工具 | Agent 调用工具获取完整 SKILL.md | ✓ |
| 平台自动判断注入 | 平台在 Execute 前自动注入 | |

**User's choice:** 内置 load_skill 工具

| Option | Description | Selected |
|--------|-------------|----------|
| 逗号分隔列表 | 名称+简短描述的逗号分隔 | ✓ |
| 分类列表 | 按类别分组 | |
| 仅名称列表 | 最小化上下文占用 | |

**User's choice:** 逗号分隔列表

| Option | Description | Selected |
|--------|-------------|----------|
| 不注册工具 | 纯指令注入，Agent 按指南行动 | ✓ |
| 注册一个查询工具 | 统一查询接口 | |

**User's choice:** 纯知识型不注册任何工具

| Option | Description | Selected |
|--------|-------------|----------|
| 全局共享 | 所有 Agent 访问所有工具 | ✓ |
| 按 Agent 绑定 | 每个 Agent 有自己的 Skill 列表 | |

**User's choice:** 全局共享（Phase 2 D-14 延续）

| Option | Description | Selected |
|--------|-------------|----------|
| 全局唯一名称 | 同名不允许共存 | ✓ |
| 允许同名 | 命名空间区分 | |

**User's choice:** 全局唯一名称

---

## 沙箱执行模型

| Option | Description | Selected |
|--------|-------------|----------|
| HTTP API 通信 | 容器内 sidecar HTTP 服务 | ✓ |
| Docker exec + stdin/stdout | 每次启动容器执行 | |
| gRPC/Unix socket | 高性能但复杂 | |

**User's choice:** HTTP API 通信

| Option | Description | Selected |
|--------|-------------|----------|
| 长驻容器 | enable 时启动，disable 时停止 | ✓ |
| 按调用创建/销毁 | 每次调用启动新容器 | |
| 共享容器池 | 多 Skill 共享基础容器 | |

**User's choice:** 长驻容器（服务型）

| Option | Description | Selected |
|--------|-------------|----------|
| 统一基础镜像 + volume 挂载 | 避免每个 Skill 构建镜像 | ✓ |
| 每个 Skill 独立镜像 | pip install 后构建专属镜像 | |

**User's choice:** 统一基础镜像 + volume 挂载

| Option | Description | Selected |
|--------|-------------|----------|
| 全局统一限制 | Settings 中统一配置 | ✓ |
| Skill 自声明 + 平台上限 | frontmatter 声明资源需求 | |
| 手动配置 | 管理员为每个 Skill 配置 | |

**User's choice:** 全局统一限制

| Option | Description | Selected |
|--------|-------------|----------|
| 提供官方 SDK | nextflow-skill-sdk pip 包 | |
| 纯约定无 SDK | 只遵循接口约定 | |
| 基础镜像 sidecar | 镜像内 sidecar 自动发现 run() 函数 | ✓ |

**User's choice:** 基础镜像 sidecar（无需 SDK import）

| Option | Description | Selected |
|--------|-------------|----------|
| 单一端口 + 路径路由 | sidecar 单端口，路径区分工具 | ✓ |
| 每个工具独立进程 | 独立 HTTP 服务进程 | |

**User's choice:** 单一端口 + 路由路由

| Option | Description | Selected |
|--------|-------------|----------|
| 健康检查 + 自动重启 | 定期 /health 检查，失败则重启 | ✓ |
| 被动错误处理 | 只在调用失败时处理 | |

**User's choice:** 健康检查 + 自动重启

**User clarification:** 不是所有 Skill 都需要容器。纯知识型无容器，有脚本但无工具的一次性脚本即启即销。

| Option | Description | Selected |
|--------|-------------|----------|
| 显式声明类型 | frontmatter 中 type 字段 | |
| 平台自动推断 | 根据结构推断 | ✓ |

**User's choice:** 平台自动推断（基于 tools 声明：无 script/ = 知识型, 有 script/ + 有 tools = 常驻服务型, 有 script/ + 无 tools = 一次性脚本型）

| Option | Description | Selected |
|--------|-------------|----------|
| 基于 tools 声明推断 | 有 tools = 服务型，无 tools = 脚本型 | ✓ |
| 统一长驻容器 | 所有有 script/ 的都长驻 | |

**User's choice:** 基于 tools 声明推断

| Option | Description | Selected |
|--------|-------------|----------|
| 即启即销 | docker run --rm | ✓ |
| 和常驻型统一管理 | 保持容器运行 | |

**User's choice:** 一次性脚本即启即销

| Option | Description | Selected |
|--------|-------------|----------|
| Agent 按需调用 | Agent 判断何时执行 | ✓ |
| 启用时自动执行 | 初始化钩子 | |

**User's choice:** Agent 按需调用

| Option | Description | Selected |
|--------|-------------|----------|
| 仅预装库 | 只用基础镜像库 | ✓ |
| 允许 pip install | enable 时安装依赖 | |
| 白名单机制 | 审核通过的包白名单 | |

**User's choice:** 一次性脚本仅允许预装库

---

## 生命周期管理

| Option | Description | Selected |
|--------|-------------|----------|
| 严格验证 | frontmatter + JSON Schema + 文件对应 | ✓ |
| 最小验证 | 只验证 SKILL.md 存在和可解析 | |
| 深度验证（试运行） | 实际在沙箱中运行测试 | |

**User's choice:** 严格验证

| Option | Description | Selected |
|--------|-------------|----------|
| 先停后启 | disable 旧 → 替换 → enable 新 | ✓ |
| 蓝绿替换 | 先启新再停旧 | |
| 优雅替换 | 等待当前调用完成 | |

**User's choice:** 先停后启

| Option | Description | Selected |
|--------|-------------|----------|
| 复用 MCP CRUD 模式 | 完整 CRUD + enable/disable 端点 | ✓ |
| 简化 CRUD | upload + list + delete + toggle | |

**User's choice:** 复用 MCP CRUD 模式

| Option | Description | Selected |
|--------|-------------|----------|
| ZIP 整包存 MinIO | 原始 ZIP 直接存储 | ✓ |
| 解压后分文件存储 | SKILL.md/script/reference 分别存储 | |

**User's choice:** ZIP 整包存 MinIO

| Option | Description | Selected |
|--------|-------------|----------|
| 自动恢复 | 重启后从 DB+MinIO 恢复已启用 Skill | ✓ |
| 重启后需要手动启用 | 所有 Skill 变为 disabled | |

**User's choice:** 自动恢复

| Option | Description | Selected |
|--------|-------------|----------|
| 扩展现有模型 | 添加字段到 Skill 表 | ✓ |
| 重新设计模型 | 从零开始 | |

**User's choice:** 扩展现有模型

| Option | Description | Selected |
|--------|-------------|----------|
| 同步替换 | 上传 API 返回时已完成替换 | ✓ |
| 异步替换 | 后台处理，需轮询状态 | |

**User's choice:** 同步替换

| Option | Description | Selected |
|--------|-------------|----------|
| 单 Skill ZIP | 一个 ZIP = 一个 Skill | ✓ |
| 多 Skill ZIP | 批量导入 | |

**User's choice:** 单 Skill ZIP

---

## Claude's Discretion

- Exact SKILL.md frontmatter schema (optional fields)
- Base image pre-installed library selection
- Resource limit default values
- Health check interval
- Reference file size threshold (direct-inject vs RAG)
- Sidecar HTTP server implementation
- load_skill tool response format
- Error handling when sandbox unavailable
- SkillToolHandler implementation details
- Logging detail level

## Deferred Ideas

- Per-agent skill binding — v2 after RBAC
- Multi-version skill coexistence — v2 with marketplace
- Skill marketplace (MKT-01) — v2
- Custom per-skill resource limits — v2
- SDK pip package — evaluate if sidecar proves limiting
- Celery for async skill processing — if sync becomes bottleneck
- Git repository import — future enhancement
- Online skill editor — future enhancement
