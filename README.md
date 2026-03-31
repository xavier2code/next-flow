# NextFlow

通用智能体（Agent）平台 — 可扩展、高性能、易集成。

## 架构概览

- **前端**: React 19 + TypeScript + Vite 7 + shadcn/ui + Zustand + TanStack Query
- **后端**: Python 3.12 + FastAPI + LangGraph + SQLAlchemy 2.x (async)
- **数据库**: PostgreSQL 16 (pgvector) + Redis 7 + Qdrant
- **协议**: MCP (Model Context Protocol) 工具集成标准
- **部署**: Docker Compose

## 核心功能

- **Agent 引擎** — 基于 LangGraph 的有状态图工作流，支持分析-规划-执行-反思-响应循环
- **对话管理** — WebSocket 实时通信，流式输出
- **技能系统** — 可插拔技能包，Docker 沙箱隔离执行
- **MCP 集成** — 标准化工具发现、调用和会话管理
- **分层记忆** — 短期对话记忆 + 长期语义记忆
- **多 LLM 支持** — OpenAI / Anthropic / Ollama / vLLM，通过 LangChain 统一接入
- **认证授权** — JWT + RBAC

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
├── backend/                  # Python 后端
│   ├── app/
│   │   ├── api/v1/          # REST API 端点
│   │   ├── api/ws/          # WebSocket 聊天
│   │   ├── core/            # 配置、安全、日志
│   │   ├── db/              # 数据库会话、Redis
│   │   ├── models/          # SQLAlchemy 模型
│   │   ├── schemas/         # Pydantic 模式
│   │   └── services/        # 业务逻辑
│   │       ├── agent_engine/ # LangGraph Agent 编排
│   │       ├── mcp/         # MCP 协议集成
│   │       ├── memory/      # 分层记忆系统
│   │       ├── skill/       # 技能系统
│   │       └── tool_registry/ # 工具注册
│   ├── alembic/             # 数据库迁移
│   └── tests/               # 测试套件
├── frontend/                 # React 前端
│   └── src/
│       ├── components/      # UI 组件
│       │   ├── auth/        # 登录注册
│       │   ├── chat/        # 聊天界面
│       │   ├── layout/      # 布局
│       │   ├── management/  # 管理页面
│       │   └── settings/    # 设置页面
│       ├── stores/          # Zustand 状态
│       ├── hooks/           # React Query hooks
│       └── types/           # TypeScript 类型
└── docker-compose.yml       # 基础设施服务
```

## API 文档

后端启动后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## License

MIT
