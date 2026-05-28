# AI Frontend Generator 项目信息

## 1. 项目定位

这是一个面向后台管理系统场景的 AI 生成式前端 POC，目标不是单纯生成页面，而是验证一条更完整的业务链路：

- 用户输入自然语言页面需求
- AI 生成共享契约 / DSL
- 前后端基于契约生成页面与接口草稿
- 页面资产沉淀到页面管理
- 页面可绑定接口资产
- 运行时页面可直接做真实 CRUD 验证

当前项目已经演进为一个“多 Agent 工作流 + 页面资产管理 + 运行时预览”的原型系统。

## 2. 当前仓库结构

```text
ai-react/
  frontend/                # Vite + React 前端
  backend/                 # FastAPI 后端
  PROJECT_CONTEXT.md       # 旧版/阶段性项目上下文
  PROJECT_INFO.md          # 当前代码状态整理
  README.md
  vercel.json              # Vercel Services 配置
```

更细一点的核心目录：

```text
frontend/src/
  App.tsx                  # 主页面与核心交互
  api.ts                   # 前端 API 请求封装与类型
  routes/AppRoutes.tsx     # 路由注册
  generated/               # 已生成运行时页面注册
  hooks/usePagesStore.ts   # 页面列表状态管理
  lib/                     # 预览、导出、格式化等工具
  components/AppFrame.tsx  # 应用外壳

backend/
  app.py                   # Vercel 兼容入口
  main.py                  # FastAPI 应用装配
  config.py                # 环境变量与配置
  routers/                 # HTTP 路由
  services/                # 业务服务与外部集成
  agents/                  # 多 Agent 工作流
  generated/               # 已生成运行时接口/服务
  schemas/                 # 工作流与共享契约 Schema
```

## 3. 技术栈

前端：

- React 19
- TypeScript 6
- Vite 8
- React Router DOM 7
- Ant Design 6

后端：

- Python
- FastAPI
- Uvicorn
- httpx

数据与外部依赖：

- Supabase REST API：存储页面、接口、绑定关系、工作流记录
- 小米 / 兼容 OpenAI 风格 Chat Completions 接口：生成 DSL / 契约
- 本地 generated 目录：承接已生成的运行时代码与 SQL 草稿

## 4. 这个项目现在能做什么

### 4.1 多 Agent 工作流生成

前端首页已经是“多 Agent 工作台”，支持输入自然语言需求并触发工作流。

当前工作流角色包括：

- Planner：自然语言转共享协议
- Frontend：生成页面与路由草稿
- Service：生成接口与 SQL 草稿
- QA：做字段与契约一致性校验

工作流结果会展示：

- 共享契约
- Agent 执行步骤
- 生成产物摘要
- SQL 初始化脚本提示

### 4.2 页面资产管理

支持把页面 DSL 保存为页面资产，并通过页面列表管理已有页面。

页面资产包含：

- 页面基础信息
- DSL 定义
- 页面路由
- 页面状态（如 draft / verified）

### 4.3 接口资产管理

支持接口定义的新增、修改、删除、列表查看，接口定义包含：

- 方法
- 路径
- action 类型
- 请求 Schema
- 响应 Schema
- mock 数据
- 状态

### 4.4 页面与接口绑定

页面可以分别绑定：

- 列表接口
- 新增接口
- 编辑接口
- 删除接口

这意味着生成页不只是静态预览，而是可以接入真实数据源或 mock 数据源，验证完整 CRUD 链路。

### 4.5 运行时生成页

当前项目已经内置了两类运行时生成页示例：

- `customer`
- `supplier`

前端运行时路由注册位置：

- [frontend/src/generated/registry.ts](/Users/wangfang/Documents/GitHub/ai-react/frontend/src/generated/registry.ts)

后端运行时接口注册位置：

- [backend/generated/registry.py](/Users/wangfang/Documents/GitHub/ai-react/backend/generated/registry.py)

生成页相关后端代码位于：

- `backend/generated/customer/`
- `backend/generated/supplier/`

## 5. 前端架构说明

前端核心入口：

- [frontend/src/App.tsx](/Users/wangfang/Documents/GitHub/ai-react/frontend/src/App.tsx)

可以把前端理解成 3 层：

### 5.1 展示层

主要由 Ant Design 页面组成，承担：

- 工作流发起
- 页面管理
- 接口管理
- 页面绑定管理
- 生成页详情与预览

### 5.2 路由层

路由定义在：

- [frontend/src/routes/AppRoutes.tsx](/Users/wangfang/Documents/GitHub/ai-react/frontend/src/routes/AppRoutes.tsx)

当前主要路由有：

- `/generator`：多 Agent 工作台
- `/pages`：页面管理
- `/pages/:pageId`：页面详情
- `/apis`：接口管理
- `/page-apis` 与 `/page-apis/:pageId`：页面接口绑定
- `/generated/...`：运行时生成页

### 5.3 数据访问层

前端 API 封装在：

- [frontend/src/api.ts](/Users/wangfang/Documents/GitHub/ai-react/frontend/src/api.ts)

特点：

- 统一走 JSON 请求
- 统一处理 `{ code, message, data }` 响应结构
- 同时定义前后端共享的主要 TS 类型

## 6. 后端架构说明

后端应用装配入口：

- [backend/main.py](/Users/wangfang/Documents/GitHub/ai-react/backend/main.py)

Vercel 兼容入口：

- [backend/app.py](/Users/wangfang/Documents/GitHub/ai-react/backend/app.py)

后端大致分为 4 层：

### 6.1 Router 层

位于 `backend/routers/`，负责暴露 HTTP 接口。

当前主要路由模块：

- `health.py`
- `dsl.py`
- `pages.py`
- `apis.py`
- `customers.py`
- `workflow.py`

### 6.2 Service 层

位于 `backend/services/`，负责：

- 调用 Supabase REST API
- 调用 LLM 接口
- 管理工作流运行记录
- 处理客户/供应商等实体数据

### 6.3 Agent 层

位于 `backend/agents/`，负责多 Agent 工作流编排。

从目录命名上可以看出当前设计已经拆出：

- `planner_agent.py`
- `frontend_agent.py`
- `service_agent.py`
- `qa_agent.py`
- `orchestrator.py`

说明项目核心已经从“单接口生成 DSL”演进为“有明确角色分工的工作流系统”。

### 6.4 Generated 层

位于 `backend/generated/`，承接生成后的运行时代码，例如：

- 实体路由
- 实体服务
- 建表 SQL
- 本地样例数据

这层相当于“生成结果的落盘区”。

## 7. 当前后端接口清单

健康检查：

- `GET /api/health`

DSL / 契约生成：

- `POST /api/dsl/generate`

工作流：

- `POST /api/workflows/generate`
- `GET /api/workflows`
- `GET /api/workflows/{run_id}`

页面管理：

- `GET /api/pages?pageNo=&pageSize=`
- `GET /api/pages/{page_id}`
- `POST /api/pages`
- `DELETE /api/pages/{page_id}`
- `GET /api/pages/{page_id}/bindings`
- `PUT /api/pages/{page_id}/bindings`

接口管理：

- `GET /api/apis?pageNo=&pageSize=`
- `POST /api/apis`
- `PUT /api/apis/{api_id}`
- `DELETE /api/apis/{api_id}`

客户示例数据：

- `GET /api/customers`
- `POST /api/customers`
- `PUT /api/customers/{customer_id}`
- `DELETE /api/customers/{customer_id}`

运行时生成接口：

- `/api/generated/...`

具体路径会随着 `backend/generated/` 中注册的实体变化。

## 8. 配置与环境变量

配置读取位置：

- [backend/config.py](/Users/wangfang/Documents/GitHub/ai-react/backend/config.py)

后端会优先读取：

- `backend/.env`

当前关键环境变量包括：

- `SUPABASE_URL`
- `SUPABASE_KEY`
- `SUPABASE_PAGES_TABLE`
- `SUPABASE_APIS_TABLE`
- `SUPABASE_BINDINGS_TABLE`
- `SUPABASE_CUSTOMERS_TABLE`
- `SUPABASE_SUPPLIERS_TABLE`
- `SUPABASE_WORKFLOW_RUNS_TABLE`
- `SUPABASE_WORKFLOW_STEPS_TABLE`
- `SUPABASE_WORKFLOW_ARTIFACTS_TABLE`
- `XIAOMI_API_BASE`
- `XIAOMI_API_KEY`
- `XIAOMI_MODEL`

已存在环境变量示例文件：

- [backend/.env.example](/Users/wangfang/Documents/GitHub/ai-react/backend/.env.example)

## 9. 本地启动方式

前端：

```bash
cd frontend
pnpm dev
```

后端：

```bash
cd frontend
pnpm run dev:server
```

这里后端命令虽然从 `frontend` 目录执行，但实际启动的是：

```bash
python -m uvicorn backend.app:app --app-dir .. --host 127.0.0.1 --port 8000
```

也就是说，`frontend/package.json` 同时承担了本地联调脚本入口。

## 10. 部署方式

根目录有：

- [vercel.json](/Users/wangfang/Documents/GitHub/ai-react/vercel.json)

当前使用的是 Vercel `experimentalServices` 配置：

- `web` -> `frontend`
- `api` -> `backend/app.py`

路由前缀：

- 前端服务挂在 `/`
- 后端服务挂在 `/api`

## 11. 当前项目状态判断

基于现有代码，可以把这个项目判断为：

- 已完成前后端分离基础设施
- 已具备 DSL / 共享契约生成能力
- 已具备多 Agent 工作流编排能力
- 已具备页面与接口资产管理能力
- 已具备页面绑定接口并验证 CRUD 的运行时雏形
- 已具备 Vercel 部署形态

但它目前仍然更像一个 POC / 验证型系统，而不是完整生产系统，原因包括：

- generated 能力仍以内置实体示例为主
- 依赖 Supabase 表结构与外部模型配置
- 生成结果的自动落盘、自动注册、自动发布链路还不是完全通用化平台

## 12. 适合怎么理解这个项目

如果要一句话总结，可以这样理解：

这是一个“让 AI 帮你生成后台 CRUD 页面，并把页面、接口、契约和运行时验证串成闭环”的 React + FastAPI 原型项目。

如果要从工程视角理解，可以分成 3 个核心模块：

1. 生成入口：自然语言 -> 共享契约 / DSL -> 多 Agent 工作流
2. 资产中心：页面、接口、绑定关系统一沉淀
3. 运行时验证：生成页接真实或 mock 数据，验证 CRUD 链路

## 13. 建议你接下来优先看的文件

如果你要继续开发，推荐阅读顺序：

1. [frontend/src/App.tsx](/Users/wangfang/Documents/GitHub/ai-react/frontend/src/App.tsx)
2. [frontend/src/api.ts](/Users/wangfang/Documents/GitHub/ai-react/frontend/src/api.ts)
3. [backend/main.py](/Users/wangfang/Documents/GitHub/ai-react/backend/main.py)
4. [backend/routers/workflow.py](/Users/wangfang/Documents/GitHub/ai-react/backend/routers/workflow.py)
5. [backend/config.py](/Users/wangfang/Documents/GitHub/ai-react/backend/config.py)
6. `backend/agents/` 整个目录
7. `backend/services/` 中的 Supabase、LLM、workflow_store
8. `frontend/src/generated/` 与 `backend/generated/`

