# Vercel 部署说明（旅行助手）

本仓库已内置 Vercel 部署配置：

- `api/index.py`：FastAPI（ASGI）入口，Vercel Python 运行时自动加载 `app`；
- `vercel.json`：把 `/api/*`、`/health` 路由到 Python 函数，其余交给前端 SPA；
- `requirements.txt`（仓库根目录）：后端依赖；
- 前端通过 `VITE_BASE_PATH` / `VITE_API_BASE_URL` 环境变量适配 Vercel 独立域名。

## 部署步骤（Vercel 控制台导入 GitHub）

1. 打开 https://vercel.com → **Add New → Project**；
2. **Import** `asdjjjjj/trip-planner` 仓库；
3. Framework Preset 选 **Vite**（自动识别），Build Command 保持 `npm run build`，Output 目录 `frontend/dist`；
4. 在 **Environment Variables** 里添加：

| 变量 | 值 |
| --- | --- |
| `VITE_BASE_PATH` | `/` |
| `VITE_API_BASE_URL` | `/` |
| `VITE_AMAP_WEB_JS_KEY` | 高德 Web JS Key |
| `LLM_API_KEY` | DeepSeek API Key |
| `LLM_BASE_URL` | `https://api.deepseek.com` |
| `LLM_MODEL_ID` | `deepseek-chat`（更快，建议） |
| `AMAP_API_KEY` | 高德 Web 服务 Key |
| `UNSPLASH_ACCESS_KEY` | Unsplash Key（可选） |
| `UNSPLASH_SECRET_KEY` | Unsplash Key（可选） |

5. 点 **Deploy**。

## ⚠️ 免费版（Hobby）时长限制

一次行程生成需要调用 DeepSeek 生成 JSON，实测耗时约 60~100 秒，
而 Vercel **Hobby 版函数最长 60 秒**，会超时。需要：

- 升级到 **Pro**（函数最长 300 秒），并把 `vercel.json` 里的
  `maxDuration` 改成 `300`；或
- 使用更快的模型（如 `deepseek-chat`）并把提示词精简，尽量压进 60 秒内。

## 常用维护

- 修改代码后 push 到 GitHub，Vercel 自动重新部署；
- 环境变量在 Vercel 项目 Settings → Environment Variables 里改；
- 日志：Vercel 项目 → Logs。
