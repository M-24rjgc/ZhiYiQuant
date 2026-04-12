# 智弈量化

智弈量化是一个以 `Tauri 2` 为桌面主框架的本地优先量化工作台。

V1 版本只面向单人本地使用，核心工作流包括：

- 行情搜索、自选、图表与技术分析
- AI 分析与分析历史
- 自定义指标、参数化指标、回测与回测历史
- 策略创建、策略运行与交易助手
- 组合持仓、价格同步、预警与监控
- 本地设置、账户资料与密码管理

当前技术栈：

- `Tauri 2`
- `Vue 2 + Ant Design Vue`
- `Python` 专业引擎
- `SQLite`

## 目录结构

```text
ZhiYiQuant/
├─ src-tauri/          # Tauri 2 桌面宿主
├─ zhiyiquant_vue/     # 桌面前端
├─ backend_api_python/ # 本地 Python 引擎
└─ docs/               # V1 文档与 V2 规划
```

## 本地开发

```bash
cd zhiyiquant_vue
npm install
npm run serve
```

```bash
cd src-tauri
cargo tauri dev
```

## 打包 Windows 安装包

```bash
cd zhiyiquant_vue
npm run build

cd ../backend_api_python
python scripts/build_sidecar.py

cd ../src-tauri
cargo tauri build --bundles msi
```

## 当前边界

V1 仓库只承载个人桌面产品，聚焦本地研究、分析、策略执行与资产管理。

未来生态能力请见 [docs/V2_DESKTOP_ECOSYSTEM_PLAN.md](docs/V2_DESKTOP_ECOSYSTEM_PLAN.md)。
