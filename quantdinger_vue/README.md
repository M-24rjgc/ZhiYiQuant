# ZhiYiQuant Web UI (Vue 2)

This is the ZhiYiQuant frontend web UI built with **Vue 2** + **Ant Design Vue**. It connects to the Python backend (`backend_api_python/`) through HTTP APIs to provide charts, indicators, backtests, AI analysis, and strategy management.

> This UI is based on the open-source `ant-design-vue-pro` ecosystem, heavily adapted for ZhiYiQuant.

## What you get

- **Dashboards**: summary views and operational panels
- **Indicator analysis**: Kline charts + indicator editing + backtest history
- **AI analysis**: multi-agent reports (optional LLM/search, configured on backend)
- **Trading assistant**: strategy lifecycle + positions/records (depending on backend capability)
- **Local auth**: login with backend-configured admin credentials

## Quick start (local development)

### Prerequisites

- Node.js 16+ recommended
- Backend running at `http://localhost:5000` (see `backend_api_python/README.md`)

### 1) Install dependencies

```bash
cd quantdinger_vue
npm install
```

### 2) Start dev server

```bash
npm run serve
```

Dev server runs at `http://localhost:8000`.

### 3) API proxy (important)

In dev mode, this project proxies `/api/*` to the backend:

- Proxy config: `quantdinger_vue/vue.config.js`
- Default target: `http://localhost:5000`

If your backend runs on a different host/port, update `vue.config.js` accordingly.

## Production build

```bash
npm run build
```

The output will be generated under `quantdinger_vue/dist/`.

## Notes

- **CORS**: when using the dev proxy, you typically don’t need extra CORS config.
- **Login**: use the credentials defined in `backend_api_python/.env` (`ADMIN_USER` / `ADMIN_PASSWORD`).

## License

Apache License 2.0. See repository root `LICENSE`.
