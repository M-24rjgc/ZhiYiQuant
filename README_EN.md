# ZhiyiQuant

ZhiyiQuant is a local-first quantitative desktop workspace built around `Tauri 2`.

V1 is scoped to a single-user desktop workflow and keeps these capabilities:

- market search, watchlists, charts, and technical analysis
- AI analysis and analysis history
- custom indicators, parameterized indicators, backtests, and backtest history
- strategy creation, execution, and trading assistant tools
- portfolio tracking, alerts, and monitoring
- local settings, profile management, and password changes

Current stack:

- `Tauri 2`
- `Vue 2 + Ant Design Vue`
- `Python` specialist engines
- `SQLite`

## Repository Layout

```text
ZhiYiQuant/
├─ src-tauri/          # Tauri 2 desktop host
├─ zhiyiquant_vue/     # desktop frontend
├─ backend_api_python/ # local Python engines
└─ docs/               # V1 docs and V2 planning
```

## Local Development

```bash
cd zhiyiquant_vue
npm install
npm run serve
```

```bash
cd src-tauri
cargo tauri dev
```

## Build the Windows Installer

```bash
cd zhiyiquant_vue
npm run build

cd ../backend_api_python
python scripts/build_sidecar.py

cd ../src-tauri
cargo tauri build --bundles msi
```

## Scope

This V1 repository only contains the personal desktop product.

Future ecosystem planning lives in [docs/V2_DESKTOP_ECOSYSTEM_PLAN.md](docs/V2_DESKTOP_ECOSYSTEM_PLAN.md).
