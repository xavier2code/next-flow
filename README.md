# NextFlow

通用智能体（Agent）平台 — 可扩展、高性能、易集成。

NextFlow 提供完整的 Agent 编排能力：基于 LangGraph 的有状态工作流引擎、标准化 MCP 工具集成、可插拔技能系统、分层记忆，以及基于 Vercel AI SDK 的流式对话前端。面向智能客服、自动化任务编排、知识库问答及企业 AI 应用集成等场景。

## 架构概览

```
┌─────────────────────────────────────────────────────┐
│                    Frontend (SPA)                    │
│          React 19 + Vite 7 + shadcn/ui              │
│        Vercel AI SDK (SSE Data Stream v2)            │
└──────────────────────┬──────────────────────────────┘
                       │ REST + SSE
┌──────────────────────▼──────────────────────────────┐
│                   FastAPI Gateway                     │
│            JWT Auth · Cursor Pagination               │
├──────────┬──────────┬──────────┬────────────────────┤
│  Agent   │  Memory  │   MCP    │      Skill         │
│  Engine  │  System  │ Manager  │    Service          │
│ LangGraph│ 3-Layer  │ Protocol │  Docker Sandbox     │
├──────────┴──────────┴──────────┴────────────────────┤
│  PostgreSQL 16  ·  Redis 7  ·  MinIO  ·  Qdrant      │
└─────────────────────────────────────────────────────┘
```

### 技术栈

| 层级 | 技术 |
|------|------|
| **前端** | React 19 + TypeScript 5.7 + Vite 7 + shadcn/ui + Zustand 5 + TanStack Query |
| **后端** | Python 3.12 + FastAPI 0.135 + LangGraph 1.1 + SQLAlchemy 2.x (async) |
| **数据库** | PostgreSQL 16 + Redis 7 + Qdrant (向量) + MinIO (对象存储) |
| **协议** | MCP (Model Context Protocol) · SSE Data Stream Protocol v2 |
| **部署** | Docker Compose · Nginx 反向代理 |

## 核心功能

- **Agent 引擎** — LangGraph 4 节点工作流（Analyze → Plan → Execute → Respond），PostgreSQL checkpointer 持久化
- **流式对话** — SSE Data Stream Protocol v2，支持 reasoning 展示、消息重新生成
- **多 LLM 支持** — OpenAI / Anthropic / Ollama / vLLM，通过 LangChain 统一接入，支持流式输出
- **分层记忆** — 短期（Redis 滑动窗口 + LLM 压缩）+ 长期（LangGraph Store 语义搜索）+ 工作记忆（AgentState）
- **MCP 集成** — 多服务器连接、工具发现（namespaced 注册）、Streamable HTTP/SSE 自动回退、健康监控
- **技能系统** — SKILL.md + ZIP 包格式验证、Docker 沙箱隔离执行、MinIO 存储
- **认证** — JWT + refresh token rotation + argon2 密码哈希
- **管理面板** — Agent / Skills / MCP 服务管理 + 用户设置

## 快速开始

### 环境要求

- Python 3.12+
- Node.js 22 LTS
- Docker & Docker Compose
- [uv](https://docs.astral.sh/uv/) (Python 包管理器)

### 1. 启动基础设施

```bash
docker compose up -d
```

启动 PostgreSQL (5432)、Redis (6380)、MinIO (9000/9001)。

### 2. 配置后端

```bash
cd backend
cp .env.example .env
```

编辑 `.env` 填入你的 API Key 和配置：

```env
# LLM Provider
DEFAULT_PROVIDER=openai
DEFAULT_MODEL=gpt-4o
OPENAI_API_KEY=your-api-key
OPENAI_API_BASE=https://api.openai.com/v1

# Embedding
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=embedding-3
EMBEDDING_API_KEY=your-embedding-api-key
EMBEDDING_API_BASE=https://open.bigmodel.cn/api/paas/v4
```

### 3. 安装后端依赖并运行

```bash
cd backend
uv sync
alembic upgrade head
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. 安装前端依赖并运行

```bash
cd frontend
npm install
npm run dev
```

前端默认运行在 http://localhost:5173，后端 API 在 http://localhost:8000。

## 项目结构

```
next-flow/
├── backend/
│   ├── app/
│   │   ├── api/v1/              # REST 端点 (auth, chat, agents, skills, mcp_servers, settings)
│   │   ├── core/                # 配置、安全、日志
│   │   ├── db/                  # 数据库会话、Redis 连接
│   │   ├── models/              # SQLAlchemy 模型
│   │   ├── schemas/             # Pydantic 请求/响应模式
│   │   └── services/
│   │       ├── agent_engine/    # LangGraph Agent 编排 (4-node pipeline)
│   │       ├── mcp/             # MCP 协议集成 (Client, Manager, 工具发现)
│   │       ├── memory/          # 三层记忆系统
│   │       ├── skill/           # 技能系统 (验证、沙箱执行)
│   │       └── tool_registry/   # 统一工具注册
│   ├── alembic/                 # 数据库迁移
│   └── tests/
├── frontend/
│   └── src/
│       ├── components/          # UI 组件 (auth, chat, layout, management, settings, shared)
│       ├── pages/               # 页面 (ChatPage, ProtectedRoute)
│       ├── hooks/               # React Query + 自定义 hooks
│       ├── stores/              # Zustand 状态管理
│       ├── lib/                 # 工具函数
│       └── types/               # TypeScript 类型定义
├── backend/Dockerfile           # 后端多阶段构建 (python:3.12-slim, Gunicorn)
├── frontend/Dockerfile          # 前端多阶段构建 (Node 22 → Nginx)
└── docker-compose.yml           # 基础设施 + 应用服务
```

## API 文档

后端启动后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Roadmap

- [x] **v1.0** — MVP: 认证、Agent 引擎、对话管理、记忆系统、MCP 集成、技能系统、前端 UI
- [ ] **v1.1** — Docker 部署就绪: 生产级容器化、Nginx 反向代理、多环境配置
- [ ] **v2.0** — RBAC、RAG 知识库、并行工具执行、Human-in-the-loop、多租户、Skill 市场

## License

MIT
