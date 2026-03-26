# 盈透证券 (IBKR) 实盘交易指南

ZhiYiQuant 支持通过盈透证券 TWS 或 IB Gateway 进行美股和港股的实盘交易。

## 概述

此功能可通过您的盈透证券账户实现美股和港股的自动化交易执行。配置完成后，您的交易策略可以通过 IBKR API 自动下单。

## 前置条件

- 盈透证券账户
- 已安装 TWS (Trader Workstation) 或 IB Gateway
- 已订阅市场数据（用于实时报价）

## 安装

`ib_insync` 库已包含在 `requirements.txt` 中。如需手动安装：

```bash
pip install ib_insync
```

## 端口参考

| 客户端 | 实盘端口 | 模拟盘端口 |
|--------|----------|------------|
| TWS    | 7497     | 7496       |
| IB Gateway | 4001 | 4002       |

## TWS / IB Gateway 配置

1. 打开 TWS 或 IB Gateway
2. 进入 **配置** → **API** → **设置**
3. 启用以下选项：
   - ✅ 启用 ActiveX 和 Socket 客户端
   - ✅ 仅允许来自本地主机的连接
4. 设置 Socket 端口（参考上表）
5. 点击 应用 / 确定

## 策略配置

创建美股或港股策略时，在"实盘交易"部分配置 IBKR 连接：

| 字段 | 说明 | 示例 |
|------|------|------|
| **券商** | 选择"盈透证券" | - |
| **主机地址** | TWS/Gateway 主机地址 | `127.0.0.1` |
| **端口** | TWS/Gateway API 端口 | `7497`（TWS 实盘） |
| **客户端 ID** | 唯一客户端标识 | `1` |
| **账户号** | 账户 ID（可选） | 留空自动选择 |

## 代码格式

| 市场 | 格式 | 示例 |
|------|------|------|
| 美股 | 股票代码 | `AAPL`, `TSLA`, `GOOGL`, `MSFT` |
| 港股 | `XXXX.HK` 或数字 | `0700.HK`, `00700`, `700` |

## 交易流程

```
策略信号 → 待执行订单队列 → IBKR 执行 → 持仓更新
```

1. 您的策略生成买入/卖出信号
2. 信号作为待执行订单入队
3. 后台工作线程连接 IBKR 并执行订单
4. 更新持仓和交易记录

## 支持的信号类型

| 信号 | 动作 | 说明 |
|------|------|------|
| `open_long` | 买入 | 开多仓 |
| `add_long` | 买入 | 加多仓 |
| `close_long` | 卖出 | 平多仓 |
| `reduce_long` | 卖出 | 减多仓 |

> **注意**：当前版本暂不支持做空交易。

## API 接口

### 连接管理

```
GET  /api/ibkr/status          # 获取连接状态
POST /api/ibkr/connect         # 连接到 TWS/Gateway
POST /api/ibkr/disconnect      # 断开连接
```

### 账户查询

```
GET  /api/ibkr/account         # 账户信息
GET  /api/ibkr/positions       # 当前持仓
GET  /api/ibkr/orders          # 未成交订单
```

### 交易

```
POST   /api/ibkr/order         # 下单
DELETE /api/ibkr/order/<id>    # 撤单
```

### 行情数据

```
GET  /api/ibkr/quote?symbol=AAPL&marketType=USStock
```

## 使用示例

### 测试连接（通过 curl）

```bash
curl -X POST http://localhost:5000/api/ibkr/connect \
  -H "Content-Type: application/json" \
  -d '{"host": "127.0.0.1", "port": 7497, "clientId": 1}'
```

### 下单

```bash
# 市价单：买入 10 股苹果
curl -X POST http://localhost:5000/api/ibkr/order \
  -H "Content-Type: application/json" \
  -d '{"symbol": "AAPL", "side": "buy", "quantity": 10, "marketType": "USStock"}'

# 限价单：卖出 100 股腾讯
curl -X POST http://localhost:5000/api/ibkr/order \
  -H "Content-Type: application/json" \
  -d '{"symbol": "0700.HK", "side": "sell", "quantity": 100, "marketType": "HShare", "orderType": "limit", "price": 300}'
```

## 重要说明

1. **TWS/Gateway 必须运行**：交易前确保 TWS 或 IB Gateway 已启动并登录
2. **市场数据订阅**：实时报价可能需要向 IBKR 订阅市场数据
3. **客户端 ID**：如果多个程序连接同一个 TWS/Gateway，使用不同的 clientId
4. **账户选择**：如有多个子账户，请指定 `account` 参数
5. **交易时间**：订单仅在市场交易时间执行

## 常见问题排查

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| 连接失败 | TWS/Gateway 未运行 | 启动并登录 TWS/Gateway |
| 连接失败 | 端口错误 | 检查 TWS/Gateway 中的 API 端口设置 |
| 连接失败 | API 未启用 | 在 TWS/Gateway 设置中启用 Socket API |
| 客户端 ID 冲突 | 相同 clientId 已连接 | 使用不同的 clientId |
| 无效合约 | 代码格式错误 | 检查股票代码格式 |
| 订单被拒绝 | 资金/保证金不足 | 检查账户余额 |

## Docker 部署

在 Docker 中运行 ZhiYiQuant 时，TWS/IB Gateway 必须能从容器中访问：

1. 在宿主机上运行 TWS/Gateway
2. 使用 `host.docker.internal` 作为主机地址（Docker Desktop）
3. 或配置 host 网络模式

## 安全建议

- 在 TWS/Gateway 中仅启用"仅允许来自本地主机的连接"
- 使用模拟盘账户进行测试
- 在策略中设置适当的仓位限制
- 定期监控您的账户

## 参见

- [Python 策略开发指南](STRATEGY_DEV_GUIDE_CN.md)
- [盈透证券 API 文档](https://interactivebrokers.github.io/tws-api/)
