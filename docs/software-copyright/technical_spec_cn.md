# ZhiYiQuant Desktop 技术架构说明

## 1. 总体架构

软件采用“三层协同”结构：

1. 桌面宿主层：基于 Tauri 2.x，负责窗口管理、应用打包、桌面生命周期和 sidecar 管理。
2. 前端交互层：基于 Vue 2 和 Ant Design Vue，负责页面展示、用户交互和业务流程编排。
3. 本地服务层：基于 Python Flask，负责市场数据处理、策略执行、AI 分析、数据库访问和业务接口。

## 2. 核心模块

### 桌面宿主层

- 配置文件：`../../src-tauri/tauri.conf.json`
- 启动逻辑：`../../src-tauri/src/lib.rs`
- 功能：拉起 Python sidecar、分配本地端口、监听退出事件、生成桌面安装包

### 前端交互层

- 入口文件：`../../quantdinger_vue/src/main.js`
- 请求封装：`../../quantdinger_vue/src/utils/request.js`
- 页面模块：指标分析、AI 分析、交易助手、持仓监控、用户管理等

### 本地服务层

- 服务入口：`../../backend_api_python/run.py`
- sidecar 入口：`../../backend_api_python/sidecar_main.py`
- 路由注册：`../../backend_api_python/app/routes/__init__.py`
- 核心服务：策略执行、市场数据、AI 分析、用户体系、持仓管理

## 3. 数据存储

当前桌面模式默认采用 SQLite 作为本地数据存储方案，数据库访问由统一封装层负责。默认数据库位置根据操作系统自动落在用户数据目录，以便桌面应用安装后可独立运行。

相关文件：

- `../../backend_api_python/app/config/database.py`
- `../../backend_api_python/app/utils/db.py`
- `../../backend_api_python/app/utils/db_sqlite.py`

## 4. 构建链路

- 前端构建：`npm run build`
- Python sidecar 构建：`python backend_api_python/scripts/build_sidecar.py`
- Tauri 安装包构建：`cargo tauri build --bundles msi`

## 5. 技术特点

- 支持桌面端与本地后端协同部署
- 支持桌面动态注入本地后端端口
- 支持多市场量化数据与策略执行能力
- 支持 AI 分析与本地数据闭环
