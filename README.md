# 智能旅行助手 🌍✈️

基于 **LangChain + FastAPI** 的智能旅行规划助手，集成**高德地图 Web 服务**（POI 搜索、天气查询、路线规划），根据用户的旅行需求自动生成个性化多日行程。

## 功能特性

- 🤖 **AI 驱动的旅行规划**：通过 LangChain 调用大模型，智能生成详细的多日旅程（景点、餐饮、酒店、预算）；
- 🗺️ **高德地图数据**：直接调用高德地图 REST API 获取真实景点、酒店和天气数据（不依赖 MCP 中间层）；
- 📅 **个性化行程**：支持选择出行日期、天数、交通方式、住宿偏好和额外要求；
- 🖼️ **景点图片**：集成 Unsplash 获取景点配图；
- 📄 **导出能力**：前端支持将行程导出为图片或 PDF。

## 技术栈

- **后端**：Python 3.10+、FastAPI、LangChain（ChatOpenAI）、高德地图 Web 服务 API
- **前端**：Vue 3、Vite、Ant Design Vue、TypeScript

## 目录结构

```
trip-planner/
├── backend/
│   ├── app/
│   │   ├── agents/            # 旅行规划器（LangChain）
│   │   ├── api/               # FastAPI 路由（trip / poi / map）
│   │   ├── models/            # 数据模型（Pydantic）
│   │   └── services/          # 大模型、高德地图、Unsplash 服务
│   ├── requirements.txt
│   ├── run.py                 # 启动脚本
│   └── .env                   # 环境配置（密钥）
└── frontend/                  # Vue 3 前端
```

## 快速开始

### 后端

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

服务默认运行在 `http://localhost:8000`，API 文档：`http://localhost:8000/docs`。

### 前端

```bash
cd frontend
npm install
npm run dev
```

浏览器打开 `http://localhost:5173`。

## 配置说明（backend/.env）

| 变量 | 说明 |
| --- | --- |
| `AMAP_API_KEY` | 高德地图 Web 服务 Key（必填，https://console.amap.com） |
| `LLM_API_KEY` | 大模型 API Key（OpenAI 兼容端点） |
| `LLM_BASE_URL` | 大模型服务地址，如 `https://api.deepseek.com` 或阿里云百炼兼容模式 |
| `LLM_MODEL_ID` | 模型名称，如 `qwen-plus`、`deepseek-chat` |
| `LLM_TIMEOUT` | 大模型请求超时时间（秒） |
| `UNSPLASH_ACCESS_KEY` / `UNSPLASH_SECRET_KEY` | Unsplash 图片服务密钥（可选） |
| `CORS_ORIGINS` | 前端跨域允许来源，逗号分隔 |

> 建议把 `LLM_MODEL_ID` 配置为通用的对话/规划模型（如 `qwen-plus`），
> 不要使用数学专用模型（如 `qwen-math-turbo`），以保证行程 JSON 输出质量。

## API 说明

- `POST /api/trip/plan`：生成旅行计划（核心接口）
- `GET /api/map/poi`：搜索 POI（兴趣点）
- `GET /api/map/weather`：查询天气
- `POST /api/map/route`：规划路线
- `GET /api/poi/detail/{id}`：获取 POI 详情
- `GET /api/poi/photo?name=景点名`：获取景点图片

## 旅行规划流程

1. **搜索景点**：根据用户偏好调用高德 POI 搜索；
2. **查询天气**：高德地理编码获取城市编码后查询天气；
3. **搜索酒店**：高德 POI 搜索酒店数据；
4. **生成行程**：将以上真实数据交给 LangChain 大模型，生成结构化 JSON 行程；
5. **兜底方案**：任何一步失败时返回基础行程，保证接口可用。
