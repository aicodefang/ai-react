# AI Frontend Generator

这个仓库已经拆成适合本地联调和 Vercel Services 部署的结构：

```text
frontend/  -> Vite React
backend/   -> FastAPI
vercel.json
```

## 本地启动

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

## Vercel

根目录 `vercel.json` 已配置 `experimentalServices`：

- `web` -> `frontend`
- `api` -> `backend/app.py`

部署时建议在 Vercel 项目设置中选择 `Services` 作为 Framework Preset。
