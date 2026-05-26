# AI Frontend Generator 项目上下文

## 1. 项目背景

这是一个面向 AI 大赛场景的前端生成 POC，目标不是只做一个“会生成页面截图”的 Demo，而是验证一条更完整的业务链路：

- 用户输入自然语言需求
- AI 生成符合业务规范的 DSL JSON
- DSL 驱动后台管理风格页面预览
- 页面资产沉淀到页面管理
- 页面可绑定接口资产
- 预览页可基于绑定接口完成真实 CRUD 验证

项目当前聚焦在 React 管理系统场景，优先验证“业务规范驱动的页面生成管理系统”。

## 2. 当前目录结构

```text
ai-ai-react-2/
  frontend/
    src/
      App.tsx
      App.css
      api.ts
    public/
    package.json
    vite.config.ts
    tsconfig.json
  backend/
    app.py
    main.py
    config.py
    models.py
    responses.py
    exceptions.py
    customers.json
    requirements.txt
    supabase_api_management.sql
    routers/
      health.py
      dsl.py
      customers.py
      apis.py
      pages.py
    services/
      customers.py
      dsl.py
      supabase.py
  vercel.json
```

说明：

- `frontend/` 是独立 Vite 前端目录
- `backend/app.py` 是 FastAPI 薄入口
- 根目录 `vercel.json` 已按 Vercel Services 配置前后端

## 3. 当前技术栈

前端：

- React 19
- TypeScript
- Vite 8
- React Router DOM 7
- Ant Design 6
- pnpm

后端：

- Python 3.14
- FastAPI
- Uvicorn
- httpx
- Pydantic v2

数据与存储：

- Supabase REST API
- 本地 JSON 文件作为客户 CRUD 示例数据源

## 4. 当前后端接口

- `GET /health`
- `POST /api/dsl/generate`
- `GET /api/pages?pageNo=&pageSize=`
- `GET /api/pages/{page_id}`
- `POST /api/pages`
- `DELETE /api/pages/{page_id}`
- `GET /api/pages/{page_id}/bindings`
- `PUT /api/pages/{page_id}/bindings`
- `GET /api/apis?pageNo=&pageSize=`
- `POST /api/apis`
- `PUT /api/apis/{api_id}`
- `DELETE /api/apis/{api_id}`
- `GET /api/customers`
- `POST /api/customers`
- `PUT /api/customers/{customer_id}`
- `DELETE /api/customers/{customer_id}`

## 5. 当前运行方式

前端启动：

```bash
cd frontend
pnpm dev
```

后端启动：

```bash
cd frontend
pnpm run dev:server
```

当前 `dev:server` 实际执行：

```bash
python -m uvicorn backend.app:app --app-dir .. --host 127.0.0.1 --port 8000
```

## 6. Vercel 部署说明

当前仓库已经整理成适合 Vercel Services 的形态：

- `frontend/` 对应前端服务
- `backend/` 对应 FastAPI 服务
- 根目录 `vercel.json` 负责统一路由

如果在 Vercel 控制台部署，这个项目应使用 `Services` 框架预设。
