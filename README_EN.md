<div align="center">
  <a href="README.md">简体中文</a> |
  <a href="README_EN.md">English</a>
</div>

<div align="center">
  <img src="https://ai.zhiyiquant.com/img/logo.e0f510a8.png" alt="ZhiYiQuant Logo" width="144" height="144">
  <h1>ZhiYiQuant Desktop</h1>
  <p><strong>v2.2.0</strong></p>
  <p>Local-first AI quantitative trading desktop software built with Tauri 2.x</p>
</div>

## Overview

ZhiYiQuant Desktop is a desktop-first quantitative trading application for market data analysis, indicator development, strategy backtesting, AI-assisted research, trading workflow management, and portfolio monitoring.

This repository is now centered on the desktop edition:

- Desktop shell: Tauri 2.x
- Frontend: Vue 2 + Ant Design Vue
- Local service: Python Flask sidecar
- Local database: SQLite

## Highlights

- Tauri 2.x desktop project integrated
- Python sidecar startup and local port handoff implemented
- SQLite enabled as the default local database for desktop mode
- Windows installer generated successfully
- Software copyright registration materials included

## Quick Start

### Frontend dev

```bash
cd quantdinger_vue
npm install
npm run serve
```

### Desktop dev

```bash
cd src-tauri
cargo tauri dev
```

### Build Windows installer

```bash
cd quantdinger_vue
npm run build

cd ../backend_api_python
python scripts/build_sidecar.py

cd ../src-tauri
cargo tauri build --bundles msi
```

## Output

Windows installer output:

```text
src-tauri/target/release/bundle/msi/ZhiYiQuant_2.2.0_x64_en-US.msi
```

## Software Copyright Materials

- [Materials Index](docs/software-copyright/README_CN.md)
- [Cover Template](docs/software-copyright/00_cover_template_cn.md)
- [Submission Packet Notes](docs/software-copyright/01_submission_packet_cn.md)
- [Source Excerpt](docs/software-copyright/source_excerpt_v2.2.0.txt)

## Docs

- [Chinese README](README.md)
- [Backend README](backend_api_python/README.md)
- [Frontend README](quantdinger_vue/README.md)
- [Strategy Development Guide](docs/STRATEGY_DEV_GUIDE.md)

## License

Code is licensed under [Apache 2.0](LICENSE).

For brand usage and redistribution involving product identity, please also review [TRADEMARKS.md](TRADEMARKS.md).
