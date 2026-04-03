# SimplePolyBot 完整使用手册（百科全书版）

> 从零部署到日常运维的一站式指南 | 适用版本: v1.0 | 最后更新: 2026年

---

## 📖 目录

- [第 0 章：快速上手（5分钟跑起来）](#第-0-章快速上手5分钟跑起来)
- [第 1 章：服务器环境准备与系统安装](#第-1-章服务器环境准备与系统安装) `<!-- 待编写 -->`
- [第 2 章：项目部署与配置](#第-2-章项目部署与配置) `<!-- 待编写 -->`
- [第 3 章：交易策略详解 ⭐核心](#第-3-章交易策略详解-核心) `<!-- 待编写 -->`
- [第 4 章：各模块功能手册](#第-4-章各模块功能手册) `<!-- 待编写 -->`
- [第 5 章：配置参数完全手册](#第-5-章配置参数完全手册) `<!-- 待编写 -->`
- [第 6 章：日常运维与监控](#第-6-章日常运维与监控) `<!-- 待编写 -->`
- [第 7 章：常见问题 FAQ](#第-7-章常见问题-faq) `<!-- 待编写 -->`
- [第 8 章：异常处理与故障排除](#第-8-章异常处理与故障排除) `<!-- 待编写 -->`
- [第 9 章：安全最佳实践](#第-9-章安全最佳实践) `<!-- 待编写 -->`
- [附录 A：命令速查表](#附录-a命令速查表) `<!-- 待编写 -->`
- [附录 B：配置文件完整示例](#附录-b配置文件完整示例) `<!-- 待编写 -->`
- [附录 C：术语表](#附录-c术语表) `<!-- 待编写 -->`

---

## 第 0 章：快速上手（5分钟跑起来）

> 🎯 **本章目标**：按照以下步骤，你可以在 5 分钟内完成系统首次部署并看到第一个交易信号。不需要理解任何代码，只需要会复制粘贴命令即可。

---

### 0.1 前置条件清单 ✅

在开始之前，请逐项确认以下条件已满足。**任何一项缺失都可能导致后续步骤失败**。

| # | 前置条件 | 状态 | 说明 |
|---|---------|------|------|
| 1 | ☐ Vultr 服务器已开通 | | IP: `216.238.91.89`，系统: Ubuntu 24.04 LTS，配置: 2vCPU / 2GB RAM / 60GB NVMe |
| 2 | ☐ Polymarket 账号已注册并完成 KYC | | 访问 [polymarket.com](https://polymarket.com) 注册，KYC 审核通常 1-3 个工作日 |
| 3 | ☐ MetaMask 钱包已创建并存入 USDC | | 建议 ≥ **$100** 起步资金（太少无法有效分散仓位） |
| 4 | ☐ Polymarket API Key 已获取（3 个） | | `api_key` / `api_secret` / `api_passphrase`，获取方式见下方说明 |
| 5 | ☐ 钱包私钥已备份 | | 格式: `0x` 开头 + 64 位十六进制字符，共 66 个字符 |

#### 🔑 如何获取 Polymarket API Key？

> 💡 **什么是 API Key？** 就像是你给机器人的一把"数字钥匙"，有了它，机器人才能代替你在 Polymarket 上买卖。

1. 打开浏览器访问 [Polymarket Developer Portal](https://docs.polymarket.com)
2. 登录你的 Polymarket 账号
3. 进入 **API Keys** 管理页面
4. 点击 **Create New API Key**
5. 系统会生成三个凭证，**立即复制保存**（只显示一次！）：
   - `api_key` — 类似于用户名
   - `api_secret` — 类似于密码
   - `api_passphrase` — 用于签名验证的口令

⚠️ **安全警告**：API Key 相当于你的交易授权，绝不要泄露给他人或提交到公开仓库！

#### 💰 如何导出 MetaMask 私钥？

1. 打开 MetaMask 浏览器扩展 / 手机 App
2. 点击右上角账户头像 → **账户详情**
3. 点击 **显示私钥** → 输入 MetaMask 密码确认
4. 复制显示的 `0x...` 开头的字符串

🔴 **极度重要**：私钥 = 你钱包里所有资产的控制权！请用密码管理器（如 1Password）妥善保管，不要存储在聊天记录或普通文本文件中。

---

### 0.2 一键部署命令序列 🚀

> 📋 **总览**：以下命令按顺序执行，共 8 大步、约 15 条命令。每条命令都可以直接复制粘贴到终端执行。
>
> ⏱️ **预计耗时**：全新服务器约 5-10 分钟（取决于网络速度）

---

#### 第一步：SSH 连接服务器

在你的本地电脑上打开终端（Windows 用户推荐使用 PowerShell 或 Windows Terminal），执行：

```bash
ssh root@216.238.91.89
```

**预期输出**：
```
The authenticity of host '216.238.91.89 (216.238.91.89)' can't be established.
ED25519 key fingerprint is SHA256:xxxxxxxxxxx...
Are you sure you want to continue connecting (yes/no/[fingerprint])?
```

输入 `yes` 回车，然后输入 Vultr 发给你的 root 密码。

✅ **成功标志**：看到类似 `root@ubuntu-24:~#` 的提示符，说明已成功登录。

❌ **如果出错**：
- `Connection refused` → 检查 IP 是否正确、服务器是否已开机
- `Permission denied` → 检查密码是否正确（注意：输入密码时屏幕不会显示任何字符，这是正常的）

---

#### 第二步：系统更新与基础工具安装

```bash
apt update && apt upgrade -y
```

> 💡 这条命令会更新系统的软件包列表并升级所有已安装的软件包。`-y` 表示自动确认所有提示。

```bash
apt install -y git python3 python3-pip python3-venv redis-server curl wget htop ufw fail2ban
```

> 📦 安装说明：
> - `git` — 从 GitHub 下载项目代码
> - `python3` / `python3-pip` / `python3-venv` — Python 运行环境和虚拟环境工具
> - `redis-server` — 消息中间件（各模块之间的"信使"）
> - `curl` / `wget` — 下载工具
> - `htop` — 系统资源监控
> - `ufw` — 防火墙
> - `fail2ban` — 入侵防护

**预期输出**：大量下载和安装日志，最后显示类似：
```
Setting up fail2ban (1.1.0-1) ...
Processing triggers for man-db (2.12.0-4build1) ...
```

✅ **成功标志**：没有红色错误信息，最后回到 `root@...:~#` 提示符。

❌ **如果出错**：
- `Unable to locate package xxx` → 先执行 `apt update` 再重试
- `E: Could not get lock` → 等待其他 apt 操作完成，或执行 `rm /var/lib/dpkg/lock-frontend` 后重试

---

#### 第三步：Redis 配置

Redis 是 SimplePolyBot 的"消息中枢"，负责在四个模块之间传递数据。

```bash
bash scripts/setup_redis.sh
```

如果脚本不存在（首次克隆前），手动执行以下等效操作：

```bash
REDIS_PASSWORD=$(openssl rand -base64 32 | tr -d '\n')
echo "你的 Redis 密码是（请记下来）: $REDIS_PASSWORD"

sed -i "s/# requirepass foobared/requirepass $REDIS_PASSWORD/" /etc/redis/redis.conf
sed -i "s/bind 127.0.0.1 ::1/bind 127.0.0.1/" /etc/redis/redis.conf
sed -i "s/protected-mode yes/protected-mode no/" /etc/redis/redis.conf
sed -i "s/# maxmemory <bytes>/maxmemory 512mb/" /etc/redis/redis.conf
sed -i "s/# maxmemory-policy noeviction/maxmemory-policy allkeys-lru/" /etc/redis/redis.conf

systemctl restart redis-server
systemctl enable redis-server
```

> 💡 **参数解释**：
> - `requirepass` — 设置连接密码（防止未授权访问）
> - `bind 127.0.0.1` — 只允许本机连接（更安全）
> - `maxmemory 512mb` — 最大内存占用 512MB（2GB 内存服务器的合理值）
> - `allkeys-lru` — 内存满时淘汰最少使用的缓存

**验证 Redis 是否正常工作**：

```bash
redis-cli -a $REDIS_PASSWORD ping
```

✅ **成功标志**：返回 `PONG`

❌ **如果出错**：
- `NOAUTH Authentication required` → 密码设置有问题，检查 redis.conf
- `Could not connect` → Redis 服务未启动，执行 `systemctl start redis-server`
- `Command not found: redis-cli` → Redis 未安装成功，重新执行第二步

---

#### 第四步：克隆项目代码

```bash
cd /opt
git clone https://github.com/EatTake/SimplePolyBot.git
cd SimplePolyBot
```

> 📁 `/opt` 是 Linux 系统中存放第三方软件的标准目录。项目将被克隆到 `/opt/SimplePolyBot/`。

**预期输出**：
```
Cloning into 'SimplePolyBot'...
remote: Enumerating objects: xxx, done.
remote: Counting objects: 100% (xxx/xxx), done.
...
Resolving deltas: 100% (100/100), done.
```

✅ **成功标志**：进入目录后执行 `ls` 能看到 `modules/`、`config/`、`scripts/`、`shared/` 等文件夹。

❌ **如果出错**：
- `Repository not found` → 检查仓库 URL 是否正确，或仓库是否为 Private（需要 SSH Key 或 Token）
- `Permission denied` → `/opt` 目录需要 root 权限，确保以 root 用户操作

---

#### 第五步：创建 Python 虚拟环境并安装依赖

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

> 💡 **什么是虚拟环境？** 相当于给项目创建一个"独立房间"，安装的 Python 包不会和系统其他程序冲突，也方便管理版本。

**预期输出**：大量的 `Collecting`、`Downloading`、`Installing` 日志，最终显示：
```
Successfully installed aiohttp-3.x.x numpy-1.x.x pandas-2.x.x py-clob-client-0.x.x PyYAML-6.x redis-5.x.x structlog-23.x.x web3-6.x.x websockets-12.x.x ... (共约 15 个包)
```

✅ **成功标志**：最后一行是 `Successfully installed ...` 且无红色 ERROR。

❌ **如果出错**：
- `No module named venv` → 执行 `apt install -y python3-venv` 后重试
- `pip: command not found` → 执行 `apt install -y python3-pip` 后重试
- 某个包编译失败（如 `web3`）→ 可能缺少系统依赖，执行 `apt install -y build-essential libffi-dev` 后重试
- 网络超时 → 使用国内镜像源：`pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`

---

#### 第六步：环境变量配置

这是最关键的一步——填入你的个人凭证信息。

```bash
cp .env.example .env
nano .env
```

> 💡 `nano` 是一个简单的文本编辑器。操作方式：直接打字编辑，`Ctrl+O` 保存，`Ctrl+X` 退出。

将 `.env` 文件中的占位符替换为你的真实信息：

```env
# ===== 必填项（必须修改）=====

# Polymarket API 凭证（从 Developer Portal 获取）
POLYMARKET_API_KEY=你的真实api_key
POLYMARKET_API_SECRET=你的真实api_secret
POLYMARKET_API_PASSPHRASE=你的真实api_passphrase

# 钱包私钥（MetaMask 导出，0x 开头 66 字符）
PRIVATE_KEY=你的真实私钥

# 钱包地址（与私钥对应，0x 开头 42 字符）
WALLET_ADDRESS=你的钱包地址

# ===== Redis 配置（使用第三步生成的密码）=====
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=第三步生成的redis密码
REDIS_DB=0

# ===== 可选项（暂时可以不改）=====
POLYGON_RPC_URL=https://polygon-rpc.com
```

⚠️ **重要提醒**：
- 所有 `=` 号前后**不要有空格**
- 不要在值中包含引号或特殊字符（除非原值就有）
- 如果某项暂时没有，保持空值即可（如 `SMTP_USERNAME=`）

**验证配置文件格式是否正确**：

```bash
source venv/bin/activate && python -c "
from dotenv import load_dotenv
import os
load_dotenv()
required = ['POLYMARKET_API_KEY','POLYMARKET_API_SECRET','POLYMARKET_API_PASSPHRASE','PRIVATE_KEY','WALLET_ADDRESS']
for k in required:
    v = os.getenv(k,'')
    status = 'OK' if v else 'MISSING'
    mask = v[:6]+'...' if len(v)>6 else v
    print(f'  [{status}] {k} = {mask}')
"
```

✅ **成功标志**：所有必填项都显示 `[OK]`

❌ **如果出现 `[MISSING]` → 对应的值没有正确填写，重新编辑 `.env` 文件

---

#### 第七步：运行交互式配置向导

```bash
source venv/bin/activate
python -m shared.config_wizard --mode quick
```

> 💡 配置向导会引导你完成策略参数的基本设置。`--mode quick` 表示快速模式，只会询问最核心的参数，其他全部使用合理的默认值。

**预期交互过程**：

```
============================================================
  🤖 SimplePolyBot 配置向导
============================================================
  模式: quick
  本向导将引导您完成交易策略的配置
============================================================

📋 第一步：基本设置

  📌 Base Cushion（基础安全垫）
     说明: OLS 回归的安全边际系数
     范围: 0.01 - 0.2
     [默认: 0.05]:
     ← 直接回车使用默认值，或输入自定义值

  📌 Alpha（趋势跟随强度）
     说明: 价格动量权重系数
     范围: 0.3 - 0.9
     [默认: 0.7]:

  ... （继续其他参数，新手建议全部回车使用默认值）

============================================================
  📋 配置摘要
============================================================
  • Base Cushion: 0.05
  • Alpha: 0.7
  • POLYMARKET_API_KEY: abcdef******
  • PRIVATE_KEY: 0xabc1******
============================================================

  确认保存此配置? (y/n): y
  ✅ 配置已确认
```

💡 **新手建议**：第一次部署时，所有参数都直接按回车使用默认值。默认值已经过调优，适合大多数场景。等熟悉系统后再根据[第 3 章](#第-3-章交易策略详解-核心)调整策略参数。

✅ **成功标志**：最后显示 `✅ 配置已确认`，且 `config/settings.yaml` 文件已被更新。

❌ **如果出错**：
- `ModuleNotFoundError` → 确认已在虚拟环境中（提示符前有 `(venv)`）
- 输入验证失败 → 根据提示的合法范围重新输入

---

#### 第八步：启动系统 🎉

终于到了最后一步！执行以下命令启动全部四个模块：

```bash
bash scripts/start_all.sh
```

这条命令会依次启动 SimplePolyBot 的四大核心模块：

| 模块 | 功能 | 类比 |
|------|------|------|
| `market_data_collector` | 通过 WebSocket 接收实时行情 | 👀 "眼睛" — 盯盘看价格 |
| `strategy_engine` | 用 OLS 回归计算买卖信号 | 🧠 "大脑" — 分析决策 |
| `order_executor` | 向 Polymarket 下单执行交易 | ✋ "手" — 执行买卖 |
| `settlement_worker` | 结算市场并赎回获胜代币 | 💰 "会计" — 清算收款 |

**预期输出**：

```
正在启动模块: market_data_collector
✅ 模块 'market_data_collector' 启动成功 (PID: 12345)
日志文件: /opt/SimplePolyBot/logs/market_data_collector.log

正在启动模块: strategy_engine
✅ 模块 'strategy_engine' 启动成功 (PID: 12346)
日志文件: /opt/SimplePolyBot/logs/strategy_engine.log

正在启动模块: order_executor
✅ 模块 'order_executor' 启动成功 (PID: 12347)
日志文件: /opt/SimplePolyBot/logs/order_executor.log

正在启动模块: settlement_worker
✅ 模块 'settlement_worker' 启动成功 (PID: 12348)
日志文件: /opt/SimplePolyBot/logs/settlement_worker.log

✅ 所有模块启动成功
```

✅ **终极成功标志**：看到上面四行 `✅ 模块 'xxx' 启动成功` + 最后一行 `✅ 所有模块启动成功`。

🎉 **恭喜！你的 SimplePolyBot 已经跑起来了！**

❌ **如果某个模块启动失败**：

1. 查看该模块的日志：`tail -50 logs/<模块名>.log`
2. 常见原因：
   - `Connection refused` (Redis) → Redis 未启动或密码不匹配
   - `Authentication failed` (API) → `.env` 中 API Key 有误
   - `Invalid private key` → 私钥格式错误（必须是 66 字符，0x 开头）
   - `ModuleNotFoundError` → 未激活虚拟环境，先执行 `source venv/bin/activate`
3. 修复后可单独重启该模块：`bash scripts/start_module.sh <模块名>`

---

### 0.3 预期成功标志 — 完整对照表

启动后，你可以通过以下方式验证系统是否完全正常运行：

#### 方式一：查看进程状态

```bash
bash scripts/monitor.sh --status
```

**预期输出**：
```
===================================
  SimplePolyBot 系统状态
===================================

✅ market_data_collector: 运行中 (PID: 12345, CPU: 0.3%, MEM: 1.2%)
✅ strategy_engine: 运行中 (PID: 12346, CPU: 0.5%, MEM: 2.1%)
✅ order_executor: 运行中 (PID: 12347, CPU: 0.1%, MEM: 1.8%)
✅ settlement_worker: 运行中 (PID: 12348, CPU: 0.1%, MEM: 1.5%)

```

#### 方式二：查看实时日志流

```bash
tail -f logs/market_data_collector.log
```

**预期输出**（持续滚动的新日志）：
```
2026-04-02 10:00:01 [INFO] WebSocket 连接建立: wss://ws-subscriptions-clob.polymarket.com/ws/market
2026-04-02 10:00:01 [INFO] 订阅资产列表: [...]
2026-04-02 10:00:05 [INFO] 收到 order_book 更新: token=0x..., bid=0.52, ask=0.55
2026-04-02 10:00:10 [INFO] PING/PONG 心跳正常
2026-04-02 10:00:15 [INFO] 收到 price_change 事件: token=0x..., price=0.53
...
```

按 `Ctrl+C` 退出日志查看。

#### 方式三：检查 Redis 消息队列

```bash
redis-cli -a $REDIS_PASSWORD LLEN market_updates
redis-cli -a $REDIS_PASSWORD LLEN signal_orders
```

**预期输出**：返回大于等于 0 的整数（表示队列中的消息数量）。如果持续增长，说明数据在正常流动。

---

### 0.4 首次交易验证步骤 🔍

系统启动后，按以下 5 步确认它真正在工作：

#### 步骤 1️⃣：确认行情数据在流入

```bash
tail -20 logs/market_data_collector.log | grep -E "(收到|price|order_book)"
```

✅ **通过标准**：最近 20 行日志中至少有 3 条包含 `收到` 或 `price` 或 `order_book` 的记录，且时间戳是当前时间附近。

#### 步骤 2️⃣：确认策略引擎在计算

```bash
tail -30 logs/strategy_engine.log | grep -E "(signal|OLS|confidence)"
```

✅ **通过标准**：能看到类似 `signal generated` 或 `OLS regression` 或 `confidence: 0.xx` 的日志输出。

#### 步骤 3️⃣：确认订单执行器就绪

```bash
tail -20 logs/order_executor.log | grep -E "(connected|ready|subscribed)"
```

✅ **通过标准**：能看到 `CLOB client connected` 或 `Redis subscriber ready` 或类似就绪消息。

#### 步骤 4️⃣：检查是否有实际交易信号产生

```bash
grep -i "signal\|order\|BUY\|SELL" logs/strategy_engine.log | tail -10
```

✅ **通过标准**：如果策略检测到机会，你会看到类似以下的日志：
```
2026-04-02 10:05:30 [INFO] 📊 交易信号产生: side=BUY, price=0.48, size=100, confidence=0.72
```

> 💡 **注意**：如果没有信号也是正常的！策略只在满足严格条件时才会触发交易。你可以等待几分钟或几小时后再检查。

#### 步骤 5️⃣：去 Polymarket 网站验证

1. 打开 [polymarket.com](https://polymarket.com) 并登录
2. 点击右上角头像 → **Portfolio**（投资组合）
3. 查看 **Activity**（活动记录）标签页

✅ **通过标准**：如果你看到新的交易记录出现在 Activity 中，说明机器人已经成功为你完成了第一笔交易！🎊

---

### 0.5 常见快速问题 FAQ ⚡

以下是新用户最常遇到的 5 个问题及秒级解决方案：

---

#### ❓ Q1：启动后某个模块立刻崩溃了

**症状**：`start_all.sh` 执行时显示 `❌ 模块 'xxx' 启动失败`

**解决方案**：

```bash
# 1. 查看崩溃日志（关键！）
cat logs/<崩溃的模块名>.log | tail -50

# 2. 最常见的 3 种原因及修复：

# 原因 A：Redis 连接失败
# → 检查 Redis 是否运行：systemctl status redis-server
# → 检查 .env 中 REDIS_PASSWORD 是否与 redis.conf 一致

# 原因 B：API 凭证错误
# → 检查 .env 中三个 POLYMARKET_* 变量是否完整复制（无多余空格）

# 原因 C：Python 依赖缺失
# → 重新安装：source venv/bin/activate && pip install -r requirements.txt
```

---

#### ❓ Q2：SSH 连接被断开了，机器人还在跑吗？

**答案**：**是的，还在跑！** 🎉

我们的启动脚本使用了 `nohup` 命令，这意味着即使 SSH 断开，进程也不会被杀死。

**验证方法**（重新 SSH 连接后执行）：

```bash
ps aux | grep -E "(market_data|strategy|order_executor|settlement)" | grep -v grep
```

你应该看到 4 个 Python 进程在运行。

---

#### ❓ Q3：怎么停止机器人？

```bash
bash scripts/stop_all.sh
```

**预期输出**：
```
正在停止模块: market_data_collector (PID: 12345)
正在停止模块: strategy_engine (PID: 12346)
正在停止模块: order_executor (PID: 12347)
正在停止模块: settlement_worker (PID: 12348)

✅ 所有模块已停止
```

> 💡 也可以单独停止单个模块：`bash scripts/stop_module.sh <模块名>`（需自行创建或使用 kill 命令）

---

#### ❓ Q4：怎么看机器人今天赚了多少钱？

**方法一：查看日志中的交易记录**

```bash
grep -i "filled\|matched\|成交" logs/order_executor.log | tail -20
```

**方法二：直接去 Polymarket 查看**

1. 登录 polymarket.com → Portfolio → Activity
2. 查看 P&L（盈亏）统计

**方法三：启用监控面板（高级）**

```bash
# 在 config/settings.yaml 中确认 monitoring.enabled: true
# 然后访问 http://216.238.91.89:9090/metrics
```

---

#### ❓ Q5：服务器重启后机器人会自动启动吗？

**默认不会**，但你可以轻松设置开机自启：

```bash
# 创建 systemd 服务文件
cat > /etc/systemd/system/simplepolybot.service << 'EOF'
[Unit]
Description=SimplePolyBot Trading System
After=network.target redis.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/SimplePolyBot
ExecStart=/bin/bash /opt/SimplePolyBot/scripts/start_all.sh
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 启用开机自启
systemctl daemon-reload
systemctl enable simplepolybot
```

之后就可以用 `systemctl start simplepolybot` 和 `systemctl stop simplepolybot` 来管理系统了。

> 📖 更详细的开机自启配置请参考[第 6 章：日常运维与监控](#第-6-章日常运维与监控)

---

### 🎯 本章小结

| 检查点 | 状态 |
|--------|------|
| 服务器 SSH 可登录 | ☐ |
| 系统依赖全部安装 | ☐ |
| Redis 正常运行并可认证 | ☐ |
| 项目代码已克隆到 /opt/SimplePolyBot | ☐ |
| Python 虚拟环境已创建且依赖已安装 | ☐ |
| `.env` 文件已填写所有必填凭证 | ☐ |
| 配置向导已完成（quick 模式） | ☐ |
| 四个模块全部启动成功 | ☐ |
| 日志中有实时数据流入 | ☐ |

全部打勾？恭喜你完成了从零到一的部署！接下来可以深入阅读后续章节来了解每个部分的细节。

> 📘 **下一步推荐**：
> - 想了解策略原理 → 阅读 [第 3 章：交易策略详解 ⭐核心](#第-3-章交易策略详解-核心)
> - 想了解如何调整参数 → 阅读 [第 5 章：配置参数完全手册](#第-5-章配置参数完全手册)
> - 想了解日常维护 → 阅读 [第 6 章：日常运维与监控](#第-6-章日常运维与监控)

---

<!-- CHAPTER_0_CONTENT_END -->

---

## 第 1 章：服务器环境准备与系统安装

<!-- CHAPTER_1_CONTENT_START -->

> 🎯 **本章目标**：从零开始，手把手教你完成服务器的基础环境搭建。包括 SSH 连接、系统更新、Python 环境、Redis 数据库、安全加固和时间同步。每一步都有详细的图文级说明和故障排查指南。
>
> ⏱️ **预计耗时**：30-45 分钟（首次操作建议慢慢来，不要急）

---

## 1.1 服务器概览与 SSH 连接

在动手之前，先确认一下我们要操作的服务器信息：

### 📋 服务器配置确认表

| 项目 | 值 | 说明 |
|------|-----|------|
| **服务商** | Vultr | 全球知名 VPS 提供商 |
| **IP 地址** | `216.238.91.89` | 服务器的"门牌号"，全世界唯一 |
| **操作系统** | Ubuntu 24.04 LTS | 长期支持版，稳定可靠 |
| **CPU** | 2 vCPU | 2 个虚拟处理器核心 |
| **内存** | 2 GB RAM | 运行内存，够用但不算富裕 |
| **硬盘** | 60 GB NVMe SSD | 固态硬盘，读写速度快 |

> 💡 **什么是 VPS？** VPS（Virtual Private Server，虚拟专用服务器）就是你在云端租的一台"迷你电脑"。它 24 小时开机、有独立 IP 地址、可以装任何软件——非常适合跑交易机器人。

---

### 🔌 Windows 用户：使用 PuTTY 连接（推荐新手）

如果你用的是 Windows 电脑，推荐使用 **PuTTY** 这个免费工具来连接服务器。

#### 第一步：下载 PuTTY

1. 打开浏览器访问 [putty.org](https://www.putty.org)
2. 点击页面上的下载链接（通常是 `putty-64bit-x.x.x-installer.msi`）
3. 双击安装包，一路"下一步"完成安装
4. 安装完成后，在开始菜单找到 **PuTTY** 并打开

#### 第二步：输入连接信息

打开 PuTTY 后，你会看到一个这样的窗口：

```
┌─ PuTTY Configuration ───────────────────────┐
│                                                │
│ Category:                                      │
│   ☑ Session                                     │
│     Host Name (or IP address)                  │
│     ┌──────────────────────────────┐           │
│     │ 216.238.91.89               │ ← 在这里输入IP │
│     └──────────────────────────────┘           │
│     Port:    [22]                               │
│     Connection type:                            │
│       ( ) Raw  ( ) Telnet  (☑) SSH             │
│                                                │
│   [ Open ]  [ Cancel ]                          │
└────────────────────────────────────────────────┘
```

**操作步骤**：
1. 在 **Host Name** 输入框中填写：`216.238.91.89`
2. **Port** 保持默认 `22`（SSH 标准端口）
3. **Connection type** 选择 **SSH**
4. 点击右下角的 **Open** 按钮

#### 第三步：首次连接 — 安全提示

点击 Open 后，会出现一个黑色终端窗口，显示以下提示：

```
The authenticity of host '216.238.91.89 (216.238.91.89)' can't be established.
ED25519 key fingerprint is:
SHA256:uNiVztksCsDhcc0u17e8s5Z7vNk4nPEyF+GpZBmQ3XQ
This key is not known by any other names.
Are you sure you want to continue connecting (yes/no/[fingerprint])?
```

**这是什么意思？**

这是服务器在向你展示它的"身份证"（公钥指纹），问你："你确定要信任这台服务器吗？"

✅ **正确做法**：输入 `yes`（注意是完整单词，不是只按 `y`），然后按回车。

> 💡 这个提示只在**第一次连接**时出现。之后 PuTTY 会记住这台服务器的指纹，不会再问了。如果以后连接时突然又弹出这个警告，说明服务器的身份可能变了（被黑客入侵或更换了系统），需要警惕！

#### 第四步：登录

确认后，会看到登录提示：

```
root@216.238.91.89's password:
```

**输入你的 root 密码**（就是 Vultr 发给你的那个初始密码）。

⚠️ **重要注意**：输入密码时，屏幕上**不会显示任何字符**（连星号 `*` 都没有）！这是 Linux 的正常安全机制，不是键盘坏了。放心输入完整密码后直接按回车即可。

✅ **成功标志**：看到类似下面的提示符，说明你已经成功登入服务器！

```
Welcome to Ubuntu 24.04 LTS (GNU/Linux 6.8.0-x86_64 x86_64)

 * Documentation:  https://help.ubuntu.com
 * Management:     https://landscape.canonical.com
 * Support:        https://ubuntu.com/advantage

root@ubuntu-2404-s-2vcpu-2gb-nyc1-01:~#
```

最后一行的 `root@ubuntu...:~#` 就是你的命令提示符，`#` 表示你是超级管理员（root 用户），可以执行任何操作。

---

### 🔌 Mac / Linux 用户：使用 Terminal 连接

Mac 和 Linux 用户不需要额外安装软件，系统自带的 Terminal 就能直接连接。

#### 操作步骤

1. 打开 **Terminal**（终端）应用
   - Mac：在 Launchpad 中搜索 "Terminal" 或按 `Cmd + Space` 输入 "Terminal"
   - Linux：按 `Ctrl + Alt + T` 快捷键

2. 输入以下命令并回车：

```bash
ssh root@216.238.91.89
```

3. 同样会遇到安全指纹提示，输入 `yes` 回车
4. 输入 root 密码（同样不显示字符），回车

✅ **成功标志**：看到 `root@ubuntu...:~#` 提示符

---

### ❌ 连接失败排查指南

如果上面的步骤没能成功连接，请对照下表排查：

| 错误症状 | 可能原因 | 解决方法 |
|----------|---------|---------|
| `Connection refused` | 服务器未开机 / SSH 服务未启动 | 登录 Vultr 控制面板检查服务器状态，确认已启动 |
| `Connection timed out` | 网络不通 / 防火墙拦截 | 检查本地网络是否正常；确认 Vultr 防火墙规则允许端口 22 |
| `Permission denied, please try again` | 密码错误 | 检查是否有多余空格；去 Vultr 控制面板重置 root 密码 |
| `Network is unreachable` | 本地网络问题 | 检查 VPN/代理设置；尝试切换网络（如手机热点测试） |
| `Host key verification failed` | 服务器指纹变化 | 执行 `ssh-keygen -R 216.238.91.89` 清除旧记录后重连 |

💡 **专业提示：使用 SSH 密钥认证替代密码**

密码登录虽然方便，但有被暴力破解的风险。强烈建议后续配置 SSH 密钥认证（详见 1.5 节）。密钥认证的安全性远高于密码——即使黑客知道你的 IP，没有私钥也无法登录。

---

## 1.2 系统基础更新与工具安装

成功登录服务器后的第一件事，就是把系统更新到最新状态并安装必要的工具软件。

### 🔄 更新系统软件包

```bash
apt update && apt upgrade -y
```

**这条命令做了什么？**
- `apt update` — 从 Ubuntu 的软件源刷新可用软件列表（就像刷新应用商店）
- `apt upgrade -y` — 将所有已安装的软件升级到最新版本（`-y` 表示自动确认，不用手动输 y）

**预期输出**（节选）：
```
Get:1 http://archive.ubuntu.com/ubuntu noble InRelease [267 kB]
Get:2 http://archive.ubuntu.com/ubuntu noble-updates InRelease [119 kB]
...
Reading package lists... Done
Calculating upgrade... Done
The following packages will be upgraded:
  libssl3 openssl base-files base-passwd bash ...
Setting up libssl3 (3.0.13-1ubuntu4.1) ...
Processing triggers for man-db (2.12.0-4build1) ...
```

✅ **成功标志**：最后回到 `root@...:~#` 提示符，没有红色 ERROR 信息。

---

### 🛠️ 安装核心工具集

```bash
apt install -y git curl wget htop vim ufw fail2ban chrony
```

每个工具的用途一览：

| 工具名 | 用途 | 为什么我们需要它？ |
|--------|------|-------------------|
| `git` | 版本控制工具 | 从 GitHub 下载 SimplePolyBot 项目代码 |
| `curl` | 命令行 HTTP 客户端 | 测试 API 连接、下载文件 |
| `wget` | 文件下载工具 | 从网上下载安装包等资源 |
| `htop` | 交互式进程监控器 | 查看服务器 CPU/内存占用情况 |
| `vim` | 文本编辑器 | 编辑配置文件（比 nano 更强大） |
| `ufw` | 防火墙管理工具 | 控制哪些端口可以对外访问 |
| `fail2ban` | 入侵防护工具 | 自动封禁暴力破解 IP |
| `chrony` | 时间同步服务 | 保持服务器时间精确（对交易至关重要！） |

**预期输出**（最后几行）：
```
Setting up fail2ban (1.1.0-1) ...
Setting up chrony (4.5-2build1) ...
Processing triggers for man-db (2.12.0-4build1) ...
Processing triggers for mailcap (4.0.5+nmu1ubuntu1) ...
```

✅ **成功标志**：所有包都显示 `Setting up ...` 且无报错，回到提示符。

---

### ❌ 安装过程常见错误解决

| 错误信息 | 原因 | 解决方法 |
|----------|------|---------|
| `E: Could not get lock /var/lib/dpkg/lock-frontend` | 有其他 apt 进程正在运行 | 等待其完成，或执行 `rm /var/lib/dpkg/lock-frontend /var/lib/dpkg/lock /var/cache/apt/archives/lock` 后重试 |
| `E: Unable to locate package xxx` | 软件源列表过期 | 先单独执行 `apt update`，然后再运行 install 命令 |
| `Err:1 ... Connection timed out` | 网络不稳定导致下载超时 | 重试一次；如持续失败可换源：编辑 `/etc/apt/sources.list` 使用国内镜像 |
| `No space left on device` | 磁盘空间不足 | 执行 `df -h` 查看空间占用，清理不必要的文件（如 `/tmp`、旧日志） |

💡 **提示**：如果在升级过程中遇到内核更新，可能会提示重启服务器。可以先不重启，等本章全部操作完成后再统一重启：`reboot`

---

## 1.3 Python 环境搭建

SimplePolyBot 是基于 Python 开发的，所以需要在服务器上准备好 Python 运行环境。

### ✅ 检查 Python 版本

```bash
python3 --version
```

**预期输出**：
```
Python 3.12.3
```

> 💡 **版本要求**：SimplePolyBot 需要 **Python 3.10 或更高版本**。Ubuntu 24.04 LTS 自带 Python 3.12，完全满足要求，无需额外安装。
>
> 如果你看到的版本号低于 3.10（比如 3.8.x），说明操作系统版本较旧，需要先升级系统或手动安装新版 Python。

---

### 📦 安装 pip 和 venv

`pip` 是 Python 的包管理器（类似 npm 之于 Node.js），`venv` 用于创建虚拟环境。

```bash
apt install -y python3-pip python3-venv
```

**验证安装结果**：

```bash
pip3 --version
python3 -m venv --help | head -3
```

**预期输出**：
```
pip 24.0 from /usr/lib/python3/dist-packages/pip (python 3.8)

usage: venv [-h] [--system-site-packages] [--symlinks | --copies]
            [--clear] [--upgrade] [--without-pip]
            ...
```

✅ **成功标志**：两条命令都能正常显示版本信息或帮助文本，没有 `command not found` 错误。

---

### ❌ 常见问题

| 问题 | 解决方法 |
|------|---------|
| `python3: command not found` | 执行 `apt install -y python3 python3-full` |
| `pip3` 版本过旧（< 21.0） | 执行 `pip3 install --upgrade pip` 升级到最新版 |
| `No module named 'venv'` | 执行 `apt install -y python3-venv`（确保和 python3 版本匹配） |

> ⚠️ **重要提醒**：目前只是安装了系统级的 Python 环境。在实际部署项目时（第 0 章 / 第 2 章），我们还会为项目创建独立的**虚拟环境**（virtual environment），以避免不同项目之间的依赖冲突。这里先确保基础环境就绪即可。

---

## 1.4 Redis 安装与配置 ⭐ 重要

Redis 是 SimplePolyBot 的**消息中枢**——四个模块之间的数据传递全靠它。这一步非常关键，请务必仔细操作。

### 📖 什么是 Redis？

简单来说，Redis 就是一个**超快的内存数据库**。你可以把它想象成一个"快递中转站"：

```
market_data_collector（行情采集器）
        ↓ 放数据到 Redis
    ┌─────────┐
    │  Redis  │ ← 中转站（消息队列）
    └─────────┘
        ↓ 取数据
strategy_engine（策略引擎）→ 计算信号 → 再放回 Redis → order_executor 取出执行
```

它的特点是：速度极快（纯内存操作）、支持多种数据结构（字符串/列表/集合/哈希表）、支持发布订阅模式（Pub/Sub）。

---

### 🔧 完整安装与配置步骤

#### 第一步：安装 Redis

```bash
apt install -y redis-server
```

**预期输出**：
```
Setting up redis-server (7.0.15-1build1) ...
Processing triggers for systemd (255.4-1ubuntu1) ...
```

安装完成后，Redis 会**自动启动**。

#### 第二步：设置连接密码 ⚠️ 生产环境必须！

Redis 默认没有密码保护，任何人只要知道 IP 和端口就能访问。在生产环境中这是极其危险的，**必须设置强密码**。

```bash
sed -i 's/# requirepass foobared/requirepass YOUR_STRONG_PASSWORD_HERE/' /etc/redis/redis.conf
```

> ⚠️ 请将 `YOUR_STRONG_PASSWORD_HERE` 替换为你自己的强密码！
>
> **密码强度要求**：
> - 长度至少 **16 位**
> - 包含大小写字母 + 数字 + 特殊符号（如 `!@#$%`）
> - 不要使用字典词汇、生日、手机号等易猜内容
> - 示例：`Sp@2026!R3d1s_S3cur3_K3y_xK9mP`
>
> 💡 **生成随机密码的方法**：
> ```bash
> openssl rand -base64 32
> ```
> 这会生成一个 32 字节的随机 Base64 字符串，安全性很高。

#### 第三步：绑定本地地址（安全加固）

默认情况下 Redis 监听所有网络接口（包括公网），这意味着理论上任何人都能尝试连接你的 Redis。我们将其限制为仅允许本地连接：

```bash
sed -i 's/bind 127.0.0.1 ::1/bind 127.0.0.1/' /etc/redis/redis.conf
```

**这行命令的作用**：将 `bind` 配置从 `127.0.0.1 ::1`（同时监听 IPv4 和 IPv6 的 localhost）改为 `bind 127.0.0.1`（仅监听 IPv4 localhost）。这样只有服务器本地的程序才能连接 Redis，外部无法访问。

> 💡 **为什么不需要开放 Redis 端口？** 因为我们的 SimplePolyBot 和 Redis 运行在同一台服务器上，程序通过 `localhost`（即 `127.0.0.1`）连接 Redis 即可，不需要从外部访问。所以防火墙也不需要放行 Redis 的 6379 端口。

#### 第四步：重启服务并设置开机自启

```bash
systemctl restart redis-server
systemctl enable redis-server
```

**解释**：
- `systemctl restart redis-server` — 让刚才修改的配置生效（必须重启才能加载新配置）
- `systemctl enable redis-server` — 设置开机自动启动（服务器重启后 Redis 会自动恢复运行）

**预期输出**：
```
Synchronizing state of redis-server.service with SysV service script with /lib/systemd/systemd-sysv-install.
Executing: /lib/systemd/systemd-sysv-install enable redis-server
Created symlink /etc/systemd/system/multi-user.target.wants/redis-server.service → /usr/lib/systemd/system/redis-server.service.
```

#### 第五步：验证 Redis 是否正常运行

**方法一：检查服务状态**

```bash
systemctl status redis-server
```

**预期输出**（关键部分）：
```
● redis-server.service - Advanced key-value store
     Loaded: loaded (/usr/lib/systemd/system/redis-server.service; enabled; preset: enabled)
     Active: active (running) since Thu 2026-04-02 10:30:00 UTC; 5s ago
       Docs: http://redis.io/documentation,
             http://redis.io/topics/administration
   Main PID: 12345 (redis-server)
      Tasks: 5 (limit: 2278)
     Memory: 1.2M
        CPU: 5ms
     CGroup: /system.slice/redis-server.service
             └─12345 "/usr/bin/redis-server 127.0.0.1:6379"
```

✅ **重点检查这三项**：
- `Active: active (running)` — 绿色，表示正在运行
- `enabled` — 表示已设置开机自启
- 最后行显示 `127.0.0.1:6379` — 确认只监听了本地地址

**方法二：使用 redis-cli 测试连通性**

```bash
redis-cli ping
```

如果你设置了密码，则需要带上 `-a` 参数：

```bash
redis-cli -a YOUR_PASSWORD ping
```

✅ **成功标志**：返回 `PONG`

```
PONG
```

> 💡 看到 `PONG` 就表示 Redis 完全正常！Redis 用"乒乓"（PING/PONG）来做健康检查——你发 PING，它回 PONG，就像打乒乓球一样简单直观。

---

### ❌ Redis 故障排查

| 问题 | 症状 | 解决方法 |
|------|------|---------|
| Redis 无法启动 | `status` 显示 `failed` | 查看 `journalctl -u redis-server -n 20` 定位原因；常见原因是配置文件语法错误，用 `redis-server --test-memory` 测试 |
| 密码认证失败 | 返回 `NOAUTH Authentication required` | 确认 redis.conf 中 `requirepass` 的值与你传入的一致（注意特殊字符可能需要引号包裹） |
| 端口 6379 被占用 | 启动时报 `Address already in use` | 执行 `lsof -i :6379` 查看占用进程，必要时 `kill` 掉 |
| 内存不足 | 日志显示 `OOM` 或 `Can't save in background` | 编辑 redis.conf 设置 `maxmemory 512mb` 和 `maxmemory-policy allkeys-lru` |
| 连接被拒绝 | `redis-cli` 返回 `Connection refused` | 确认 Redis 服务已启动（`systemctl start redis-server`）；确认 bind 地址正确 |

---

## 1.5 安全加固基础

服务器暴露在公网上，随时面临各种自动化扫描和攻击尝试。本节将进行最基本的安全加固，大幅提升服务器的安全性。

### 👤 创建专用运行用户

**为什么不一直用 root？**

root 用户拥有系统的最高权限，一旦被攻破，攻击者可以为所欲为。最佳实践是：日常操作使用普通用户，仅在需要时临时提权。

```bash
useradd -m -s /bin/bash polybot
usermod -aG sudo polybot
```

**解释**：
- `useradd -m -s /bin/bash polybot` — 创建名为 `polybot` 的用户（`-m` 自动创建家目录，`-s /bin/bash` 指定使用 bash shell）
- `usermod -aG sudo polybot` — 将 `polybot` 加入 `sudo` 组，使其可以使用 `sudo` 命令获取管理员权限

**验证创建结果**：

```bash
id polybot
```

**预期输出**：
```
uid=1001(polybot) gid=1001(polybot) groups=1001(polybot),27(sudo)
```

可以看到 `polybot` 同时属于 `polybot` 组和 `sudo` 组。

---

### 🔑 配置 SSH 密钥认证

SSH 密钥认证比密码登录安全得多。原理是用一对"钥匙"（公钥+私钥）代替密码：公钥放在服务器上，私钥留在你电脑里。登录时服务器用公钥验证你的私钥，无需传输密码。

#### 在本地电脑上生成密钥对（如果没有的话）

**Windows 用户（PowerShell）**：

```powershell
ssh-keygen -t ed25519 -C "your_email@example.com"
```

**Mac/Linux 用户（Terminal）**：

```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```

一路回车使用默认设置（可以设置 passphrase 额外加密私钥，但不是必须的）。

生成的密钥文件位置：
- **私钥**（绝对保密！）：`~/.ssh/id_ed25519`
- **公钥**（要上传到服务器）：`~/.ssh/id_ed25519.pub`

#### 将公钥上传到服务器

**方法一：使用 ssh-copy-id（推荐，Mac/Linux/Windows PowerShell 都支持）**

```bash
ssh-copy-id polybot@216.238.91.89
```

输入一次 polybot 的密码后，公钥就会自动复制到服务器上。

**方法二：手动复制（如果 ssh-copy-id 不可用）**

1. 在本地查看公钥内容：

```bash
cat ~/.ssh/id_ed25519.pub
```

2. 复制输出的整行内容（以 `ssh-ed25519` 开头的一长串）

3. 在服务器上执行：

```bash
mkdir -p /home/polybot/.ssh
echo "你复制的公钥内容粘贴在这里" >> /home/polybot/.ssh/authorized_keys
chown -R polybot:polybot /home/polybot/.ssh
chmod 700 /home/polybot/.ssh
chmod 600 /home/polybot/.ssh/authorized_keys
```

✅ **验证密钥登录**：现在你应该可以用密钥直接登录了，不再需要输入密码：

```bash
ssh polybot@216.238.91.89
```

如果能直接进入而不要求输入密码，说明配置成功！

---

### 🛡️ 配置 fail2ban（自动封禁暴力破解）

fail2ban 会监控日志文件，当发现某个 IP 多次尝试失败的登录后，自动用防火墙规则将该 IP 封禁一段时间。

```bash
systemctl enable fail2ban
systemctl start fail2ban
```

**验证运行状态**：

```bash
systemctl status fail2ban
```

**预期输出关键行**：
```
Active: active (running)
```

> 💡 **默认配置已经够用**：fail2ban 默认会监控 SSH 服务（端口 22），当同一个 IP 在 10 分钟内尝试失败 5 次，就自动封禁 10 分钟。这些参数可以在 `/etc/fail2ban/jail.local` 中自定义。

---

### 🔥 配置 UFW 防火墙

UFW（Uncomplicated Firewall）是 Ubuntu 自带的防火墙管理工具，名字就说明了它的设计理念——**简单易用**。

⚠️ **极度重要：在执行以下命令前，务必确认你已经能用 `polybot` 用户通过 SSH 密钥登录！否则启用防火墙后可能把自己锁在外面！**

```bash
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw enable
```

**逐条解释**：

| 命令 | 作用 | 为什么 |
|------|------|--------|
| `ufw default deny incoming` | 默认拒绝所有入站连接 | 除了你明确开放的端口，其他一律拒绝 |
| `ufw default allow outgoing` | 允许所有出站连接 | 服务器主动向外请求（如 API 调用、系统更新）不受限 |
| `ufw allow ssh` | 放行 SSH 端口（22） | 否则你自己也连不上来了！ |
| `ufw enable` | 启动防火墙 | 使以上规则生效 |

**启用时会提示**：
```
Command may disrupt existing ssh connections. Proceed with operation (y|n)?
```

输入 `y` 回车确认。

**验证防火墙状态**：

```bash
ufw status verbose
```

**预期输出**：
```
Status: Active
Logging: on (low)
Default: deny (incoming), allow (outgoing), disabled (routed)
New profiles: skip

To                         Action      From
--                         ------      ----
22/tcp                     ALLOW IN    Anywhere
22/tcp (v6)                ALLOW IN    Anywhere (v6)
```

✅ **成功标志**：`Status: Active`，且能看到 `22/tcp ALLOW IN` 规则。

> 💡 后续如果需要开放其他端口（比如 Web 监控面板），使用 `ufw allow <端口号>` 即可。例如 `ufw allow 9090` 开放 Grafana 端口。

---

## 1.6 时间同步（交易时间敏感）

对于量化交易系统而言，**时间的准确性至关重要**。订单的时间戳、市场结算时间判定、WebSocket 心跳超时判断……这些都依赖于精确的系统时间。如果服务器时间偏差过大，可能导致：
- 订单被交易所因时间戳无效而拒绝
- GTD（Good-Til-Date）订单在错误的时间过期
- 结算时间判断失误
- 日志时间线混乱，难以排查问题

目标是将时间误差控制在 **100 毫秒以内**。

---

### 🕐 安装并配置 chrony 时间同步服务

chrony 是一个优秀的时间同步守护进程，相比传统的 ntpd，它在虚拟机环境下表现更好，且同步速度更快。

#### 第一步：确认 chrony 已安装

在 1.2 节中我们已经安装过 chrony，这里确认一下：

```bash
chronyd --version
```

**预期输出**：
```
chronyd (chrony) version 4.5
```

如果显示 `command not found`，执行 `apt install -y chrony`。

#### 第二步：检查 NTP 服务器配置

```bash
grep "^server\|^pool" /etc/chrony/chrony.conf
```

**预期输出**（Ubuntu 24.04 默认配置通常已包含）：
```
pool ntp.ubuntu.com        iburst maxsources 3
pool 0.ubuntu.pool.ntp.org iburst maxsources 1
pool 1.ubuntu.pool.ntp.org iburst maxsources 1
pool 2.ubuntu.pool.ntp.org iburst maxsources 1
```

> 💡 **这些是什么？** NTP（Network Time Protocol）服务器池就是互联网上的"标准时钟"。chrony 会从这些服务器获取准确时间并同步到你的服务器。`iburst` 表示初始同步时加快请求频率（尽快对齐时间），`maxsources` 限制同时使用的服务器数量。

如果输出为空或你想添加更多可靠的 NTP 服务器，可以编辑配置文件：

```bash
nano /etc/chrony/chrony.conf
```

在文件开头添加一行：

```
server pool.ntp.org iburst
```

保存退出（`Ctrl+O` → 回车 → `Ctrl+X`）。

#### 第三步：重启并启用服务

```bash
systemctl restart chronyd
systemctl enable chronyd
```

#### 第四步：验证时间同步状态

```bash
chronyc tracking
```

**预期输出**（关键指标解读）：
```
Reference ID    : A29C5340 (ntp-1.abc.com)
Stratum         : 3
Ref time (UTC)  : Thu 2026-04-02 11:00:00.123456
System time     : 0.000002445 seconds slow of NTP time
Last offset     : +0.000001234 seconds
RMS offset      : 0.000000567 seconds
Frequency       : 12.345 slow (gain=-0.123ppm)
Residual freq   : -0.000 ppm
Skew            : 0.025 ppm
Root delay      : 0.012345 seconds
Root dispersion : 0.000456 seconds
Update interval : 1024.0 seconds
Leap status     : Normal
```

✅ **重点关注以下三个指标**：

| 指标 | 含义 | 合格标准 |
|------|------|---------|
| **System time** | 当前系统时间与 NTP 标准时间的差值 | **误差 < 0.01 秒（10ms）** 为理想状态，< 0.1 秒（100ms）为合格 |
| **Last offset** | 上一次同步的时间偏移量 | 应该接近 0，正负几毫秒内 |
| **Leap status** | 闰秒状态 | 显示 `Normal` 即正常 |

如果你的 `System time` 显示类似 `0.000002445 seconds slow of NTP time`，说明误差只有约 **2.4 微秒**，精度非常高！🎉

#### 第五步：查看当前服务器时间

```bash
date
timedatectl
```

**预期输出**：
```
Thu Apr  2 11:05:00 UTC 2026

               Local time: Thu 2026-04-02 11:05:00 UTC
           Universal time: Thu 2026-04-02 11:05:00 UTC
                 RTC time: Thu 2026-04-02 11:04:58
                Time zone: Etc/UTC (UTC, +0000)
System clock synchronized: yes
              NTP service: active
          RTC in local TZ: no
```

✅ **关键确认项**：
- `System clock synchronized: yes` — 已同步 ✅
- `NTP service: active` — NTP 服务运行中 ✅

---

### ❌ 时间同步故障排查

| 问题 | 症状 | 解决方法 |
|------|------|---------|
| 时间偏差大（>1秒） | `System time` 显示数秒甚至更大的偏差 | 执行 `systemctl restart chronyd` 强制重新同步；检查防火墙是否放行了 UDP 123 端口（`ufw allow 123/udp`） |
| `NTP service: inactive` | chronyd 未运行 | 执行 `systemctl start chronyd && systemctl enable chronyd` |
| Stratum = 16 | 无法联系到任何 NTP 服务器 | 检查网络连接；确认 DNS 正常（`ping pool.ntp.org`）；检查防火墙规则 |
| 时间跳变 | 系统时间突然大幅变化 | 可能是虚拟化环境的已知问题；在 chrony.conf 中添加 `makestep 1.0 3` 允许在前 3 次更新时步进调整时间 |

---

### 🎯 本章小结 — 环境准备检查清单

完成以上所有步骤后，请逐一核对以下检查点：

| # | 检查项 | 验证命令 | 预期结果 | 状态 |
|---|--------|---------|---------|------|
| 1 | SSH 可正常登录 | `ssh polybot@216.238.91.89` | 无需密码即可进入 | ☐ |
| 2 | 系统已更新至最新 | `apt list --upgradable 2>/dev/null \| wc -l` | 输出为 0（无待更新包） | ☐ |
| 3 | Python 3.10+ 可用 | `python3 --version` | 显示 3.10+ | ☐ |
| 4 | pip 和 venv 已安装 | `pip3 --version && python3 -m venv --help` | 均正常显示 | ☐ |
| 5 | Redis 运行正常 | `redis-cli ping` | 返回 `PONG` | ☐ |
| 6 | Redis 已设密码 | `redis-cli -a 你的密码 ping` | 返回 `PONG` | ☐ |
| 7 | Redis 仅本地监听 | `ss -tlnp \| grep 6379` | 显示 `127.0.0.1:6379` | ☐ |
| 8 | polybot 用户已创建 | `id polybot` | 显示 uid/gid/groups | ☐ |
| 9 | SSH 密钥登录可用 | `ssh polybot@216.238.91.89` | 免密登录成功 | ☐ |
| 10 | fail2ban 运行中 | `systemctl status fail2ban` | `active (running)` | ☐ |
| 11 | UFW 防火墙已启用 | `ufw status` | `Status: Active` | ☐ |
| 12 | 时间同步正常 | `chronyc tracking` | System time 误差 < 100ms | ☐ |

全部打勾 ✅？恭喜你，服务器环境准备工作圆满完成！接下来就可以进入 **[第 0 章](#第-0-章快速上手5分钟跑起来)** 进行一键部署，或者深入 **[第 2 章](#第-2-章项目部署与配置)** 了解详细的项目部署流程。

<!-- CHAPTER_1_CONTENT_END -->

---

## 第 2 章：项目部署与配置

<!-- CHAPTER_2_CONTENT_START -->

> 🎯 **本章目标**：从零开始把 SimplePolyBot 部署到你的服务器上，完成所有配置，让四个模块成功跑起来。本章是整个部署过程的核心操作手册，每一步都配有预期输出和错误排查。

---

### 2.1 克隆项目与目录结构说明 📁

首先把项目代码从 GitHub 下载到服务器：

```bash
cd /opt
git clone https://github.com/EatTake/SimplePolyBot.git
cd SimplePolyBot
ls -la
```

> 💡 `/opt` 是 Linux 系统中专门用来存放第三方软件的标准目录，就像 Windows 的 `Program Files`。把项目放在这里既规范又方便管理。

**预期输出**：
```
total 120
drwxr-xr-x   8 root root  4096 Apr  2 10:00 .
drwxr-xr-x   3 root root  4096 Apr  2 10:00 ..
drwxr-xr-x   5 root root  4096 Apr  2 10:00 config
drwxr-xr-x   6 root root  4096 Apr  2 10:00 modules
drwxr-xr-x   3 root root  4096 Apr  2 10:00 shared
drwxr-xr-x   2 root root  4096 Apr  2 10:00 scripts
drwxr-xr-x   3 root root  4096 Apr  2 10:00 tests
drwxr-xr-x   2 root root  4096 Apr  2 10:00 docs
-rw-r--r--   1 root root   512 Apr  2 10:00 requirements.txt
-rw-r--r--   1 root root  1024 Apr  2 10:00 .env.example
-rw-r--r--   1 root root  2048 Apr  2 10:00 README.md
```

✅ **成功标志**：能看到 `config/`、`modules/`、`shared/`、`scripts/` 这几个核心目录。

❌ **如果出错**：
- `Repository not found` → 检查仓库地址是否正确；如果是私有仓库需要 SSH Key 或 Access Token
- `Permission denied` → `/opt` 需要 root 权限，确保用 `sudo` 或以 root 登录

---

#### 完整目录结构一览

下面是项目的完整"地图"，建议你先通读一遍，对每个文件夹有个整体印象：

```
SimplePolyBot/
├── config/
│   ├── settings.yaml              # ⭐ 主配置文件 — 策略参数、Redis、模块开关全在这里
│   └── presets/                   # 预设方案目录 — 三种风险档位的参数模板
│       ├── conservative.yaml      #   保守型（新手推荐）
│       ├── balanced.yaml          #   平衡型（默认）
│       └── aggressive.yaml        #   激进型（老手专用）
│
├── modules/                       # 四大核心模块（每个都是独立进程）
│   ├── market_data_collector/     # 👀 市场数据收集器 — WebSocket 接收实时行情
│   │   ├── main.py               #     入口文件
│   │   └── binance_ws.py         #     WebSocket 客户端（连接 Polymarket）
│   │
│   ├── strategy_engine/           # 🧠 策略引擎 — OLS 回归计算买卖信号
│   │   ├── main.py               #     入口文件
│   │   ├── signal_generator.py   #     信号生成器（核心算法）
│   │   └── safety_cushion.py     #     安全垫计算模块
│   │
│   ├── order_executor/            # ✋ 订单执行器 — 向 Polymarket 下单
│   │   ├── main.py               #     入口文件
│   │   ├── clob_client.py        #     Polymarket CLOB API 封装
│   │   └── order_manager.py      #     订单生命周期管理
│   │
│   └── settlement_worker/         # 💰 结算工作器 — 市场结算 + 代币赎回
│       └── main.py               #     入口文件
│
├── shared/                        # 🔧 共享工具库（被所有模块引用）
│   ├── config.py                 # 配置加载器（读取 YAML + .env）
│   ├── config_validator.py       # 配置合法性验证
│   ├── config_wizard.py          # 交互式配置向导
│   ├── config_presets.py         # 预设方案管理
│   ├── error_formatter.py        # 错误信息美化输出
│   ├── logger.py                 # 统一日志系统
│   ├── parameter_registry.py     # 参数注册表（所有可配置参数的元信息）
│   ├── redis_client.py           # Redis 连接封装
│   ├── retry_decorator.py        # 自动重试装饰器
│   └── credential_manager.py     # 凭证安全管理
│
├── scripts/                       # 🛠 运维脚本
│   ├── start_all.sh             # 一键启动全部 4 个模块
│   └── start_module.sh          # 启动单个指定模块
│
├── tests/                         # ✅ 测试套件
├── docs/                          # 📖 本文档所在目录
├── requirements.txt              # Python 依赖清单
├── .env.example                  # 环境变量模板（复制为 .env 后填写）
└── README.md                     # 项目说明文档
```

> 💡 **快速记忆法**：`config` 放设置，`modules` 是四大金刚（眼脑手会计），`shared` 是公共工具箱，`scripts` 是遥控器。

---

### 2.2 Python 虚拟环境与依赖安装 🐍

这一步给项目创建一个**独立的 Python 环境**，避免和系统的其他程序产生冲突。

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### 什么是 venv？为什么必须用它？

想象一下：你的电脑是一个大药房，系统自带的 Python 是"公共药柜"。如果你直接往公共药柜里装药（`pip install`），可能会和其他病人（其他程序）的药产生冲突——比如 A 程序需要 `numpy 1.x`，B 程序却需要 `numpy 2.x`，这就炸了 💥

**venv 的作用就是给你的项目发一个独立的"私人药箱"** 📦：
- 药箱里的药只属于这个项目，不影响别人
- 你可以精确控制每个项目的依赖版本
- 删除项目时连药箱一起扔掉，干干净净

激活虚拟环境后，你的终端提示符前面会出现 `(venv)` 标记：
```
(venv) root@ubuntu:~/SimplePolyBot#
```

✅ **成功标志**：最后一行显示 `Successfully installed ...` 且无红色 ERROR，类似：
```
Successfully installed aiohttp-3.9.5 numpy-1.26.4 pandas-2.2.1 py-clob-client-0.3.0 PyYAML-6.0.1 redis-5.0.1 structlog-24.1.0 web3-6.19.0 websockets-12.0 ...
```

❌ **常见错误及解决方法**：

| 错误现象 | 原因 | 解决命令 |
|---------|------|---------|
| `No module named venv` | 系统未安装 venv 模块 | `apt install -y python3-venv` |
| `pip: command not found` | 未安装 pip | `apt install -y python3-pip` |
| `Permission denied` | 用了系统的 pip 而非 venv 内的 | 先执行 `source venv/bin/activate` 再安装 |
| numpy 编译失败 (`error: command 'gcc' failed`) | 缺少编译工具链 | `apt install -y python3-dev build-essential` |
| web3 安装报版本冲突 | 缓存残留 | `pip install --force-reinstall web3` |
| `Read timed out` / 下载很慢 | 网络问题（国内用户常见） | 使用镜像源：<br>`pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple` |

---

### 2.3 环境变量配置详解（.env）⭐ 最重要的一步

`.env` 文件存放的是你的**个人敏感凭证**——API 密钥、钱包私钥等。这是整个部署过程中最关键也最容易出错的一步，请务必仔细操作！

#### 第一步：创建 .env 文件

```bash
cp .env.example .env
nano .env
```

> 💡 `cp` 是复制命令，把模板 `.env.example` 复制成 `.env`。然后 `nano` 打开编辑器修改它。
>
> 编辑器操作提示：直接打字修改内容 → `Ctrl+O` 回车保存 → `Ctrl+X` 退出

#### 第二步：逐项理解并填写每个变量

打开 `.env` 后你会看到类似下面的模板。下表逐行解释每个变量是什么、从哪里获取、填什么：

| 变量名 | 含义 | 从哪里获取 | 示例值 |
|--------|------|-----------|--------|
| `POLYMARKET_API_KEY` | API 密钥 ID（相当于用户名） | Polymarket 后台 → 见下方教程 | `abc123def456...` |
| `POLYMARKET_API_SECRET` | API 签名密钥（相当于密码） | 同上（⚠️ 只显示一次！） | `xyz789ghi012...` |
| `POLYMARKET_API_PASSPHRASE` | API 口令（你自己设的） | 同上创建时自定义 | `my_secret_phrase_2026` |
| `PRIVATE_KEY` | MetaMask 钱包私钥 | MetaMask → 账户详情 → 导出私钥 | `0x1234abcd5678...` (66字符) |
| `WALLET_ADDRESS` | 钱包公钥地址 | MetaMask 直接复制 | `0xAbCdEf123456...` (42字符) |
| `REDIS_HOST` | Redis 服务器地址 | 本地部署填 localhost | `localhost` |
| `REDIS_PORT` | Redis 端口号 | 默认 6379 | `6379` |
| `REDIS_PASSWORD` | Redis 连接密码 | [第 1 章](#第-1-章服务器环境准备与系统安装)第三步设置的密码 | `your_redis_pass_here` |
| `POLYGON_RPC_URL` | Polygon 区块链 RPC 地址 | 免费公共 RPC 即可 | `https://polygon-rpc.com` |

#### 🔑 Polymarket API Key 获取详细步骤（图文级文字指引）

这是新手最容易卡住的地方，请按以下步骤**一步一步**操作：

1. **打开浏览器访问** [polymarket.com](https://polymarket.com)，用你的账号登录
2. **点击右上角的头像/账户图标**，在下拉菜单中选择 **Profile**（个人资料）
3. **在 Profile 页面滚动到底部**，找到 **API Access** 区域
4. **点击 "Create API Key" 按钮**
5. 系统会生成三个凭证，**立即用纸笔或密码管理器记录下来**：

   ```
   ╔══════════════════════════════════════════╗
   ║  ⚠️ 以下信息只显示一次！关闭页面后无法再查看！ ║
   ╠══════════════════════════════════════════╣
   ║                                            ║
   ║  api_key:        abc123def456...           ║
   ║  api_secret:     xyz789ghi012... ← 只出现一次！║
   ║  api_passphrase: （你自己输入一个）          ║
   ║                                            ║
   ╚══════════════════════════════════════════╝
   ```

6. 把这三个值分别填入 `.env` 对应的位置

⚠️ **如果忘了保存 api_secret 怎么办？** → 回到 Polymarket Profile 页面，删除旧的 API Key，重新创建一个新的。

#### 💰 MetaMask 私钥导出详细步骤

1. **打开 MetaMask 浏览器扩展或手机 App**
2. 点击右上角圆形**账户头像**
3. 选择 **账户详情（Account Details）**
4. 点击 **显示私键（Show Private Key）**
5. 输入你的 MetaMask 密码进行确认
6. 屏幕上会显示一串以 `0x` 开头的字符，共 66 位——这就是私钥

🔴 **极度重要安全提醒**：
- 私钥 = 你钱包里**所有资产的控制权**！任何人拿到它都能转走你的钱
- **绝对不要**把私钥存在聊天记录、普通文本文件、或者截图里
- 推荐使用 **1Password / Bitwarden** 等密码管理器存储
- 填写完 `.env` 后立即进行下一步的权限设置

#### 第三步：设置 .env 文件权限 🔒

```bash
chmod 600 .env
```

这条命令让 `.env` 文件**只有你本人能读写**，其他任何人都无法查看。这就像给文件上了一把锁。

```bash
# 验证权限是否设置正确
ls -la .env
```

✅ **预期输出**：`-rw-------` 开头（表示只有 owner 可读写）

#### 第四步：验证 .env 是否填写正确

```bash
source venv/bin/activate && python -c "
from dotenv import load_dotenv
import os
load_dotenv()
required = ['POLYMARKET_API_KEY','POLYMARKET_API_SECRET','POLYMARKET_API_PASSPHRASE','PRIVATE_KEY','WALLET_ADDRESS']
for k in required:
    v = os.getenv(k,'')
    status = '✅ OK' if v else '❌ MISSING'
    mask = v[:6]+'...' if len(v)>6 else '(空)'
    print(f'  [{status}] {k} = {mask}')
"
```

✅ **预期输出**：所有必填项都显示 `✅ OK`

❌ **如果有 ❌ MISSING** → 对应的值没有正确填写，重新执行 `nano .env` 补充

---

### 2.4 配置向导使用教程 🧙‍♂️

SimplePolyBot 提供了一个**交互式配置向导**，它会像聊天一样一步步问你问题，帮你自动生成正确的配置文件。不需要手动编辑复杂的 YAML！

#### 三种模式对比

| 模式 | 命令 | 适用场景 | 问的问题数 | 耗时 |
|------|------|---------|-----------|------|
| **quick（快速）** | `--mode quick` | 🌟 新手第一次部署 | ~8 个核心问题 | 2 分钟 |
| **standard（标准）** | `--mode standard` | 想要更多控制权的一般用户 | ~20 个问题 | 5 分钟 |
| **expert（专家）** | `--mode expert` | 高级玩家想调每一个细节 | 全部 39 个参数 | 15 分钟 |

此外还有一个**纯验证模式**（不修改任何配置，只检查当前是否合法）：

```bash
python -m shared.config_wizard --validate-only
```

#### 🚀 Quick 模式实战演示（推荐新手使用）

```bash
source venv/bin/activate
python -m shared.config_wizard --mode quick
```

**预期交互过程实录**（`←` 表示你需要输入的内容）：

```
============================================================
  🤖 SimplePolyBot 配置向导  v1.0
============================================================
  模式: quick 🚀
  本向导将引导您完成交易策略的核心配置
  新手提示：不确定的选项直接按回车使用默认值即可
============================================================


📋 第 1/5 步：资金安全设置

  📌 Base Cushion（基础安全垫系数）
     说明: OLS 回归的安全边际缓冲值，越大越保守
     范围: 0.01 ~ 0.20
     [默认: 0.05]: ← 直接回车

  📌 Alpha（趋势跟随强度）
     说明: 价格动量的权重，越大越激进
     范围: 0.30 ~ 0.90
     [默认: 0.50]: ← 直接回车


📋 第 2/5 步：仓位风控

  📌 单市场最大持仓金额 ($)
     范围: 100 ~ 50000
     [默认: 5000]: ← 直接回车

  📌 总最大风险敞口 ($)
     范围: 1000 ~ 100000
     [默认: 20000]: ← 直接回车

  📌 止损比例 (%)
     范围: 5 ~ 30
     [默认: 10]: ← 直接回车

  📌 止盈比例 (%)
     范围: 10 ~ 50
     [默认: 20]: ← 直接回车


📋 第 3/5 步：Redis 连接验证

  正在测试 Redis 连接...
  ✅ Redis 连接成功 (localhost:6379)


📋 第 4/5 步：凭证安全检查

  📌 POLYMARKET_API_KEY: abcdef******  ✅ 已检测
  📌 POLYMARKET_API_SECRET: xyz789******  ✅ 已检测
  📌 PRIVATE_KEY: 0xabc1******  ✅ 已检测
  📌 WALLET_ADDRESS: 0xABcd******  ✅ 已检测


📋 第 5/5 步：确认配置摘要

============================================================
  📋 配置预览
============================================================
  策略模式: balanced（平衡型）
  Base Cushion: 0.05
  Alpha: 0.50
  最大单仓: $5,000
  最大敞口: $20,000
  止损: 10% | 止盈: 20%
  日亏损限额: $500
============================================================

  确认保存此配置到 config/settings.yaml? (y/n): ← 输入 y 回车

  ✅ 配置已保存！
  📄 文件路径: /opt/SimplePolyBot/config/settings.yaml

  下一步: 执行 bash scripts/start_all.sh 启动系统
```

#### 关于敏感信息的掩码显示 ⚠️

你可能注意到上面的输出中，API Key 和私钥都显示成了 `abcdef******` —— 这是向导的**安全掩码功能**，防止你的敏感信息在终端屏幕上被旁边的人看到。

即使你在终端输入了完整的密钥，显示时也会自动隐藏中间部分，只保留前 6 位字符用于辨认。

💡 **新手建议**：第一次部署时，**所有问题都直接按回车使用默认值**。默认值经过调优，适合大多数入门场景。等你熟悉了系统运行逻辑后，再用 standard 或 expert 模式微调参数。

✅ **成功标志**：最后显示 `✅ 配置已保存！` 且 `config/settings.yaml` 文件已被更新（可以用 `cat config/settings.yaml` 确认）

❌ **如果出错**：
- `ModuleNotFoundError: No module named 'shared'` → 确认已在项目根目录且已激活 venv（提示符前有 `(venv)`）
- `Redis connection failed` → 先确认 Redis 在运行：`systemctl status redis-server`
- `ValidationError: xxx` → 根据提示的错误信息和合法范围重新输入

---

### 2.5 预设方案选择指南 ⚖️

如果你不想一个个回答问题，SimplePolyBot 还提供了**三档预设方案**，像选游戏难度一样一键应用。

#### 三档方案全面对比

| 维度 | Conservative（保守型） 🟢 | Balanced（平衡型） 🟡 | Aggressive（激进型） 🔴 |
|------|--------------------------|----------------------|------------------------|
| **适用人群** | 新手 / 学习阶段 | 一般用户【默认推荐】 | 经验丰富的量化交易者 |
| **base_cushion**（安全垫） | 0.03（高缓冲，更谨慎） | 0.02（适中） | 0.01（低缓冲，更灵敏） |
| **alpha**（趋势强度） | 0.3（缓慢跟随） | 0.5（平衡响应） | 0.7（积极追涨杀跌） |
| **max_position**（单仓上限） | $2,000 | $5,000 | $8,000 |
| **max_exposure**（总敞口） | $8,000 | $20,000 | $50,000 |
| **stop_loss**（止损线） | 8%（较早止损） | 10%（标准） | 15%（容忍更大波动） |
| **take_profit**（止盈线） | 15%（落袋为安） | 20%（标准） | 30%（追求更高收益） |
| **daily_loss_limit**（日亏限额） | $200 | $500 | $2,000 |
| **信号过滤阈值** | 严格（减少噪音交易） | 中等 | 宽松（捕捉更多机会） |
| **预期收益** | 低但稳定 | 中等 | 高但波动大 |
| **最大回撤风险** | 小 | 中 | 大 |
| **心理压力** | 😌 轻松 | 😐 一般 | 😰 较大 |

#### 如何选择？

```
你是哪种类型的用户？

┌─────────────────────────────────────────────┐
│                                             │
│   🟢 Conservative                           │
│   → 我刚接触量化交易，不想亏太多钱           │
│   → 我先用小资金跑起来看看效果              │
│   → 我的资金量 < $5,000                     │
│                                             │
│   🟡 Balanced  ← 大多数人的选择              │
│   → 我有一些交易经验，愿意承担中等风险       │
│   → 我想在收益和风险之间取得平衡            │
│   → 我的资金量 $5,000 ~ $20,000             │
│                                             │
│   🔴 Aggressive                             │
│   → 我是资深交易者，了解自己的风险承受能力   │
│   → 我追求高收益，能接受较大回撤            │
│   → 我的资金量 > $20,000                    │
│                                             │
└─────────────────────────────────────────────┘
```

#### 一键应用预设方案

```bash
source venv/bin/activate

# 应用平衡型（推荐大多数用户使用）
python -m shared.config_presets apply balanced

# 或者选择其他档次
python -m shared.config_presets apply conservative   # 保守型
python -m shared.config_presets apply aggressive     # 激进型
```

**预期输出**：
```
正在加载预设方案: balanced...
✅ 预设方案已应用到 config/settings.yaml
  - base_cushion: 0.02
  - alpha: 0.50
  - max_position: 5000
  - max_exposure: 20000
  - stop_loss_pct: 0.10
  - take_profit_pct: 0.20
  - daily_loss_limit: 500

💡 提示: 你可以随时通过配置向导微调这些参数:
    python -m shared.config_wizard --mode standard
```

> 💡 **预设方案 ≠ 最终定局**：应用预设后，你仍然可以运行配置向导（2.4 节）来覆盖其中任意参数。预设只是一个"快捷起点"。

---

### 2.6 首次启动验证 🚀

配置全部完成后，终于可以启动系统了！我们分两步走：先单独测试一个模块确认基础环境没问题，再一次性启动全部四个模块。

#### 第一步：单独测试市场数据收集器

```bash
source venv/bin/activate
python -m modules.market_data_collector.main
```

**预期日志输出**（看到以下内容说明连接成功）：
```
2026-04-02 10:00:01 [INFO] ========================================
2026-04-02 10:00:01 [INFO]   Market Data Collector 启动中...
2026-04-02 10:00:01 [INFO] ========================================
2026-04-02 10:00:01 [INFO] 加载配置: config/settings.yaml
2026-04-02 10:00:01 [INFO] Redis 连接成功: localhost:6379
2026-04-02 10:00:02 [INFO] 🌐 WebSocket 连接建立: wss://ws-subscriptions-clob.polymarket.com/ws/market
2026-04-02 10:00:02 [INFO] 订阅资产列表: [0xabc..., 0xdef..., 0x123...]
2026-04-02 10:00:05 [INFO] 📊 收到 order_book 更新: token=0xabc..., best_bid=0.52, best_ask=0.55
2026-04-02 10:00:10 [INFO] 💓 PING/PONG 心跳正常
```

✅ **成功标志**：看到 `WebSocket 连接建立` 和 `收到 order_book 更新` 的日志，说明数据已经在流入了。

此时按 **Ctrl+C** 停止测试（这只是验证，不是正式运行）。

❌ **如果模块立刻退出且没有上面那些日志**：

| 日志中的错误信息 | 原因 | 解决方法 |
|---------------|------|---------|
| `Connection refused` to Redis | Redis 没运行 | `systemctl start redis-server` |
| `NOAUTH Authentication required` | Redis 密码不匹配 | 检查 `.env` 中 `REDIS_PASSWORD` 和 redis.conf 是否一致 |
| `Authentication failed` | API Key 有误 | 检查 `.env` 中三个 `POLYMARKET_*` 变量 |
| `Invalid private key format` | 私钥格式错误 | 必须是 `0x` 开头 + 64 位十六进制，共 66 字符 |
| `ModuleNotFoundError` | 未在 venv 中 | 执行 `source venv/bin/activate` 再运行 |

#### 第二步：启动全部四个模块

```bash
bash scripts/start_all.sh
```

这条命令会依次启动 SimplePolyBot 的四大核心模块：

| 模块 | 功能 | 类比 |
|------|------|------|
| `market_data_collector` | 通过 WebSocket 接收实时行情 | 👀 **眼睛** — 盯盘看价格 |
| `strategy_engine` | 用 OLS 回归计算买卖信号 | 🧠 **大脑** — 分析决策 |
| `order_executor` | 向 Polymarket 下单执行交易 | ✋ **手** — 执行买卖 |
| `settlement_worker` | 结算市场并赎回获胜代币 | 💰 **会计** — 清算收款 |

**预期输出**：
```
正在启动模块: market_data_collector
✅ 模块 'market_data_collector' 启动成功 (PID: 12345)
日志文件: /opt/SimplePolyBot/logs/market_data_collector.log

正在启动模块: strategy_engine
✅ 模块 'strategy_engine' 启动成功 (PID: 12346)
日志文件: /opt/SimplePolyBot/logs/strategy_engine.log

正在启动模块: order_executor
✅ 模块 'order_executor' 启动成功 (PID: 12347)
日志文件: /opt/SimplePolyBot/logs/order_executor.log

正在启动模块: settlement_worker
✅ 模块 'settlement_worker' 启动成功 (PID: 12348)
日志文件: /opt/SimplePolyBot/logs/settlement_worker.log

✅ 所有模块启动成功
```

🎉 **终极成功标志**：四行 `✅ 模块 'xxx' 启动成功` + 最后一行 `✅ 所有模块启动成功`

#### 如何查看实时日志

启动成功后，你可以用以下命令"盯着"某个模块的实时日志输出：

```bash
# 查看行情数据模块的实时日志（持续滚动）
tail -f logs/market_data_collector.log

# 查看策略引擎的实时日志
tail -f logs/strategy_engine.log

# 查看订单执行器的实时日志
tail -f logs/order_executor.log
```

> 💡 `tail -f` 表示持续跟踪文件末尾的新内容，日志会像瀑布一样不断滚下来。按 `Ctrl+C` 可以退出查看。

**健康的日志应该长这样**（持续有新内容出现）：
```
2026-04-02 10:01:05 [INFO] 收到 price_change 事件: token=0x..., new_price=0.53
2026-04-02 10:01:10 [INFO] PING/PONG 心跳正常
2026-04-02 10:01:15 [INFO] 收到 order_book 更新: bid=0.51, ask=0.54, spread=0.03
2026-04-02 10:01:20 [INFO] 📊 信号计算完成: direction=BUY, confidence=0.68
...
```

---

### 2.7 进程管理（systemd 开机自启）🔄

目前我们的机器人是通过 `start_all.sh` 手动启动的——这意味着如果服务器重启，机器人不会自动恢复运行。为了让它**开机自启 + 崩溃自动重启**，我们需要把它注册为 systemd 服务。

#### 创建 systemd 服务文件

我们需要为每个模块创建一个服务文件。以下是第一个模块的完整模板，其他三个只需改名字即可：

```ini
# /etc/systemd/system/simplepolybot-market-data.service
[Unit]
Description=SimplePolyBot Market Data Collector
Documentation=https://github.com/EatTake/SimplePolyBot
After=network.target redis.service
Wants=redis.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/SimplePolyBot
ExecStart=/opt/SimplePolyBot/venv/bin/python -m modules.market_data_collector.main
Restart=always
RestartSec=5
EnvironmentFile=/opt/SimplePolyBot/.env

# 安全加固
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=/opt/SimplePolyBot/logs /opt/SimplePolyBot/config

# 资源限制
MemoryMax=512M
CPUQuota=50%

[Install]
WantedBy=multi-user.target
```

> 💡 **关键参数解释**：
> - `Restart=always` — 崩溃后自动重启，永不放弃
> - `RestartSec=5` — 崩溃后等待 5 秒再重启（避免疯狂重启导致雪崩）
> - `EnvironmentFile=` — 自动加载 `.env` 中的环境变量
> - `MemoryMax=512M` — 内存超限时自动杀死防泄漏
> - `CPUQuota=50%` — 最多占用半个 CPU 核心

其余三个服务文件，只需要修改 **Description** 和 **ExecStart** 中的模块名：

```ini
# simplepolybot-strategy.service
Description=SimplePolyBot Strategy Engine
ExecStart=/opt/SimplePolyBot/venv/bin/python -m modules.strategy_engine.main

# simplepolybot-order-executor.service
Description=SimplePolyBot Order Executor
ExecStart=/opt/SimplePolyBot/venv/bin/python -m modules.order_executor.main

# simplepolybot-settlement.service
Description=SimplePolyBot Settlement Worker
ExecStart=/opt/SimplePolyBot/venv/bin/python -m modules.settlement_worker.main
```

#### 一键创建并启用所有服务

```bash
# 创建 4 个服务文件
cat > /etc/systemd/system/simplepolybot-market-data.service << 'EOF'
[Unit]
Description=SimplePolyBot Market Data Collector
After=network.target redis.service
[Service]
Type=simple
User=root
WorkingDirectory=/opt/SimplePolyBot
ExecStart=/opt/SimplePolyBot/venv/bin/python -m modules.market_data_collector.main
Restart=always
RestartSec=5
EnvironmentFile=/opt/SimplePolyBot/.env
[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/simplepolybot-strategy.service << 'EOF'
[Unit]
Description=SimplePolyBot Strategy Engine
After=network.target redis.service
[Service]
Type=simple
User=root
WorkingDirectory=/opt/SimplePolyBot
ExecStart=/opt/SimplePolyBot/venv/bin/python -m modules.strategy_engine.main
Restart=always
RestartSec=5
EnvironmentFile=/opt/SimplePolyBot/.env
[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/simplepolybot-order-executor.service << 'EOF'
[Unit]
Description=SimplePolyBot Order Executor
After=network.target redis.service
[Service]
Type=simple
User=root
WorkingDirectory=/opt/SimplePolyBot
ExecStart=/opt/SimplePolyBot/venv/bin/python -m modules.order_executor.main
Restart=always
RestartSec=5
EnvironmentFile=/opt/SimplePolyBot/.env
[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/simplepolybot-settlement.service << 'EOF'
[Unit]
Description=SimplePolyBot Settlement Worker
After=network.target redis.service
[Service]
Type=simple
User=root
WorkingDirectory=/opt/SimplePolyBot
ExecStart=/opt/SimplePolyBot/venv/bin/python -m modules.settlement_worker.main
Restart=always
RestartSec=5
EnvironmentFile=/opt/SimplePolyBot/.env
[Install]
WantedBy=multi-user.target
EOF

# 重新加载 systemd 配置
systemctl daemon-reload

# 设置开机自启
systemctl enable simplepolybot-market-data.service
systemctl enable simplepolybot-strategy.service
systemctl enable simplepolybot-order-executor.service
systemctl enable simplepolybot-settlement.service

# 启动所有服务
systemctl start simplepolybot-market-data.service
systemctl start simplepolybot-strategy.service
systemctl start simplepolybot-order-executor.service
systemctl start simplepolybot-settlement.service
```

#### 验证服务状态

```bash
# 查看所有 SimplePolyBot 服务的状态
systemctl status simplepolybot-*
```

✅ **预期输出**（每个都显示 `active (running)` 并带绿色圆点 `●`）：
```
● simplepolybot-market-data.service - SimplePolyBot Market Data Collector
     Loaded: loaded (/etc/systemd/system/simplepolybot-market-data.service; enabled; vendor preset: enabled)
     Active: active (running) since Thu 2026-04-02 10:00:05 UTC; 30s ago
   Main PID: 12345 (python)
      Tasks: 1 (limit: 4662)
     Memory: 45.2M
        CPU: 1.234s
     CGroup: /system.slice/simplepolybot-market-data.service
             └─12345 /opt/SimplePolyBot/venv/bin/python -m modules.market_data_collector.main

● simplepolybot-strategy.service - SimplePolyBot Strategy Engine
     Loaded: loaded (...; enabled)
     Active: active (running) ...

● simplepolybot-order-executor.service - SimplePolyBot Order Executor
     Loaded: loaded (...; enabled)
     Active: active (running) ...

● simplepolybot-settlement.service - SimplePolyBot Settlement Worker
     Loaded: loaded (...; enabled)
     Active: active (running) ...
```

#### systemd 常用运维命令速查

| 操作 | 命令 |
|------|------|
| 查看某模块日志 | `journalctl -u simplepolybot-market-data -f` |
| 重启某模块 | `systemctl restart simplepolybot-strategy` |
| 停止某模块 | `systemctl stop simplepolybot-order-executor` |
| 查看某模块资源占用 | `systemctl status simplepolybot-settlement` |
| 一次性停止全部 | `systemctl stop simplepolybot-*` |
| 一次性启动全部 | `systemctl start simplepolybot-*` |
| 取消开机自启 | `systemctl disable simplepolybot-*` |

> 💡 从今以后，你再也不需要手动 `bash scripts/start_all.sh` 了。服务器重启后 systemd 会自动拉起所有模块，崩溃了也会在 5 秒后自动恢复。这就是**生产级部署**的标准做法！

---

### 🎯 本章小结 — 部署检查清单

完成以上 7 个步骤后，请逐项确认：

| # | 检查点 | 命令/方式 | 状态 |
|---|--------|----------|------|
| 1 | 项目代码已克隆到 `/opt/SimplePolyBot/` | `ls /opt/SimplePolyBot/modules/` | ☐ |
| 2 | Python 虚拟环境已创建 | `(venv)` 出现在提示符前 | ☐ |
| 3 | 所有 Python 依赖已安装 | `pip list \| wc -l` 显示 > 15 个包 | ☐ |
| 4 | `.env` 文件已填写且权限为 600 | `ls -la .env` 显示 `-rw-------` | ☐ |
| 5 | `.env` 验证脚本全部 OK | 2.3 节第四步的验证脚本 | ☐ |
| 6 | 配置向导已完成 | `config/settings.yaml` 存在且非空 | ☐ |
| 7 | 四个模块均能启动 | `bash scripts/start_all.sh` 全部成功 | ☐ |
| 8 | 日志中有实时数据流入 | `tail -f logs/*.log` 有持续输出 | ☐ |
| 9 | systemd 服务已注册并运行 | `systemctl status simplepolybot-*` 全部 active | ☐ |
| 10 | 服务器重启后自动恢复 | `reboot` 后再次检查第 9 项 | ☐ |

全部打勾？🎉 **恭喜你完成了 SimplePolyBot 的完整生产级部署！**

> 📘 **下一步推荐**：
> - 想了解策略原理 → 阅读 [第 3 章：交易策略详解 ⭐核心](#第-3-章交易策略详解-核心)
> - 想了解每个配置参数的含义 → 阅读 [第 5 章：配置参数完全手册](#第-5-章配置参数完全手册)
> - 想了解日常维护和监控 → 阅读 [第 6 章：日常运维与监控](#第-6-章日常运维与监控)

<!-- CHAPTER_2_CONTENT_END -->

---

## 第 3 章：交易策略详解 ⭐核心

<!-- CHAPTER_3_CONTENT_START -->

> 🎯 **本章目标**：彻底理解 SimplePolyBot 的交易策略是如何工作的——从"它到底在做什么"到"每个参数怎么调"。这是整份手册**最核心、最详细**的章节，请务必仔细阅读。
>
> ⚠️ **前置知识要求**：无需任何金融或编程背景。如果你知道"低买高卖能赚钱"，就足够读懂本章全部内容。

---

### 3.1 策略概述：这个系统到底是做什么的？

#### 3.1.1 一句话解释

SimplePolyBot 是一个 **24 小时不休息的自动化预测市场交易员**。它在 Polymarket 平台上自动买卖"预测代币"，通过数学模型判断价格的"真实价值"，在市场定价偏离时低买高卖赚取差价。

#### 3.1.2 生活化类比

想象你有一个**超级勤奋的朋友**，他的工作是这样的：

| 现实生活中的交易员 | SimplePolyBot 机器人 |
|---|---|
| 👀 用眼睛盯盘看价格变化 | `market_data_collector` 模块通过 WebSocket 实时接收行情 |
| 🧠 用大脑分析趋势（涨了还是跌了？） | `strategy_engine` 模块用 OLS 回归计算买卖信号 |
| ✋ 用手在手机上下单买入/卖出 | `order_executor` 模块向 Polymarket 提交订单 |
| 💰 会计核对盈亏、结算收款 | `settlement_worker` 模块处理市场结算和代币赎回 |

这个"朋友"的优势：
- **不睡觉**：7×24 小时运行，不错过任何机会
- **不被情绪影响**：不会因为恐慌抛售，也不会因为贪婪追高
- **计算速度快**：毫秒级完成分析和决策
- **严格执行纪律**：该止损就止损，该止盈就止盈

#### 3.1.3 目标市场类型

Polymarket 上有多种类型的市场，SimplePolyBot 主要针对以下两类：

##### Binary Markets（二元市场）

最经典的市场类型，回答 Yes/No 问题：

| 市场示例 | YES 代币含义 | NO 代币含义 |
|---|---|---|
| "特朗普会在 2024 年当选总统吗？" | 他会当选 | 他不会当选 |
| "比特币年底会突破 10 万美元吗？" | 会突破 | 不会突破 |
| "某球队会赢得冠军吗？" | 会赢 | 不会赢 |

**代币价格的含义**：
- YES 代币价格 = **0.65** → 市场认为这件事发生的概率是 **65%**
- 如果事件最终发生 → YES 代币价值变为 **$1.00**（赚 $0.35）
- 如果事件最终没有发生 → YES 代币价值变为 **$0.00**（亏 $0.65）

##### Fast Markets（快速市场）⭐ 本系统重点

这是 SimplePolyBot 的**主战场**。以 "Bitcoin Up or Down - 5 Minutes" 为例：

```
┌─────────────────────────────────────────────────────┐
│  📊 Bitcoin Up or Down - 5 Minutes                  │
│                                                     │
│  问题: 从现在起 5 分钟后，比特币价格会上涨还是下跌？   │
│                                                     │
│  规则:                                              │
│  • 结束时的价格 ≥ 开始时的价格 → 解析为 "Up"          │
│  • 结束时的价格 < 开始时的价格 → 解析为 "Down"        │
│  • 价格数据由 Chainlink Oracle 提供（防操纵）         │
│                                                     │
│  特点:                                              │
│  • 每 5 分钟创建一个新的市场实例                      │
│  • 高频滚动，全天候运行                               │
│  • 适合量化策略自动交易                               │
└─────────────────────────────────────────────────────┘
```

**为什么选择 Fast Markets 作为主战场？**

| 优势 | 说明 |
|---|---|
| 🔄 **高频机会** | 每 5 分钟一个新市场 = 每天 ~288 个交易机会 |
| ⏱️ **短周期** | 5 分钟结算，资金周转快，不用等几天几周 |
| 📊 **数据驱动** | 价格由 Chainlink Oracle 提供，数据可靠 |
| 🤖 **机器友好** | 规则明确清晰，非常适合算法交易 |
| 💰 **低门槛** | 单笔交易金额可以很小（几美元起） |

#### 3.1.4 核心盈利逻辑

SimplePolyBot 的赚钱逻辑可以用一句话概括：

> **当市场低估了某个结果的可能性时买入，当价格回归合理区间或事件确定时卖出获利。**

具体来说，系统通过以下步骤实现盈利：

```
步骤 1: 数据收集
  └─ 通过 WebSocket 接收实时价格数据（每秒多次更新）

步骤 2: 趋势分析
  └─ 用 OLS（最小二乘法）回归分析历史价格走势
  └─ 判断当前价格是在上涨趋势还是下跌趋势

步骤 3: 信号生成
  └─ 通过四重过滤机制判断是否应该出手
  └─ 计算信号置信度（0~1 之间，越高越可信）

步骤 4: 安全垫计算
  └─ 根据安全垫公式计算"最大愿意付出的买入价格"
  └─ 确保即使判断失误，亏损也在可控范围内

步骤 5: 下单执行
  └─ 以限价单方式提交订单（只以低于/等于目标价格买入）
  └─ 绝不追高，保持交易纪律

步骤 6: 止损止盈
  └─ 浮亏达到阈值 → 自动止损离场
  └─ 盈利达到目标 → 自动止盈锁定利润

步骤 7: 结算收款
  └─ 市场结算后，获胜代币价值变为 $1.00
  └─ 自动赎回 USDC 到账户
```

---

### 3.2 安全垫机制 (Safety Cushion) ⭐⭐ 最重要

> 💡 **为什么这一节最重要？** 安全垫是整个系统的"保命符"。它决定了你在每次交易中愿意承担多大风险。理解并正确配置安全垫参数，是长期稳定盈利的关键。

#### 3.2.1 公式详解

安全垫的核心公式如下：

```
Total Cushion = Base Cushion + α × |K| × √Time Remaining
```

让我们用**开车跟车**的生活化类比来理解每一项：

| 公式项 | 类比 | 含义 | 在交易中的意义 |
|---|---|---|---|
| **Base Cushion**（基础垫子） | 最小安全车距 | 不管什么情况都保留的安全距离 | 固定的安全边际，确保不会以接近市价的价格买入 |
| **α (Alpha)** | 路况系数 | 根据路况动态调整车距 | 根据市场波动程度调整缓冲空间的大小 |
| **\|K\|**（斜率绝对值） | 当前车速 | 车速越快需要的刹车距离越长 | 价格变动越剧烈，需要更大的安全边际 |
| **√Time Remaining**（剩余时间平方根） | 距目的地的距离 | 快到了就可以跟紧点 | 时间越充裕，越有耐心等待更好的价格 |
| **Total Cushion**（总安全垫） | 最终决定的车距 | 实际保持的距离 | 最终决定的"最大买入价"与"市价"之间的差距 |

**⚠️ 重要修复说明（Bug #1 + #2 + #3 已修复）**：

旧版公式存在**量纲混用问题**——将 BTC 绝对价格（如 $67,000）与 Polymarket 概率价格（0-1 范围）直接相减，导致计算出无意义的结果。**当前版本已完全修正此问题**，所有计算统一在**概率空间（0-1）**内进行。

**最大买入价格的修正后公式**：

```
max_buy = best_ask × (1 - cushion) × decay_factor
```

其中：
- **best_ask**: Polymarket 合约最佳卖价（概率空间，0-1 范围）
- **cushion**: Total Safety Cushion（概率空间）
- **decay_factor**: 时间衰减因子（见下方详细说明）

这意味着：系统以**订单簿最佳卖价为基准**，按安全垫比例打折后再乘以时间衰减因子，得到最终愿意出的最高买入价。如果最佳卖价是 0.53，总安全垫是 0.047，衰减因子是 0.75，那么系统最高只愿意出 `0.53 × 0.953 × 0.75 ≈ 0.379` 的价格买入。

> 🎯 **核心思想**：永远不要追高！只在价格足够便宜的时候才出手。且所有计算均在概率空间完成，不再混入 BTC 绝对价格。

#### 3.2.1.1 时间衰减因子 (time_decay_factor)

时间衰减因子是新引入的关键组件，用于根据剩余时间动态调节买入意愿：

```
decay_factor = 0.5 + 0.5 × (time_remaining / FAST_MARKET_DURATION)
```

其中 `FAST_MARKET_DURATION = 300 秒`（5 分钟 Fast Market 的总时长）。

| 剩余时间 | time_remaining / 300 | decay_factor | 行为解读 |
|---|---|---|---|
| **300s（刚开始）** | 1.0 | **1.00** | 最激进：市场刚开盘，时间充裕，可以等待更好的价格 |
| **150s（一半）** | 0.5 | **0.75** | 中等：趋势逐渐明朗，适当提高参与度 |
| **60s（接近结束）** | 0.2 | **0.60** | 偏保守：时间不多，但仍有操作空间 |
| **10s（快结束）** | 0.033 | **0.52** | 最保守：临近结算，不确定性极高，大幅压低出价 |

**设计理念**：
- 刚开始时（decay ≈ 1.0）：不急于入场，因为还有大量时间观察市场
- 接近结束时（decay → 0.5）：即使想买也必须极度保守，因为 Chainlink Oracle 价格已基本确定，此时高价买入几乎无利润空间

#### 3.2.2 参数影响对照表

为了让你直观感受每个参数对最终决策的影响，我们来看一组数值对比。

**场景假设**：best_ask = **0.53**，斜率 K = **0.008**，剩余时间 = **60 秒**

| 参数 | 默认值 | 改为 | Total Cushion 变化 | decay 变化 | 最大买入价变化 | 影响解读 |
|---|---|---|---|---|---|---|
| **base_cushion** | 0.02 | **0.05** | 0.047 → **0.077** (+0.03) | 不变 | 0.379 → **0.366** (-0.013) | 更保守，少花钱买，但也可能错过更多机会 |
| **alpha (α)** | 0.5 | **0.7** | 0.047 → **0.061** (+0.014) | 不变 | 0.379 → **0.370** (-0.009) | 波动市场更谨慎，buffer 增加 40% |
| **slope_k (\|K\|)** | 0.008 | **0.020** | 0.047 → **0.086** (+0.039) | 不变 | 0.379 → **0.345** (-0.034) | 大幅波动时大幅降低买入价 |
| **time_remaining** | 60s | **20s** | 0.047 → **0.033** (-0.014) | 0.60→**0.533** | 0.379 → **0.270** (-0.109) | 时间紧迫时安全垫和衰减双重压缩出价 |

> 💡 **注意**：与旧版公式不同，新公式中 `time_remaining` 同时影响 **Total Cushion**（通过 √Time 项）和 **decay_factor**（通过线性比例），因此对最终买入价的影响比以前更显著。

**逐行解读**：

1. **base_cushion 从 0.02 调大到 0.05**：
   - 安全垫增加了 0.03（从 4.7 分钱增加到 7.7 分钱）
   - 最大买入价从 0.379 降到 0.366（更便宜才买）
   - **后果**：更安全，但可能因为出价太低而错过很多交易机会

2. **alpha 从 0.5 调大到 0.7**：
   - buffer 部分增加了 40%（因为 alpha 是 buffer 的乘数）
   - 这意味着系统对价格波动更加敏感
   - **后果**：在高波动市场中表现更好，但在平稳市场中可能过于保守

3. **斜率 K 从 0.008 增加到 0.020**（价格变动更剧烈）：
   - 安全垫几乎翻倍（+0.039），这是所有参数中影响最大的
   - **原因**：斜率越大说明价格变动越快，风险越高，所以需要更大的安全边际
   - **后果**：在剧烈波动的市场中保护你的资金，但也意味着更少成交

4. **剩余时间从 60 秒减少到 20 秒**：
   - 安全垫变小了（因为 √20 < √60），同时 decay_factor 从 0.60 降到 0.533
   - **原因**：时间紧迫时，双重效应压缩最终出价——安全垫缩小但衰减因子也降低
   - **后果**：临近结算时出价大幅降低（-0.109），反映临近结算的高不确定性风险

#### 3.2.3 完整计算场景举例 ⭐⭐⭐

让我们用一个真实的 Fast Market 场景来走一遍完整的计算流程。

**场景设定**："Bitcoin Up or Down - 5 Minutes" 市场

```
【已知条件】
├─ BTC 当前价格 (Current Price):   67052 USD
├─ BTC 起始价格 (Start Price):     67000 USD
├─ Polymarket best_ask:            0.53（概率空间）
├─ OLS 回归斜率 K:                 0.008（价格在缓慢上涨）
├─ R² 决定系数:                    0.72（趋势拟合度良好）
├─ 剩余时间:                       45 秒
└─ 参数设置: base_cushion=0.02, alpha=0.5
```

**逐步计算过程**：

```
第一步：检查价格差额（BTC 绝对价格空间）
  ┌──────────────────────────────────────────┐
  │ 价格差额 = |BTC当前价 - BTC起始价|         │
  │         = |67052 - 67000|                │
  │         = 52 USD                         │
  │                                          │
  │ ✅ 52 ≥ 0.01（最小阈值）→ 有足够的价格变动空间 │
  └──────────────────────────────────────────┘

第二步：检查时间窗口
  ┌──────────────────────────────────────────┐
  │ 剩余时间 = 45 秒                          │
  │                                          │
  │ 有效窗口范围: [10秒, 100秒]               │
  │                                          │
  │ ✅ 10 ≤ 45 ≤ 100 → 时间合适              │
  │                                          │
  │ ❌ 如果 >100s: 太早，趋势还不明确          │
  │ ❌ 如果 <10s:  太晚，来不及成交            │
  └──────────────────────────────────────────┘

第三步：检查趋势拟合度 (R²)
  ┌──────────────────────────────────────────┐
  │ R² = 0.72                                │
  │                                          │
  │ R² 的含义:                               │
  │ • R² = 1.0 → 所有点完美落在趋势线上       │
  │ • R² = 0.5 → 一半的变异可以被趋势解释      │
  │ • R² = 0.0 → 趋势线完全无法解释数据        │
  │                                          │
  │ ✅ 0.72 ≥ 0.5（最低要求）→ 趋势可信度较高  │
  └──────────────────────────────────────────┘

第四步：计算安全垫（概率空间）
  ┌──────────────────────────────────────────┐
  │                                          │
  │ ④ Base Cushion = 0.02（固定值，概率空间）   │
  │                                          │
  │ ⑤ Buffer Cushion = α × |K| × √Time       │
  │    = 0.5 × |0.008| × √45                 │
  │    = 0.5 × 0.008 × 6.708                 │
  │    = 0.027                                │
  │                                          │
  │ ⑥ Total Cushion = Base + Buffer          │
  │    = 0.02 + 0.027                         │
  │    = 0.047（概率空间）                     │
  │                                          │
  └──────────────────────────────────────────┘

第五步：计算最大买入价格（修正后公式 ⭐）
  ┌──────────────────────────────────────────┐
  │                                          │
  │ ⑦ 时间衰减因子:                           │
  │    decay = 0.5 + 0.5 × (45 / 300)        │
  │         = 0.5 + 0.5 × 0.15               │
  │         = 0.5 + 0.075 = 0.575             │
  │                                          │
  │ ⑧ 新公式计算:                             │
  │    max_buy = best_ask × (1 - cushion) × decay │
  │            = 0.53 × (1 - 0.047) × 0.575  │
  │            = 0.53 × 0.953 × 0.575        │
  │            = 0.290                        │
  │                                          │
  │ ⑨ 取整范围限制:                           │
  │    max(0.01, min(0.99, 0.290)) = 0.29    │
  │                                          │
  │    （确保价格在合法范围内：0.01 ~ 0.99）   │
  │                                          │
  │ ⚠️ 注意: 结果 0.29 远低于旧公式的 0.47，   │
  │    因为新公式引入了 decay_factor，且       │
  │    所有计算在概率空间完成                  │
  │                                          │
  └──────────────────────────────────────────┘

第六步：计算信号置信度（Sigmoid 归一化版 ⭐）
  ┌──────────────────────────────────────────┐
  │                                          │
  │ Confidence = R²×0.5 + sigmoid_斜率×0.3 + sigmoid_差额×0.2 │
  │                                          │
  │ R² 权重 50%（不变）:                      │
  │   0.72 × 0.5 = 0.36                       │
  │                                          │
  │ 斜率权重 30%（Sigmoid 归一化）:           │
  │   normalized_slope = sigmoid(50×(0.002-0.002)) │
  │                   = sigmoid(0) = 0.50     │
  │   0.50 × 0.3 = 0.15                      │
  │                                          │
  │ 差额权重 20%（Sigmoid 归一化）:           │
  │   normalized_diff = sigmoid(0.02×(52-50)) │
  │                  = sigmoid(0.04) ≈ 0.51   │
  │   0.51 × 0.2 = 0.10                      │
  │                                          │
  │ 置信度 = 0.36 + 0.15 + 0.10 = 0.61        │
  │                                          │
  │ ✅ 0.61 ≥ 0.6（最低要求）→ 信号有效        │
  │                                          │
  │ 💡 对比旧版: 旧公式给出 0.64（因截断饱和），│
  │    新版给出 0.51（更真实的区分度）          │
  │                                          │
  └──────────────────────────────────────────┘

第七步：安全垫比较检查（Bug #3 修复 ⭐）
  ┌──────────────────────────────────────────┐
  │                                          │
  │ 检查: price_difference < safety_cushion?  │
  │                                          │
  │ ⚠️ 这里的比较涉及量纲转换:               │
  │   price_difference = 52 USD（绝对价格空间）│
  │   safety_cushion = 0.047（概率空间）       │
  │                                          │
  │ 实际实现中，此检查在 determine_action()   │
  │ 内部处理量纲一致性后执行。若价格变动幅度   │
  │ 不足以覆盖安全垫成本，则拒绝交易。         │
  │                                          │
  │ ✅ 本场景: 价格变动足够大 → 通过检查      │
  │                                          │
  └──────────────────────────────────────────┘
```

**最终决策结果**：

```
┌──────────────────────────────────────────────┐
│  📊 信号动作: BUY（买入）                      │
│  📈 方向: UP（价格上涨中，买 YES 代币）         │
│  💰 最大买入价格: 0.29（即不超过 29 美分买入）   │
│  🎯 置信度: 61%（中等，Sigmoid 归一化后更真实） │
│                                              │
│  📝 执行指令:                                 │
│  向 Polymarket CLOB 提交限价买单:             │
│  • token: Bitcoin Up YES                    │
│  • price: ≤ 0.29                            │
│  • size: [根据 order_sizes 配置]             │
│  • type: GTC (Good-Til-Cancelled)           │
│                                              │
│  ⚠️ 与旧版对比:                               │
│  • 旧版 max_buy: 0.47（量纲混用，虚高）        │
│  • 新版 max_buy: 0.29（概率空间，真实）        │
│  • 旧版置信度: 0.64（硬编码截断饱和）          │
│  • 新版置信度: 0.61（Sigmoid 平滑归一化）     │
└──────────────────────────────────────────────┘
```

**如果参数不同会怎样？**

```
┌─ 场景 A: 保守模式 (base_cushion=0.05) ─────────┐
│                                                  │
│  Total = 0.05 + 0.027 = 0.077                   │
│  decay = 0.575（不变）                            │
│  Max Buy = 0.53 × (1-0.077) × 0.575             │
│         = 0.53 × 0.923 × 0.575 = 0.281 → 取整 0.28 │
│                                                  │
│  对比默认模式:                                   │
│  • 买入价更低 (0.28 vs 0.29)                    │
│  • 更安全，但成交概率下降                        │
│  • 适合: 高波动市场或新手阶段                    │
│                                                  │
└──────────────────────────────────────────────────┘

┌─ 场景 B: 激进模式 (alpha=0.7) ─────────────────┐
│                                                  │
│  Buffer = 0.7 × 0.008 × 6.708 = 0.038           │
│  Total = 0.02 + 0.038 = 0.058                   │
│  Max Buy = 0.53 × (1-0.058) × 0.575             │
│         = 0.53 × 0.942 × 0.575 = 0.287 → 取整 0.29 │
│                                                  │
│  对比默认模式:                                   │
│  • buffer 增大 40%，但新公式下总价差增幅有限      │
│  • 成交概率略有提升                              │
│  • 适合: 对模型有高度信心的场景                  │
│                                                  │
└──────────────────────────────────────────────────┘

┌─ 场景 C: 时间充裕 (time_remaining=150s) ────────┐
│                                                  │
│  Total = 0.02 + 0.5×0.008×√150 = 0.02+0.049=0.069│
│  decay = 0.5 + 0.5×(150/300) = 0.5+0.25 = 0.75  │
│  Max Buy = 0.53 × (1-0.069) × 0.75              │
│         = 0.53 × 0.931 × 0.75 = 0.370 → 取整 0.37 │
│                                                  │
│  解读: 时间充裕时 decay_factor 升高至 0.75，      │
│   系统更愿意以较高价格入场（0.37 vs 默认 0.29）， │
│   因为还有充足时间观察和调整                     │
│                                                  │
└──────────────────────────────────────────────────┘
```

#### 3.2.4 各参数调优指南

##### base_cushion（基础安全垫）调参建议

| 设为 | 适合场景 | 后果 | 新手推荐？ |
|---|---|---|---|
| **0.01 ~ 0.02** | 激进 / 低波动市场 | 买入价接近市价，容易成交，但利润薄，一旦判断错误亏损较快 | ❌ 不推荐新手 |
| **0.02 ~ 0.05** | 平衡 / 一般市场 | **兼顾安全性和成交概率，是最常用的范围** | ✅ **强烈推荐** |
| **0.05 ~ 0.10** | 保守 / 高波动市场 | 买入价远低于市价，非常安全，但可能长时间无法成交 | ⚠️ 适合学习期 |

##### alpha（趋势跟随强度）调参建议

| 设为 | 适合场景 | 后果 | 新手推荐？ |
|---|---|---|---|
| **0.1 ~ 0.3** | 极度保守 | 几乎不受价格波动影响，base_cushion 主导决策 | ❌ 可能过于保守 |
| **0.3 ~ 0.5** | 稳健操作 | **适度跟随波动，buffer 占比合理** | ✅ **推荐默认范围** |
| **0.5 ~ 0.7** | 积极跟随 | 大幅波动时显著降低买入价，保护性强 | ⚠️ 需要一定经验 |
| **0.7 ~ 1.0** | 激进追涨 | buffer 可能非常大，导致几乎不买入 | ❌ 不推荐 |

---

### 3.3 信号生成器 (Signal Generator) ⭐

> 🧠 信号生成器是整个系统的"大脑"。它接收原始市场数据，经过层层过滤和计算，最终输出一个明确的交易指令：BUY（买）、WAIT（等）、还是 HOLD（持有）。

#### 3.3.1 三种信号类型

| 信号 | 含义 | 触发条件 | 系统行为 |
|---|---|---|---|
| **🟢 BUY** | 发出买入指令 | 四重过滤**全部通过** | 向 CLOB 提交限价买单，价格 ≤ Max Buy Price |
| **🟡 WAIT** | 等待观望 | 任一过滤条件**未满足** | 不执行任何操作，继续监控市场数据 |
| **🔵 HOLD** | 持有现有仓位 | 已有持仓且无需调整 | 保持现状，等待止损/止盈触发 |

**信号流转图**：

```
                ┌──────────────────┐
                │   接收市场数据     │
                │ (价格/时间/成交量) │
                └────────┬─────────┘
                         │
                         ▼
                ┌──────────────────┐
                │  OLS 回归分析     │
                │  计算趋势线和指标  │
                └────────┬─────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │    四重过滤机制        │
              │  (详见 3.3.2 节)      │
              └────────┬─────────────┘
                       │
           ┌───────────┼───────────┐
           │ 全部通过    │ 任一未通过  │ 已有仓位
           ▼           ▼           ▼
        🟢 BUY       🟡 WAIT     🔵 HOLD
           │           │           │
           ▼           ▼           ▼
      提交限价单    继续监控     保持不变
```

#### 3.3.2 四重过滤机制

这是信号生成的核心质量控制环节。**必须全部通过才会发出 BUY 信号**，任何一项不达标都会导致 WAIT。

```
                    ┌─────────────────────────┐
    市场数据输入 ──▶│   过滤 1: 时间窗口检查    │── 失败 → 🟡 WAIT
                    │   10秒 ≤ 剩余时间 ≤ 100秒  │
                    └───────────┬─────────────┘
                                │ ✅ 通过
                    ┌───────────▼─────────────┐
                    │   过滤 2: 价格差额检查    │── 失败 → 🟡 WAIT
                    │   |当前价 - 起始价| ≥ 0.01 │
                    └───────────┬─────────────┘
                                │ ✅ 通过
                    ┌───────────▼─────────────┐
                    │   过滤 3: 趋势拟合度     │── 失败 → 🟡 WAIT
                    │   R² 决定系数 ≥ 0.5      │
                    └───────────┬─────────────┘
                                │ ✅ 通过
                    ┌───────────▼─────────────┐
                    │   过滤 4: 信号置信度     │── 失败 → 🟡 WAIT
                    │   Confidence ≥ 0.6       │
                    └───────────┬─────────────┘
                                │ ✅ 全部通过
                                ▼
                           🟢 BUY 信号!
```

**每层过滤的通俗解释**：

##### 过滤 1：时间窗口（10秒 ~ 100秒）

| 剩余时间 | 状态 | 原因 |
|---|---|---|
| **> 100 秒** | ❌ 太早 | 市场刚开始，价格还没形成明显趋势，OLS 回归的数据点太少，预测不可靠 |
| **10 ~ 100 秒** | ✅ 合适 | 有足够的历史数据做回归分析，同时还有足够的时间完成交易 |
| **< 10 秒** | ❌ 太晚 | 即使发出信号，订单也可能来不及在市场结算前成交 |

> 💡 **类比**：就像烤蛋糕——太早打开烤箱看会失败（没熟），太晚拿出来会烤焦。只有在合适的时机才能做出完美判断。

##### 过滤 2：价格差额（≥ 0.01）

| 价格差额 | 状态 | 原因 |
|---|---|---|
| **< 0.01（1 美分）** | ❌ 差距太小 | 价格几乎没有变动，没有足够的利润空间覆盖手续费和滑点成本 |
| **≥ 0.01** | ✅ 有空间 | 存在至少 1 美分的价差，扣除费用后仍可能有正收益 |

> 💡 **注意**：0.01 是最小差额阈值。在实际交易中，你需要更大的差额才能获得有意义的利润（通常建议 ≥ 0.03 ~ 0.05）。

##### 过滤 3：R² 趋势拟合度（≥ 0.5）

**R²（R-squared，决定系数）是什么？**

想象你在一张纸上画散点图（每个点代表某一时刻的价格），然后画一条"最佳拟合直线"穿过这些点。R² 就是衡量这些点**有多贴近这条直线**的指标。

| R² 值 | 含义 | 散点图样子 |
|---|---|---|
| **1.0** | 完美拟合 | 所有点都在直线上 |
| **0.8** | 很好拟合 | 点紧密聚集在直线周围 |
| **0.5** | 一般拟合 | **最低接受标准** — 点大致沿直线分布，但有明显分散 |
| **0.3** | 较差拟合 | 点很分散，直线只能解释部分趋势 |
| **0.0** | 无拟合 | 完全随机，直线毫无意义 |

```
R² = 0.85 (优秀)          R² = 0.55 (及格)          R² = 0.25 (不及格)

    price                      price                      price
      │                          │                          │
   0.56├──●                       │                     ●         ●
      │   ＼                      │                  ●     ＼   ●
   0.54├──－●                     │               ●   ＼  ―――●
      │     ＼                    │            ●      ＼    ＼
   0.52├―――――●←趋势线             │         ●   ―――――――●      ＼
      │       ＼                  │      ●                    ＼●
   0.50├―――――――●                  │   ●―――――――――――――――――――――――●←趋势线
      │         ＼                │
   0.48├―――――――――●               │
      │                           │
      └―――――――――→ time           └―――――――――→ time           └――→ time
```

> 💡 **为什么要求 R² ≥ 0.5？** 因为低于 0.5 意味着"趋势线"的解释力还不如抛硬币。在这种情况下根据趋势做决策，和在黑暗中瞎猜没什么区别。

##### 过滤 4：信号置信度（≥ 0.6）

置信度是一个综合评分（0 ~ 1），由三个维度加权计算得出（详见 3.3.3 节）。它是四道过滤的**最后一道关卡**，确保只有高质量的信号才会被执行。

#### 3.3.3 置信度计算公式

```
Confidence = R² × 0.5 + normalized_slope × 0.3 + normalized_diff × 0.2
```

**⚠️ 重要修复说明（Bug #4 已修复）**：

旧版归一化方法存在**严重缺陷**——使用 `min(x × N, 1.0)` 硬编码截断，导致典型 BTC 市场数据下斜率系数**总是饱和到 1.0**，丧失区分能力。

**当前版本已改用 Sigmoid 函数进行平滑归一化**，确保典型值落在 **[0.3, 0.7]** 的敏感区间内，提供真实的信号质量区分度。

**三个组成部分**：

| 组成部分 | 权重 | 含义 | 为什么重要 |
|---|---|---|---|
| **R²（决定系数）** | **50%** | 趋势线的可靠性 | 权重最高——如果趋势本身不可信，其他都没意义 |
| **Sigmoid 归一化斜率** | **30%** | 价格变化的强度（平滑映射） | 斜率越大说明趋势越强，信号越值得关注 |
| **Sigmoid 归一化价格差额** | **20%** | 实际价格变动的幅度（平滑映射） | 差额越大意味着潜在利润空间越大 |

**Sigmoid 归一化处理（Bug #4 修复版）**：

为了让不同量纲的指标可以在同一公式中比较，同时避免硬编码截断导致的饱和问题，采用 Sigmoid 函数进行平滑归一化：

```python
def _sigmoid(x: float) -> float:
    """数值稳定的 Sigmoid 实现"""
    if x > 500: return 1.0   # 防止上溢
    if x < -500: return 0.0  # 防止下溢
    return 1.0 / (1.0 + math.exp(-x))

# 斜率归一化：Sigmoid(50 × (abs_slope - 0.002))
#   - 中心点选为 0.002（BTC 典型斜率中位数）
#   - 缩放因子 50 控制曲线陡峭度
#   - 典型 abs_slope ∈ [0.0005, 0.005] → 输出 ∈ [0.27, 0.73]
normalized_slope = _sigmoid(50 * (abs_slope - 0.002))

# 价格差额归一化：Sigmoid(0.02 × (price_diff - 50))
#   - 中心点选为 50 USD（BTC 5分钟典型价格变动）
#   - 缩放因子 0.02 控制 USD→概率空间的映射灵敏度
#   - 典型 price_diff ∈ [10, 200] → 输出 ∈ [0.35, 0.95]
normalized_difference = _sigmoid(0.02 * (price_difference - 50))
```

**Sigmoid 参数选择理由**：

| 参数 | 值 | 选择理由 |
|---|---|---|
| **斜率中心点** | 0.002 | BTC 5 分钟窗口 OLS 回归的典型斜率中位数 |
| **斜率缩放因子** | 50 | ±0.01 斜率偏移 → ±0.25 输出变化，确保敏感区分 |
| **差额中心点** | 50 USD | BTC 正常波动范围的中等水平 |
| **差额缩放因子** | 0.02 | ±50 USD 偏移 → ±0.5 输出变化，覆盖极端场景 |

**完整计算示例（修复后）**：

```
已知:
  R² = 0.72
  斜率 K = 0.008
  价格差额 = 52 USD

计算:

① R² 部分（不变）:    0.72 × 0.5 = 0.36

② 斜率部分（Sigmoid 归一化）:
   原始值: 0.008
   中心化: 0.008 - 0.002 = 0.006
   缩放:   50 × 0.006 = 0.30
   Sigmoid: sigmoid(0.30) ≈ 0.574（在敏感区间！）
   加权:   0.574 × 0.3 = 0.17

   💡 对比旧版: min(0.008×1000, 1.0) = min(8.0, 1.0) = 1.0（饱和！）
      新版给出 0.574，保留了真实区分度

③ 差额部分（Sigmoid 归一化）:
   原始值: 52 USD
   中心化: 52 - 50 = 2
   缩放:   0.02 × 2 = 0.04
   Sigmoid: sigmoid(0.04) ≈ 0.510（接近中心点）
   加权:   0.510 × 0.2 = 0.10

④ 总置信度:  0.36 + 0.17 + 0.10 = 0.63

✅ 0.63 ≥ 0.6 → 通过置信度过滤!

💡 关键改进:
   旧版结果: 0.36 + 0.30 + 0.04 = 0.70（斜率饱和虚高）
   新版结果: 0.36 + 0.17 + 0.10 = 0.63（更真实的评估）
   差异来源: 斜率从 1.0（饱和）降到 0.57（真实）
```

#### 3.3.4 方向判断 (UP / DOWN)

确定了要买入之后，还需要决定**买哪个方向的代币**：

| 条件 | 方向 | 操作 | 代币类型 |
|---|---|---|---|
| **当前价格 > 起始价格** | **UP ↑** | 买 **YES** 代币 | 赌"价格上涨/结果发生" |
| **当前价格 < 起始价格** | **DOWN ↓** | 买 **NO** 代币 | 赌"价格下跌/结果不发生" |
| **当前价格 = 起始价格** | 无方向 | 通常不触发 BUY | 价格没变，无趋势可循 |

**Fast Market 中的具体应用**：

对于 "Bitcoin Up or Down - 5 Minutes" 市场：
- 判断为 **UP** → 买入 **Up-YES** 代币（赌 BTC 价格会涨）
- 判断为 **DOWN** → 买入 **Down-YES** 代币（赌 BTC 价格会跌）

> 💡 **注意**：在 Fast Market 中，UP 和 DOWN 是两个独立的代币。你不能同时持有两个方向的代币（那样无论如何都会亏掉一边的成本）。

---

### 3.4 止损止盈机制

> 🛡️ 止损止盈是你的"自动驾驶保险系统"。它确保即使在你不看盘的时候，系统也能自动保护你的资金或锁定利润。

#### 3.4.1 功能概览

| 功能 | 触发条件 | 系统行为 | 配置路径 |
|---|---|---|---|
| **🔴 自动止损** | 浮亏 ≥ stop_loss_percentage | 立即卖出持仓，止损离场 | `strategy.stop_loss_take_profit.stop_loss_percentage` |
| **🟢 自动止盈** | 盈利 ≥ take_profit_percentage | 立即卖出持仓，锁定利润 | `strategy.stop_loss_take_profit.take_profit_percentage` |

**工作流程**：

```
买入成交后开始监控
        │
        ▼
  ┌─────────────────┐
  │  实时计算盈亏 %   │
  │  盈亏 = (当前价 - 买入价) / 买入价 × 100%
  └────────┬────────┘
           │
     ┌─────┴─────┐
     ▼           ▼
  盈利 ≥ 目标   亏损 ≥ 限额
     │           │
     ▼           ▼
  🟢 止盈!     🔴 止损!
  卖出锁定利润   卖出控制损失
```

#### 3.4.2 三档参数建议对照表

| 档位 | 止损线 | 止盈线 | 止盈/止损比 | 适合场景 | 特点 |
|---|---|---|---|---|---|
| 🟢 **保守档** | 5% | 15% | **3:1** | 学习阶段、高波动市场 | 容错率高，即使胜率 33% 也能保本 |
| 🟡 **平衡档** | 10% | 20% | **2:1** | **默认推荐** | 兼顾风控与收益，适合大多数用户 |
| 🔴 **激进档** | 15% | 30% | **2:1** | 低波动、高确信度市场 | 利润空间大，但对策略准确性要求高 |

**数学原理：为什么止盈/止损比很重要？**

假设你的策略胜率为 **40%**（即 10 次交易中 4 次盈利 6 次亏损）：

```
使用 保守档 (止损5%, 止盈15%, 比例 3:1):
  4次盈利: 4 × (+15%) = +60%
  6次亏损: 6 × (-5%)  = -30%
  净收益: +30% ✅ 正期望!

使用激进档 (止损15%, 止盈30%, 比例 2:1):
  4次盈利: 4 × (+30%) = +120%
  6次亏损: 6 × (-15%) = -90%
  净收益: +30% ✅ 也是正期望，但波动更大

使用糟糕比例 (止损10%, 止盈10%, 比例 1:1):
  4次盈利: 4 × (+10%) = +40%
  6次亏损: 6 × (-10%) = -60%
  净收益: -20% ❌ 负期望，长期必亏!
```

💡 **专业提示**：止盈/止损比建议**不低于 2:1**。这样即使只有 40% 的胜率也能保持正期望收益。这就是所谓的"截断亏损，让利润奔跑"。

#### 3.4.3 启用与禁用

止损止盈功能可以通过配置开关控制：

```yaml
strategy:
  stop_loss_take_profit:
    enabled: true    # 设为 false 可完全禁用自动止损止盈
    stop_loss_percentage: 0.10    # 10% 止损
    take_profit_percentage: 0.20  # 20% 止盈
```

> ⚠️ **警告**：不建议禁用止损止盈！除非你有充分的理由并且能够实时监控每一笔交易。没有止损保护的交易就像开车不系安全带——平时没事，一出事就是大事。

---

### 3.4.4 时间驱动的价格限制（Bug #7 修复）⭐

> ⏰ **为什么价格限制要由时间驱动？** Fast Market 的核心特征是**时间敏感性**——剩余时间越短，Chainlink Oracle 价格越接近最终结果，市场确定性越高，因此应该允许更高的买入价格来捕捉最后的机会。

#### 时间阶梯设计

```
┌─────────────────────────────────────────────────────────────┐
│              时间驱动价格限制阶梯表                           │
├──────────────┬──────────┬──────────┬─────────────────────────┤
│  剩余时间     │ 基础限制   │ 置信度微调 │ 最终范围               │
├──────────────┼──────────┼──────────┼─────────────────────────┤
│  > 80 秒     │ 0.75     │ ±0.02    │ [0.73, 0.77]           │
│  (刚开始)    │          │          │ 保守：趋势不明朗，避免追高  │
├──────────────┼──────────┼──────────┼─────────────────────────┤
│  > 40 秒     │ 0.85     │ ±0.02    │ [0.83, 0.87]           │
│  (中间阶段)  │          │          │ 适度：趋势逐渐明朗         │
├──────────────┼──────────┼──────────┼─────────────────────────┤
│  > 15 秒     │ 0.90     │ ±0.02    │ [0.88, 0.92]           │
│  (接近结束)  │          │          │ 积极：方向基本确定         │
├──────────────┼──────────┼──────────┼─────────────────────────┤
│  ≤ 15 秒     │ 0.93     │ ±0.02    │ [0.91, 0.95]           │
│  (最后时刻)  │          │          │ 激进：结果几乎确定，追入   │
└──────────────┴──────────┴──────────┴─────────────────────────┘

⚠️ 硬性边界: 最终范围被钳制在 [0.60, 0.98]
   - 下限 0.60: 即使再保守也要保留最低参与度
   - 上限 0.98: 即使再激进也至少留 2% 利润空间
```

#### 置信度微调规则

| 置信度条件 | 微调值 | 说明 |
|---|---|---|
| **confidence ≥ 0.8** | **+0.02** | 高置信信号允许更高出价 |
| **0.5 ≤ confidence < 0.8** | **0** | 标准情况不做调整 |
| **confidence < 0.5** | **-0.02** | 低置信信号进一步压低出价 |

#### 设计理念对比

| 维度 | 旧版（固定阈值） | 新版（时间驱动） |
|---|---|---|
| **驱动因素** | 置信度等级 | **剩余时间（主）+ 置信度（辅）** |
| **阈值数量** | 4 个固定值 | **4 个基础值 × 3 种微调 = 12 种组合** |
| **动态性** | 静态查表 | **随时间连续变化** |
| **适用场景** | 一般市场 | **Fast Market（时间敏感型）** |
| **最终范围** | [0.50, 0.98] | **[0.60, 0.98]**（更合理的下限） |

---

### 3.4.5 determine_action() 完整决策逻辑（含 Bug #3 修复）

> 🔍 `determine_action()` 是信号生成器的**最终裁决者**——所有前置计算的结果汇聚于此，决定是 BUY、WAIT 还是 HOLD。

#### 完整过滤流程（6 重检查）

```
                    ┌─────────────────────────────────┐
        输入 ─────▶│   ① 时间窗口检查                  │── 失败 → 🟡 WAIT
                    │   10s ≤ time_remaining ≤ 100s    │
                    └───────────┬─────────────────────┘
                                │ ✅ 通过
                    ┌───────────▼─────────────────────┐
                    │   ② 价格差额检查                  │── 失败 → 🟡 WAIT
                    │   price_diff ≥ 0.01             │
                    └───────────┬─────────────────────┘
                                │ ✅ 通过
                    ┌───────────▼─────────────────────┐
                    │   ③ R² 趋势拟合度检查              │── 失败 → 🟡 WAIT
                    │   r_squared ≥ 0.5               │
                    └───────────┬─────────────────────┘
                                │ ✅ 通过
                    ┌───────────▼─────────────────────┐
                    │   ④ 置信度检查                    │── 失败 → 🟡 WAIT
                    │   confidence ≥ 0.6              │
                    └───────────┬─────────────────────┘
                                │ ✅ 通过
                    ┌───────────▼─────────────────────┐
                    │   ⑤ 价格限制检查（Bug #7 修复）     │── 失败 → 🟡 WAIT
                    │   max_buy ≤ time_based_limit     │
                    └───────────┬─────────────────────┘
                                │ ✅ 通过
                    ┌───────────▼─────────────────────┐
                    │   ⑥ 安全垫比较（Bug #3 修复 ⭐）    │── 失败 → 🟡 WAIT
                    │   price_diff ≥ safety_cushion    │
                    └───────────┬─────────────────────┘
                                │ ✅ 全部通过
                                ▼
                           🟢 BUY 信号!
```

#### 过滤 ⑥ 详细说明（Bug #3 修复）

这是旧版缺失的关键检查——**确保价格变动幅度足以覆盖安全垫成本**：

```python
# determine_action() 中的关键代码（signal_generator.py 第 285-291 行）
if price_difference < safety_cushion:
    logger.debug(
        "价格差额未超过安全垫（Bug #3 修复）",
        price_difference=price_difference,
        safety_cushion=safety_cushion
    )
    return SignalAction.WAIT
```

**含义**：如果 BTC 价格只变动了 $20（price_diff=20），但安全垫要求 0.047 的概率空间折扣（相当于约 $30+ 的隐含成本），那么这笔交易的期望收益为负，系统拒绝入场。

> 💡 **注意**：此检查涉及 BTC 绝对价格空间与 Polymarket 概率空间的量纲转换。实际实现中，系统内部会进行一致性处理后再执行比较。

---

### 3.4.6 信号流架构图（更新版）

> 🏗️ 展示从原始数据到最终订单的完整链路，包括 Phase 1 新增的 MarketDiscovery、SignalAdapter、RedisPublisher 模块。

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SimplePolyBot 信号流架构                          │
│                         （Phase 1 更新版）                            │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────┐     ┌──────────────┐     ┌──────────────────┐
│              │     │              │     │                  │
│  Gamma API   │────▶│ Market       │────▶│ Signal           │
│  CLOB API    │     │ Discovery    │     │ Adapter          │
│              │     │ (新模块)      │     │ (新模块)          │
└──────────────┘     └──────────────┘     └────────┬─────────┘
                                                   │
                                                   ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────────┐
│              │     │              │     │                  │
│  WebSocket   │────▶│ OLS 回归     │◀────│ TradingSignal    │
│  Market Data │     │ 分析引擎     │     │ (统一数据结构)     │
│  Collector   │     │              │     │                  │
└──────────────┘     └──────┬───────┘     └────────┬─────────┘
                            │                      │
                            ▼                      ▼
                   ┌────────────────┐      ┌──────────────────┐
                   │                │      │                  │
                   │  Signal        │      │  Redis Publisher  │
                   │  Generator     │─────▶│  (新模块)         │
                   │  (四重过滤)     │      │  signal_orders    │
                   │                │      │                  │
                   └───────┬────────┘      └────────┬─────────┘
                           │                        │
                           ▼                        ▼
                   ┌────────────────┐      ┌──────────────────┐
                   │                │      │                  │
                   │  Safety Cushion│      │  Order Executor   │
                   │  Calculator    │      │  (CLOB 订单提交)   │
                   │  (概率空间)     │      │                  │
                   └────────────────┘      └──────────────────┘


═══════════════════════════════════════════════════════════════

统一数据结构: TradingSignal

{
    "signal_id": "sig_20260402_abc123",    // 全局唯一 ID
    "token_id": "0x...",                     // Polymarket 代币 ID
    "market_id": "btc-updown-5m_xxx",       // 市场标识
    "action": "BUY",                         // BUY / WAIT / HOLD
    "side": "BUY",                           // BUY / SELL
    "direction": "UP",                       // UP / DOWN / None
    "price": 0.29,                           // 最大买入价（概率空间）
    "size": 100,                             // 订单大小
    "confidence": 0.61,                      // Sigmoid 归一化置信度
    "strategy": "fast_market",               // 策略类型标识
    "timestamp": 174xxx.xxx,                 // Unix 时间戳

    // 调试/审计字段
    "current_price": 67052.0,                // BTC 当前绝对价格
    "start_price": 67000.0,                  // BTC 周期起始价格
    "price_difference": 52.0,                // 价格差额（USD）
    "max_buy_price": 0.29,                   // 计算出的最大买入价
    "safety_cushion": 0.047,                 // 安全垫（概率空间）
    "slope_k": 0.008,                        // OLS 斜率
    "r_squared": 0.72,                       // R² 决定系数
    "time_remaining": 45.0                   // 剩余时间（秒）
}
```

**新增模块说明**：

| 模块 | 位置 | 功能 | 与原有模块的关系 |
|---|---|---|---|
| **MarketDiscovery** | `shared/market_discovery.py` | 自动发现符合条件的 Fast Market 市场 | 替代手动配置 token_id |
| **SignalAdapter** | `shared/signal_adapter.py` | 将策略信号转换为标准订单格式 | 连接 Strategy Engine ↔ Order Executor |
| **RedisPublisher** | Redis `signal_orders` channel | 异步消息队列，解耦信号生成与订单执行 | 替代直接函数调用 |

### 3.5 策略参数完全对照表

> 📋 本节汇总了 `strategy` 相关的全部 **17 个参数**，是日常调参的速查手册。每个参数都包含：默认值、取值范围、通俗解释、调整后果和实战建议。

#### 3.5.1 安全垫参数（2 个）

| # | 参数路径 | 中文名 | 默认值 | 取值范围 | 一句话功能 |
|---|---|---|---|---|---|
| 1 | `strategy.base_cushion` | 基础安全垫 | **0.02** | 0.01 ~ 0.20 | 无论什么情况都保留的最小安全距离 |
| 2 | `strategy.alpha` | 趋势跟随系数 | **0.5** | 0.1 ~ 1.0 | 价格波动时额外增加的安全缓冲倍数 |

**详细说明**：

**参数 1: strategy.base_cushion**

| 维度 | 内容 |
|---|---|
| **通俗解释** | 就像开车时与前车的"最小安全距离"，不管路况多好都不能小于这个值 |
| **调大的后果** | 买入价更低 → 更安全 → 但成交机会减少 → 可能错过一些小利润的交易 |
| **调小的后果** | 买入价更高 → 更容易成交 → 但安全边际降低 → 亏损风险增大 |
| **新手推荐值** | **0.02 ~ 0.05** |
| **实战举例** | 设为 0.05 时，即使市场价是 0.50，你也只愿意最多付 0.45 买入；设为 0.01 时，你可能愿意付 0.49 买入 |

**参数 2: strategy.alpha**

| 维度 | 内容 |
|---|---|
| **通俗解释** | "路况调节器"——路滑（波动大）就拉大安全距离，路好（波动小）就缩短距离 |
| **调大的后果** | 波动市场中的 buffer 显著增大 → 极端情况下可能几乎不买入 |
| **调小的后果** | 几乎忽略波动因素 → base_cushion 成为主导 → 在剧烈波动时保护不足 |
| **新手推荐值** | **0.3 ~ 0.5** |
| **实战举例** | 当比特币突然暴涨暴跌时（K 值很大），alpha=0.7 会把安全垫拉得很大，防止你在高点接盘 |

#### 3.5.2 最大买入价格参数（4 个）

| # | 参数路径 | 中文名 | 默认值 | 取值范围 | 一句话功能 |
|---|---|---|---|---|---|
| 3 | `strategy.max_buy_prices.default` | 默认最大买入价 | **0.50** | 0.01 ~ 0.99 | 通用情况下的买入价格上限 |
| 4 | `strategy.max_buy_prices.high_confidence` | 高置信度上限 | **0.60** | 0.01 ~ 0.99 | 当信号置信度很高时允许的最高买入价 |
| 5 | `strategy.max_buy_prices.low_volatility` | 低波动上限 | **0.55** | 0.01 ~ 0.99 | 市场平稳时可适当提高的买入价 |
| 6 | `strategy.max_buy_prices.fast_market` | 快速市场上限 | **0.55** | 0.01 ~ 0.99 | Fast Market 专用的买入价格上限 |

**详细说明**：

这组参数构成了一个**分层价格控制系统**。系统会根据当前市场状况自动选择适用的上限：

```
选择逻辑:
  if 置信度 ≥ 0.8 且属于高确信场景:
      使用 high_confidence (0.60)  ← 最宽松
  elif 属于低波动市场:
      使用 low_volatility (0.55)
  elif 属于 Fast Market:
      使用 fast_market (0.55)
  else:
      使用 default (0.50)          ← 最严格
```

| 维度 | 内容 |
|---|---|
| **通俗解释** | 就像给不同场景设置不同的"最高出价"——普通商品砍价狠一点，遇到特别想要的可以适当多出点 |
| **调高的后果** | 更容易成交 → 但单笔潜在亏损增大 |
| **调低的后果** | 更安全 → 但大量信号会因为"出价不够高"而无法成交 |
| **新手推荐值** | 保持默认即可，default=0.50 对新手足够安全 |
| **实战举例** | 如果你发现系统总是 WAIT 从不 BUY，可以把 default 调高到 0.53 ~ 0.55 试试 |

#### 3.5.3 订单大小参数（3 个）

| # | 参数路径 | 中文名 | 默认值 | 取值范围 | 一句话功能 |
|---|---|---|---|---|---|
| 7 | `strategy.order_sizes.default` | 默认订单大小 | **100** | 1 ~ 10000 | 标准情况下的下单数量（单位：代币数量） |
| 8 | `strategy.order_sizes.min` | 最小订单大小 | **10** | 1 ~ 1000 | 单笔交易最少下多少单 |
| 9 | `strategy.order_sizes.max` | 最大订单大小 | **500** | 10 ~ 50000 | 单笔交易最多下多少单（风控硬限制） |

**详细说明**：

| 维度 | 内容 |
|---|---|
| **通俗解释** | 控制"每次出手买多少货"——买太少赚不到钱，买太多一次亏惨 |
| **order_sizes.default** | 日常使用的标准下单量，设为 100 意味着每笔交易买卖 100 个代币 |
| **order_sizes.min** | 防止订单太小（手续费的固定成本会让小额交易无利可图） |
| **order_sizes.max** | 防止一次押注太大（单一交易的绝对损失上限） |
| **调大 default 的后果** | 单笔利润潜力增大 → 但单笔亏损风险也同步增大 |
| **调小 default 的后果** | 更安全 → 但需要更多交易次数才能积累可观利润 |
| **新手推荐值** | default=**50 ~ 100**（按每代币 $0.50 计算，单笔 $25 ~ $50） |
| **实战举例** | 账户余额 $100 时，建议 default=50（单笔约 $25，占总资金 25%）；余额 $1000 时可用 default=200 |

#### 3.5.4 风险管理参数（5 个）

| # | 参数路径 | 中文名 | 默认值 | 取值范围 | 一句话功能 |
|---|---|---|---|---|---|
| 10 | `strategy.risk_management.max_position_size` | 单市场最大持仓 | **500** | 1 ~ 10000 | 在同一个市场上最多持有多少代币 |
| 11 | `strategy.risk_management.max_total_exposure` | 总风险敞口上限 | **1000** | 1 ~ 50000 | 所有持仓的总价值上限（USDC） |
| 12 | `strategy.risk_management.max_daily_loss` | 日最大亏损限额 | **50** | 1 ~ ∞ | 一天内最多亏多少钱就停止交易 |
| 13 | `strategy.risk_management.max_drawdown` | 最大回撤限制 | **0.20** | 0.05 ~ 0.50 | 从峰值回撤多少比例就暂停交易 |
| 14 | `strategy.risk_management.min_balance` | 最小保留余额 | **20** | 1 ~ ∞ | 账户至少保留多少钱不动（应急储备） |

**详细说明**：

**参数 10: max_position_size（单市场最大持仓）**

| 维度 | 内容 |
|---|---|
| **通俗解释** | "不要把鸡蛋放在同一个篮子里"——单个市场的仓位不能太大 |
| **调大的后果** | 单一市场集中度提高 → 该市场判断失误时损失更大 |
| **调小的后果** | 强制分散投资 → 需要同时在多个市场建仓才能用完资金 |
| **新手推荐值** | **200 ~ 500**（不超过总资金的 20%） |
| **实战举例** | 设为 500 意味着在 "BTC Up/Down" 这个市场上最多持有 500 个代币（约 $250） |

**参数 11: max_total_exposure（总风险敞口上限）**

| 维度 | 内容 |
|---|---|
| **通俗解释** | "钱包里最多拿多少钱去冒险"——所有在建仓位的总价值不能超过这个数 |
| **调大的后果** | 可用资金增多 → 但极端情况下最大可能亏损也增大 |
| **调小的后果** | 相当一部分资金闲置 → 收益速度变慢，但安全性提高 |
| **新手推荐值** | 总资金的 **50% ~ 70%**（永远留有余量） |
| **实战举例** | 账户 $1000，设 max_total_exposure=700，意味着最多 $700 在市场中，$300 闲着备用 |

**参数 12: max_daily_loss（日最大亏损限额）⭐ 重要**

| 维度 | 内容 |
|---|---|
| **通俗解释** | "今天最多输这么多，输了就收手"——日级别的熔断机制 |
| **调大的后果** | 允许更大的日内波动 → 但可能出现严重的一天亏损 |
| **调小的后果** | 更早停止交易 → 保护本金，但可能错过下午的反弹机会 |
| **新手推荐值** | 总资金的 **5% ~ 10%** |
| **实战举例** | 账户 $1000，设 max_daily_loss=80，意味着今天累计亏损 $80 后系统自动停止开新仓 |

**参数 13: max_drawdown（最大回撤限制）**

| 维度 | 内容 |
|---|---|
| **通俗解释** | "从最高点跌了多少就该停下来反思"——相对于历史峰值的最大跌幅 |
| **调大的后果** | 允许更深度的回撤 → 可能经历痛苦的连亏期 |
| **调小的后果** | 更早触发保护 → 但可能在正常波动中被误触 |
| **新手推荐值** | **0.15 ~ 0.20**（15% ~ 20%） |
| **实战举例** | 账户从 $1000 涨到 $1200（峰值），之后回落到 $1020（回撤 15%），若 max_drawdown=0.15 则刚好触发暂停 |

**参数 14: min_balance（最小保留余额）**

| 维度 | 内容 |
|---|---|
| **通俗解释** | "压箱底的钱不能动"——无论多么好的机会，都要留这笔钱作为最后防线 |
| **调大的后果** | 更多资金被锁死 → 可用于交易的资金减少 |
| **调小的后果** | 应急储备不足 → 连续亏损后可能无法支付 Gas 费或其他必要开支 |
| **新手推荐值** | 至少 **$20 ~ $50**（覆盖几次 Gas 费 + 最低交易门槛） |
| **实战举例** | 设为 30 意味着账户余额降到 $30 以下时，系统拒绝一切新开仓操作 |

#### 3.5.5 止损止盈参数（3 个）

| # | 参数路径 | 中文名 | 默认值 | 取值范围 | 一句话功能 |
|---|---|---|---|---|---|
| 15 | `strategy.stop_loss_take_profit.enabled` | 止损止盈开关 | **true** | true / false | 是否启用自动止损止盈功能 |
| 16 | `strategy.stop_loss_take_profit.stop_loss_percentage` | 止损百分比 | **0.10** | 0.01 ~ 0.50 | 亏损达到多少比例时自动卖出 |
| 17 | `strategy.stop_loss_take_profit.take_profit_percentage` | 止盈百分比 | **0.20** | 0.01 ~ 1.0 | 盈利达到多少比例时自动卖出 |

**详细说明**：

| 维度 | 内容 |
|---|---|
| **enabled 开关** | 设为 `false` 完全关闭自动止损止盈（**不推荐！**） |
| **stop_loss_percentage** | 0.10 = 亏损 10% 时自动止损。越小越敏感，越大越宽容 |
| **take_profit_percentage** | 0.20 = 盈利 20% 时自动止盈。越小越容易触发（频繁小赚），越大越难触发（追求大赚） |
| **新手推荐值** | 止损 **0.05 ~ 0.10**，止盈 **0.15 ~ 0.20**（保守档） |
| **实战举例** | 以 0.50 价格买入 100 个代币（成本 $50）：止损 10% 意味着价格跌到 0.45 以下时自动卖出（亏 $5）；止盈 20% 意味着价格涨到 0.60 以上时自动卖出（赚 $10） |

---

### 3.6 完整交易决策流程追踪

> 🔍 让我们把前面学到的所有知识串联起来，跟踪一笔交易从"数据输入"到"订单成交"的完整生命周期。

**场景**："Bitcoin Up or Down - 5 Minutes" 市场，剩余时间 45 秒

```
═══════════════════════════════════════════════════════
  🕐 T+0秒 — 数据采集阶段
═══════════════════════════════════════════════════════

  market_data_collector 通过 WebSocket 收到最新数据:
  {
    "token_id": "0xabc... (Bitcoin Up YES)",
    "current_price": 0.52,
    "start_price": 0.50,
    "best_bid": 0.51,
    "best_ask": 0.53,
    "time_remaining": 45,
    "volume_24h": 150000
  }

  → 数据存入 Redis → 发送消息给 strategy_engine


═══════════════════════════════════════════════════════
  🕐 T+0.1秒 — OLS 回归分析
═══════════════════════════════════════════════════════

  strategy_engine 取出最近 N 个价格数据点进行回归:

  时间(s)  价格
  ───────  ─────
  -300     0.495
  -240     0.498
  -180     0.501
  -120     0.508
  -60      0.515
   0       0.520  ← 当前

  OLS 回归结果:
  ├─ 斜率 K = 0.008（每分钟上涨 0.8 美分）
  ├─ R² = 0.72（拟合良好）
  └─ 趋势方向: UP ↑


═══════════════════════════════════════════════════════
  🕐 T+0.2秒 — 四重过滤检查
═══════════════════════════════════════════════════════

  ✅ 过滤1 - 时间窗口: 45秒 ∈ [10, 100] → PASS
  ✅ 过滤2 - 价格差额: |0.52-0.50|=0.02 ≥ 0.01 → PASS
  ✅ 过滤3 - R²拟合度: 0.72 ≥ 0.5 → PASS
  ✅ 过滤4 - 置信度: 0.64 ≥ 0.6 → PASS

  → 四项全部通过! 进入下一步


═══════════════════════════════════════════════════════
  🕐 T+0.3秒 — 安全垫计算
═══════════════════════════════════════════════════════

  Base Cushion  = 0.02
  Buffer        = 0.5 × 0.008 × √45 = 0.027
  Total Cushion = 0.02 + 0.027 = 0.047

  Max Buy Price = 0.52 - 0.047 = 0.473 → 取整 0.47


═══════════════════════════════════════════════════════
  🕐 T+0.4秒 — 风控检查
═══════════════════════════════════════════════════════

  当前总持仓: $350
  max_total_exposure: $1000
  ✅ $350 ≤ $1000 → 未超限, 可以开新仓

  今日已亏损: $12
  max_daily_loss: $50
  ✅ $12 ≤ $50 → 未超限, 可以继续交易

  当前账户余额: $680
  min_balance: $20
  ✅ $680 ≥ $20 → 余额充足


═══════════════════════════════════════════════════════
  🕐 T+0.5秒 — 信号生成 & 发送
═══════════════════════════════════════════════════════

  最终信号:
  {
    "action": "BUY",
    "direction": "UP",
    "token_id": "0xabc... (Bitcoin Up YES)",
    "price": 0.47,
    "size": 100,
    "confidence": 0.64,
    "timestamp": "2026-04-02T10:05:30.500Z"
  }

  → 信号写入 Redis queue: signal_orders
  → order_executor 订阅并收到此消息


═══════════════════════════════════════════════════════
  🕐 T+0.7秒 — 订单执行
═══════════════════════════════════════════════════════

  order_executor 构建 CLOB 订单:

  POST https://clob.polymarket.com/orders
  {
    "token_id": "0xabc...",
    "side": "BUY",
    "price": 0.47,
    "size": 100,
    "type": "GTC"
  }

  Polymarket CLOB 响应:
  {
    "order_id": "0xdef...",
    "status": "live",        ← 订单已在订单簿上
    "filled_size": 0          ← 尚未成交，等待匹配
  }


═══════════════════════════════════════════════════════
  🕐 T+3秒 — 订单成交!
═══════════════════════════════════════════════════════

  WebSocket 推送成交通知:
  {
    "event_type": "order_matched",
    "order_id": "0xdef...",
    "filled_price": 0.47,     ← 以目标价成交!
    "filled_size": 100,
    "total_cost": 47.00        ← 花费 $47 买入 100 个代币
  }

  ✅ 交易成功! 持仓建立完毕。
  → 系统转入持仓监控模式（等待止损/止盈/结算）


═══════════════════════════════════════════════════════
  🕐 T+45秒 — 市场结算
═══════════════════════════════════════════════════════

  Chainlink Oracle 报告:
  结束价格: 0.523 ≥ 起始价格 0.50
  → 结果: UP ✓

  你的代币价值: 100 × $1.00 = $100.00
  你的成本:    100 × $0.47 = $47.00
  你的利润:    $100.00 - $47.00 = **$53.00** 🎉

  settlement_worker 自动赎回 USDC 到账户
```

---

### 🎯 本章小结

| 核心概念 | 一句话总结 | 关键要点 |
|---|---|---|
| **策略概述** | 24 小时自动交易的预测市场机器人 | 主要针对 Fast Market（5 分钟滚动市场） |
| **安全垫公式** | `Total = Base + α × \|K\| × √Time`（概率空间） | 决定了"最多花多少钱买"，是风控的核心 |
| **max_buy 新公式** | `max_buy = best_ask × (1-cushion) × decay` | ⭐ Bug #1+#2 修复：量纲统一到概率空间 |
| **时间衰减因子** | `decay = 0.5 + 0.5 × (time/300)` | ⭐ 新增：时间越短越保守 |
| **六重过滤** | 时间、差额、R²、置信度、价格限制、安全垫比较 | ⭐ Bug #3+#7 修复：新增过滤 ⑤⑥ |
| **Sigmoid 置信度** | `R²×0.5 + sigmoid(斜率)×0.3 + sigmoid(差额)×0.2` | ⭐ Bug #4 修复：不再饱和，典型值 [0.3, 0.7] |
| **时间驱动价格限制** | >80s→0.75, >40s→0.85, >15s→0.90, ≤15s→0.93 | ⭐ Bug #7 修复：替代固定阈值，最终范围 [0.60, 0.98] |
| **止损止盈** | 亏损 X% 止损，盈利 Y% 止盈 | 建议比例不低于 2:1 |
| **信号流架构** | MarketDiscovery → SignalAdapter → RedisPublisher → OrderExecutor | ⭐ Phase 1 新增模块链路 |
| **统一数据结构** | TradingSignal（含调试/审计字段） | 所有模块间传递的标准格式 |

**Bug 修复汇总（Phase 0 + Phase 1）**：

| Bug ID | 问题 | 修复方案 | 影响范围 |
|---|---|---|---|
| #1 | max_buy 混用 BTC 绝对价格与概率价格 | 改为 `best_ask × (1-cushion) × decay` | 安全垫计算 |
| #2 | 缺少 time_decay_factor 时间衰减 | 新增 `decay = 0.5 + 0.5*(time/300)` | 价格公式 |
| #3 | 缺少 price_diff < safety_cushion 检查 | 在 determine_action() 新增过滤 ⑥ | 决策逻辑 |
| #4 | 置信度归一化硬编码截断饱和 | 改用 Sigmoid 函数平滑归一化 | 信号质量评估 |
| #7 | 价格限制使用固定阈值而非时间驱动 | 改为 4 级时间阶梯 + 置信度微调 | 风险控制 |

**新手行动清单**：

- [ ] 理解安全垫公式的每一项含义（⭐ 注意：现在是概率空间）
- [ ] 能够手动完成一次安全垫计算（用 3.2.3 的例子练习）
- [ ] 知道**六重**过滤分别检查什么（旧版是四重）
- [ ] 明白 Sigmoid 置信度是怎么算出来的（⭐ 不再截断饱和）
- [ ] 了解时间驱动的价格限制阶梯表
- [ ] 了解 MarketDiscovery / SignalAdapter / RedisPublisher 三个新模块
- [ ] 设置合理的止损止盈参数（建议先从保守档开始）

> 📘 **下一步推荐**：
> - 想了解各模块的技术细节 → 阅读 [第 4 章：各模块功能手册](#第-4-章各模块功能手册)
> - 想了解如何修改参数配置 → 阅读 [第 5 章：配置参数完全手册](#第-5-章配置参数完全手册)
> - 想了解日常运维操作 → 阅读 [第 6 章：日常运维与监控](#第-6-章日常运维与监控)

<!-- CHAPTER_3_CONTENT_END -->

---

## 第 4 章：各模块功能手册

<!-- CHAPTER_4_CONTENT_START -->

> 💡 **本章导读**：SimplePolyBot 由 4 个核心模块组成，它们像工厂流水线一样协同工作：市场数据收集器负责"看盘"，策略引擎负责"思考"，订单执行器负责"下单"，结算工作器负责"收钱"。本章将逐一介绍每个模块的功能、配置和运维要点。

---

## 4.1 市场数据收集器 (`market_data_collector`)

### 功能概述

市场数据收集器是整个系统的"眼睛"，它的职责非常单一且重要：

- 通过 **WebSocket** 长连接接入 Polymarket CLOB 的 Market Channel
- **实时接收**三类行情数据：订单簿更新（book）、价格变动（price_change）、最新成交价（last_trade_price）
- 将解析后的结构化数据**发布到 Redis Pub/Sub** 的 `market_data` 频道
- 策略引擎订阅该频道即可拿到最新行情

### 架构图

```
Polymarket WebSocket Server
        │ (wss://ws-subscriptions-clob.polymarket.com/ws/market)
        ▼
┌─────────────────────────────┐
│   market_data_collector      │
│  ┌───────────────────────┐  │
│  │    binance_ws.py      │  │ ← WebSocket 连接管理
│  │  ───────────────────  │  │
│  │  ✅ 连接建立与认证     │  │
│  │  ✅ 消息解析与分类     │  │
│  │  ✅ 心跳 PING/PONG    │  │
│  │  ✅ 断线自动重连       │  │
│  └───────────┬───────────┘  │
│              ▼               │
│      Redis Pub/Sub           │ ← 发布到 market_data 频道
└─────────────────────────────┘
```

### 关键配置参数

在 `settings.yaml` 的 `modules.market_data_collector` 节点下配置：

| 参数 | 默认值 | 含义 | 调优建议 |
|------|--------|------|----------|
| `websocket.url` | `wss://ws-subscriptions-clob.polymarket.com/ws/market` | WebSocket 服务端地址 | ⚠️ **不要修改**，这是官方地址 |
| `reconnect_delay` | `5s` | 断线后首次等待重连时间 | 网络不稳定可调大到 `10s` |
| `max_reconnect_attempts` | `10` | 最大重连次数 | 保持默认即可 |
| `ping_interval` | `10s` | 客户端发送心跳间隔 | 保持默认 |
| `pong_timeout` | `10s` | 等待服务端心跳响应的超时时间 | 保持默认 |
| `markets_update_interval` | `60s` | 刷新订阅市场列表的间隔 | 保持默认 |

### 日志解读指南

日志文件位于 `logs/market_data_collector.log`。

**✅ 正常运行日志**：

```
[INFO] WebSocket 连接已建立 wss://ws-subscriptions-clob.polymarket.com/ws/market
[INFO] 成功订阅 12 个资产: [...]
[INFO] 收到 book 更新: token=0xabc, best_bid=0.51, best_ask=0.53
[INFO] 心跳 PONG 正常 (延迟=45ms)
```

含义：一切正常，数据正在持续流入。

**⚠️ 警告日志**：

```
[WARN] WebSocket 连接断开，正在重连... (第 3/10 次)
[WARN] 心跳响应延迟过高: 8500ms (阈值: 10000ms)
[WARN] 订阅资产列表为空，等待下次刷新...
```

含义：网络波动或服务器繁忙，系统正在自动恢复，通常无需人工干预。

**❌ 错误日志**：

```
[ERROR] WebSocket 连接失败: Connection refused (errno 111)
[ERROR] 达到最大重连次数(10)，停止重连
[ERROR] 消息解析异常: JSON decode error at line 23
```

含义：需要检查网络连通性或联系技术支持。

### 断线重连行为

| 阶段 | 说明 |
|------|------|
| **检测方式** | 心跳超时（`pong_timeout` 内未收到 PONG）或连接异常关闭 |
| **重连策略** | 指数退避：5s → 10s → 20s → 40s → ... → 上限由 `max_reconnect_attempts` 控制 |
| **数据恢复** | 重连成功后自动重新订阅所有之前关注的资产 ID，不会丢失订阅 |

---

## 4.2 策略引擎 (`strategy_engine`)

### 功能概述

策略引擎是系统的"大脑"，它做的事情可以概括为：

1. 从 **Redis 订阅** `market_data` 频道，接收收集器推送的实时行情
2. 将价格序列送入 **OLS 线性回归模型**，计算价格趋势
3. 结合 **安全垫算法**计算最大可买入价格
4. 经过**四重过滤**后生成交易信号（BUY / WAIT / HOLD）
5. 将信号**发布到 Redis** 的 `trading_signals` 频道，供订单执行器消费

### 子模块职责

| 子模块 | 对应文件 | 核心职责 |
|--------|----------|----------|
| **信号生成器** | `signal_generator.py` | 价格差额计算 → 方向判断（UP/DOWN）→ 四重过滤 → 置信度评分 |
| **安全垫计算器** | `safety_cushion.py` | Base Cushion（基础安全垫）+ Buffer Cushion（缓冲垫）动态计算 |

### OLS 回归原理（通俗解释）

> 🎯 你不需要成为数学家也能理解这个概念。

**OLS = Ordinary Least Squares（普通最小二乘法）**

想象你在纸上画了一堆散点（代表过去一段时间内的价格），然后你想画一条**最贴合这些点的直线**：

```
价格 ↑
     │    ●
     │      ●
     │   ●     ← 散点 = 历史价格
     │ ●
     │●___________ 斜率 K > 0 → 趋势向上（看涨）
     └────────────→ 时间

     │●
     │  ●
     │    ●     ← 散点 = 历史价格
     │      ●
     │        ↘ 斜率 K < 0 → 趋势向下（看跌）
     └────────────→ 时间
```

- **斜率 K**：直线的倾斜程度 = 价格变化速度。K 为正说明在涨，K 为负说明在跌
- **R²（R-squared）**：散点贴近直线的程度。`1.0` = 完美贴合（趋势很明确），`0.5` = 一般，`0.0` = 完全不相关（纯噪音）

策略引擎用这两个指标来判断："现在的价格趋势是否足够强、足够可信？"

### 信号格式

策略引擎发布到 Redis 的交易信号是一个 JSON 对象：

```json
{
  "action": "BUY",
  "direction": "UP",
  "current_price": 0.52,
  "max_buy_price": 0.47,
  "confidence": 0.64,
  "timestamp": 1700000000.0,
  "token_id": "abc123..."
}
```

| 字段 | 含义 | 示例值 |
|------|------|--------|
| `action` | 操作指令 | `BUY`（买入）/ `WAIT`（观望）/ `HOLD`（持有） |
| `direction` | 预测方向 | `UP`（看涨）/ `DOWN`（看跌） |
| `current_price` | 当前市场价格 | `0.52`（即 52 美分） |
| `max_buy_price` | 安全垫保护下的最高买入价 | `0.47`（低于当前价，留出安全空间） |
| `confidence` | 置信度（0~1） | `0.64`（64% 的把握） |
| `timestamp` | 信号生成时间戳 | Unix 时间戳 |
| `token_id` | 目标代币 ID | Polymarket 的条件代币标识符 |

### 关键配置

在 `settings.yaml` 的 `modules.strategy_engine` 节点下配置：

| 参数 | 默认值 | 含义 |
|------|--------|------|
| `signal_check_interval` | `10s` | 每隔多少秒检查一次是否需要生成新信号 |
| `max_concurrent_orders` | `5` | 同时允许的最大未完成订单数量 |
| `order_timeout` | `30s` | 单笔订单的超时时间 |
| `active_strategies` | `[base_cushion, trend_following]` | 当前启用的策略列表 |
| `min_confidence` | `0.6` | 低于此置信度的信号将被丢弃 |
| `min_volume` | `100` | 最小交易量门槛（单位：份额） |

---

## 4.3 订单执行器 (`order_executor`)

### 功能概述

订单执行器是系统的"手"，负责将策略引擎的决策转化为实际操作：

- 从 **Redis 订阅** `trading_signals` 频道，接收 BUY/WAIT/HOLD 信号
- 根据信号创建**限价单**（指定价格和数量）
- 使用 EIP-712 + API 凭证**签名订单**
- **提交到 Polymarket CLOB API**
- 进入监控循环，追踪订单状态变化：`live` → `matched` → `confirmed`
- 处理取消、部分成交等异常情况

### 订单类型详解

| 类型 | 全称 | 行为 | 推荐使用场景 |
|------|------|------|-------------|
| **GTC** | Good-Til-Cancelled | 一直挂在订单簿上，直到被完全成交或手动取消 | ✅ **默认推荐**，适合大多数情况的标准限价单 |
| **GTD** | Good-Til-Date | 到达指定时间后自动取消 | 事件驱动交易（如体育比赛结束前必须成交） |
| **FOK** | Fill-Or-Kill | 要么全部立即成交，要么全部取消 | 用作市价单替代品，要求"立刻、全部"成交 |
| **FAK** | Fill-And-Kill | 能成交多少先成交多少，剩余部分立即取消 | 允许部分成交的市价单 |

> 💡 新手建议：始终使用 **GTC** 类型，它是可控性最好的订单方式。

### CLOB API 交互流程

```
收到 BUY 信号 (来自 Redis)
        ↓
  创建订单对象
  { tokenID, price, size, side=BUY }
        ↓
  签名订单
  (EIP-712 结构化签名 + API Key 认证)
        ↓
  POST /order 提交到 clob.polymarket.com
        ↓
  返回 orderID → 进入状态监控循环
        ↓
  定期 GET /order/{id} 查询状态
  live → matched → confirmed (终态)
         ↘ cancelled / failed
```

### Gas 管理

Polymarket 运行在 Polygon 链上，下单需要支付少量 Gas：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `max_gas_price` | `100 gwei` | 最高愿意支付的 Gas 单价 |
| `gas_limit_multiplier` | `1.2` | 在预估 Gas 基础上上浮 20%，防止 Gas 不足导致交易失败 |

### 关键配置

在 `settings.yaml` 的 `modules.order_executor` 节点下配置：

| 参数 | 默认值 | 含义 |
|------|--------|------|
| `host` | `https://clob.polymarket.com` | CLOB API 服务地址 |
| `chain_id` | `137` | Polygon 主网链 ID |
| `api_timeout` | `30s` | 单次 API 请求超时时间 |
| `default_order_type` | `GTC` | 默认使用的订单类型 |
| `max_order_age` | `3600s` | 订单最长存活时间（超过自动取消） |
| `cancel_on_error` | `true` | 出现错误时是否自动取消待处理订单 |

---

## 4.4 结算工作器 (`settlement_worker`)

### 功能概述

结算工作器是系统的"会计"，负责在市场出结果后把钱收回来：

- **定期轮询**检查已结算的市场（即事件已有最终结果）
- 对**获胜仓位**调用 CTF 合约的 `redeem()` 方法进行代币赎回
- 将赢得的 **USDC.e** 赎回到你的钱包
- 追踪所有持仓的历史记录
- 支持批量处理以提高效率

### 结算流程

```
每 60 秒触发一次检查
        ↓
  查询钱包当前的活跃持仓列表
        ↓
  对每个持仓，查询对应市场是否已结算
        ↓
  ┌─ 已结算 且 我方获胜（持有了正确方向的代币）
  │     ↓
  │   调用 CTF Contract.redeemPositions()
  │     ↓
  │   USDC.e 自动转入钱包 ✅
  │     ↓
  │   记录结算历史
  │
  └─ 未结算 或 我方输了 → 跳过，下次再查
```

### 关键配置

在 `settings.yaml` 的 `modules.settlement_worker` 节点下配置：

| 参数 | 默认值 | 含义 |
|------|--------|------|
| `check_interval` | `60s` | 结算检查的时间间隔 |
| `batch_size` | `50` | 每批处理的持仓数量上限 |
| `track_history` | `true` | 是否记录结算历史日志 |
| `max_history_days` | `30` | 历史记录保留天数 |

---

## 4.5 四模块总览对比表

| 维度 | market_data_collector | strategy_engine | order_executor | settlement_worker |
|------|-----------------------|----------------|---------------|-------------------|
| **角色比喻** | 👀 眼睛（盯盘） | 🧠 大脑（分析） | ✋ 手（下单） | 💰 会计（收钱） |
| **输入来源** | Polymarket WebSocket 行情 | Redis 市场数据频道 | Redis 交易信号频道 | 区块链结算事件 |
| **输出目标** | Redis 市场数据频道 | Redis 交易信号频道 | Polymarket CLOB API | CTF 合约赎回调用 |
| **日志文件** | `logs/market_data_collector.log` | `logs/strategy_engine.log` | `logs/order_executor.log` | `logs/settlement_worker.log` |
| **依赖的外部服务** | Polymarket WS Server | Redis Server | Redis + CLOB API | Polygon RPC 节点 |
| **能否独立运行** | ✅ 可以独立运行 | ❌ 需要 market_data 提供数据 | ❌ 需要 strategy_engine 提供信号 | ✅ 可以独立运行 |
| **CPU 占用** | 低（主要是 I/O） | 中（OLS 回归计算） | 低（API 调用为主） | 很低（定时轮询） |
| **内存占用** | ~50 MB | ~80 MB | ~60 MB | ~30 MB |

### 模块间数据流转示意

```
market_data_collector          strategy_engine            order_executor         settlement_worker
┌─────────────────┐       ┌──────────────────┐      ┌────────────────┐     ┌─────────────────┐
│  WebSocket 接收  │──Redis──▶│  OLS 回归分析    │──Redis─▶│  创建并提交订单  │     │  定时检查结算    │
│  解析 & 发布     │ Pub/Sub  │  安全垫计算      │Pub/Sub │  监控订单状态    │     │  赎回获胜代币    │
└─────────────────┘       └──────────────────┘      └────────────────┘     └─────────────────┘
                                                                                   ▲
                                                                           Polygon 链上事件
```

> 🔑 **关键理解**：四个模块通过 **Redis Pub/Sub** 松耦合连接，彼此不直接调用。这意味着你可以单独重启某个模块而不影响其他模块——就像流水线上换掉一个工人不会让整条线停摆一样。

<!-- CHAPTER_4_CONTENT_END -->

---

## 第 5 章：配置参数完全手册

<!-- CHAPTER_5_CONTENT_START -->

> ⚠️ **本章为配置参数字典**，涵盖 `settings.yaml` 中全部 **51 个参数**的完整说明。每个参数均从 [parameter_registry.py](../shared/parameter_registry.py) 提取真实元数据。Phase 1 新增 18 个参数（MarketDiscovery 6 + StopLossMonitor 3 + SignalAdapter 4 + RiskManager 索引 5）。
> 敏感参数（API 密钥、密码等）已标注 🔒 安全警告。

---

## 5.1 Category 1：Strategy 策略参数（17 个）

策略参数控制交易决策的核心逻辑，包括价格计算、订单规模、风险管理和自动止损止盈。**这是新手最需要关注的参数组。**

---

#### `strategy.base_cushion` — 基础缓冲值

> 用于计算买入价格的安全缓冲，值越大买入越保守

| 属性 | 值 |
|------|-----|
| **数据类型** | float |
| **默认值** | 0.02 |
| **取值范围** | 0.0 ~ 1.0 |
| **必填/可选** | 可选 |
| **敏感信息** | 否 |
| **配置级别** | core |
| **所属分类** | strategy |

**📖 功能详解**：该参数直接参与买入价格的计算公式：`实际买入价 = 当前市场价格 - base_cushion`。它本质上是一个"安全垫"，确保你不会以市场当前的最高价买入，而是以一个折扣价入场。例如当前价格为 0.70，base_cushion 为 0.02 时，你的出价为 0.68。

**⚙️ 直接后果**：增大此值 → 买入价格更低、更保守，但可能错过快速上涨的机会；减小此值 → 更容易成交，但利润空间被压缩。

**🔗 关联参数**：`strategy.alpha`（两者共同决定最终买入价）、`strategy.max_buy_prices.*`（价格上限）

**❌ 错误配置症状**：设置过大（如 > 0.10）→ 几乎所有订单都无法成交；设置过小（如 < 0.005）→ 失去安全缓冲意义，追高风险大增。

**🔧 调试方法**：查看日志中 `calculated_buy_price` 字段，确认最终出价 = 当前价 - base_cushion 调整后的值。

**💡 新手推荐值**：**0.05** — 新手应优先保护本金，宁可少赚也不要追高。

**三档建议值对照**：
| 场景 | 推荐值 | 理由 |
|------|--------|------|
| 🟢 保守 | 0.05 | 较大缓冲，适合初学者控制风险 |
| 🟡 平衡（默认） | 0.02 | 标准缓冲，兼顾成交率与安全性 |
| 🔴 激进 | 0.01 | 最小缓冲，追求最大化参与度 |

---

#### `strategy.alpha` — Alpha 价格调整系数

> 动态调整买入价格的系数，与市场波动性联动

| 属性 | 值 |
|------|-----|
| **数据类型** | float |
| **默认值** | 0.5 |
| **取值范围** | 0.0 ~ 1.0 |
| **必填/可选** | 可选 |
| **敏感信息** | 否 |
| **配置级别** | core |
| **所属分类** | strategy |

**📖 功能详解**：Alpha 是策略引擎的核心调节旋钮。它将 base_cushion 的效果按比例放大或缩小：在高波动市场中，较低的 alpha 会进一步压低买入价；在低波动市场中，较高的 alpha 允许更积极地参与交易。alpha 与 base_cushion 共同构成双层价格过滤机制。

**⚙️ 直接后果**：alpha 越低 → 对 base_cushion 的放大效应越弱，整体更保守；alpha 越高 → 价格调整幅度越大，对市场波动更敏感。

**🔗 关联参数**：`strategy.base_cushion`（基础缓冲，alpha 是其乘数）、各 `max_buy_prices.*` 参数

**❌ 错误配置症状**：设为 0 → base_cushion 完全失效；设为 1.0 → 在极端波动时可能过度激进或过度保守。

**🔧 调试方法**：对比不同 alpha 下同一市场的 `adjusted_price` 日志输出差异。

**💡 新手推荐值**：**0.3** — 降低波动敏感性，让系统行为更可预测。

**三档建议值对照**：
| 场景 | 推荐值 | 理由 |
|------|--------|------|
| 🟢 保守 | 0.3 | 低波动敏感度，减少情绪化交易 |
| 🟡 平衡（默认） | 0.5 | 标准灵敏度，适应大多数市场环境 |
| 🔴 激进 | 0.7 | 高波动敏感度，捕捉更多短期机会 |

---

#### `strategy.max_buy_prices.default` — 默认最大买入价格

> 所有市场的通用买入价格上限（占代币面值的比例）

| 属性 | 值 |
|------|-----|
| **数据类型** | float |
| **默认值** | 0.95 |
| **取值范围** | 0.0 ~ 1.0 |
| **必填/可选** | 可选 |
| **敏感信息** | 否 |
| **配置级别** | core |
| **所属分类** | strategy |

**📖 功能详解**：这是系统级别的"硬天花板"。无论策略信号多么强烈，如果市场当前价格超过此阈值，系统将拒绝执行买单。设置为 0.95 意味着你最多愿意花 95 美分买一个面值为 $1.00 的代币，至少保留 5 美分的理论利润空间。

**⚙️ 直接后果**：降低此值 → 利润空间更大但错过高概率市场；提高此值 → 可参与更多市场但压缩单笔利润。

**🔗 关联参数**：`strategy.max_buy_prices.high_confidence`、`strategy.max_buy_prices.low_volatility`、`strategy.max_buy_prices.fast_market`（三者均以此为基础变体）

**❌ 错误配置症状**：设为 1.0 → 无利润空间，手续费即可吞噬收益；设过低（如 < 0.80）→ 大量合理机会被过滤。

**🔧 调试方法**：检查日志中的 `price_limit_rejected` 计数器，观察被拦截的订单数量。

**💡 新手推荐值**：**0.85** — 留足 15% 利润空间覆盖手续费和滑点。

**三档建议值对照**：
| 场景 | 推荐值 | 理由 |
|------|--------|------|
| 🟢 保守 | 0.85 | 15% 安全边际，覆盖手续费+滑点 |
| 🟡 平衡（默认） | 0.95 | 5% 标准边际，主流做市策略常用值 |
| 🔴 激进 | 0.98 | 仅留 2% 边际，适用于高频低利策略 |

---

#### `strategy.max_buy_prices.high_confidence` — 高置信度最大买入价格

> 当策略信号置信度较高时允许的最大买入价格

| 属性 | 值 |
|------|-----|
| **数据类型** | float |
| **默认值** | 0.98 |
| **取值范围** | 0.0 ~ 1.0 |
| **必填/可选** | 可选 |
| **敏感信息** | 否 |
| **配置级别** | advanced |
| **所属分类** | strategy |

**📖 功能详解**：当策略引擎判定当前信号来源可靠、历史准确率高时，会启用此更高阈值替代默认上限。这相当于给"好机会"开了一个绿色通道——允许以更高的价格入场博取更大的确定性收益。

**⚙️ 直接后果**：高于 default 值 → 高置信信号可以突破常规限制；低于 default 值 → 该参数形同虚设，永远不会触发。

**🔗 关联参数**：`strategy.max_buy_prices.default`（必须 ≥ 此值才有效）、`modules.strategy_engine.signal_filter.min_confidence`（触发条件）

**❌ 错误配置症状**：设得比 default 还低 → 永远不会被使用；设过高（如 0.999）→ 高置信场景下几乎无利润空间。

**🔧 调试方法**：搜索日志中 `using_high_confidence_price_limit` 标记的出现频率和对应结果。

**💡 新手推荐值**：**0.92** — 即使高置信也保持克制，避免过度自信陷阱。

**三档建议值对照**：
| 场景 | 推荐值 | 理由 |
|------|--------|------|
| 🟢 保守 | 0.92 | 高置信也不追高，保持纪律性 |
| 🟡 平衡（默认） | 0.98 | 给可信信号适度放宽空间 |
| 🔴 激进 | 0.99 | 极高置信下接近满仓参与 |

---

#### `strategy.max_buy_prices.low_volatility` — 低波动市场最大买入价格

> 低波动市场中允许的最大买入价格

| 属性 | 值 |
|------|-----|
| **数据类型** | float |
| **默认值** | 0.92 |
| **取值范围** | 0.0 ~ 1.0 |
| **必填/可选** | 可选 |
| **敏感信息** | 否 |
| **配置级别** | advanced |
| **所属分类** | strategy |

**📖 功能详解**：针对价格变动平缓的市场（如长期政治事件预测），系统识别到低波动特征后会切换到此参数作为价格上限。低波动市场虽然方向确定性较高，但收益率天然偏低，因此需要控制买入成本。

**⚙️ 直接后果**：此值通常低于 default → 低波动市场更严格控制成本；若高于 default → 与设计初衷矛盾。

**🔗 关联参数**：`strategy.max_buy_prices.default`、`strategy.base_cushion`

**❌ 错误配置症状**：设得过高 → 低波动市场利润微薄甚至亏损；设得过低 → 合理的低风险机会被浪费。

**🔧 调试方法**：查看 `market_volatility_classification` 日志字段确认波动分类是否正确应用了对应参数。

**💡 新手推荐值**：**0.88** — 低波动市场本身收益有限，需严格控本。

**三档建议值对照**：
| 场景 | 推荐值 | 理由 |
|------|--------|------|
| 🟢 保守 | 0.88 | 低波动=低收益，必须严控成本 |
| 🟡 平衡（默认） | 0.92 | 适度的低波动市场参与门槛 |
| 🔴 激进 | 0.96 | 低波动市场也可积极布局 |

---

#### `strategy.max_buy_prices.fast_market` — 快速市场最大买入价格

> 针对 Fast Market（如 5 分钟 BTC 涨跌）的最大买入价格限制

| 属性 | 值 |
|------|-----|
| **数据类型** | float |
| **默认值** | 0.90 |
| **取值范围** | 0.0 ~ 1.0 |
| **必填/可选** | 可选 |
| **敏感信息** | 否 |
| **配置级别** | expert |
| **所属分类** | strategy |

**📖 功能详解**：Fast Market（如 "Bitcoin Up or Down - 5 Minutes"）是 Polymarket 上结算周期最短、流动性最差、滑点最大的市场类型。此参数为此类高风险场景设置了最严格的买入价格上限，是整个价格体系中最保守的一道防线。

**⚙️ 直接后果**：此值显著低于其他 max_buy_prices → Fast Market 参与门槛最高；调高此值 → 承担更高的流动性风险和滑点损失。

**🔗 关联参数**：`strategy.max_buy_prices.default`、`modules.market_data_collector.websocket`（Fast Market 数据依赖 WebSocket 实时推送）

**❌ 错误配置症状**：设得过高（如 > 0.95）→ 在流动性差的 Fast Market 中极易被套；忽略此参数 → 回退到 default 值 0.95，对 Fast Market 过于宽松。

**🔧 调试方法**：专门监控 Fast Market 类型订单的 `slippage` 和 `fill_rate` 指标。

**💡 新手推荐值**：**0.80** — 强烈建议新手完全避开 Fast Market 或使用最保守值。

**三档建议值对照**：
| 场景 | 推荐值 | 理由 |
|------|--------|------|
| 🟢 保守 | 0.80 | 20% 安全边际，对抗极端滑点 |
| 🟡 平衡（默认） | 0.90 | 标准 Fast Market 风险溢价 |
| 🔴 激进 | 0.94 | 经验丰富的交易者可适当放宽 |

---

#### `strategy.order_sizes.default` — 默认订单大小

> 每笔交易的默认下单金额（USDC）

| 属性 | 值 |
|------|-----|
| **数据类型** | int |
| **默认值** | 100 |
| **取值范围** | 10 ~ 10000 |
| **必填/可选** | 可选 |
| **敏感信息** | 否 |
| **配置级别** | core |
| **所属分类** | strategy |

**📖 功能详解**：这是每笔订单的"标准单位"。当策略引擎生成买入/卖出信号但没有指定特殊金额时，系统将使用此值作为下单金额。它直接影响单笔交易的风险敞口——100 USDC 的订单意味着最多亏损 100 USDC（在不考虑部分成交的情况下）。

**⚙️ 直接后果**：增大 → 单笔风险上升、资金利用率提高；减小 → 单笔风险降低、需要更多笔数才能达到目标仓位。

**🔗 关联参数**：`strategy.order_sizes.min`（下限）、`strategy.order_sizes.max`（上限）、`strategy.risk_management.max_position_size`（总仓位约束）

**❌ 错误配置症状**：设得过大（如 > 总资金 10%）→ 单笔亏损即可造成重大打击；设得过小（如 < 10）→ 手续费占比过高侵蚀利润。

**🔧 调试方法**：检查 `order_size_used` 日志字段，确认实际下单金额符合预期。

**💡 新手推荐值**：**50** — 小额起步，先验证策略有效性再逐步加仓。

**三档建议值对照**：
| 场景 | 推荐值 | 理由 |
|------|--------|------|
| 🟢 保守 | 50 | 单笔低风险，适合学习阶段 |
| 🟡 平衡（默认） | 100 | 标准单位，平衡效率与风险 |
| 🔴 激进 | 500 | 大额订单，需配合强风控使用 |

---

#### `strategy.order_sizes.min` — 最小订单大小

> 允许的最小下单金额（USDC），低于此值的订单将被拒绝

| 属性 | 值 |
|------|-----|
| **数据类型** | int |
| **默认值** | 10 |
| **取值范围** | 1 ~ 10000 |
| **必填/可选** | 可选 |
| **敏感信息** | 否 |
| **配置级别** | standard |
| **所属分类** | strategy |

**📖 功能详解**：防止产生"蚂蚁仓"——金额极小以至于手续费就能吃掉全部潜在利润的无效订单。Polymarket 的交易存在固定成本（Gas + 手续费），过小的订单在经济上完全不划算。此参数在订单提交前进行最后一道金额校验。

**⚙️ 直接后果**：提高此值 → 过滤掉更多小额订单，减少无效交易；降低此值 → 允许更精细的仓位调整，但增加垃圾订单风险。

**🔗 关联参数**：`strategy.order_sizes.default`（必须 ≤ default）、`strategy.order_sizes.max`（必须 ≤ max）

**❌ 错误配置症状**：设得比 default 或 max 还大 → 所有正常订单都会被拒绝；设为 1 或 2 → 大量无经济意义的微小订单。

**🔧 调试方法**：统计 `order_size_below_minimum` 拒绝日志的频率。

**💡 新手推荐值**：**20** — 新手阶段避免任何小额噪音交易。

**三档建议值对照**：
| 场景 | 推荐值 | 理由 |
|------|--------|------|
| 🟢 保守 | 20 | 严格过滤小额订单，保持干净的交易记录 |
| 🟡 平衡（默认） | 10 | 标准最小值，允许灵活的小额补仓 |
| 🔴 激进 | 5 | 极致精细化仓位管理，高手专用 |

---

#### `strategy.order_sizes.max` — 最大订单大小

> 允许的最大下单金额（USDC），超出的订单将被拆分或拒绝

| 属性 | 值 |
|------|-----|
| **数据类型** | int |
| **默认值** | 1000 |
| **取值范围** | 10 ~ 100000 |
| **必填/可选** | 可选 |
| **敏感信息** | 否 |
| **配置级别** | standard |
| **所属分类** | strategy |

**📖 功能详解**：单笔交易的"天花板"。当策略信号建议的大额仓位超过此限制时，系统会将订单拆分为多笔分别提交（如果启用了拆单逻辑），或者直接拒绝（未启用拆单时）。这是防止单次操作失误导致灾难性损失的硬性约束。

**⚙️ 直接后果**：降低 → 大仓位必须分批建仓，降低冲击成本但增加操作复杂度；提高 → 允许一次性建仓，但单笔风险集中。

**🔗 关联参数**：`strategy.order_sizes.default`（必须 ≥ default）、`strategy.order_sizes.min`（必须 ≥ min）、`strategy.risk_management.max_position_size`（单市场总仓限制）

**❌ 错误配置症状**：设得小于 default → 正常默认订单都会被拦截；设得过大且无拆单逻辑 → 可能超出市场深度导致严重滑点。

**🔧 调试方法**：关注 `order_split_into_N_parts` 或 `order_exceeds_max_size` 日志事件。

**💡 新手推荐值**：**500** — 严格限制单笔上限，强制分批操作养成好习惯。

**三档建议值对照**：
| 场景 | 推荐值 | 理由 |
|------|--------|------|
| 🟢 保守 | 500 | 强制分批建仓，降低单点风险 |
| 🟡 平衡（默认） | 1000 | 中等额度，适合多数市场深度 |
| 🔴 激进 | 5000 | 大额订单，需深流动性市场配合 |

---

#### `strategy.risk_management.max_position_size` — 单市场最大持仓

> 单个预测市场中允许持有的最大仓位金额（USDC）

| 属性 | 值 |
|------|-----|
| **数据类型** | int |
| **默认值** | 5000 |
| **取值范围** | 100 ~ 100000 |
| **必填/可选** | 可选 |
| **敏感信息** | 否 |
| **配置级别** | core |
| **所属分类** | strategy |

**📖 功能详解**："不要把鸡蛋放在同一个篮子里"的量化实现。无论某个市场看起来多么有吸引力，一旦该市场的累计持仓金额触及此上限，系统将停止在该市场继续加仓。这是分散化投资的第一道防线。

**⚙️ 直接后果**：降低 → 分散化程度更高，单一市场黑天鹅影响有限；提高 → 允许集中押注高确信市场，但集中风险激增。

**🔗 关联参数**：`strategy.risk_management.max_total_exposure`（全局上限，应 ≥ 各 market max 之和）、`strategy.order_sizes.max`（单笔 ≤ 单市场）

**❌ 错误配置 symptoms**：设得过高（如 > 总资金 50%）→ 违背分散原则，一次判断错误即可重伤账户；设得过低 → 无法在任何市场建立有意义的位置。

**🔧 调试方法**：查询 Redis 中每个 token_id 的 `position_value`，确认无一超标。

**💡 新手推荐值**：**2000** — 严格执行分散化，单个市场不超过总资金 10-15%。

**三档建议值对照**：
| 场景 | 推荐值 | 理由 |
|------|--------|------|
| 🟢 保守 | 2000 | 高度分散，单市场风险可控 |
| 🟡 平衡（默认） | 5000 | 适度集中，允许重仓高确信市场 |
| 🔴 激进 | 10000 | 集中投资策略，需极强研究能力 |

---

#### `strategy.risk_management.max_total_exposure` — 总风险敞口上限

> 所有持仓的总金额上限（USDC），资金安全第一道防线

| 属性 | 值 |
|------|-----|
| **数据类型** | int |
| **默认值** | 20000 |
| **取值范围** | 1000 ~ 500000 |
| **必填/可选** | 可选 |
| **敏感信息** | 否 |
| **配置级别** | core |
| **所属分类** | strategy |

**📖 功能详解**：全账户级别的"水位线"。无论有多少个诱人的市场机会，只要所有持仓的总价值触及此限额，系统立即暂停一切开仓操作。这是防止在行情狂热时过度杠杆、在熊市中越亏越补的根本性风控手段。

**⚙️ 直接后果**：降低 → 更多现金储备，抗风险能力更强但资金利用率低；提高 → 更充分利用资金但爆仓风险上升。

**🔗 关联参数**：`strategy.risk_management.max_position_size`（各市场之和不应超过此值）、`strategy.risk_management.min_balance`（保留余额不参与敞口计算）

**❌ 错误配置症状**：设得接近或超过账户总额 → 无任何安全余量，一次系统性风险即可归零；设得过低（如 < 总资金 20%）→ 资金大量闲置。

**🔧 调试方法**：监控 `total_exposure` 指标和 `exposure_limit_reached` 告警事件。

**💡 新手推荐值**：**10000** — 保留至少 50% 现金，用时间换经验。

**三档建议值对照**：
| 场景 | 推荐值 | 理由 |
|------|--------|------|
| 🟢 保守 | 10000 | 半仓操作，极端行情下仍能存活 |
| 🟡 平衡（默认） | 20000 | 标准敞口，约 60-70% 资金利用率 |
| 🔴 激进 | 50000 | 高仓位运行，专业团队级别 |

---

#### `strategy.risk_management.max_daily_loss` — 日最大亏损限额

> 每日允许的最大亏损金额（USDC），触发后当日停摆

| 属性 | 值 |
|------|-----|
| **数据类型** | int |
| **默认值** | 500 |
| **取值范围** | 50 ~ 50000 |
| **必填/可选** | 可选 |
| **敏感信息** | 否 |
| **配置级别** | core |
| **所属分类** | strategy |

**📖 功能详解**：每日的"熔断开关"。系统实时追踪当日已实现亏损 + 浮动亏损的总和，一旦触及此限额，立即锁定所有交易功能直到次日 UTC 0:00 重置。这是防止"赌徒谬误"——连续亏损后加大仓位试图翻本——的自动化机制。

**⚙️ 直接后果**：降低 → 更早触发熔断，保护剩余本金但可能中断盈利恢复过程；提高 → 允许更大回撤空间，但连续错误判断的代价更高。

**🔗 关联参数**：`strategy.risk_management.max_drawdown`（账户级回撤控制，比日亏损更长周期）、`system.log_level`（熔断事件需记录 ERROR 级别日志）

**❌ 错误配置症状**：设得过高（如 > 总资金 10%）→ 单日可能遭受重创；设得过低（如 < 50）→ 正常波动即可触发熔断，严重影响策略执行。

**🔧 调试方法**：检查 `daily_pnl_tracker` 中的累积亏损值和 `daily_loss_limit_hit` 事件计数。

**💡 新手推荐值**：**200** — 宁可早停不可晚停，保住本金最重要。

**三档建议值对照**：
| 场景 | 推荐值 | 理由 |
|------|--------|------|
| 🟢 保守 | 200 | 极早熔断，最大程度保护本金 |
| 🟡 平衡（默认） | 500 | 日亏损控制在 2-3% 以内 |
| 🔴 激进 | 2000 | 允许较大日内波动，需强心理素质 |

---

#### `strategy.risk_management.max_drawdown` — 最大回撤比例

> 从账户峰值允许的最大回撤比例，触发后风控熔断直至人工确认

| 属性 | 值 |
|------|-----|
| **数据类型** | float |
| **默认值** | 0.15 |
| **取值范围** | 0.05 ~ 0.5 |
| **必填/可选** | 可选 |
| **敏感信息** | 否 |
| **配置级别** | core |
| **所属分类** | strategy |

**📖 功能详解**：比日亏损更长周期的保护机制。系统持续追踪账户权益的历史峰值（peak equity），当当前权益从峰值下跌的比例超过此阈值时，触发**永久性熔断**——不是等到次日自动恢复，而是必须人工介入审查后才可重新启动。这是应对系统性风险（如市场崩盘、策略失效）的最后屏障。

**⚙️ 直接后果**：降低（如 0.08）→ 更早触发熔断，峰值回撤被严格控制在 8% 以内；提高（如 0.25）→ 允许更深度的回撤，但恢复难度呈指数级增长。

**🔗 关联参数**：`strategy.risk_management.max_daily_loss`（日级保护，先于 drawdown 触发）、`strategy.stop_loss_take_profit.enabled`（单仓位级保护，最先触发）

**❌ 错误配置症状**：设为 0.5 → 账户腰斩才熔断，基本失去保护意义；设为 0.05 → 正常策略波动即可触发，过于敏感。

**🔧 调试方法**：监控 `peak_equity`、`current_equity`、`drawdown_percentage` 三个指标的实时仪表板。

**💡 新手推荐值**：**0.08** — 专业量化基金的常见水平，严格保护本金曲线。

**三档建议值对照**：
| 场景 | 推荐值 | 理由 |
|------|--------|------|
| 🟢 保守 | 0.08 | 最大回撤 8%，基金行业标准 |
| 🟡 平衡（默认） | 0.15 | 15% 回撤容忍度，个人交易者常用 |
| 🔴 激进 | 0.25 | 25% 回撤空间，高收益伴随高风险 |

---

#### `strategy.risk_management.min_balance` — 最小保留余额

> 账户中必须保留的最小 USDC 余额，不参与交易

| 属性 | 值 |
|------|-----|
| **数据类型** | int |
| **默认值** | 100 |
| **取值范围** | 10 ~ 10000 |
| **必填/可选** | 可选 |
| **敏感信息** | 否 |
| **配置级别** | standard |
| **所属分类** | strategy |

**📖 功能详解**：账户的"应急备用金"。这部分 USDC 被锁定，不计入可用交易余额，永远不被用于开仓。其用途包括：支付 Polygon 网络 Gas 费、覆盖可能的清算费用、在极端行情中提供最后的操作余地。即使总风险敞口已达上限，min_balance 也必须保持完整。

**⚙️ 直接后果**：提高 → 应急能力增强但可交易资金减少；降低 → 更多资金可用于交易但在极端情况下可能无法支付 Gas 导致操作瘫痪。

**🔗 关联参数**：`strategy.risk_management.max_total_exposure`（实际可用余额 = 总余额 - min_balance - 当前敞口）

**❌ 错误配置症状**：设为 0 → 无法支付 Gas 费，链上操作全部卡死；设得过高（如 > 总资金 30%）→ 资金利用效率严重低下。

**🔧 调试方法**：检查 `available_balance` 是否始终 ≥ `min_balance`。

**💡 新手推荐值**：**500** — 多留一些应急资金，Gas 费波动时不会被动。

**三档建议值对照**：
| 场景 | 推荐值 | 理由 |
|------|--------|------|
| 🟢 保守 | 500 | 充足的 Gas 费储备 + 应急缓冲 |
| 🟡 平衡（默认） | 100 | 基础 Gas 费保障 |
| 🔴 激进 | 50 | 最小保留，最大化资金利用率 |

---

#### `strategy.stop_loss_take_profit.enabled` — 止损止盈功能开关

> 是否启用自动止损止盈机制

| 属性 | 值 |
|------|-----|
| **数据类型** | bool |
| **默认值** | true |
| **取值范围** | true / false |
| **必填/可选** | 可选 |
| **敏感信息** | 否 |
| **配置级别** | standard |
| **所属分类** | strategy |

**📖 功能详解**：自动化的"智能交易助手"。开启后，系统会对每个活跃持仓持续监控价格变化——当浮亏达到止损线时自动卖出离场，当浮盈达到止盈线时自动锁定利润。这意味着你不需要 24 小时盯盘，系统会在预设条件下代你执行操作。

**⚙️ 直接后果**：开启 → 全自动仓位管理，无需人工干预；关闭 → 所有持仓必须手动管理，忘记止损可能导致无限亏损。

**🔗 关联参数**：`strategy.stop_loss_take_profit.stop_loss_percentage`、`strategy.stop_loss_take_profit.take_profit_percentage`（关闭后两者无效）

**❌ 错误配置症状**：生产环境中关闭 → 失去最重要的自动化保护层；开发调试时可临时关闭。

**🔧 调试方法**：开启后观察 `auto_stop_loss_triggered` 和 `auto_take_profit_triggered` 事件的触发情况。

**💡 新手推荐值**：**true** — 除非你在手动测试，否则永远不要关闭。

**三档建议值对照**：
| 场景 | 推荐值 | 理由 |
|------|--------|------|
| 🟢 保守 | ✅ true | 必须开启，这是最基本的自我保护 |
| 🟡 平衡（默认） | ✅ true | 默认开启，自动化仓位管理 |
| 🔴 激进 | ✅ true | 即使激进策略也需要止损止盈 |

---

#### `strategy.stop_loss_take_profit.stop_loss_percentage` — 止损比例

> 触发自动止损的价格下跌百分比

| 属性 | 值 |
|------|-----|
| **数据类型** | float |
| **默认值** | 0.10 |
| **取值范围** | 0.02 ~ 0.5 |
| **必填/可选** | 可选 |
| **敏感信息** | 否 |
| **配置级别** | standard |
| **所属分类** | strategy |

**📖 功能详解**：持仓的"逃生出口"。当你以 0.60 的价格买入某代币后，如果价格跌至 0.54（下跌 10%），系统将自动挂出卖单止损离场。这个比例决定了你愿意在一笔错误的交易上承受多大损失才认赔出场。

**⚙️ 直接后果**：降低（如 0.05）→ 更早止损，单笔亏损小但可能被正常波动震出去；提高（如 0.20）→ 给予更多容忍空间但单笔最大亏损翻倍。

**🔗 关联参数**：`strategy.stop_loss_take_profit.take_profit_percentage`（建议止盈/止损比 ≥ 2:1）、`strategy.stop_loss_take_profit.enabled`（必须开启才生效）

**❌ 错误配置症状**：设得过高（如 > 0.30）→ 一笔止损即可造成重大伤害；设得过低（如 < 0.03）→ 几乎任何波动都触发止损，无法持有仓位。

**🔧 调试方法**：回测历史数据中不同止损比例下的 `stop_loss_rate`（被止损出局的比例）和 `avg_stop_loss_amount`（平均止损金额）。

**💡 新手推荐值**：**0.05** — 快速认错，小亏即走，保护本金。

**三档建议值对照**：
| 场景 | 推荐值 | 理由 |
|------|--------|------|
| 🟢 保守 | 0.05 | 5% 即止损，严格控制单笔亏损 |
| 🟡 平衡（默认） | 0.10 | 10% 标准止损，给予合理波动空间 |
| 🔴 激进 | 0.20 | 20% 宽松止损，趋势策略需要更大容忍度 |

---

#### `strategy.stop_loss_take_profit.take_profit_percentage` — 止盈比例

> 触发自动止盈的价格上涨百分比

| 属性 | 值 |
|------|-----|
| **数据类型** | float |
| **默认值** | 0.20 |
| **取值范围** | 0.05 ~ 0.8 |
| **必填/可选** | 可选 |
| **敏感信息** | 否 |
| **配置级别** | standard |
| **所属分类** | strategy |

**📖 功能详解**：利润的"落袋为安"按钮。当持仓浮盈达到此比例时，系统自动卖出锁定利润。这解决了人性中"贪心"的问题——很多交易者因为想赚更多而眼睁睁看着利润回吐甚至转亏。自动止盈确保你不会犯这个错误。

**⚙️ 直接后果**：降低（如 0.10）→ 更早锁利，胜率高但平均盈利小；提高（如 0.40）→ 追求大赢，但大部分仓位可能在回调中回到原点。

**🔗 关联参数**：`strategy.stop_loss_take_profit.stop_loss_percentage`（风险收益比 = take_profit / stop_loss，建议 ≥ 2:1）、`strategy.stop_loss_take_profit.enabled`

**❌ 错误配置症状**：设得比止损还低（如止损 0.15、止盈 0.10）→ 负期望值系统，必亏；设得过高（如 > 0.50）→ 几乎永远不会触发，形同虚设。

**🔧 调试方法**：分析 `take_profit_triggered` 事件的平均获利金额 vs 如果不止盈的最终结果对比。

**💡 新手推荐值**：**0.10** — 小步快跑，频繁锁利建立信心。

**三档建议值对照**：
| 场景 | 推荐值 | 理由 |
|------|--------|------|
| 🟢 保守 | 0.10 | 快速止盈，积小胜为大胜 |
| 🟡 平衡（默认） | 0.20 | 20% 标准止盈，2:1 风险收益比 |
| 🔴 激进 | 0.40 | 40% 止盈，追求单笔大赢 |

---

## 5.2 Category 2：Connection 连接参数（11 个）

连接参数控制 Redis 缓存层的网络配置、连接池管理和故障恢复策略。Redis 是 SimplePolyBot 的核心基础设施，负责实时订单簿缓存、WebSocket 消息队列和分布式锁。

> 🔒 **安全提醒**：`redis.password` 为敏感参数，请通过环境变量 `${REDIS_PASSWORD}` 注入，切勿明文写在 YAML 中。

---

#### `redis.host` — Redis 主机地址

> Redis 服务器的主机名或 IP 地址

| 属性 | 值 |
|------|-----|
| **数据类型** | str |
| **默认值** | localhost |
| **取值范围** | 有效主机名 / IPv4 / IPv6 |
| **必填/可选** | 必填 |
| **敏感信息** | 否 |
| **配置级别** | core |
| **所属分类** | connection |

**📖 功能详解**：系统连接 Redis 服务器的目标地址。开发环境通常是 `localhost` 或 `127.0.0.1`；生产环境应为内网 IP 地址或 Kubernetes Service 名称，以确保低延迟和高可靠性。

**⚙️ 直接后果**：配置错误 → 系统启动时立即报连接失败，所有依赖 Redis 的模块（订单簿缓存、消息队列等）全部不可用。

**🔗 关联参数**：`redis.port`（必须配对使用）、`redis.password`（认证凭据）

**❌ 错误配置症状**：写错 IP/域名 → `ConnectionRefusedError`；使用公网 IP → 延迟高且安全隐患；DNS 解析失败 → 启动卡住。

**🔧 调试方法**：`ping <host>` 测试网络连通性；`telnet <host> <port>` 测试端口可达性。

**💡 新手推荐值**：**localhost** — 本地 Docker 或直装 Redis 时使用。

**三档建议值对照**：
| 场景 | 推荐值 | 理由 |
|------|--------|------|
| 🟢 本地开发 | localhost | 直连本地 Redis 实例 |
| 🟡 Docker Compose | redis | 使用容器服务名 |
| 🔴 生产部署 | 10.0.1.x (内网IP) | 内网地址，低延迟高安全 |

---

#### `redis.port` — Redis 端口号

> Redis 服务监听的 TCP 端口

| 属性 | 值 |
|------|-----|
| **数据类型** | int |
| **默认值** | 6379 |
| **取值范围** | 1 ~ 65535 |
| **必填/可选** | 必填 |
| **敏感信息** | 否 |
| **配置级别** | core |
| **所属分类** | connection |

**📖 功能详解**：Redis 服务的标准 TCP 端口。6379 是 Redis 的默认端口，也是绝大多数安装使用的端口。如果你在同一台机器上运行多个 Redis 实例（如开发/测试分离），则需要使用不同端口。

**⚙️ 直接后果**：端口错误 → 与 host 错误效果相同，连接被拒绝。

**🔗 关联参数**：`redis.host`（主机+端口组成完整连接地址）

**❌ 错误配置症状**：端口被防火墙拦截 → 连接超时而非拒绝；端口被其他服务占用 → 可能连到错误的服务。

**🔧 调试方法**：`netstat -an \| findstr <port>` 确认端口监听状态。

**💡 新手推荐值**：**6379** — Redis 标准端口，无需修改。

**三档建议值对照**：
| 场景 | 推荐值 | 理由 |
|------|--------|------|
| 🟢 标准安装 | 6379 | Redis 官方默认端口 |
| 🟡 多实例 | 6380 / 6381 | 第二/第三个实例 |
| 🔴 自定义 | 自定义 | 特殊安全需求 |

---

#### `redis.password` — Redis 认证密码 🔒

> Redis 服务器的认证密码，空字符串表示无密码

| 属性 | 值 |
|------|-----|
| **数据类型** | str |
| **默认值** | （空字符串） |
| **取值范围** | 任意非空字符串 |
| **必填/可选** | 可选 |
| **敏感信息** | **是 ⚠️** |
| **配置级别** | core |
| **所属分类** | connection |

**📖 功能详解**：Redis AUTH 命令使用的密码凭证。当 Redis 配置了 `requirepass` 后，客户端必须在连接后立即发送 AUTH 命令才能执行任何操作。**生产环境必须设置密码**，否则任何人都能读写你的缓存数据（包括订单簿、持仓信息等敏感数据）。

> ⚠️ **安全警告**：此参数包含敏感凭证。务必通过环境变量 `${REDIS_PASSWORD}` 注入，禁止明文写入 YAML 文件或提交至版本控制系统。

**⚙️ 直接后果**：密码错误 → `AuthenticationFailedError`，所有 Redis 操作失败；空密码但服务端要求认证 → 同样失败。

**🔗 关联参数**：`redis.host`、`redis.port`

**❌ 错误配置症状**：密码泄露 → 缓存数据可被第三方读取/篡改；密码遗忘 → 无法连接，需重置 Redis。

**🔧 调试方法**：`redis-cli -h <host> -p <port> -a <password> ping` 验证连通性和认证。

**💡 新手推荐值**：**（通过环境变量注入强密码）** — 开发环境可为空，生产环境必须有强密码。

**三档建议值对照**：
| 场景 | 推荐值 | 理由 |
|------|--------|------|
| 🟢 本地开发 | （空） | Docker 隔离即可，简化流程 |
| 🟡 测试环境 | test_redis_2024 | 固定测试密码 |
| 🔴 生产环境 | ${REDIS_PASSWORD} | 环境变量注入，32位随机字符串 |

---

#### `redis.db` — Redis 数据库编号

> 使用的 Redis 数据库编号（0-15）

| 属性 | 值 |
|------|-----|
| **数据类型** | int |
| **默认值** | 0 |
| **取值范围** | 0 ~ 15 |
| **必填/可选** | 可选 |
| **敏感信息** | 否 |
| **配置级别** | standard |
| **所属分类** | connection |

**📖 功能详解**：Redis 支持在单个实例中逻辑隔离出 16 个独立数据库（编号 0-15）。SimplePolyBot 默认使用 db 0。如果你需要在同一 Redis 实例中运行多个应用实例（如开发/生产共享一台服务器），可以为不同环境分配不同的 db 编号以避免数据冲突。

**⚙️ 直接后果**：选择错误的 db → 读不到预期的数据（数据在其他 db 中）；多实例使用相同 db → 数据互相覆盖。

**🔗 关联参数**：无直接关联，但需与其他使用同一 Redis 的应用协调。

**❌ 错误配置症状**：db 编号超出 0-15 范围 → 连接时报错；两个应用用了同一个 db → KEY 冲突导致数据损坏。

**🔧 调试方法**：`redis-cli -n <db_number> keys "*"` 查看 db 中的数据。

**💡 新手推荐值**：**0** — 单实例使用默认数据库即可。

**三档建议值对照**：
| 场景 | 推荐值 | 理由 |
|------|--------|------|
| 🟢 单实例 | 0 | 默认数据库，简单直接 |
| 🟡 双环境 | 0(prod) / 1(dev) | 生产开发隔离 |
| 🔴 多租户 | 2-15 | 每租户独占一个 db |

---

#### `redis.pool.max_connections` — 连接池最大连接数

> Redis 连接池中允许创建的最大连接数量

| 属性 | 值 |
|------|-----|
| **数据类型** | int |
| **默认值** | 50 |
| **取值范围** | 1 ~ 500 |
| **必填/可选** | 可选 |
| **敏感信息** | 否 |
| **配置级别** | advanced |
| **所属分类** | connection |

**📖 功能详解**：连接池是性能优化的关键组件。系统不会每次操作都新建 TCP 连接（开销大），而是维护一组可复用的连接。max_connections 设定了这个池子的容量上限。当所有连接都在忙时，新请求要么排队等待，要么（超时后）直接失败。

**⚙️ 直接后果**：过小（如 < 10）→ 高并发时请求排队，延迟飙升；过大（如 > 200）→ 占用过多服务器资源（文件描述符、内存），Redis 服务端也可能拒绝。

**🔗 关联参数**：`redis.pool.min_idle_connections`（空闲连接应 ≤ max_connections）、`redis.pool.connection_timeout`（排队超时控制）

**❌ 错误配置症状**：设得太小 → 日志中出现大量 `ConnectionPoolExhausted` 或 `timeout waiting for available connection`；设得太大 → Redis 报 `max clients reached`。

**🔧 调试方法**：监控 `pool_active_connections`、`pool_idle_connections`、`pool_wait_count` 指标。

**💡 新手推荐值**：**10** — 个人使用足够，避免资源浪费。

**三档建议值对照**：
| 场景 | 推荐值 | 理由 |
|------|--------|------|
| 🟢 低流量 | 10 | 个人开发者/少量市场订阅 |
| 🟡 平衡（默认） | 50 | 中等流量，多模块并行 |
| 🔴 高流量 | 200 | 生产环境，大量并发请求 |

---

#### `redis.pool.min_idle_connections` — 连接池最小空闲连接

> 连接池中始终保持的最小空闲连接数（预热连接）

| 属性 | 值 |
|------|-----|
| **数据类型** | int |
| **默认值** | 5 |
| **取值范围** | 0 ~ 100 |
| **必填/可选** | 可选 |
| **敏感信息** | 否 |
| **配置级别** | advanced |
| **所属分类** | connection |

**📖 功能详解**：连接池的"常备军"。即使当前没有请求，池子也会维持至少这么多个已建立的空闲连接。当下一个请求到来时，可以直接使用这些预热好的连接，省去了 TCP 三次握手 + Redis AUTH 的时间（通常节省 5-50ms）。对于低延迟要求高的交易系统，这个预热机制至关重要。

**⚙️ 直接后果**：增大 → 首次请求更快，但占用更多常驻资源；设为 0 → 冷启动时第一个请求总是慢的（需新建连接）。

**🔗 关联参数**：`redis.pool.max_connections`（idle 不应超过 max 的 50%）

**❌ 错误配置症状**：设得接近 max_connections → 没有余量处理突发流量；设为 0 且流量突发 → 每个请求都要等待建连。

**🔧 调试方法**：观察启动后 `pool_idle_connections` 是否迅速达到设定值。

**💡 新手推荐值**：**2** — 少量预热即可满足个人使用。

**三档建议值对照**：
| 场景 | 推荐值 | 理由 |
|------|--------|------|
| 🟢 低流量 | 2 | 基础预热，减少冷启动延迟 |
| 🟡 平衡（默认） | 5 | 标准预热，应对一般并发 |
| 🔴 高流量 | 20 | 大量预热连接，随时待命 |

---

#### `redis.pool.connection_timeout` — 连接超时时间

> 从连接池获取连接的超时时间（秒）

| 属性 | 值 |
|------|-----|
| **数据类型** | int |
| **默认值** | 5 |
| **取值范围** | 1 ~ 60 |
| **必填/可选** | 可选 |
| **敏感信息** | 否 |
| **配置级别** | advanced |
| **所属分类** | connection |

**📖 功能详解**：当连接池中所有连接都在忙碌时，新请求进入等待队列。此参数定义最长等待时间——超过后不再等待而是抛出超时异常。它是系统的"耐心底线"，防止因 Redis 故障导致整个交易系统卡死。

**⚙️ 直接后果**：缩短 → 更快发现 Redis 问题并降级处理，但可能误杀正常的瞬时高峰；延长 → 更宽容地等待，但 Redis 真正故障时系统响应变慢。

**🔗 关联参数**：`redis.pool.max_connections`（池子越大越不容易超时）、`redis.retry.max_attempts`（超时后的重试策略）

**❌ 错误配置症状**：设太短（如 1s）→ 正常负载波动就超时；设太长（如 30s）→ Redis 挂了之后系统要半分钟才发现。

**🔧 调试方法**：统计 `connection_timeout_exception` 的发生频率和 P99 延迟。

**💡 新手推荐值**：**5 秒** — 标准值，适合大多数场景。

**三档建议值对照**：
| 场景 | 推荐值 | 理由 |
|------|--------|------|
| 🟢 快速失败 | 3s | 尽快暴露问题，适合有降级方案的场景 |
| 🟡 平衡（默认） | 5s | 标准超时，兼容性和响应速度平衡 |
| 🔴 宽容模式 | 10s | 允许较长等待，Redis 临时抖动时不误报 |

---

#### `redis.pool.socket_timeout` — Socket 读写超时

> 单个 Redis 操作的 Socket 超时时间（秒）

| 属性 | 值 |
|------|-----|
| **数据类型** | int |
| **默认值** | 5 |
| **取值范围** | 1 ~ 60 |
| **必填/可选** | 可选 |
| **敏感信息** | 否 |
| **配置级别** | advanced |
| **所属分类** | connection |

**📖 功能详解**：与 connection_timeout 不同，这个超时针对的是**已经拿到连接之后的实际操作**。比如你执行一个 `GET orderbook:btc:asks` 命令，如果 Redis 因为处理大量数据（如 MGET 一次获取几百个 key）而导致响应缓慢，socket_timeout 就是等待这次操作完成的时限。

**⚙️ 直接后果**：缩短 → 复杂操作（批量查询）更容易超时；延长 → 操作卡住时系统反应迟钝。

**🔗 关联参数**：`redis.pool.connection_timeout`（通常两者设为相同值）、Redis 服务端的 `timeout` 配置

**❌ 错误配置症状**：设太短 → 批量操作（MGET/MSET）经常超时；设太长 → Redis 卡死时线程长时间阻塞。

**🔧 调试方法**：对不同类型的 Redis 操作（单 key vs 批量）分别计时，确认是否在此范围内。

**💡 新手推荐值**：**5 秒** — 与 connection_timeout 保持一致。

**三档建议值对照**：
| 场景 | 推荐值 | 理由 |
|------|--------|------|
| 🟢 快速操作为主 | 3s | 单 key 操作很快完成 |
| 🟡 平衡（默认） | 5s | 通用值，适配混合工作负载 |
| 🔴 批量操作多 | 10s | MGET/MSET 等批量命令需要更多时间 |

---

#### `redis.retry.max_attempts` — 最大重试次数

> Redis 操作失败后的最大重试次数

| 属性 | 值 |
|------|-----|
| **数据类型** | int |
| **默认值** | 3 |
| **取值范围** | 0 ~ 10 |
| **必填/可选** | 可选 |
| **敏感信息** | 否 |
| **配置级别** | standard |
| **所属分类** | connection |

**📖 功能详解**：网络不是完美的——瞬时的丢包、Redis 切主、GC 停顿都可能导致单次操作失败。此参数定义系统在放弃之前会尝试多少次。每次重试之间会有间隔（由 retry_delay 控制），配合指数退避可以优雅地度过临时故障。

**⚙️ 直接后果**：增多 → 更有希望穿越临时故障，但故障持续时的总延迟更长；设为 0 → 任何瞬时错误都直接上报，不做任何重试。

**🔗 关联参数**：`redis.retry.retry_delay`（每次重试的等待时间）、`redis.retry.exponential_backoff`（是否翻倍增长延迟）

**❌ 错误配置症状**：设得过高（如 10 次 + 退避）→ 一个故障操作可能阻塞数十秒；写操作重试太多 → 可能导致数据重复写入。

**🔧 调试方法**：统计 `retry_attempt_N` 分布图，看大多数操作在第几次重试成功。

**💡 新手推荐值**：**3** — 标准三次重试，覆盖绝大多数瞬时故障。

**三档建议值对照**：
| 场景 | 推荐值 | 理由 |
|------|--------|------|
| 🟢 关键操作 | 5 | 订单提交等关键操作多尝试几次 |
| 🟡 平衡（默认） | 3 | 标准重试，平衡可靠性与延迟 |
| 🔴 非关键操作 | 1 | 缓存读取等操作失败影响不大 |

---

#### `redis.retry.retry_delay` — 重试间隔时间

> 每次重试之间的基础等待时间（秒）

| 属性 | 值 |
|------|-----|
| **数据类型** | int |
| **默认值** | 1 |
| **取值范围** | 0 ~ 30 |
| **必填/可选** | 可选 |
| **敏感信息** | 否 |
| **配置级别** | standard |
| **所属分类** | connection |

**📖 功能详解**：重试不是立刻进行的——那样会给正在恢复中的 Redis 造成"惊群效应"，反而加剧问题。retry_delay 是首次重试前的等待时间。如果开启了指数退避（exponential_backoff=true），后续重试的等待时间会依次翻倍：1s → 2s → 4s...

**⚙️ 直接后果**：增大 → 给 Redis 更多恢复时间，但故障期间用户体验下降；减小 → 更快重试但可能加重故障 Redis 的负担。

**🔗 关联参数**：`redis.retry.exponential_backoff`（控制是否翻倍）、`redis.retry.max_attempts`（总重试次数 × 延迟 = 最大额外耗时）

**❌ 错误配置症状**：设为 0 → 无间隔重试，可能触发 Redis 的自我保护机制；设得过长 → 用户感知到明显卡顿。

**🔧 调试方法**：测量从第一次失败到最终成功（或彻底失败）的总耗时。

**💡 新手推荐值**：**1 秒** — 标准初始延迟，配合指数退避效果良好。

**三档建议值对照**：
| 场景 | 推荐值 | 理由 |
|------|--------|------|
| 🟢 快速恢复 | 0.5s | 低延迟优先，适合内网稳定环境 |
| 🟡 平衡（默认） | 1s | 标准初始延迟 |
| 🔴 宽松恢复 | 3s | 给 Redis 充分恢复时间 |

---

#### `redis.retry.exponential_backoff` — 指数退避开关

> 是否启用指数退避策略（每次重试延迟翻倍）

| 属性 | 值 |
|------|-----|
| **数据类型** | bool |
| **默认值** | true |
| **取值范围** | true / false |
| **必填/可选** | 可选 |
| **敏感信息** | 否 |
| **配置级别** | standard |
| **所属分类** | connection |

**📖 功能详解**：智能重试的核心策略。开启后，重试间隔不再是固定的 retry_delay，而是按几何级数增长：第 1 次重试等 1s，第 2 次等 2s，第 3 次等 4s...这种策略基于一个观察：**如果前一次重试失败了，说明系统还没恢复，下一次应该给它更多时间**。同时避免了多个客户端同时重试造成的"羊群效应"。

**⚙️ 直接后果**：开启 → 优雅应对持续数秒的临时故障；关闭 → 固定间隔重试，简单但不够智能。

**🔗 关联参数**：`redis.retry.retry_delay`（退避的基础值/首项）、`redis.retry.max_attempts`（退避次数上限）

**❌ 错误配置症状**：关闭后遇到持续故障 → 固定间隔重试可能加重系统负担；开启后 max_attempts 过大 → 总等待时间可能非常长（1+2+4+8+16=31秒 for 5次）。

**🔧 调试方法**：对比开启/关闭两种模式下 `total_retry_time` 指标。

**💡 新手推荐值**：**true** — 生产环境强烈建议开启，这是业界标准做法。

**三档建议值对照**：
| 场景 | 推荐值 | 理由 |
|------|--------|------|
| 🟢 生产环境 | ✅ true | 标准最佳实践，避免雪崩 |
| 🟡 平衡（默认） | ✅ true | 默认开启，智能重试 |
| 🔴 调试场景 | ❌ false | 固定间隔便于复现和排查问题 |

---

## 5.3 Category 3：Module 模块参数（5 个）

模块参数控制 SimplePolyBot 四大核心模块的启停状态和数据源配置。每个模块都是独立运行的进程/线程，可以通过这些开关精确控制系统的功能组合。

---

#### `modules.market_data_collector.enabled` — 市场数据收集器开关

> 控制市场数据收集器模块是否启动

| 属性 | 值 |
|------|-----|
| **数据类型** | bool |
| **默认值** | true |
| **取值范围** | true / false |
| **必填/可选** | 可选 |
| **敏感信息** | 否 |
| **配置级别** | core |
| **所属分类** | module |

**📖 功能详解**：市场数据收集器是 SimplePolyBot 的"感官系统"。它通过 WebSocket 连接 Polymarket CLOB Market Channel，实时接收订单簿更新、最新成交价、最优买卖价等数据，并将这些数据缓存到 Redis 供策略引擎消费。**关闭此模块 = 系统失明**。

**⚙️ 直接后果**：开启 → 实时数据流入 Redis，策略引擎有据可依；关闭 → 无实时数据，策略引擎无法生成信号，订单执行器也无从参考价格。

**🔗 关联参数**：`modules.market_data_collector.websocket.url`（数据源地址）、`modules.strategy_engine.enabled`（下游消费者）

**❌ 错误配置症状**：关闭后策略引擎仍在运行 → 生成基于过期数据的错误信号；WebSocket URL 错误 → 连接不断重试消耗资源。

**🔧 调试方法**：查看 `ws_connection_status` 和 `data_points_received_per_second` 指标。

**💡 新手推荐值**：**true** — 这是系统运行的必要前提，除非纯离线测试否则不要关闭。

**三档建议值对照**：
| 场景 | 推荐值 | 理由 |
|------|--------|------|
| 🟢 正常运行 | ✅ true | 必须开启，数据是一切的基础 |
| 🟡 平衡（默认） | ✅ true | 默认开启 |
| 🔴 离线回测 | ❌ false | 使用历史数据回测时无需实时数据流 |

---

#### `modules.market_data_collector.websocket.url` — WebSocket 连接地址

> Polymarket CLOB WebSocket Market Channel 端点 URL（只读）

| 属性 | 值 |
|------|-----|
| **数据类型** | str |
| **默认值** | wss://ws-subscriptions-clob.polymarket.com/ws/market |
| **取值范围** | 有效 wss:// URL |
| **必填/可选** | 必填 |
| **敏感信息** | 否 |
| **配置级别** | core |
| **所属分类** | module |

**📖 功能详解**：数据收集器的"电话号码"。这是 Polymarket 官方提供的 WebSocket Market Channel 端点，用于订阅实时市场数据推送。连接成功后，系统发送资产 ID 列表进行订阅，随后持续接收 `book`（订单簿变更）、`last_trade_price`（最新成交价）、`best_bid_ask`（最优报价）等事件。

> ⚠️ **重要提示**：此参数为只读配置，**请勿修改**。使用 Polymarket 官方提供的端点地址以确保数据准确性和协议兼容性。

**⚙️ 直接后果**：URL 错误 → WebSocket 连接失败，数据收集中断；修改为非官方端点 → 协议不兼容导致解析错误。

**🔗 关联参数**：`modules.market_data_collector.enabled`（必须开启才使用此 URL）

**❌ 错误配置症状**：改为 http:// → WebSocket 需要 wss:// 协议；改为自建代理 → 需确保完整转发协议。

**🔧 调试方法**：使用 `wscat` 工具手动连接此 URL 验证可达性。

**💡 新手推荐值**：**保持默认值不动** — 这是官方端点，修改会导致数据异常。

**三档建议值对照**：
| 场景 | 推荐值 | 理由 |
|------|--------|------|
| 🟢 正式使用 | （默认官方URL） | 官方端点，稳定可靠 |
| 🟡 平衡（默认） | （默认官方URL） | 请勿修改 |
| 🔴 代理模式 | 自建代理URL | 企业级部署经代理统一管控 |

---

#### `modules.strategy_engine.enabled` — 策略引擎开关

> 控制策略引擎模块是否启动

| 属性 | 值 |
|------|-----|
| **数据类型** | bool |
| **默认值** | true |
| **取值范围** | true / false |
| **必填/可选** | 可选 |
| **敏感信息** | 否 |
| **配置级别** | core |
| **所属分类** | module |

**📖 功能详解**：策略引擎是 SimplePolyBot 的"大脑"。它持续从 Redis 读取市场数据收集器缓存的订单簿和价格信息，运行配置的策略算法（如 base_cushion、trend_following 等），生成买入/卖出信号传递给订单执行器。**关闭此模块 = 系统瘫痪**——没有信号就没有交易。

**⚙️ 直接后果**：开启 → 持续分析市场数据，产出交易信号；关闭 → 无信号产生，订单执行器闲置，整个交易流水线断裂。

**🔗 关联参数**：`modules.market_data_collector.enabled`（上游数据源，关闭则引擎无数据可分析）、`modules.order_executor.enabled`（下游执行者）、`strategy.*`（所有策略参数都是引擎的输入）

**❌ 错误配置症状**：单独关闭策略引擎但保持执行器开启 → 执行器无单可下；开启引擎但数据收集器关闭 → 引擎基于陈旧数据产出垃圾信号。

**🔧 调试方法**：监控 `signals_generated`、`signal_confidence_distribution`、`strategy_cycle_time` 指标。

**💡 新手推荐值**：**true** — 核心模块，除非你想让系统"只看不买"否则必须开启。

**三档建议值对照**：
| 场景 | 推荐值 | 理由 |
|------|--------|------|
| 🟢 全自动交易 | ✅ true | 完整交易流水线运转 |
| 🟡 平衡（默认） | ✅ true | 默认开启 |
| 🔴 观察模式 | ❌ false | 只收集数据不执行交易，用于学习市场 |

---

#### `modules.order_executor.enabled` — 订单执行器开关

> 控制订单执行器模块是否启动

| 属性 | 值 |
|------|-----|
| **数据类型** | bool |
| **默认值** | true |
| **取值范围** | true / false |
| **必填/可选** | 可选 |
| **敏感信息** | 否 |
| **配置级别** | core |
| **所属分类** | module |

**📖 功能详解**：订单执行器是 SimplePolyBot 的"双手"。它接收策略引擎产生的交易信号，调用 CLOB Client API 向 Polymarket 提交订单（GTC/GTD/FOK/FAK），并持续跟踪订单状态（live → matched → confirmed）。同时管理已有订单的生命周期（取消、修改、到期处理）。

**⚙️ 直接后果**：开启 → 信号可以转化为真实交易，资金进出市场；关闭 → 策略引擎产出的信号全部被丢弃，系统变为"纸上谈兵"模式。

**🔗 关联参数**：`modules.strategy_engine.enabled`（上游信号源）、`api.polymarket.*`（API 凭证，执行器必需）、`strategy.order_sizes.*`（订单金额参数）

**❌ 错误配置症状**：开启但 API 凭证缺失 → 每次下单都报认证错误；关闭但策略引擎开启 → 信号堆积浪费计算资源。

**🔧 调试方法**：跟踪 `orders_submitted`、`orders_filled`、`orders_rejected`、`average_fill_latency` 指标。

**💡 新手推荐值**：**true** — 核心模块，关闭等于关掉了赚钱的能力。

**三档建议值对照**：
| 场景 | 推荐值 | 理由 |
|------|--------|------|
| 🟢 实盘交易 | ✅ true | 信号转化为真实订单 |
| 🟡 平衡（默认） | ✅ true | 默认开启 |
| 🔴 模拟/Dry-run | ❌ false | 验证策略逻辑但不真金白银下单 |

---

#### `modules.settlement_worker.enabled` — 结算工作器开关

> 控制结算工作器模块是否启动

| 属性 | 值 |
|------|-----|
| **数据类型** | bool |
| **默认值** | true |
| **取值范围** | true / false |
| **必填/可选** | 可选 |
| **敏感信息** | 否 |
| **配置级别** | standard |
| **所属分类** | module |

**📖 功能详解**：结算工作器是 SimplePolyBot 的"收银员"。当 Polymarket 上的预测市场到期结算后，工作器自动检测已结束的市场，对赢得的代币发起赎回（redeem）操作，将 USDC 收回账户。如果没有这个模块，你可能赢了市场却忘了去领奖。

**⚙️ 直接后果**：开启 → 已结算市场的代币自动赎回，USDC 及时回笼；关闭 → 代币停留在钱包中，需要手动通过 Polymarket UI 或合约交互赎回。

**🔗 关联参数**：`api.polymarket.*`（赎回操作需要 API 认证）、`modules.market_data_collector.enabled`（需要市场状态数据来判断是否已结算）

**❌ 错误配置症状**：长期关闭 → 大量已赢代币未赎回，资金被锁定；API 凭证过期 → 赎回操作反复失败。

**🔧 调试方法**：查看 `markets_settled`、`tokens_redeemed`、`usdc_recovered` 统计。

**💡 新手推荐值**：**true** — 自动赎回是基本功能，不要让赢的钱躺在那里。

**三档建议值对照**：
| 场景 | 推荐值 | 理由 |
|------|--------|------|
| 🟢 自动化管理 | ✅ true | 到期自动赎回，无需人工干预 |
| 🟡 平衡（默认） | ✅ true | 默认开启 |
| 🔴 手动管理 | ❌ false | 自己通过 UI 手动赎回（不推荐） |

---

## 5.4 Category 4：API 参数（3 个）

API 参数包含与 Polymarket CLOB 交互所需的三件套认证凭证。**这是系统中安全等级最高的参数组**。

> 🔒🔒🔒 **最高安全警告**：以下三个参数均为**极度敏感信息**。泄露任何一个都将导致他人可以冒充你的身份进行交易操作，包括但不限于：买卖你的持仓、提取你的资金、篡改你的订单。**必须且只能通过环境变量注入**，严禁明文存储在任何文件中。

---

#### `api.polymarket.api_key` — Polymarket API Key 🔒🔒🔒

> Polymarket CLOB API 密钥标识符，用于请求身份认证

| 属性 | 值 |
|------|-----|
| **数据类型** | str |
| **默认值** | （空字符串） |
| **取值范围** | 由 Polymarket 生成的密钥字符串 |
| **必填/可选** | **必填** |
| **敏感信息** | **是 ⚠️⚠️⚠️** |
| **配置级别** | core |
| **所属分类** | api |

**📖 功能详解**：API 三件套之一——身份标识。当你的系统向 Polymarket CLOB 发送请求时，这个 key 告诉服务器"我是谁"。它在 HTTP Header 中以 `API-Key` 字段传输。你需要通过 Polymarket 后台的 Developer Settings 页面生成这组凭证。

> 🔴 **严重警告**：
> - **绝对禁止**将此值明文写入 `settings.yaml` 或任何代码文件
> - **绝对禁止**将包含此值的文件提交到 Git 仓库
> - **必须**通过环境变量 `${POLYMARKET_API_KEY}` 注入
> - 泄露后果：他人可冒充你的身份进行所有交易操作

**⚙️ 直接后果**：缺失或错误 → 所有 API 请求返回 401/403 错误，系统完全无法运行。

**🔗 关联参数**：`api.polymarket.api_secret`（签名密钥，必须配对）、`api.polymarket.api_passphrase`（口令短语，三件套缺一不可）

**❌ 错误配置症状**：Key 无效 → `Invalid API Key` 错误；Key 过期 → 需要在 Polymarket 后台重新生成；Key 泄露 → **立即撤销并在后台重新生成**。

**🔧 调试方法**：使用 curl 测试 `curl -H "API-Key: YOUR_KEY" https://clob.polymarket.com/time` 验证有效性。

**💡 新手推荐值**：**通过环境变量注入** — 去 Polymarket 后台 Settings → API Keys 创建新的 API Key。

**三档建议值对照**：
| 场景 | 推荐值 | 理由 |
|------|--------|------|
| 🟢 开发环境 | ${POLYMARKET_API_KEY} | 环境变量注入，.env 文件管理 |
| 🟡 平衡（默认） | ${POLYMARKET_API_KEY} | 唯一正确的方式 |
| 🔴 生产环境 | Secrets Manager | AWS/GCP KMS 托管，动态加载 |

---

#### `api.polymarket.api_secret` — Polymarket API Secret 🔒🔒🔒

> Polymarket CLOB API 签名密钥，HMAC-SHA256 签名验证

| 属性 | 值 |
|------|-----|
| **数据类型** | str |
| **默认值** | （空字符串） |
| **取值范围** | 由 Polymarket 生成的签名密钥字符串 |
| **必填/可选** | **必填** |
| **敏感信息** | **是 ⚠️⚠️⚠️** |
| **配置级别** | core |
| **所属分类** | api |

**📖 功能详解**：API 三件套之二——签名密钥。这是安全等级最高的凭证。系统使用此 secret 对每个 API 请求进行 HMAC-SHA256 签名，Polymarket 服务端用同样的 secret 验证签名，确保请求确实来自你且未被篡改。即使攻击者截获了你的请求，没有 secret 也无法伪造签名。

> 🔴 **严重警告**：此密钥的安全等级等同于**银行卡密码 + 支付密码的组合**。泄露意味着攻击者可以：
> - 以你的身份提交任意订单
> - 取消你的现有订单
> - 查询你的完整持仓和交易历史
> - **通过 Gnosis Safe 多签转移你的资金**

**⚙️ 直接后果**：缺失或错误 → 签名验证失败，所有写操作（下单/取消）被拒。

**🔗 关联参数**：`api.polymarket.api_key`（标识符）、`api.polymarket.api_passphrase`（口令）

**❌ 错误配置症状**：Secret 不匹配 Key → `Signature verification failed`；Secret 泄露 → **这是最危险的情况，必须立即轮换所有三个凭证**。

**🔧 调试方法**：使用 Polymarket 提供的签名验证工具或 SDK 自带的 `verifyCredentials()` 方法。

**💡 新手推荐值**：**通过环境变量 `${POLYMARKET_API_SECRET}` 注入** — 生成 API Key 时 Secret 只显示一次，务必妥善保存。

**三档建议值对照**：
| 场景 | 推荐值 | 理由 |
|------|--------|------|
| 🟢 开发环境 | ${POLYMARKET_API_SECRET} | .env 文件加入 .gitignore |
| 🟡 平衡（默认） | ${POLYMARKET_API_SECRET} | 唯一正确方式 |
| 🔴 生产环境 | AWS Secrets Manager | 加密存储 + 审计日志 + 自动轮换 |

---

#### `api.polymarket.api_passphrase` — Polymarket API Passphrase 🔒🔒🔒

> Polymarket CLOB API 口令短语，完成三件套认证

| 属性 | 值 |
|------|-----|
| **数据类型** | str |
| **默认值** | （空字符串） |
| **取值范围** | 由 Polymarket 生成的口令字符串 |
| **必填/可选** | **必填** |
| **敏感信息** | **是 ⚠️⚠️⚠️** |
| **配置级别** | core |
| **所属分类** | api |

**📖 功能详解**：API 三件套之三——口令短语。配合 api_key 和 api_secret 一起构成完整的认证体系。在某些 API 端点中，passphrase 作为额外的验证因子传输，提供 beyond-key-and-secret 的安全保障。三个参数缺一不可，任何一个缺失都会导致认证失败。

> 🔴 **严重警告**：与 api_secret 相同的安全等级。三件套中任何一个泄露都应视为**全套凭证泄露**，必须立即在 Polymarket 后台撤销并重新生成全部三个。

**⚙️ 直接后果**：缺失 → 部分端点返回认证错误；与 key/secret 不匹配 → 同样认证失败。

**🔗 关联参数**：`api.polymarket.api_key`、`api.polymarket.api_secret`（三件套必须来自同一次生成）

**❌ 错误配置症状**：Passphrase 来自不同批次的 Key/Secret → 认证不匹配；Passphrase 含特殊字符 → 注意 YAML 转义和引号处理。

**🔧 调试方法**：SDK 的 `createOrDeriveApiKey()` 方法会一次性返回三件套，确保一致性。

**💡 新手推荐值**：**通过环境变量 `${POLYMARKET_API_PASSPHRASE}` 注入** — 与另外两个凭证一起管理。

**三档建议值对照**：
| 场景 | 推荐值 | 理由 |
|------|--------|------|
| 🟢 开发环境 | ${POLYMARKET_API_PASSPHRASE} | .env 文件统一管理三个凭证 |
| 🟡 平衡（默认） | ${POLYMARKET_API_PASSPHRASE} | 唯一正确方式 |
| 🔴 生产环境 | HashiCorp Vault | 企业级秘密管理方案 |

---

## 5.5 Category 5：System 系统参数（2 个）

系统参数定义运行时环境和日志行为，影响整个系统的全局表现。

---

#### `system.environment` — 运行环境模式

> 当前系统的运行环境：development / staging / production

| 属性 | 值 |
|------|-----|
| **数据类型** | str |
| **默认值** | development |
| **取值范围** | development / staging / production |
| **必填/可选** | 可选 |
| **敏感信息** | 否 |
| **配置级别** | core |
| **所属分类** | system |

**📖 功能详解**：全局环境开关。不同环境下系统的行为有显著差异：
- **development**：详细日志、宽松校验、模拟模式可用、调试接口开放
- **staging**：类生产配置但使用测试数据/测试网络，用于预发布验证
- **production**：精简日志、严格校验、安全加固、性能优化全开

许多模块会根据此值自动调整行为，如日志详细程度、安全检查严格度、监控采样频率等。

**⚙️ 直接后果**：development → 方便调试但性能较低、安全性较弱；production → 最佳性能和安全但问题排查较困难。

**🔗 关联参数**：`system.log_level`（通常 production 用 INFO/WARNING，development 用 DEBUG）、`api.polymarket.*`（production 必须使用真实凭证）

**❌ 错误配置症状**：production 环境使用了 development 配置 → 安全漏洞和性能问题；development 环境误用 production 配置 → 调试困难且可能产生真实交易。

**🔧 调试方法**：检查启动日志中的 `environment: xxx` 确认当前模式。

**💡 新手推荐值**：**development** — 学习和调试阶段保持在开发模式。

**三档建议值对照**：
| 场景 | 推荐值 | 理由 |
|------|--------|------|
| 🟢 本地开发 | development | 完整 DEBUG 日志，宽松校验 |
| 🟡 预发布验证 | staging | 接近生产的配置，测试网数据 |
| 🔴 正式上线 | production | 性能优化+安全加固+精简日志 |

---

#### `system.log_level` — 日志级别

> 全局日志输出的详细程度

| 属性 | 值 |
|------|-----|
| **数据类型** | str |
| **默认值** | INFO |
| **取值范围** | DEBUG / INFO / WARNING / ERROR / CRITICAL |
| **必填/可选** | 可选 |
| **敏感信息** | 否 |
| **配置级别** | core |
| **所属分类** | system |

**📖 功能详解**：控制日志管道的"过滤器粗细"。Python logging 标准五级：
- **DEBUG**：最详细信息，包括每个变量的值、每次函数调用——仅用于开发调试
- **INFO**：正常运行信息，订单提交、连接建立、策略信号——生产环境推荐
- **WARNING**：潜在问题，重试操作、参数接近边界、非致命异常
- **ERROR**：操作失败，订单被拒、API 调用失败、数据解析错误
- **CRITICAL**：系统级故障，无法恢复的错误、安全告警、资金相关异常

**⚙️ 直接后果**：DEBUG → 日志量巨大（可能 GB/小时），磁盘空间消耗快但问题定位容易；CRITICAL → 几乎无日志输出，出了问题无从查起。

**🔗 关联参数**：`system.environment`（通常联动配置）、磁盘监控告警（日志量过大时触发）

**❌ 错误配置症状**：生产环境用 DEBUG → 磁盘打满、IO 竞争影响交易性能；开发环境用 CRITICAL → 看不到任何有用信息。

**🔧 调试方法**：`grep -c "LEVEL" app.log` 统计各级别日志数量；检查日志文件增长率。

**💡 新手推荐值**：**DEBUG** — 学习阶段需要尽可能多的信息来理解系统行为。

**三档建议值对照**：
| 场景 | 推荐值 | 理由 |
|------|--------|------|
| 🟢 问题排查 | DEBUG | 全量日志，逐行追踪代码执行路径 |
| 🟡 平衡（默认） | INFO | 标准信息量，覆盖关键业务事件 |
| 🔴 生产运行 | WARNING | 仅记录异常和警告，最小化 IO 开销 |

---

## 5.6 Category 6：MarketDiscovery 市场发现参数（6 个）

> 🆕 **Phase 1 新增**：MarketDiscovery 模块负责自动扫描 Polymarket Gamma API 和 CLOB API，发现符合条件的 Fast Market 市场（如 "Bitcoin Up or Down - 5 Minutes"），替代手动配置 token_id 的方式。

---

#### `strategy.market_discovery.enabled` — 市场发现模块开关

> 控制市场发现模块是否启用

| 属性 | 值 |
|------|-----|
| **数据类型** | bool |
| **默认值** | true |
| **取值范围** | true / false |
| **必填/可选** | 可选 |
| **敏感信息** | 否 |
| **配置级别** | core |
| **所属分类** | market_discovery |

**📖 功能详解**：Fast Market 策略必须开启此模块。开启后，系统会定时扫描 Gamma API 获取活跃的 Fast Market 列表，通过 slug_prefix 过滤出目标市场（如 `btc-updown-5m`），并将结果缓存供策略引擎使用。

**⚙️ 直接后果**：关闭 → 无法自动发现新市场，只能依赖手动配置；开启 → 自动跟踪每 5 分钟滚动生成的新 Fast Market 实例。

**🔗 关联参数**：`strategy.market_discovery.slug_prefix`（过滤目标）、`strategy.market_discovery.refresh_interval`（扫描频率）

**❌ 错误配置症状**：关闭且无手动 token_id → 策略引擎无市场可交易；slug_prefix 配置错误 → 找不到匹配的市场

**🔧 调试方法**：查看日志中 `market_discovered` / `no_matching_markets` 事件频率

**💡 新手推荐值**：**true**

#### `strategy.market_discovery.gamma_api_url` — Gamma API 地址

> Polymarket Gamma API 的基础 URL

| 属性 | 值 |
|------|-----|
| **数据类型** | str |
| **默认值** | https://gamma-api.polymarket.com |
| **取值范围** | 有效 URL |
| **必填/可选** | 必填 |
| **敏感信息** | 否 |
| **配置级别** | core |
| **所属分类** | market_discovery |

**📖 功能详解**：Gamma API 是 Polymarket 官方提供的市场元数据查询接口，用于获取事件列表、市场信息、标签过滤等。MarketDiscovery 通过此 API 发现可交易的 Fast Market。

**⚙️ 直接后果**：URL 错误 → 所有市场发现请求失败；使用非官方地址 → 数据格式可能不兼容

**🔧 调试方法**：`curl {gamma_api_url}/events?limit=1` 验证可达性

**💡 新手推荐值**：保持默认官方地址

#### `strategy.market_discovery.clob_api_url` — CLOB API 地址

> Polymarket CLOB API 的基础 URL

| 属性 | 值 |
|------|-----|
| **数据类型** | str |
| **默认值** | https://clob.polymarket.com |
| **取值范围** | 有效 URL |
| **必填/可选** | 必填 |
| **敏感信息** | 否 |
| **配置级别** | core |
| **所属分类** | market_discovery |

**📖 功能详解**：CLOB API 用于获取订单簿深度、交易量等实时数据，辅助判断市场的流动性和活跃度。

**💡 新手推荐值**：保持默认官方地址

#### `strategy.market_discovery.cache_ttl` — 缓存生存时间 (TTL)

> 市场发现结果的缓存时间（秒）

| 属性 | 值 |
|------|-----|
| **数据类型** | int |
| **默认值** | 300 |
| **取值范围** | 60 ~ 3600 |
| **必填/可选** | 可选 |
| **敏感信息** | 否 |
| **配置级别** | standard |
| **所属分类** | market_discovery |

**📖 功能详解**：在此时间内重复查询将返回缓存结果，减少 API 调用频率，避免触发速率限制。

**三档建议值对照**：
| 场景 | 推荐值 | 理由 |
|---|---|---|
| 低频模式 | 600 | 10 分钟刷新一次，节省 API 配额 |
| 平衡（默认） | 300 | 5 分钟刷新，Fast Market 滚动周期合理 |
| 高频模式 | 120 | 2 分钟刷新，最快捕捉新市场 |

#### `strategy.market_discovery.slug_prefix` — 市场 Slug 前缀过滤

> 用于筛选目标市场的 slug 前缀模式

| 属性 | 值 |
|------|-----|
| **数据类型** | str |
| **默认值** | btc-updown-5m |
| **取值范围** | 预定义列表 |
| **必填/可选** | 可选 |
| **敏感信息** | 否 |
| **配置级别** | standard |
| **所属分类** | market_discovery |

**📖 功能详解**：只有 slug 匹配此前缀的市场才会被策略引擎处理。Polymarket 的 Fast Market slug 格式为 `{prefix}-{timestamp}`，如 `btc-updown-5m-1743900000`。

**可选值**：
| 值 | 对应市场类型 |
|---|---|
| btc-updown-5m | Bitcoin Up or Down - 5 Minutes ⭐ 默认 |
| btc-updown-15m | Bitcoin Up or Down - 15 Minutes |
| btc-updown-1h | Bitcoin Up or Down - 1 Hour |

#### `strategy.market_discovery.refresh_interval` — 市场刷新间隔

> 定时刷新活跃市场列表的间隔时间（秒）

| 属性 | 值 |
|------|-----|
| **数据类型** | int |
| **默认值** | 60 |
| **取值范围** | 30 ~ 300 |
| **必填/可选** | 可选 |
| **敏感信息** | 否 |
| **配置级别** | standard |
| **所属分类** | market_discovery |

**📖 功能详解**：控制 MarketDiscovery 模块扫描新市场的频率。Fast Market 每 5 分钟滚动一次，因此 60 秒的刷新间隔是合理的——不会错过任何新实例，也不会过度消耗 API 配额。

**三档建议值对照**：
| 场景 | 推荐值 | 理由 |
|---|---|---|
| 慢速 | 120 | 2 分钟刷新，适合低频交易策略 |
| 平衡（默认） | 60 | 1 分钟刷新，标准 Fast Market 策略 |
| 快速 | 30 | 30 秒刷新，需要最早发现新市场时使用 |

---

## 5.7 Category 7：RiskManager 风控管理器参数（5 个）

> 🆕 **Phase 1 新增**：RiskManager 是独立的风控管理器模块，与 strategy.risk_management 配置协同工作，提供账户级别的实时风险监控和熔断机制。

> ⚠️ 注意：以下参数在 `parameter_registry.py` 中注册于 `strategy.risk_management.*` 路径下，但作为独立 RiskManager 模块的运行时参数参考。

| # | 参数路径 | 中文名 | 默认值 | 取值范围 | 一句话功能 |
|---|---|---|---|---|---|
| 1 | `strategy.risk_management.max_position_size` | 单市场最大持仓 | **5000** | 100 ~ 100000 | 单个预测市场中允许持有的最大仓位金额（USDC） |
| 2 | `strategy.risk_management.max_total_exposure` | 总风险敞口上限 | **20000** | 1000 ~ 500000 | 所有持仓的总金额上限（USDC） |
| 3 | `strategy.risk_management.max_daily_loss` | 日最大亏损限额 | **500** | 50 ~ 50000 | 每日允许的最大亏损金额（USDC） |
| 4 | `strategy.risk_management.max_drawdown` | 最大回撤比例 | **0.15** | 0.05 ~ 0.50 | 从账户峰值允许的最大回撤比例 |
| 5 | `strategy.risk_management.min_balance` | 最小保留余额 | **100** | 10 ~ 10000 | 账户中必须保留的最小 USDC 余额 |

**详细说明请参见 [第 3 章 3.5.4 节](#354-风险管理参数5-个)**，此处为速查索引。RiskManager 模块在运行时读取这些参数并执行：

- **开仓前检查**：每次下单前验证 `max_position_size` 和 `max_total_exposure`
- **日内熔断**：实时追踪 P&L，触及 `max_daily_loss` 时停止开仓
- **回撤保护**：持续监控权益曲线，超出 `max_drawdown` 时触发人工确认
- **余额底线**：确保可用余额 ≥ `min_balance`，防止无法支付 Gas

---

## 5.8 Category 8：StopLossMonitor 止损监控器参数（3 个）

> 🆕 **Phase 1 新增**：StopLossMonitor 是独立运行的止损止盈监控模块，即使全局止损止盈开关开启，也可通过此模块的独立开关进行细粒度控制。

---

#### `stop_loss_monitor.enabled` — 止损监控器独立开关

> 止损监控器模块的独立启用开关

| 属性 | 值 |
|------|-----|
| **数据类型** | bool |
| **默认值** | true |
| **取值范围** | true / false |
| **必填/可选** | 可选 |
| **敏感信息** | 否 |
| **配置级别** | standard |
| **所属分类** | risk_control |

**📖 功能详解**：即使全局 `stop_loss_take_profit.enabled` 为 true，也可通过此参数单独关闭止损监控器。两者都为 true 时止损功能才生效。这提供了更精细的控制粒度——例如在调试订单执行器时可以单独关闭止损而不影响其他风控逻辑。

**🔗 关联参数**：`strategy.stop_loss_take_profit.enabled`（全局开关，必须同时为 true）

**💡 新手推荐值**：**true**

#### `stop_loss_monitor.check_interval` — 止损检查间隔

> 止损监控器扫描持仓并评估止损/止盈条件的间隔时间（秒）

| 属性 | 值 |
|------|-----|
| **数据类型** | int |
| **默认值** | 30 |
| **取值范围** | 5 ~ 300 |
| **必填/可选** | 可选 |
| **敏感信息** | 否 |
| **配置级别** | standard |
| **所属分类** | risk_control |

**📖 功能详解**：越频繁则响应越快但资源消耗越大。Fast Market 结算周期仅 5 分钟，建议使用较短间隔确保及时止损。

**三档建议值对照**：
| 场景 | 推荐值 | 适用场景 |
|---|---|---|
| 实时模式 | 10 | Fast Market 高频止损需求 |
| 平衡（默认） | 30 | 标准 Fast Market 策略 |
| 宽松模式 | 60 | 普通市场或低频交易 |

#### `stop_loss_monitor.notification_threshold` — 止损通知阈值

> 触发通知的最低亏损金额（USDC）

| 属性 | 值 |
|------|-----|
| **数据类型** | int |
| **默认值** | 50 |
| **取值范围** | 10 ~ 10000 |
| **必填/可选** | 可选 |
| **敏感信息** | 否 |
| **配置级别** | advanced |
| **所属分类** | risk_control |

**📖 功能详解**：仅当单次止损平仓亏损超过此值时发送告警通知，避免过多无效告警淹没重要信息。建议设置为 `min_order_size` 的 2-5 倍。

**三档建议值对照**：
| 场景 | 推荐值 | 理由 |
|---|---|---|
| 敏感 | 20 | 几乎所有止损都通知 |
| 平衡（默认） | 50 | 只关注有意义的亏损 |
| 宽容 | 200 | 仅大额亏损才打扰 |

---

## 5.9 Category 9：SignalAdapter 信号适配器参数（4 个）

> 🆕 **Phase 1 新增**：SignalAdapter 模块负责将策略引擎生成的原始信号转换为标准化的订单格式，处理订单大小映射、字段校验等工作，是 Strategy Engine 与 Order Executor 之间的桥梁。

---

#### `signal_adapter.default_size` — 信号适配器默认订单大小

> 信号适配器将策略信号转换为订单时的默认下单金额（USDC）

| 属性 | 值 |
|------|-----|
| **数据类型** | int |
| **默认值** | 100 |
| **取值范围** | 10 ~ 10000 |
| **必填/可选** | 可选 |
| **敏感信息** | 否 |
| **配置级别** | core |
| **所属分类** | signal_adapter |

**📖 功能详解**：当信号中没有指定特殊金额、或 size_map 匹配失败时使用的默认下单量。应与 `strategy.order_sizes.default` 保持一致或略小。

**三档建议值对照**：
| 场景 | 推荐值 | 单笔风险 |
|---|---|---|
| 保守 | 50 | 约 $25（按 $0.50/代币计算） |
| 平衡（默认） | 100 | 约 $50 |
| 激进 | 500 | 约 $250 |

#### `signal_adapter.min_size` — 信号适配器最小订单大小

> 信号适配器允许的最小下单金额（USDC）

| 属性 | 值 |
|------|-----|
| **数据类型** | int |
| **默认值** | 10 |
| **取值范围** | 1 ~ 5000 |
| **必填/可选** | 可选 |
| **敏感信息** | 否 |
| **配置级别** | standard |
| **所属分类** | signal_adapter |

**📖 功能详解**：低于此值的信号将被忽略或合并到下一笔交易。防止产生"蚂蚁仓"——手续费即可吞噬全部潜在利润的无效订单。

**🔗 关联参数**：必须 ≤ `default_size` 且 ≤ `max_size`

**💡 新手推荐值**：**25**（新手阶段避免小额噪音交易）

#### `signal_adapter.max_size` — 信号适配器最大订单大小

> 信号适配器允许的最大下单金额（USDC）

| 属性 | 值 |
|------|-----|
| **数据类型** | int |
| **默认值** | 1000 |
| **取值范围** | 100 ~ 50000 |
| **必填/可选** | 可选 |
| **敏感信息** | 否 |
| **配置级别** | standard |
| **所属分类** | signal_adapter |

**📖 功能详解**：超过此值的信号将被拆分或截断。这是 SignalAdapter 层面的硬性限制，与 Strategy Engine 的 `order_sizes.max` 形成双重保险。

**🔗 关联参数**：必须 ≥ `default_size` 且 ≥ `min_size`

**💡 新手推荐值**：**500**（强制分批操作养成好习惯）

#### `signal_adapter.size_map` — 信号强度到订单大小映射表

> 根据策略信号置信度/强度映射到不同订单大小的配置字典

| 属性 | 值 |
|------|-----|
| **数据类型** | dict |
| **默认值** | {"high": 500, "medium": 200, "low": 50} |
| **取值范围** | 键: 字符串, 值: 正整数 |
| **必填/可选** | 可选 |
| **敏感信息** | 否 |
| **配置级别** | advanced |
| **所属分类** | signal_adapter |

**📖 功能详解**：实现动态仓位管理——高置信信号用大仓位博取更高收益，低置信信号用小仓位控制风险。当信号等级无法匹配 size_map 中的键时，回退到 `default_size`。

**默认映射解读**：
| 信号等级 | 订单大小 | 使用场景 |
|---|---|---|
| high | 500 USDC | R² > 0.8 + 强趋势 + 大价差 |
| medium | 200 USDC | 标准合格信号 |
| low | 50 USDC | 勉强达标的边缘信号 |

---

### 5.10 参数速查表

> 📋 涵盖 `settings.yaml` 中全部 **56 个参数**的完整索引。Phase 1 新增 18 个参数（MarketDiscovery 6 + StopLossMonitor 3 + SignalAdapter 4 + RiskManager 索引 5）。

| # | 参数路径 | 分类 | 级别 | 默认值 | 敏感 |
|---|---------|------|------|--------|------|
| **Strategy 策略参数（17 个）** |||||
| 1 | `strategy.base_cushion` | strategy | core | 0.02 | ❌ |
| 2 | `strategy.alpha` | strategy | core | 0.5 | ❌ |
| 3 | `strategy.max_buy_prices.default` | strategy | core | 0.95 | ❌ |
| 4 | `strategy.max_buy_prices.high_confidence` | strategy | advanced | 0.98 | ❌ |
| 5 | `strategy.max_buy_prices.low_volatility` | strategy | advanced | 0.92 | ❌ |
| 6 | `strategy.max_buy_prices.fast_market` | strategy | expert | 0.90 | ❌ |
| 7 | `strategy.order_sizes.default` | strategy | core | 100 | ❌ |
| 8 | `strategy.order_sizes.min` | strategy | standard | 10 | ❌ |
| 9 | `strategy.order_sizes.max` | strategy | standard | 1000 | ❌ |
| 10 | `strategy.risk_management.max_position_size` | strategy | core | 5000 | ❌ |
| 11 | `strategy.risk_management.max_total_exposure` | strategy | core | 20000 | ❌ |
| 12 | `strategy.risk_management.max_daily_loss` | strategy | core | 500 | ❌ |
| 13 | `strategy.risk_management.max_drawdown` | strategy | core | 0.15 | ❌ |
| 14 | `strategy.risk_management.min_balance` | strategy | standard | 100 | ❌ |
| 15 | `strategy.stop_loss_take_profit.enabled` | strategy | standard | true | ❌ |
| 16 | `strategy.stop_loss_take_profit.stop_loss_percentage` | strategy | standard | 0.10 | ❌ |
| 17 | `strategy.stop_loss_take_profit.take_profit_percentage` | strategy | standard | 0.20 | ❌ |
| 18 | `redis.host` | connection | core | localhost | ❌ |
| 19 | `redis.port` | connection | core | 6379 | ❌ |
| 20 | `redis.password` | connection | core | "" | 🔒 |
| 21 | `redis.db` | connection | standard | 0 | ❌ |
| 22 | `redis.pool.max_connections` | connection | advanced | 50 | ❌ |
| 23 | `redis.pool.min_idle_connections` | connection | advanced | 5 | ❌ |
| 24 | `redis.pool.connection_timeout` | connection | advanced | 5 | ❌ |
| 25 | `redis.pool.socket_timeout` | connection | advanced | 5 | ❌ |
| 26 | `redis.retry.max_attempts` | connection | standard | 3 | ❌ |
| 27 | `redis.retry.retry_delay` | connection | standard | 1 | ❌ |
| 28 | `redis.retry.exponential_backoff` | connection | standard | true | ❌ |
| 29 | `modules.market_data_collector.enabled` | module | core | true | ❌ |
| 30 | `modules.market_data_collector.websocket.url` | module | core | wss://... | ❌ |
| 31 | `modules.strategy_engine.enabled` | module | core | true | ❌ |
| 32 | `modules.order_executor.enabled` | module | core | true | ❌ |
| 33 | `modules.settlement_worker.enabled` | module | standard | true | ❌ |
| 34 | `api.polymarket.api_key` | api | core | "" | 🔒🔒🔒 |
| 35 | `api.polymarket.api_secret` | api | core | "" | 🔒🔒🔒 |
| 36 | `api.polymarket.api_passphrase` | api | core | "" | 🔒🔒🔒 |
| 37 | `system.environment` | system | core | development | ❌ |
| 38 | `system.log_level` | system | core | INFO | ❌ |
| **🆕 MarketDiscovery 市场发现（6 个）** |||||
| 39 | `strategy.market_discovery.enabled` | market_discovery | core | true | ❌ |
| 40 | `strategy.market_discovery.gamma_api_url` | market_discovery | core | https://gamma-api.polymarket.com | ❌ |
| 41 | `strategy.market_discovery.clob_api_url` | market_discovery | core | https://clob.polymarket.com | ❌ |
| 42 | `strategy.market_discovery.cache_ttl` | market_discovery | standard | 300 | ❌ |
| 43 | `strategy.market_discovery.slug_prefix` | market_discovery | standard | btc-updown-5m | ❌ |
| 44 | `strategy.market_discovery.refresh_interval` | market_discovery | standard | 60 | ❌ |
| **🆕 StopLossMonitor 止损监控（3 个）** |||||
| 45 | `stop_loss_monitor.enabled` | risk_control | standard | true | ❌ |
| 46 | `stop_loss_monitor.check_interval` | risk_control | standard | 30 | ❌ |
| 47 | `stop_loss_monitor.notification_threshold` | risk_control | advanced | 50 | ❌ |
| **🆕 SignalAdapter 信号适配器（4 个）** |||||
| 48 | `signal_adapter.default_size` | signal_adapter | core | 100 | ❌ |
| 49 | `signal_adapter.min_size` | signal_adapter | standard | 10 | ❌ |
| 50 | `signal_adapter.max_size` | signal_adapter | standard | 1000 | ❌ |
| 51 | `signal_adapter.size_map` | signal_adapter | advanced | {dict} | ❌ |

> **总计：51 个参数** | Strategy: 17 | Connection: 11 | Module: 5 | API: 3 | System: 2 | **MarketDiscovery: 6** | **StopLossMonitor: 3** | **SignalAdapter: 4** | **敏感参数：4 个**（redis.password + API 三件套）
>
> 📊 **Phase 1 新增：18 个参数**（原 38 → 51，含 RiskManager 索引复用 strategy.risk_management.* 的 5 个参数）

---

### 5.11 parameter_registry.py 元数据验证说明

> ✅ **T3.3 验证结果**：[parameter_registry.py](../shared/parameter_registry.py) 已包含全部 **51 个参数**的完整元数据定义。

#### 参数注册函数分布

| 注册函数 | 参数数量 | 分类 | 对应文档章节 |
|---|---|---|---|
| `_register_strategy_params()` | 17 | strategy | [5.1 Category 1](#51-category-1strategy-策略参数17-个) |
| `_register_market_discovery_params()` | **6 🆕** | market_discovery | [5.6 Category 6](#56-category-6marketdiscovery-市场发现参数6-个) |
| `_register_signal_adapter_params()` | **4 🆕** | signal_adapter | [5.9 Category 9](#59-category-9signaladapter-信号适配器参数4-个) |
| `_register_stop_loss_monitor_params()` | **3 🆕** | risk_control | [5.8 Category 8](#58-category-8stoplossmonitor-止损监控器参数3-个) |
| `_register_redis_params()` | 11 | connection | [5.2 Category 2](#52-category-2connection-连接参数11-个) |
| `_register_module_params()` | 5 | module | 内嵌于各 Category |
| `_register_api_params()` | 3 | api | 内嵌于各 Category |
| `_register_system_params()` | 2 | system | [5.5 Category 5](#55-category-5system-系统参数2-个) |

#### 元数据完整性检查项

每个 ParameterInfo 记录均包含以下字段：

| 字段 | 必填 | 说明 |
|---|---|---|
| `key` | ✅ | 参数路径（如 `strategy.base_cushion`） |
| `name` | ✅ | 中文名称 |
| `description` | ✅ | 功能描述 |
| `type` | ✅ | 数据类型（int/float/str/bool/dict） |
| `default` | ✅ | 默认值 |
| `range` | 可选 | 取值范围元组 |
| `choices` | 可选 | 枚举可选值列表 |
| `required` | ✅ | 是否必填 |
| `sensitive` | ✅ | 是否敏感信息 |
| `category` | ✅ | 所属分类标识 |
| `level` | ✅ | 配置级别（core/standard/advanced/expert） |
| `suggestions` | 可选 | 三档建议值字典 |
| `depends_on` | 可选 | 关联参数列表 |
| `validation_hint` | ✅ | 验证提示信息 |

> 💡 **使用方式**：其他模块（如配置校验器、UI 表单渲染器、文档生成器）可通过 `ParameterRegistry.get_instance().get_all()` 获取完整参数列表，实现类型安全的配置管理。

<!-- CHAPTER_5_CONTENT_END -->

---

## 第 6 章：日常运维与监控

<!-- CHAPTER_6_CONTENT_START -->

### 6.1 每日巡检清单

以 checklist 格式呈现，每项包含命令和预期结果：

- [ ] **1. 检查所有模块运行状态**
  ```bash
  systemctl status simplepolybot-*
  # 或
  ps aux | grep -E "(market_data|strategy|order_executor|settlement)" | grep -v grep
  ```
  ✅ 预期：4 个进程全部 active (running)
  ❌ 异常：某个进程 dead / 不存在 → 见 8.2 节故障排查

- [ ] **2. 检查 Redis 连接状态**
  ```bash
  redis-cli -a YOUR_PASSWORD ping
  ```
  ✅ 预期：PONG

- [ ] **3. 查看最近错误日志**
  ```bash
  journalctl -u simplepolybot-* --since "24 hours ago" -p err --no-pager | tail -20
  # 或
  grep -i "error\|exception\|traceback" logs/*.log | tail -20
  ```

- [ ] **4. 检查钱包余额**
  （通过 Polymarket 网页或 API 查询 USDC.e 余额）

- [ ] **5. 检查当前持仓**
  （查看 settlement_worker 的历史记录或 Polymarket Portfolio）

- [ ] **6. 检查磁盘空间**
  ```bash
  df -h /opt/SimplePolyBot
  ```
  ✅ 预期：使用率 < 80%

- [ ] **7. 检查内存使用**
  ```bash
  free -h
  ```
  ✅ 预期：可用内存 > 500MB（2GB 服务器）

- [ ] **8. 检查今日交易统计**
  （查看 order_executor 日志中的 filled 订单数量）

### 6.2 启停操作命令全集

#### 单模块操作

```bash
# 启动单个模块
bash scripts/start_module.sh market_data_collector
bash scripts/start_module.sh strategy_engine
bash scripts/start_module.sh order_executor
bash scripts/start_module.sh settlement_worker

# 停止单个模块（systemd）
systemctl stop simplepolybot-market-data
systemctl stop simplepolybot-strategy-engine
systemctl stop simplepolybot-order-executor
systemctl stop simplepolybot-settlement-worker

# 重启单个模块
systemctl restart simplepolybot-market-data

# 查看状态
systemctl status simplepolybot-market-data
```

#### 全部模块操作

```bash
# 一键启动全部
bash scripts/start_all.sh

# 一键停止全部
systemctl stop simplepolybot-*.service

# 一键重启全部
systemctl restart simplepolybot-*.service

# 查看全部状态
systemctl status simplepolybot-*.service
```

### 6.3 日志查看技巧

常用命令组合：

```bash
# 实时跟踪日志
tail -f logs/market_data_collector.log
journalctl -u simplepolybot-market-data -f

# 搜索关键词
grep "BUY\|SELL" logs/strategy_engine.log | tail -20
grep "error" logs/*.log

# 按时间范围查看
journalctl -u simplepolybot-order-executor --since "2026-01-01" --until "2026-01-02"

# 统计错误数
grep -c "ERROR" logs/order_executor.log

# 查看最近的 N 行
tail -100 logs/settlement_worker.log
```

**日志级别含义表：**

| 级别 | 含义 | 何时关注 |
|------|------|----------|
| DEBUG | 最详细的调试信息 | 排查问题时临时开启 |
| INFO | 正常运行信息 | 日常监控 |
| WARNING | 警告（不影响运行） | 定期检查 |
| ERROR | 错误（需要关注） | **立即查看** |
| CRITICAL | 致命错误 | **立即处理** |

### 6.4 监控端口说明

```
:8080 — Health Check 端点
  GET http://216.238.91.89:8080/health
  返回: {"status": "healthy", "modules": {...}}
  用途：监控探活、负载均衡健康检查

:9090 — Metrics 端点
  GET http://216.238.91.89:9090/metrics
  返回: Prometheus 格式的指标数据
  用途：Grafana 数据源、性能监控
```

### 6.5 备份与恢复

```bash
# 备份配置文件
tar czf /opt/backups/config-$(date +%Y%m%d).tar.gz \
    config/settings.yaml .env config/presets/

# 备份数据目录
tar czf /opt/backups/data-$(date +%Y%m%d).tar.gz data/

# 自动备份脚本示例（可加入 crontab）
# 0 3 * * * /opt/scripts/backup.sh
```

**恢复步骤：**

1. 停止所有模块
2. 解压备份到对应目录
3. 重启所有模块
4. 验证日志正常

### 6.6 版本更新流程

```bash
# 1. 进入项目目录
cd /opt/SimplePolyBot

# 2. 停止所有模块
systemctl stop simplepolybot-*.service

# 3. 备份当前版本
cp -r . ../SimplePolyBot-backup-$(date +%Y%m%d)

# 4. 拉取最新代码
git pull origin main

# 5. 更新依赖（如有变化）
source venv/bin/activate
pip install -r requirements.txt

# 6. 重启所有模块
systemctl start simplepolybot-*.service

# 7. 验证启动成功
systemctl status simplepolybot-*.service
```

<!-- CHAPTER_6_CONTENT_END -->

---

## 第 7 章：常见问题 FAQ

<!-- CHAPTER_7_CONTENT_START -->

> 💡 **使用提示**：按 `Ctrl+F` 搜索关键词可快速定位问题。本章覆盖部署、配置、运行、账户四大阶段共 **34 个**高频问题。

---

## 第一部分：部署阶段 FAQ

---

### Q1: Python 版本太旧怎么办？

**A**: 先检查当前版本：

```bash
python3 --version
```

- 如果显示 **3.12 或更高**，无需操作（Ubuntu 24.04 自带 3.12）
- 如果显示 **3.8 或更旧**，执行以下命令升级：

```bash
sudo apt update
sudo apt install python3.12 python3.12-venv python3.12-dev -y
```

创建虚拟环境时使用新版本：

```bash
python3.12 -m venv venv
source venv/bin/activate
```

**原因解释**: Polymarket CLOB Client 和 web3.py 等库需要 Python 3.10+ 的语法特性（如 `match/case`、类型注解增强等），旧版本 Python 无法正确安装或运行这些依赖。

**预防措施**: 部署前第一时间执行 `python3 --version` 确认版本，养成在虚拟环境中工作的习惯。

---

### Q2: pip 安装报错 Permission denied？

**A**: 这是新手**最常遇到**的问题之一。请按顺序检查：

```bash
# 1️⃣ 确认是否已激活虚拟环境
which pip
# ✅ 正确输出：/opt/SimplePolyBot/venv/bin/pip
# ❌ 错误输出：/usr/bin/pip 或 /usr/local/bin/pip

# 2️⃣ 如果没激活，先激活
source /opt/SimplePolyBot/venv/bin/activate

# 3️⃣ 再次确认
which pip
# 现在应该指向 venv 目录了

# 4️⃣ 重新安装
pip install -r requirements.txt
```

**原因解释**: 你使用了**系统级 pip** 而非虚拟环境内的 pip。系统目录 `/usr/lib/` 需要 root 权限才能写入，而虚拟环境的 `venv/` 目录属于当前用户，不需要 sudo。

**预防措施**: 每次打开新终端窗口后，**第一件事就是** `source venv/bin/activate`。可以在 `~/.bashrc` 末尾添加别名提醒自己。

---

### Q3: Redis 安装后无法启动？

**A**: 逐步排查：

```bash
# 1️⃣ 查看 Redis 服务状态
sudo systemctl status redis-server

# 2️⃣ 如果显示 failed，查看详细日志
sudo journalctl -u redis-server -n 50

# 3️⃣ 常见修复——测试内存配置
sudo redis-server --test-memory 128

# 4️⃣ 手动启动看报错信息
sudo redis-server /etc/redis/redis.conf
```

常见错误及对应解决：

| 报错信息 | 原因 | 解决方法 |
|---|---|---|
| `Address already in use` | 端口被占用 | `ss -tlnp \| grep 6379` 找到并停掉占用进程 |
| `Can't open config file` | 配置文件路径错误 | `redis-server --dir /etc/redis` |
| `OOM` / `out of memory` | 服务器内存不足 | 见 **Q8** |

**原因解释**: Redis 启动失败通常是配置文件语法错误、端口冲突或服务器内存不足导致的。Redis 默认会占用可用内存的一定比例作为缓存。

**预防措施**: 安装完成后立即执行 `redis-cli ping` 验证，返回 `PONG` 表示正常。将 Redis 设为开机自启：`sudo systemctl enable redis-server`。

---

### Q4: git clone 超时或速度极慢？

**A**: 国内服务器访问 GitHub 经常不稳定。三种解决方案：

**方案一：使用镜像代理（推荐）**

```bash
git clone https://ghproxy.com/https://github.com/EatTake/SimplePolyBot.git
```

**方案二：使用 GitHub 镜像站**

```bash
git clone https://github.com/EatTake/SimplePolyBot.git
# 如果超时，换成：
git clone https://gitclone.com/github.com/EatTake/SimplePolyBot.git
```

**方案三：配置代理（如果你有）**

```bash
git config --global http.proxy http://127.0.0.1:7890
git config --global https.proxy http://127.0.0.1:7890
git clone https://github.com/EatTake/SimplePolyBot.git
# 用完后取消代理
git config --global --unset http.proxy
git config --global --unset https.proxy
```

**原因解释**: GitHub 的服务器在国外，国内网络连接经常受到干扰或限速。镜像站通过中转加速下载。

**预防措施**: 优先选择镜像站克隆。如果项目已克隆但后续 `git pull` 也慢，可以长期配置代理。

---

### Q5: venv 激活后提示找不到 python3？

**A**: 重建虚拟环境：

```bash
# 1️⃣ 退出当前环境（如果有的话）
deactivate

# 2️⃣ 删除旧的虚拟环境
rm -rf venv

# 3️⃣ 用系统默认 python3 重新创建
python3 -m venv venv

# 4️⃣ 激活
source venv/bin/activate

# 5️⃣ 验证
which python3
# 应该显示：/opt/SimplePolyBot/venv/bin/python3
python3 --version
```

**原因解释**: 虚拟环境创建时会"绑定"创建时的 Python 版本路径。如果之后系统 Python 路径变化（比如升级了 Python），或者 venv 是用错误的 python 创建的，激活后就找不到匹配的解释器了。

**预防措施**: 创建 venv 时始终使用 `python3 -m venv venv` 而不是直接调用某个具体版本的 python。

---

### Q6: numpy 或 web3 安装编译失败？

**A**: 这是因为缺少编译所需的系统依赖。执行：

```bash
# 安装基础编译工具
sudo apt install -y python3-dev build-essential libssl-dev pkg-config

# 如果是 numpy 编译失败，还需要：
sudo apt install -y libopenblas-dev liblapack-dev gfortran

# 清理之前的安装缓存后重试
pip cache purge
pip install numpy web3 --no-cache-dir
```

如果仍然失败，尝试使用预编译的 wheel 包：

```bash
pip install --only-binary :all: numpy web3
```

**原因解释**: `numpy` 底层是 C/Fortran 代码，需要在本地编译；`web3.py` 依赖一些需要 SSL 编译的原生库。没有这些开发包，pip 只能尝试从源码编译，很容易失败。

**预防措施**: 在首次 `pip install -r requirements.txt` 之前，先执行上面的依赖安装命令。大多数云服务器（Vultr、AWS 等）默认不包含这些开发包。

---

### Q7: 端口 6379 被 Redis 以外的服务占用了？

**A**: 排查并处理端口冲突：

```bash
# 1️⃣ 查看谁占用了 6379
ss -tlnp | grep 6379

# 输出示例：
# LISTEN  0  128  0.0.0.0:6379  0.0.0.0:*  users:(("redis-server",pid=12345,fd=7))
# 或者可能是其他进程

# 2️⃣ 如果是其他进程占用了
# 方案 A：停掉那个进程（如果你确定它没用）
sudo kill <PID>

# 方案 B：让 Redis 使用其他端口
sudo nano /etc/redis/redis.conf
# 找到 port 6379 改为 port 6380
```

如果改了 Redis 端口，记得同步修改 `.env` 文件中的 `REDIS_HOST`：

```env
REDIS_HOST=localhost:6380
```

**原因解释**: 一台服务器上可能运行着多个服务，端口是服务的"门牌号"，不能重复。默认情况下 Redis 使用 6379，但其他软件也可能选用这个端口。

**预防措施**: 部署前先用 `ss -tlnp` 查看哪些端口已被占用，提前规划端口分配。

---

### Q8: 内存不足 OOM（Out of Memory）？

**A**: 2GB RAM 的入门级服务器特别容易出现这个问题。紧急处理步骤：

```bash
# 1️⃣ 查看内存使用情况
free -h

# 2️⃣ 创建 2GB swap 分区（虚拟内存）
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 3️⃣ 设置开机自动挂载 swap
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# 4️⃣ 限制 Redis 最大内存（避免吃掉所有内存）
sudo nano /etc/redis/redis.conf
# 添加或修改：
# maxmemory 256mb
# maxmemory-policy allkeys-lru

# 5️⃣ 重启 Redis 使配置生效
sudo systemctl restart redis-server
```

同时关闭不必要的服务来释放内存：

```bash
# 查看占用内存最多的进程
ps aux --sort=-%mem | head -10
```

**原因解释**: Linux 的 OOM Killer 会在物理内存耗尽时强制杀掉占用内存最大的进程——很可能就是你的机器人或 Redis。2GB 服务器同时跑 Redis + Python 模块确实比较紧张。

**预防措施**: 至少使用 2GB RAM 的服务器，并按照上述步骤预先配置 swap。定期 `free -h` 监控内存使用情况。

---

### Q9: 防火墙 ufw 启动后被锁在外面了？

**A**: 别慌！通过云服务商控制面板的 **VNC Console**（远程控制台）登录：

```bash
# 通过 VNC 登录后执行：

# 1️⃣ 临时关闭防火墙
sudo ufw disable

# 2️⃣ 查看当前的规则（找出哪条规则把你锁在外面了）
sudo ufw status verbose

# 3️⃣ 正确的 SSH 开放方式应该是：
sudo ufw allow 22/tcp
sudo ufw allow ssh

# 4️⃣ 确认规则无误后再重新启用
sudo ufw enable
```

**正确的防火墙初始配置**（防止再次发生）：

```bash
# 默认拒绝所有入站
sudo ufw default deny incoming
# 默认允许所有出站
sudo ufw default allow outgoing
# 开放 SSH
sudo ufw allow 22/tcp
# 开放 HTTP/HTTPS（如果需要）
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
# 启用防火墙
sudo ufw enable
```

**原因解释**: `ufw enable` 会立即生效。如果在开放 SSH 端口之前就启用了防火墙，你的 SSH 连接会被直接切断，而服务器本身还在运行——只是你连不上去了。

**预防措施**: **永远先添加 allow 规则，再执行 ufw enable**。每次修改规则前先确认 SSH 端口（22）是开放的。

---

### Q10: apt update 报错 "repository does not have a Release file"?

**A**: 这是软件源列表损坏导致的。逐步修复：

```bash
# 1️⃣ 查看有哪些源文件
ls /etc/apt/sources.list.d/

# 2️⃣ 找到可疑的第三方源文件（尤其是 PPA）
# 常见的罪魁祸首：已经失效的 PPA、手动添加的错误源

# 3️⃣ 备份后删除有问题的源文件
sudo mv /etc/apt/sources.list.d/有问题的文件.list /tmp/

# 4️⃣ 重新更新
sudo apt update

# 5️⃣ 如果还不行，重置为官方默认源
sudo cp /etc/apt/sources.list /etc/apt/sources.list.bak
# 然后用官方源内容替换 sources.list（Ubuntu 24.04 默认源即可）
```

**原因解释**: Ubuntu 从各种软件仓库（repository）获取软件包列表。如果某个仓库地址错误、过期或不可达，`apt update` 就会报错并中断整个更新过程。

**预防措施**: 尽量只使用 Ubuntu 官方源和知名第三方源。添加 PPA 前确认该 PPA 仍维护中。

---

## 第二部分：配置阶段 FAQ

---

### Q11: Polymarket API Key 在哪里获取？

**A**: 按以下步骤操作：

1. 打开浏览器访问 [polymarket.com](https://polymarket.com) 并登录
2. 点击右上角**头像图标**
3. 选择 **Profile**（个人资料）
4. 找到 **API Access** 区域
5. 点击 **Create API Key**
6. 系统会生成三个值：
   - `API Key`
   - `API Secret` ⚠️
   - `API Passphrase`

> ⚠️ **极其重要**：`api_secret` **只显示一次**！页面关闭后就再也看不到了。务必立即复制并妥善保存。

将这三个值填入 `.env` 文件对应位置：

```env
POLY_API_KEY=你的api_key
POLY_API_SECRET=你的api_secret
POLY_API_PASSPHRASE=你的api_passphrase
```

**原因解释**: API 凭证是程序代替你执行交易的"数字身份证"。Secret 相当于密码，Polymarket 为了安全考虑只在创建时显示一次。

**预防措施**: 获取后立即填写到 `.env` 中，并将 `.env` 文件权限设为 `chmod 600 .env`（仅所有者可读写）。另外把凭证备份到安全的密码管理器中。

---

### Q12: MetaMask 私钥格式不对？

**A**: 私钥有严格的格式要求：

```
✅ 正确格式：0x + 64位十六进制字符 = 总共66个字符
示例：0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef

❌ 常见错误：
• 多了空格或换行符 → 复制时连带空格一起复制了
• 少了字符 → 复制不完整
• 没有 0x 前缀 → 有些工具要求带前缀
• 大小写混用 → 十六进制不区分大小写，但保持一致更好
```

**如何获取正确的私钥**：

1. 打开 MetaMask 浏览器扩展
2. 点击右上角三个点 → **账户详情**
3. 点击 **导出私钥**（需要输入 MetaMask 密码）
4. 全选复制（确保没有多余空格）

**验证私钥格式**：

```bash
# 在 Python 中验证长度
python3 -c "
key = '你的私钥'
assert key.startswith('0x'), '必须以0x开头'
assert len(key) == 66, f'长度应为66，实际{len(key)}'
int(key, 16)  # 验证是否为合法十六进制
print('✅ 私钥格式正确')
"
```

**原因解释**: 私钥是以太坊钱包的核心凭证，格式由以太坊标准定义。任何格式错误都会导致签名失败，进而无法在 Polymarket 上交易。

**预防措施**: 私钥泄露 = 资产丢失。**绝不要**将私钥提交到 Git、发到聊天工具、或存储在不安全的地方。使用环境变量或密钥管理服务存储。

---

### Q13: 找不到 .env 文件？

**A**: `.env` 文件的位置和创建方法：

```bash
# 1️⃣ 确认你在项目根目录
cd /opt/SimplePolyBot

# 2️⃣ 列出隐藏文件（以.开头的文件默认不显示）
ls -la

# 3️⃣ 如果没有 .env，从模板创建
cp .env.example .env

# 4️⃣ 编辑填入你的配置
nano .env
```

`.env` 文件的完整路径应该是：

```
/opt/SimplePolyBot/.env
```

**原因解释**: `.env` 文件名以点号开头，在 Linux 中表示隐藏文件。`ls` 命令默认不显示隐藏文件，所以很多新手以为文件"不存在"。此外，`.env` 已经被加入 `.gitignore`，不会随代码一起 clone 下来，需要手动从模板创建。

**预防措施**: `ls -la` 是好习惯，可以看到所有文件包括隐藏文件。部署完成后的第一步就是 `cp .env.example .env` 并填写配置。

---

### Q14: 配置向导报错 "Invalid value for xxx"？

**A**: 这说明输入的值不符合验证规则。处理方法：

```bash
# 1️⃣ 先用验证模式检查现有配置，不会修改任何东西
python -m modules.config_wizard --validate-only

# 2️⃣ 向导会告诉你哪个字段有问题、正确范围是什么
# 例如：
# ❌ ERROR: min_confidence must be between 0.0 and 1.0, got 150
# ❌ ERROR: max_position_size must be a positive integer, got -5

# 3️⃣ 重新运行向导，输入合法值
python -m modules.config_wizard
```

**常见值的合法范围参考**：

| 参数名 | 合法范围 | 示例 |
|---|---|---|
| `min_confidence` | 0.0 ~ 1.0 | 0.65 |
| `max_position_size` | 正整数 | 100 |
| `tick_size` | 0.01 的倍数 | 0.01 |
| `reconnect_delay` | 正数（秒） | 5 |
| `redis_port` | 1 ~ 65535 | 6379 |

**原因解释**: 配置向导内置了数据验证逻辑（类似 Python 的 Pydantic 或 TypeScript 的 Zod），会在写入前检查每个字段的类型和范围，防止因配置错误导致运行时崩溃。

**预防措施**: 不确定参数含义时，使用 `--validate-only` 先检查。填数值时参考 `settings.yaml` 中的注释说明。

---

### Q15: 应用预设方案后配置没变？

**A**: 排查步骤：

```bash
# 1️⃣ 确认 settings.yaml 是否真的被修改了
cat config/settings.yaml | grep -A5 "preset"

# 2️⃣ 检查文件权限
ls -la config/settings.yaml
# 应该类似于：-rw-r--r-- 1 user user 2048 ...
# 如果是 --------- 或 www-data 所有，说明权限不对

# 3️⃣ 修正权限
chmod 644 config/settings.yaml

# 4️⃣ 重新应用预设
python -m modules.config_wizard --preset conservative

# 5️⃣ 重启模块使配置生效
sudo systemctl restart simplepolybot-*.service
```

**原因解释**: 可能的原因有三个：(1) 文件权限不足导致无法写入；(2) 向导写入了但模块还在使用旧配置（未重启）；(3) 预设方案本身没有包含你期望修改的字段。

**预防措施**: 修改配置后**一定要重启**对应模块才能生效。可以用 `systemctl status` 确认服务已在运行最新配置。

---

### Q16: YAML 格式错误（缩进/冒号/引号）？

**A**: YAML 对格式非常敏感，这是最常见的配置错误来源。

**YAML 三大铁律**：

```
❌ 用 Tab 缩进     →    ✅ 必须用空格（建议 2 个空格）
❌ 冒号后面没空格  →    ✅ key: value（冒号+空格）
❌ 特殊字符没加引号 →    ✅ 字符串含 : # { } [ ] , & * ? 时用引号包裹
```

**验证 YAML 是否合法**：

```bash
# 方法一：Python 验证（推荐）
python3 -c "
import yaml, sys
try:
    with open('config/settings.yaml') as f:
        data = yaml.safe_load(f)
    print('✅ YAML 格式正确')
except yaml.YAMLError as e:
    print(f'❌ YAML 格式错误: {e}')
"

# 方法二：在线验证
# 将内容粘贴到 https://yamlchecker.com/
```

**典型错误示例**：

```yaml
# ❌ 错误：用了 Tab
redis:
	host: localhost   # ← 这里是 Tab！

# ❌ 错误：冒号后没空格
redis:host:localhost

# ✅ 正确
redis:
  host: localhost
  port: 6379
```

**原因解释**: YAML 用缩进来表示层级关系（类似 Python），但不像 JSON 有明确的括号标记结构。一个看不见的 Tab 字符就能破坏整个文件的解析。

**预防措施**: 编辑 YAML 时开启编辑器的「显示空白字符」功能（VS Code: `Render Whitespace: All`）。保存前用上述 Python 命令验证一次。

---

### Q17: 环境变量 .env 没有生效？

**A**: `.env` 不是系统环境变量，它是由应用程序在启动时加载的。验证方法：

```bash
# 1️⃣ 直接测试 Config 类能否读取
cd /opt/SimplePolyBot
source venv/bin/activate
python3 -c "
from shared.config import Config
c = Config()
print('REDIS_HOST:', c.get('redis.host'))
print('WALLET_ADDRESS:', c.get('wallet.address')[:10], '...')
"

# 2️⃣ 如果报错 FileNotFoundError
# → 说明 .env 文件不存在或路径不对
# 确认：
pwd                    # 应该在项目根目录
ls -la .env            # 文件是否存在

# 3️⃣ 如果能读取但值不对
# → 检查 .env 中是否有拼写错误
grep REDIS_HOST .env
```

**常见拼写错误**：

```env
# ❌ 错误
REDIS HOST=localhost        # 不能有空格
REDIS_HOST= localhost       # 等号后不能有空格
REDIS_HOST =localhost       # 等号前后都不能有空格

# ✅ 正确
REDIS_HOST=localhost
```

**原因解释**: `.env` 文件通过 `python-dotenv` 库在程序启动时解析加载到 `os.environ` 中。它不是 shell 环境变量，所以在终端里 `echo $REDIS_HOST` 是看不到值的——只有 Python 程序内部能读到。

**预防措施**: 填写 `.env` 时注意等号两边不能有空格。修改 `.env` 后重启模块才能加载新值。

---

### Q18: WALLET_ADDRESS 填什么？

**A**: 填写你的 **MetaMask 钱包地址**，格式如下：

```
✅ 正确格式：0x + 40位十六进制字符 = 总共42个字符
示例：0x742d35Cc6634C0532925a3b844Bc9e7595f2bD18
```

**获取方法**：

1. 打开 MetaMask 浏览器扩展
2. 确保选择了正确的账户（左上角下拉框）
3. 点击账户名称旁边的**复制按钮**（两个重叠的小方块图标）
4. 地址会自动复制到剪贴板

**重要**：`WALLET_ADDRESS` 必须和 `PRIVATE_KEY` 来自**同一个 MetaMask 账户**。如果私钥是账户 A 的，但钱包地址填的是账户 B 的，签名验证会全部失败。

**验证一致性**：

```bash
python3 -c "
from eth_account import Account
private_key = '0x你的私钥'
acct = Account.from_key(private_key)
print('私钥对应的地址:', acct.address)
print('.env 中的地址:  ', '你的.env中的WALLET_ADDRESS')
assert acct.address.lower() == '你的地址'.lower(), '❌ 地址和私钥不匹配！'
print('✅ 地址和私钥一致')
"
```

**原因解释**: Polymarket 用钱包地址标识你的身份，用私钥对订单进行签名。两者必须配对，否则链上验证会拒绝你的交易。

**预防措施**: 从 MetaMask 复制地址和导出私钥时，确保是同一个账户。建议在 `.env` 文件中用注释标明是哪个账户。

---

## 第三部分：运行阶段 FAQ

---

### Q19: 模块启动后立即退出（exit code 1）？

**A**: 这是最常见的运行时故障。按顺序排查：

```bash
# 1️⃣ 查看该模块的最新日志（最重要的排查手段）
tail -100 logs/signal_generator.log
# 替换为你实际出问题的模块名

# 2️⃣ 最常见的两大原因：

# 原因 A：.env 未正确配置
# 日志中会出现 KeyError 或 FileNotFoundError
# → 回到第二部分 FAQ 检查 .env 配置

# 原因 B：Redis 连接失败
# 日志中会出现 Connection refused 或 AuthenticationError
# → 继续看 Q20

# 3️⃣ 检查 Redis 是否正常运行
redis-cli ping
# ✅ 返回 PONG = 正常
# ❌ 返回 Could not connect = Redis 有问题

# 4️⃣ 手动运行模块看详细报错
source venv/bin/activate
python3 -m modules.signal_generator
```

**快速诊断清单**：

| 检查项 | 命令 | 预期结果 |
|---|---|---|
| Redis 运行中？ | `systemctl is-active redis-server` | active |
| Redis 可连接？ | `redis-cli ping` | PONG |
| .env 存在？ | `ls -la .env` | 文件存在 |
| Python 路径？ | `which python3` | venv 内的路径 |
| 端口未被占用？ | `ss -tlnp \| grep 6379` | 只有 redis |

**原因解释**: exit code 1 表示程序因错误退出。对于 SimplePolyBot 来说，90% 的情况是配置缺失或外部依赖（主要是 Redis）不可达。

**预防措施**: 首次启动前依次确认：Redis 运行 → .env 配置完成 → 虚拟环境激活 → 手动跑通一次 → 再交给 systemd 管理。

---

### Q20: Redis 连接被拒绝 Connection refused？

**A**: 逐步排查 Redis 连接问题：

```bash
# 1️⃣ Redis 服务是否在运行？
sudo systemctl status redis-server
# 如果不是 active (running)，启动它：
sudo systemctl start redis-server

# 2️⃣ Redis 是否真的在监听？
ss -tlnp | grep 6379
# 应该看到：LISTEN  0  128  127.0.0.1:6379

# 3️⃣ 能否手动连接？
redis-cli ping
# 如果返回 NOAUTH Authentication required → 密码问题（见下）

# 4️⃣ 密码是否正确？
redis-cli -a 你的密码 ping
# 如果能返回 PONG，说明密码没问题
# 检查 .env 中的 REDIS_PASSWORD 是否与 redis.conf 中 requirepass 一致

# 5️⃣ 地址和端口是否正确？
# .env 中 REDIS_HOST 默认是 localhost（即 127.0.0.1）
# 如果 Redis 装在其他机器上，需要填实际 IP
```

**如果以上都没问题还是连不上**：

```bash
# 检查防火墙是否阻止了本地连接
sudo iptables -L -n | grep 6379
# 本地连接通常不受防火墙影响，但如果 Redis 绑定了非 localhost 地址就需要放行
```

**原因解释**: `Connection refused` 意味着目标端口上没有任何服务在监听。要么 Redis 没启动，要么监听了不同的地址/端口，要么被防火墙拦截。

**预防措施**: 将 Redis 设为开机自启（`sudo systemctl enable redis-server`），避免服务器重启后忘记启动。

---

### Q21: WebSocket 断连且重连失败？

**A**: WebSocket 用于接收 Polymarket 实时行情数据，断连会导致信号生成器失去数据源。

```bash
# 1️⃣ 检查网络连通性
curl -I https://polymarket.com
# 应该返回 HTTP 200

# 2️⃣ 检查 DNS 解析
nslookup ws-subscriptions-clob.polymarket.com
# 应该返回 IP 地址

# 3️⃣ 测试 WebSocket 端口是否可达
curl -v -o /dev/null wss://ws-subscriptions-clob.polymarket.com/ws/market
# 注意 wss://（不是 https://）

# 4️⃣ 查看日志中的断连原因
tail -200 logs/signal_generator.log | grep -i "websocket\|disconnect\|reconnect\|error"

# 5️⃣ 如果是间歇性断连，增加重连延迟
nano config/settings.yaml
# 修改：
# websocket:
#   reconnect_delay: 10    # 从默认 5 秒改为 10 秒
#   max_reconnect_attempts: 20
```

**常见断连原因**：

| 原因 | 症状 | 解决方法 |
|---|---|---|
| 网络不稳定 | 频繁断开又重连 | 增大 reconnect_delay |
| 服务器 IP 被 Polymarket 限制 | 一直连不上 | 联系客服或更换 IP |
| DNS 解析失败 | 连接超时 | 配置备用 DNS（8.8.8.8） |
| Proxy/防火墙拦截 | 握手失败 | 检查防火墙规则 |

**原因解释**: WebSocket 是长连接协议，任何网络波动都可能导致连接中断。Polymarket 的 WebSocket 服务器也有自己的连接限制和心跳机制，如果客户端响应不及时也会主动断开。

**预防措施**: 确保 websocket 模块内置了指数退避重连机制（1s→2s→4s→8s...）。在网络质量较差的环境中适当增大重连延迟。

---

### Q22: 订单提交失败 "NOT_ENOUGH_BALANCE"？

**A**: 这说明你的 Polymarket 账户余额不足。

```bash
# 1️⃣ 在日志中确认错误详情
tail -50 logs/order_executor.log | grep -i balance

# 2️⃣ 登录 Polymarket 查看余额
# 进入 Portfolio 页面 → 查看 Available Balance
# 注意看的是 USDC.e 余额，不是其他代币
```

**充值 USDC.e 的方法**：

1. 打开 [Polymarket Deposit 页面](https://polymarket.com/portfolio/deposit)
2. 选择通过 Polygon 网络充值
3. 可以从交易所（如 Coinbase、Binance）提币 **USDC.e** 到 Polymarket 钱包地址
4. 也可以通过 QuickSwap 等 DEX 兑换

> ⚠️ **关键区别**：必须是 **USDC.e**（Bridged USDC，原生代币 ID 不同），不是普通 USDC。两种代币在 Polygon 网络上是不同的 ERC-20 代币。

**原因解释**: Polymarket 使用 Polygon 网络上的 USDC.e 作为结算货币。下单时系统会预冻结相应金额，如果余额不足则订单会被 CLOB API 直接拒绝。

**预防措施**: 在 `.env` 中合理设置 `max_position_size`，确保单笔订单金额不超过账户总余额的一定比例（如 20%）。定期检查账户余额。

---

### Q23: 订单提交失败 "INVALID_ORDER_MIN_TICK_SIZE"？

**A**: 价格不符合市场的最小变动单位。

```bash
# 1️⃣ 查看日志中的详细错误
tail -30 logs/order_executor.log | grep -i tick

# 2️⃣ Polymarket 大多数市场的 tick_size 是 0.01
# 即价格只能是 0.01, 0.02, 0.03 ... 0.99

# 3️⃣ 检查 price 计算逻辑
# 问题可能出在 safety_cushion 导致价格偏移后不再符合 tick_size
```

**系统应该自动处理的**：order_executor 在提交订单前会将价格对齐到有效的 tick_size。如果仍然出现这个错误，说明：

```python
# 可能的问题代码模式（示意）
price = calculated_price + safety_cushion
# 如果 calculated_price = 0.555, safety_cushion = 0.003
# 结果 price = 0.558 → 不符合 0.01 的整数倍！

# 正确做法：
import math
tick_size = 0.01
price = math.floor((calculated_price + safety_cushion) / tick_size) * tick_size
# 或使用 round
price = round(calculated_price + safety_cushion / tick_size) * tick_size
```

**原因解释**: CLOB（中央限价订单簿）要求所有价格必须是最小变动单位（tick size）的整数倍。这就像股票价格不能精确到小数点后 3 位一样——交易所规定了最小报价单位。

**预防措施**: 确保订单价格计算函数中有 tick_size 对齐逻辑。可以在提交前加一个 `assert price % 0.01 == 0` 的校验。

---

### Q24: 信号一直 WAIT，从不触发 BUY？

**A**: 信号生成器的四重过滤条件可能有一个或多个没通过。

```bash
# 1️⃣ 查看信号生成器日志，找到过滤日志
tail -200 logs/signal_generator.log | grep -i "filter\|wait\|reject\|pass\|fail"

# 2️⃣ 你应该能看到类似这样的输出：
# [FILTER] R²=0.32 < min_r_squared(0.5) → REJECT
# [FILTER] price_diff=0.005 < min_price_difference(0.01) → REJECT
# [FILTER] confidence=0.58 < min_confidence(0.65) → REJECT
# [FILTER] trend=neutral → REJECT
```

**四重过滤条件说明**：

| 过滤条件 | 含义 | 默认阈值 | 如何调低 |
|---|---|---|---|
| **R² 检验** | OLS 回归拟合度 | ≥ 0.5 | 改 `min_r_squared: 0.3` |
| **价格差额** | 当前价与预测价的差距 | ≥ 0.01 | 改 `min_price_difference: 0.005` |
| **置信度** | 综合信心分数 | ≥ 0.65 | 改 `min_confidence: 0.55` |
| **趋势方向** | 价格趋势是否明确 | 非 neutral | — |

**临时调试方法**（不建议长期使用）：

```yaml
# config/settings.yaml 中临时降低阈值
signal:
  min_confidence: 0.50      # 从 0.65 降到 0.50
  min_r_squared: 0.3         # 从 0.5 降到 0.3
  min_price_difference: 0.005 # 从 0.01 降到 0.005
```

**原因解释**: 四重过滤是系统的安全网，目的是确保只有在高确定性时才下单。如果市场处于横盘震荡状态（无明显趋势），R² 自然会很低，信号就一直 WAIT。

**预防措施**: WAIT 是正常的！不是每 5 分钟都有交易机会。如果连续多小时都是 WAIT，可以考虑切换到波动性更大的市场，或者适当调整阈值（但要权衡风险）。

---

### Q25: OLS 回归 R² 值一直很低？

**A**: R² 低意味着价格数据的线性趋势不明显。

**首先理解：这很正常！**

```
R² = 1.0 → 价格完美沿直线运动（几乎不可能）
R² = 0.8 → 强趋势（不错的机会）
R² = 0.5 → 有一定趋势（默认阈值）
R² = 0.2 → 弱趋势/噪音为主（大部分时间是这样）
R² = 0.0 → 完全随机游走
```

**改善 R² 的方法**：

```yaml
# 1️⃣ 增大数据窗口（更多数据点 = 更稳定的回归）
ols:
  window_minutes: 30    # 从默认 15 分钟增加到 30 分钟

# 2️⃣ 换一个波动性更大的市场
market:
  target: "Bitcoin Up or Down - 5 Minutes"  # 波动较大
  # 避免：政治类市场（价格变动缓慢）
```

**什么时候该担心 R² 低**：

- ✅ **不用担心**：每天有若干时段 R² > 0.5，触发几次交易就够了
- ⚠️ **需要注意**：连续 24 小时 R² 都 < 0.3，可能是数据源问题
- 🔴 **需要排查**：R² 始终为 0 或接近 0，检查 WebSocket 数据流是否正常

**原因解释**: OLS（最小二乘法）线性回归假设价格近似线性变动。但在真实市场中，大量时间是随机噪音（布朗运动），尤其在短时间窗口内（5 分钟）。只有当市场出现明确趋势时 R² 才会升高。

**预防措施**: 不要过度追求高 R²。R² 太高的市场反而可能意味着趋势即将反转。0.5~0.7 是比较理想的区间。

---

### Q26: 止损触发了但订单没有成交？

**A**: 止损单发出去了但市场没人接盘。

```bash
# 1️⃣ 查看订单执行器日志
tail -100 logs/order_executor.log | grep -i "stop_loss\|sell\|fill\|status"

# 2️⃣ 确认订单状态
# 你应该能看到类似：
# Stop-loss order placed: price=0.35, size=50, type=GTC
# Order status: live (waiting to be matched)
# → 订单挂上了但还没成交

# 3️⃣ 检查市场流动性
# 到 Polymarket 市场页面查看 order book 深度
# 如果买盘深度很浅，你的卖单可能排在后面
```

**订单类型的影响**：

| 类型 | 行为 | 止损场景下的效果 |
|---|---|---|
| **GTC** | 一直挂着直到成交或取消 | ✅ 推荐，会一直等待买家 |
| **GTD** | 到期自动取消 | ⚠️ 如果到期前无人接单就失败了 |
| **FOK** | 全部成交或全部取消 | ❌ 不适合止损（流动性不足时直接取消） |
| **FAK** | 部分成交后取消剩余 | 🔄 折中方案 |

**改善止损成交率的方法**：

```yaml
# 使用 GTC 类型 + 略低于市价的价格
stop_loss:
  order_type: GTC
  price_offset: 0.02   # 比当前市价低 2%，更容易成交
```

**原因解释**: Polymarket 是订单簿市场，不是即时成交的市场。你的卖单需要有人愿意以你的价格（或更好的价格）买入。在流动性不足的市场（尤其是快结算的市场），买盘深度可能非常薄。

**预防措施**: 止损单使用 GTC 类型而非 FOK。监控市场流动性，在深度过浅的市场中减少仓位规模。

---

### Q27: 结算工作器没有赎回已获胜代币？

**A**: 结算赎回涉及链上交互，有几个前提条件：

```bash
# 1️⃣ 确认市场是否已结算
tail -100 logs/settlement_worker.log | grep -i "resolved\|redeem\|settle"

# 2️⃣ 检查是否有足够的 MATIC（Polygon Gas）
# 结算赎回需要支付链上 Gas 费
# 钱包中至少需要 0.5~1 MATIC

# 3️⃣ 检查 CTF 合约授权状态
# 首次使用需要 approve ConditionalTokens 合约
# 日志中如果有 "approval needed" 相关信息，说明还未授权
```

**手动检查市场结算状态**：

1. 打开 Polymarket 对应的市场页面
2. 查看市场状态是否显示 **Resolved**
3. 确认你持有的代币是**获胜方**（Yes 或 No 中结算为 1 的那侧）

**如果 MATIC 不足**：

```bash
# 从交易所购买少量 MATIC（Polygon 网络）
# 或使用 Gas 赞助服务
# Polymarket 的 Builder Relayer 可以免除部分 Gas（取决于操作类型）
```

**原因解释**: 赎回（Redeem）是一个链上交易调用，需要将持有的条件代币交还给 CTF（Conditional Token Framework）合约，合约验证结算结果后返还 USDC.e。整个过程需要消耗 MATIC 作为 Gas。

**预防措施**: 钱包中始终保持至少 1-2 MATIC 的余额。可以设置一个低余额告警。

---

### Q28: 日志文件越来越大，磁盘快满了？

**A**: 日志轮转是生产环境的必备配置。

**方案一：配置 logrotate（推荐，系统级方案）**

```bash
# 创建 logrotate 配置文件
sudo nano /etc/logrotate.d/simplepolybot
```

写入以下内容：

```
/opt/SimplePolyBot/logs/*.log {
    daily              # 每天轮转
    missingok          # 文件不存在不报错
    rotate 30          # 保留 30 个历史文件
    compress           # 压缩旧日志
    delaycompress      # 最近的一次不压缩（方便查看）
    notifempty         # 空文件不轮转
    copytruncate       # 复制后清空（不用重启服务）
    size 100M          # 超过 100MB 就轮转（即使不到一天）
}
```

测试配置是否生效：

```bash
sudo logrotate -d /etc/logrotate.d/simplepolybot  # dry run（调试模式）
sudo logrotate -f /etc/logrotate.d/simplepolybot  # 强制执行一次
```

**方案二：Python RotatingFileHandler（应用级方案）**

如果项目已使用 Python logging 模块，可以修改配置：

```python
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    'logs/signal_generator.log',
    maxBytes=50 * 1024 * 1024,  # 50MB
    backupCount=10               # 保留 10 个备份
)
```

**清理旧日志**：

```bash
# 手动删除 30 天前的日志
find /opt/SimplePolyBot/logs/ -name "*.log" -mtime +30 -delete

# 查看日志占用空间
du -sh /opt/SimplePolyBot/logs/
```

**原因解释**: Python 的 FileHandler 默认不断追加写入同一个文件，长时间运行后日志文件可达数 GB。磁盘一旦写满，所有服务（包括 Redis）都会崩溃。

**预防措施**: 部署时就配置好 logrotate。建议设置单个日志文件上限 100MB，保留 30 天。

---

### Q29: CPU 或内存占用过高？

**A**: 首先确认什么是"过高"。

**正常资源占用参考值**（2GB RAM 服务器）：

| 模块 | CPU | 内存 |
|---|---|---|
| signal_generator | 5-15% | 80-150MB |
| order_executor | 2-8% | 50-80MB |
| settlement_worker | 1-5% | 30-50MB |
| risk_manager | 1-3% | 20-40MB |
| Redis | 1-3% | 100-256MB |
| **合计** | **< 30%** | **< 500MB** |

**排查步骤**：

```bash
# 1️⃣ 查看实时资源占用（交互式界面）
htop
# 按 F6 排序，按 MEM% 或 CPU% 排列
# 看哪个进程占用最高

# 或使用 top（更通用）
top -o %MEM

# 2️⃣ 常见的高占用原因

# 原因 A：OLS 计算量过大
# → 减小 ols.window_minutes 或增加计算间隔

# 原因 B：Redis 连接池泄漏
# → 重启相关模块释放连接
sudo systemctl restart simplepolybot-*.service

# 原因 C：日志写入过于频繁
# → 调整日志级别为 WARNING（不要用 DEBUG 长期运行）
```

**设置资源限制（防患于未然）**：

```ini
# /etc/systemd/system/simplepolybot-signal-generator.service 中添加：
[Service]
CPUQuota=50%
MemoryMax=300M
```

**原因解释**: CPU 高通常是计算密集型操作（如 OLS 回归频率太高）；内存高通常是连接池未释放、数据缓存过大或内存泄漏。

**预防措施**: 使用 systemd 的 `CPUQuota` 和 `MemoryMax` 限制每个服务的资源上限。定期 `htop` 巡检资源使用情况。

---

## 第四部分：账户相关 FAQ

---

### Q30: 如何充值 USDC.e 到 Polymarket？

**A**: 详细步骤：

**方法一：通过 Polymarket 官方充值页面（最简单）**

1. 登录 [polymarket.com](https://polymarket.com)
2. 点击右上角 **Deposit** 按钮
3. 页面会显示你的 Polymarket 钱包地址
4. 选择充值方式：
   - **信用卡/借记卡**（手续费较高，适合小额）
   - **银行转账**（手续费较低，适合大额）
   - **加密货币转账**（从其他钱包或交易所转入）

**方法二：从交易所提币（手续费最低）**

1. 在支持的交易所（Coinbase、Binance、Kraken 等）购买 USDC
2. **提币时选择 Polygon 网络**（不是 Ethereum 主网！）
3. **确认代币是 USDC.e（Bridged USDC）**
   - Coinbase: 选择 "USDC" 然后选 Polygon 网络（通常会自动桥接为 USDC.e）
   - Binance: 搜索 "USDC.e" 或使用普通 USDC 通过桥接转换
4. 提币地址填入你的 Polymarket 钱包地址
5. 等待到账（Polygon 网络通常几分钟确认）

**方法三：通过 DEX 兑换（如果你已有其他加密货币）**

1. 在 [QuickSwap](https://quickswap.exchange/) 或 [Uniswap](https://app.uniswap.org/) 上连接钱包
2. 切换到 **Polygon 网络**
3. 用 MATIC、WETH 等兑换 **USDC.e**
4. 将 USDC.e 转入 Polymarket 钱包

> ⚠️ **USDC vs USDC.e 区别**：
> - **USDC**：Circle 公司发行的原生代币
> - **USDC.e**：通过桥接（Bridge）到 Polygon 网络的版本
> - Polymarket **只接受 USDC.e**！充错代币无法用于交易。

**原因解释**: Polymarket 构建在 Polygon 网络之上，使用 USDC.e 作为结算货币。USDC.e 是以太坊主网上 USDC 通过官方桥接到 Polygon 的版本，两者在技术上是不同的 ERC-20 代币。

**预防措施**: 充值前再三确认：Polygon 网络 + USDC.e。可以先转入小额测试，确认到账后再充大额。

---

### Q31: Gas 费从哪里扣？需要多少 MATIC？

**A**: Gas 费用说明：

**Gas 支付货币**：**MATIC**（Polygon 网络的原生代币）

**哪些操作需要付 Gas**：

| 操作 | 是否需要 Gas | 大约消耗 |
|---|---|---|
| 下单/取消订单（CLOB） | ❌ 不需要 | 0 MATIC |
| 修改报价 | ❌ 不需要 | 0 MATIC |
| **结算赎回 Redeem** | ✅ 需要 | ~0.01-0.05 MATIC |
| **批准授权 Approve** | ✅ 需要（仅首次） | ~0.02-0.05 MATIC |
| 转账（钱包间） | ✅ 需要 | ~0.001 MATIC |

好消息：Polymarket 使用 **Builder Relayer** 技术，大部分日常交易操作（下单、撤单、修改）是**免 Gas** 的！只有在链上结算赎回时才需要少量 MATIC。

**需要准备多少 MATIC**：

```bash
# 对于纯自动化交易场景：
# 日常使用：0.5 MATIC 可用数周~数月
# 建议保留：1-2 MATIC 以备不时之需
# 获取方式：任意支持 Polygon 的交易所购买少量 MATIC
```

**如何查询 MATIC 余额**：

```bash
# 方法一：Polymarket Portfolio 页面
# 方法二：PolygonScan
# 访问 https://polygonscan.com/address/你的钱包地址

# 方法三：命令行（web3.py）
python3 -c "
from web3 import Web3
w3 = Web3(Web3.HTTPProvider('https://polygon-rpc.com'))
balance = w3.eth.get_balance('你的钱包地址')
print(f'MATIC 余额: {Web3.from_wei(balance, \"ether\")}')
"
```

**原因解释**: Polygon 网络的 Gas 费用以太坊主网便宜约 1000 倍。一笔普通的链上交易只需约 0.001 MATIC（不到 $0.001）。Polymarket 的 Builder Relayer 进一步将大部分操作的 Gas 费代付了。

**预防措施**: 钱包中始终保持 ≥ 1 MATIC。可以在交易所设置低价提醒，当 MATIC 低于一定价格时补仓。

---

### Q32: 如何查询钱包余额？

**A**: 三种查询方式：

**方式一：Polymarket 网页端（最直观）**

1. 登录 polymarket.com
2. 点击右上角头像 → **Portfolio**
3. 可看到：
   - **Total Portfolio Value**：投资组合总价值
   - **Available Balance**：可用 USDC.e 余额
   - **Open Positions**：当前持仓
   - **Realized P/L**：已实现盈亏

**方式二：PolygonScan（链上精确数据）**

1. 访问 [polygonscan.com](https://polygonscan.com)
2. 搜索栏输入你的钱包地址（0x 开头）
3. 可看到：
   - **MATIC Balance**：MATIC 余额
   - **Token Holdings**：所有 ERC-20 代币余额（包括 USDC.e）
   - **Transaction History**：所有链上交易记录

**方式三：命令行查询（脚本化/自动化）**

```bash
# 创建一个快速查询脚本
cat > check_balance.py << 'EOF'
from web3 import Web3
from shared.config import Config

config = Config()
w3 = Web3(Web3.HTTPProvider('https://polygon-rpc.com'))

address = config.get('wallet.address')

# MATIC 余额
matic = w3.eth.get_balance(address)
print(f"MATIC: {Web3.from_wei(matic, 'ether')}")

# USDC.e 余额（需要合约地址和 ABI）
usdc_e_contract = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
abi = [{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}]
contract = w3.eth.contract(address=usdc_e_contract, abi=abi)
usdc_balance = contract.functions.balanceOf(address).call()
print(f"USDC.e: {Web3.from_wei(usdc_balance, 'mwei')}")
EOF

python3 check_balance.py
```

**原因解释**: Polymarket 的资产存在于 Polygon 链上，所以最准确的数据源是区块链本身。Polymarket 页面是从链上同步数据后展示的，可能有短暂延迟。

**预防措施**: 定期检查余额，尤其是在大量交易后。可以设置定时任务每日自动查询并记录余额变化。

---

### Q33: API 凭证过期或被盗怎么办？

**A**: 这是一个安全问题，需要**立即行动**。

**🚨 紧急处理步骤**：

```
第 1 步（最重要）：立刻去 Polymarket 撤销旧凭证
  ↓
第 2 步：生成新的 API Key
  ↓
第 3 步：更新 .env 文件
  ↓
第 4 步：重启所有模块
  ↓
第 5 步（如果怀疑私钥泄露）：立即转移资产！
```

**详细操作**：

```bash
# === 第 1 步：撤销旧 API 凭证 ===
# 1. 登录 polymarket.com
# 2. 头像 → Profile → API Access
# 3. 找到旧的 API Key → 点击 Revoke
# 4. 该凭证立即失效，任何人无法再使用

# === 第 2 步：生成新的 API Key ===
# 同样在 API Access 页面点击 Create API Key
# ⚠️ 再次提醒：secret 只显示一次！立即复制保存

# === 第 3 步：更新 .env ===
nano /opt/SimplePolyBot/.env
# 修改以下三个值：
POLY_API_KEY=新的key
POLY_API_SECRET=新的secret
POLY_API_PASSPHRASE=新的passphrase

# === 第 4 步：重启模块 ===
sudo systemctl restart simplepolybot-*.service

# === 第 5 步：如果怀疑私钥泄露（最严重的情况）===
# 1. 创建一个新的 MetaMask 账户（新私钥）
# 2. 将所有资产（USDC.e + MATIC + 持仓代币）从旧钱包转到新钱包
# 3. 更新 .env 中的 PRIVATE_KEY 和 WALLET_ADDRESS
# 4. 旧私钥视为已废弃，永远不再使用
```

**如何判断凭证是否被盗**：

- 🚨 Polymarket 上出现你从未执行过的交易
- 🚨 API 用量异常激增
- 🚨 你收到了来自 Polymarket 的安全警告邮件
- 🚨 `.env` 文件出现在 Git 仓库或公开位置

**原因解释**: API Secret 相当于你的交易密码。任何人拿到它都能以你的身份下单、取消订单、查询持仓。如果私钥泄露就更严重——攻击者可以将你钱包中的所有资产转走。

**预防措施**:
- `.env` 文件权限设为 `chmod 600`（仅所有者可读写）
- 绝不将 `.env` 提交到 Git（已在 `.gitignore` 中排除）
- 定期轮换 API Key（建议每 90 天）
- 使用密码管理器存储凭证副本
- 启用 Polymarket 的两步验证（2FA）

---

### Q34: 如何安全地停止机器人？

**A**: 分两种停止方式：

**方式一：优雅停止（推荐，日常使用）**

```bash
# 停止所有 SimplePolyBot 服务
# systemd 会发送 SIGTERM 信号，模块收到后会：
# → 完成当前正在处理的订单
# → 关闭 WebSocket 连接
# → 释放 Redis 连接
# → 保存必要的状态数据
# → 然后才退出

sudo systemctl stop simplepolybot-*.service

# 停止单个模块
sudo systemctl stop simplepolybot-signal_generator.service
sudo systemctl stop simplepolybot-order_executor.service

# 确认已停止
sudo systemctl status simplepolybot-*.service
# 应该显示 inactive (dead)
```

**方式二：紧急停止（出现问题时的应急手段）**

```bash
# 立即终止所有 Python 模块进程
# ⚠️ 不会等待当前操作完成！可能导致数据不一致
pkill -f "modules\..*\.main"

# 或更精准地杀掉特定模块
pkill -f "signal_generator"
pkill -f "order_executor"
```

**停止后的状态说明**：

| 状态项 | 优雅停止后 | 紧急停止后 |
|---|---|---|
| 未完成的订单 | ✅ 安全，GTC 订单仍挂在 CLOB 上 | ⚠️ 可能丢失内存中的状态 |
| WebSocket 连接 | ✅ 正常关闭 | ❌ 异常断开 |
| Redis 连接 | ✅ 释放回连接池 | ⚠️ 可能泄漏连接 |
| 进程中的数据 | ✅ 已持久化 | ❌ 可能丢失 |
| 下次启动 | ✅ 自动恢复监控 | ✅ 可恢复，但需检查一致性 |

**重启机器人**：

```bash
# 启动所有服务
sudo systemctl start simplepolybot-*.service

# 设置开机自启（如果还没设置）
sudo systemctl enable simplepolybot-*.service

# 查看所有服务状态
sudo systemctl status simplepolybot-*.service
```

**原因解释**: 优雅停止给程序一个"收拾善后"的机会。正在进行的订单提交操作会被允许完成，避免了半写入数据库或半提交订单的不一致状态。紧急停止相当于直接拔电源——能用但风险更高。

**预防措施**: 日常运维一律使用优雅停止。只在模块完全无响应（卡死）时才使用紧急停止。停止前最好看一下日志确认没有正在进行的关键操作。

---

> 📌 **本章小结**：以上 34 个问题覆盖了从部署到日常运维的全生命周期。遇到问题时，**先看日志（logs/ 目录）**永远是第一原则——90% 的答案都在日志里。如果本章没有覆盖你的问题，欢迎到项目 Issues 反馈。

<!-- CHAPTER_7_CONTENT_END -->

---

## 第 8 章：异常处理与故障排除

<!-- CHAPTER_8_CONTENT_START -->

## 8.1 故障诊断决策树

### 快速诊断流程

#### 第一步：确定问题范围

**系统完全无响应？**
├─ 是 → 检查服务器是否存活
│   ├─ ping 216.238.91.89 不通 → Vultr 控制台检查机器状态
│   └─ ping 通但 SSH 不上 → 检查 SSH 服务 / 防火墙 / 网络带宽
│
└─ 否 → 能 SSH 登录，继续第二步

#### 第二步：定位故障模块

**检查各模块状态：**
```bash
systemctl status simplepolybot-*.service
```

├─ 全部 failed → 检查公共依赖（Redis / 网络 / .env）
│   └─ 见 8.2.1「所有模块无法启动」
│
├─ 单个模块 failed → 针对该模块排查
│   ├─ market_data_collector → 见 8.2.2
│   ├─ strategy_engine → 见 8.2.3
│   ├─ order_executor → 见 8.2.4
│   └─ settlement_worker → 见 8.2.5
│
└─ 全部 running 但异常 → 检查业务逻辑
    └─ 见 8.2.6「功能性故障」

#### 第三步：收集诊断信息

无论哪种情况，先收集以下信息：
```bash
# 最近 100 行日志
journalctl -u simplepolybot-* -n 100 --no-pager

# 系统资源
free -h && df -h && uptime

# 网络连通性
curl -sI https://clob.polymarket.com | head -5
redis-cli -a YOUR_PASS ping
```

## 8.2 按症状分类排查指南

### 8.2.1 所有模块无法启动

**症状**：systemctl start 后全部 immediately exited

**排查顺序**：

| 序号 | 检查项 | 命令/方法 |
|------|--------|-----------|
| 1 | `.env` 文件是否存在且格式正确 | `cat .env \| head -20` |
| 2 | Redis 是否运行？ | `redis-cli ping` |
| 3 | Python venv 是否激活？ | `which python3` |
| 4 | requirements.txt 依赖是否全装？ | `pip list` |
| 5 | config/settings.yaml YAML 格式是否合法？ | `python -c "import yaml; yaml.safe_load(open('config/settings.yaml'))"` |

### 8.2.2 单个模块崩溃（market_data_collector）

**症状**：其他模块正常，仅此模块反复重启

**常见原因及解决**：

| 原因 | 日志关键词 | 解决方法 |
|------|-----------|----------|
| WebSocket 连接失败 | ConnectionRefusedError / timeout | 检查 DNS 和防火墙出站规则 |
| Redis 发布失败 | redis connection error | 检查 Redis 密码和端口 |
| 内存溢出 | MemoryError / OOM killed | 增加 swap 或降低 websocket.orderbook_depth |

### 8.2.3 单个模块崩溃（strategy_engine）

**常见原因**：

| 原因 | 日志关键词 | 解决方法 |
|------|-----------|----------|
| 收不到市场数据 | subscribe timeout | 检查 market_data_collector 是否正常运行 |
| OLS 计算错误 | LinAlgError / singular matrix | 数据点太少，等更多数据积累 |
| NumPy 版本冲突 | ImportError | `pip install --force-reinstall numpy` |

### 8.2.4 单个模块崩溃（order_executor）

**常见原因**：

| 原因 | 日志关键词 | 解决方法 |
|------|-----------|----------|
| API 认证失败 | 401 Unauthorized | 检查 api_key/api_secret/api_passphrase |
| 私钥无效 | Invalid private key | 检查 PRIVATE_KEY 格式（0x + 64 hex） |
| 余额不足 | INSUFFICIENT_BALANCE | 充值 USDC.e |
| Gas 不足 | Out of gas | 钱包充入 MATIC |

### 8.2.5 单个模块崩溃（settlement_worker）

**常见原因**：

| 原因 | 日志关键词 | 解决方法 |
|------|-----------|----------|
| RPC 连接失败 | RPC connection error | 检查 POLYGON_RPC_URL 是否可达 |
| 合约调用失败 | revert / out of gas | 增加 Gas 或检查合约地址 |

### 8.2.6 无法连接 Redis

**完整排查链路**：

```bash
# 1. Redis 进程是否存在？
ps aux | grep redis-server

# 2. Redis 是否监听？
ss -tlnp | grep 6379

# 3. 本地能否连接？
redis-cli -a YOUR_PASSWORD ping

# 4. 密码是否匹配？
# 对比 .env 的 REDIS_PASSWORD 和 /etc/redis/redis.conf 的 requirepass

# 5. 防火墙是否阻止？
# Redis 仅需本地访问，不需要开放防火墙端口
```

### 8.2.7 无法连接 Polymarket API

**排查**：

```bash
# 测试 API 可达性
curl -s https://clob.polymarket.com/time | head -1
# 预期返回 JSON 时间戳

# 测试 WebSocket
wscat -c "wss://ws-subscriptions-clob.polymarket.com/ws/market"
# 应能建立连接
```

### 8.2.8 内存/CPU 过载

**症状**：top 显示 CPU > 80% 或 free 显示可用内存 < 100MB

**解决**：

```bash
# 查看哪个进程吃资源
htop

# 如果是 Python 进程：
# 1. 降低 connection pool 大小
# 2. 减少 orderbook_depth
# 3. 增加 swap（见 FAQ Q8）

# 临时应急：重启最占资源的模块
systemctl restart simplepolybot-strategy-engine
```

## 8.3 CLOB API 关键错误码对照表

| 错误码 | 含义 | 常见原因 | 解决方法 |
|--------|------|----------|----------|
| INVALID_ORDER_MIN_TICK_SIZE | 价格不符合最小变动单位 | safety_cushion 计算结果精度问题 | 检查价格计算逻辑 |
| INVALID_ORDER_NOT_ENOUGH_BALANCE | 余额不足 | USDC.e 不够 | 充值 |
| INVALID_ORDER_PRICE_BAND | 价格超出允许范围 | 价格 < 0.01 或 > 0.99 | 检查 max_buy_price 计算 |
| INVALID_ORDER_SIZE | 订单大小超出限制 | 超过 order_sizes.max | 降低订单金额 |
| UNAUTHORIZED | 认证失败 | API Key/Secret/Passphrase 有误 | 重新生成并更新 .env |
| RATE_LIMITED | 触发速率限制 | 请求太频繁 | 降低 signal_check_interval |
| ORDER_NOT_FOUND | 订单不存在 | orderID 错误或已被取消 | 检查订单状态查询 |
| FOK_ORDER_NOT_FILLED_ERROR | FOK 订单无法完全成交 | 市场深度不足 | 改用 GTC 类型 |

## 8.4 紧急停止程序

当发现严重问题时（如异常大额交易、凭证泄露），执行紧急停止：

```bash
#!/bin/bash
# === SimplePolyBot 紧急停止脚本 ===
echo "🚨 [EMERGENCY] 正在紧急停止 SimplePolyBot..."

# 1. 停止所有 systemd 服务
systemctl stop simplepolybot-*.service 2>/dev/null

# 2. 强制杀掉残留进程
pkill -9 -f "modules\..*\.main" 2>/dev/null

# 3. 确认全部停止
sleep 2
REMAINING=$(ps aux | grep -E "modules\..*\.main" | grep -v grep | wc -l)

if [ "$REMAINING" -eq 0 ]; then
    echo "✅ 所有 SimplePolyBot 进程已停止"
else
    echo "⚠️ 仍有 $REMAINING 个进程，强制清理中..."
    kill -9 $(pgrep -f "simplepolybot") 2>/dev/null
fi

echo ""
echo "📋 停止后的检查清单："
echo "  1. 检查 Polymarket 上是否有未完成的大额订单"
echo "  2. 检查钱包余额是否正常"
echo "  3. 查看最后 50 条日志确认停止前的状态"
echo "  4. 排查问题根源后再重启"
```

## 8.5 数据恢复流程

崩溃后的恢复步骤：

### 崩溃恢复 Checklist

- [ ] **1. 确认系统已完全停止**（见 8.4 节）
- [ ] **2. 检查磁盘和数据完整性**
  ```bash
  df -h                    # 磁盘空间
  ls -la data/             # 数据目录是否完好
  ls -la logs/             # 日志是否可读
  ```
- [ ] **3. 分析崩溃原因**
  ```bash
  journalctl -u simplepolybot-* --since "1 hour ago" -p err --no-pager
  # 找到最后一条 ERROR 或 CRITICAL 日志
  ```
- [ ] **4. 修复根本问题**（根据 8.2 节的排查指南）
- [ ] **5. 从备份恢复配置**（如有必要）
  ```bash
  tar xzf /opt/backups/config-latest.tar.gz -C /
  ```
- [ ] **6. 逐步启动验证**
  ```bash
  # 先启动依赖服务
  systemctl start redis-server
  
  # 再逐个启动模块
  systemctl start simplepolybot-market-data
  sleep 5
  systemctl status simplepolybot-market-data  # 确认 OK
  
  systemctl start simplepolybot-strategy-engine
  # ... 依次启动其余模块
  ```
- [ ] **7. 全面巡检**（参照第 6 章每日巡检清单）
- [ ] **8. 记录事故报告**（时间、原因、影响、修复措施）

<!-- CHAPTER_8_CONTENT_END -->

---

## 第 9 章：安全最佳实践

<!-- CHAPTER_9_CONTENT_START -->

### 9.1 私钥安全管理

- ❌ 绝不在代码中硬编码私钥
- ✅ 通过环境变量 `PRIVATE_KEY` 注入
- ✅ `.env` 文件权限设为 `chmod 600`
- ✅ 私钥仅保存在服务器本地，不传 Git
- ⚠️ **私钥泄露 = 资金全部丢失**

### 9.2 API 凭证保护

- Polymarket API Secret 只在生成时显示一次
- 定期轮换（建议每 90 天）
- 使用最小权限原则（只给必要的 API 权限）
- 凭证存储在 `.env` 中，不提交到版本控制

### 9.3 服务器加固

```bash
# SSH 配置优化 (/etc/ssh/sshd_config)
PermitRootLogin no          # 禁止 root 远程登录
PasswordAuthentication no   # 禁止密码登录（仅允许密钥）
MaxAuthTries 3              # 最大尝试次数
Port 22222                  # 改用非标准端口（可选）

# fail2ban 已在 1.5 节配置

# 定期更新
apt upgrade -y              # 建议每月执行
```

### 9.4 网络安全

- Redis 仅绑定 `127.0.0.1`（不暴露公网）
- UFW 防火墙仅开放必要端口（SSH + 可选的 8080/9090 仅限内网）
- 不安装不必要的网络服务
- 定期检查 `ss -tlnp` 监听端口

### 9.5 资金安全

- `min_balance` 设置合理的保留余额（≥ $100）
- `max_daily_loss` 设置日亏损上限
- 不要把所有资金放入一个市场
- 定期将盈利提取到冷钱包

### 9.6 审计日志

关键操作自动记录：

- 所有订单提交和成交
- 所有配置变更
- 所有登录尝试（fail2ban 日志）

**定期审查命令：**

```bash
journalctl -u fail2ban --since "7 days ago"
```

<!-- CHAPTER_9_CONTENT_END -->

---

## 附录 A：命令速查表

<!-- APPENDIX_A_CONTENT_START -->

### A.1 部署相关

```bash
# SSH 连接服务器
ssh root@216.238.91.89
ssh polybot@216.238.91.89

# 系统更新
apt update && apt upgrade -y

# 安装基础工具链
apt install -y git python3 python3-pip python3-venv redis-server curl wget htop ufw fail2ban chrony

# Redis 服务管理
systemctl status redis-server
redis-cli -a YOUR_PASSWORD ping
redis-cli -a YOUR_PASSWORD INFO server

# 项目克隆与进入目录
cd /opt && git clone https://github.com/EatTake/SimplePolyBot.git && cd SimplePolyBot
```

### A.2 Python 环境

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install --upgrade pip
pip install -r requirements.txt

# 验证核心依赖是否正常
python -c "import web3, redis, yaml; print('All OK')"

# 退出虚拟环境
deactivate
```

### A.3 配置管理

```bash
# 复制环境变量模板并编辑
cp .env.example .env
nano .env

# 配置向导（三种模式）
python -m shared.config_wizard --mode quick       # 快速模式，最少交互
python -m shared.config_wizard --mode standard     # 标准模式，逐步引导
python -m shared.config_wizard --mode expert       # 专家模式，全部可调
python -m shared.config_wizard --validate-only     # 仅验证当前配置

# 应用预设方案
python -m shared.config_presets apply balanced      # 平衡型（推荐）
python -m shared.config_presets apply conservative   # 保守型（新手首选）
python -m shared.config_presets apply aggressive     # 激进型（高阶用户）
python -m shared.config_presets list                # 列出所有可用方案
python -m shared.config_presets diff cons aggr      # 对比两个方案差异

# 生成配置文档
python -m shared.config_docs generate               # 生成 Markdown 文档
python -m shared.config_docs schema                 # 导出 JSON Schema
python -m shared.config_docs env                    # 生成 .env.example

# 独立验证配置
python -m shared.config_validator                  # 完整配置校验
```

### A.4 启动停止

```bash
# 一键启动全部模块
bash scripts/start_all.sh

# 启动单个模块
bash scripts/start_module.sh market_data_collector   # 市场数据采集
bash scripts/start_module.sh strategy_engine          # 策略引擎
bash scripts/start_module.sh order_executor           # 订单执行器
bash scripts/start_module.sh settlement_worker        # 结算工作进程

# systemd 管理（生产环境推荐）
systemctl start simplepolybot-*.service              # 启动全部服务
systemctl stop simplepolybot-*.service               # 停止全部服务
systemctl restart simplepolybot-*.service            # 重启全部服务
systemctl status simplepolybot-*.service             # 查看全部状态

# 单模块 systemd 操作
systemctl start simplepolybot-market-data            # 仅启动市场数据模块
systemctl stop simplepolybot-market-data             # 仅停止市场数据模块
systemctl restart simplepolybot-market-data          # 仅重启市场数据模块
```

### A.5 日志查看

```bash
# 实时跟踪各模块日志
tail -f logs/market_data_collector.log              # 市场数据日志
tail -f logs/strategy_engine.log                     # 策略引擎日志
tail -f logs/order_executor.log                      # 订单执行日志
tail -f logs/settlement_worker.log                   # 结算工作日志

# systemd 日志查看
journalctl -u simplepolybot-market-data -f           # 实时跟踪某模块
journalctl -u simplepolybot-* --since "1 hour ago"   # 最近 1 小时全部日志
journalctl -u simplepolybot-* -p err                 # 仅显示错误级别

# 关键词搜索
grep "BUY\|SELL" logs/strategy_engine.log | tail -20  # 最近 20 条交易信号
grep -i "error" logs/*.log | tail -20                # 最近 20 条错误记录
grep -c "ERROR" logs/order_executor.log              # 统计订单执行错误数
```

### A.6 监控检查

```bash
# 系统资源概览
free -h                                              # 内存使用情况
df -h /                                             # 磁盘使用情况
uptime                                             # 运行时间与系统负载
htop                                               # 交互式资源监控面板

# 进程状态检查
ps aux | grep -E "(market_data|strategy|order|settlement)" | grep -v grep

# Redis 连接与状态
redis-cli -a YOUR_PASSWORD info server              # Redis 服务器信息
redis-cli -a YOUR_PASSWORD client list              # 当前客户端连接列表

# 网络连通性测试
curl -sI https://clob.polymarket.com | head -3       # 检测 Polymarket API 可达性
ss -tlnp                                           # 查看本机监听端口

# 内置健康检查端点
curl http://localhost:8080/health                    # 系统健康状态
curl http://localhost:9090/metrics                   # Prometheus 指标数据
```

### A.7 备份恢复

```bash
# 创建完整备份（含配置、环境变量、数据、日志）
tar czf /opt/backups/simplepolybot-$(date +%Y%m%d).tar.gz \
    config/ .env data/ logs/

# 从备份恢复
tar xzf /opt/backups/simplepolybot-latest.tar.gz -C /opt/SimplePolyBot/
```

### A.8 安全操作

```bash
# 文件权限设置
chmod 600 .env                                      # 环境变量文件仅本人可读写
chmod 644 config/settings.yaml                      # 配置文件所有人可读

# 防火墙管理
ufw status                                          # 查看当前防火墙规则
ufw allow ssh                                       # 开放 SSH 端口
ufw enable                                          # 启用防火墙

# 紧急停止（慎用）
pkill -9 -f "modules\..*\.main"                     # 强制终止所有 Python 模块进程
systemctl stop simplepolybot-*.service              # 优雅停止所有 systemd 服务
```

### A.9 版本更新

```bash
cd /opt/SimplePolyBot
systemctl stop simplepolybot-*.service               # 先停止所有服务
cp -r . ../SimplePolyBot-backup-$(date +%Y%m%d)      # 创建回滚备份
git pull origin main                                 # 拉取最新代码
source venv/bin/activate && pip install -r requirements.txt  # 更新依赖
systemctl start simplepolybot-*.service              # 重启所有服务
```

<!-- APPENDIX_A_CONTENT_END -->

---

## 附录 B：配置文件完整示例

<!-- APPENDIX_B_CONTENT_START -->

### B.1 settings.yaml 完整注释版

以下为 `config/settings.yaml` 的逐项中文注释说明。**实际部署时请勿直接复制此版本**，应从项目根目录的原始文件为基础修改。

```yaml
# ============================================================
# SimplePolyBot 主配置文件 (config/settings.yaml)
# 所有数值参数均可通过环境变量覆盖，格式: ${ENV_KEY:默认值}
# ============================================================

# -------------------- 策略核心参数 --------------------
strategy:
  base_cushion: 0.05         # 基础安全缓冲值（5%），买入价与当前价的最低安全距离
  alpha: 0.7                 # 价格调整系数（0~1），越大对波动越敏感

  max_buy_prices:            # 各场景下的最大买入价格上限
    default: 0.95            # 默认场景：最高出价 95 分
    high_confidence: 0.98    # 高置信度：允许出到 98 分
    low_volatility: 0.92     # 低波动市场：限制在 92 分
    fast_market: 0.9         # 快速市场（如 BTC 5min）：更保守，90 分封顶

  order_sizes:               # 单笔订单金额设置（单位：USDC.e）
    default: 100             # 默认每笔 $100
    min: 10                  # 最小单笔 $10
    max: 1000                # 最大单笔 $1000

  risk_management:           # 风险管理参数
    max_position_size: 5000      # 单个市场最大持仓 $5000
    max_total_exposure: 20000    # 总风险敞口上限 $20000
    max_daily_loss: 500          # 单日最大亏损限额 $500
    max_drawdown: 0.15           # 最大回撤容忍度 15%
    min_balance: 100             # 账户最低保留余额 $100

  stop_loss_take_profit:     # 止损止盈设置
    enabled: true                # 启用自动止损止盈
    stop_loss_percentage: 0.1    # 亏损达 10% 自动卖出止损
    take_profit_percentage: 0.2  # 盈利达 20% 自动卖出止盈

# -------------------- Redis 连接配置 --------------------
redis:
  host: ${REDIS_HOST:localhost}        # Redis 地址，支持环境变量覆盖
  port: ${REDIS_PORT:6379}             # Redis 端口
  password: ${REDIS_PASSWORD:}         # Redis 密码（空=无密码）
  db: ${REDIS_DB:0}                    # Redis 数据库编号
  pool:                                # 连接池配置
    max_connections: 50                # 最大连接数
    min_idle_connections: 5            # 最小空闲连接
    connection_timeout: 5              # 连接超时（秒）
    socket_timeout: 5                  # Socket 超时（秒）
  retry:                               # 重试策略
    max_attempts: 3                    # 最大重试次数
    retry_delay: 1                     # 重试间隔（秒）
    exponential_backoff: true          # 启用指数退避

# -------------------- 模块开关与参数 --------------------
modules:
  market_data_collector:        # 市场数据采集模块
    enabled: true
    websocket:
      url: wss://ws-subscriptions-clob.polymarket.com/ws/market  # WebSocket 地址
      reconnect_delay: 5         # 断线重连初始延迟（秒）
      max_reconnect_attempts: 10 # 最大重连次数
      ping_interval: 10          # 心跳发送间隔（秒）
      pong_timeout: 10           # 等待 PONG 超时（秒）
    collection:
      markets_update_interval: 60    # 市场列表刷新间隔（秒）
      orderbook_depth: 20            # 订单簿深度（档位）
      price_history_interval: 300    # 价格历史采集间隔（秒）

  strategy_engine:             # 策略引擎模块
    enabled: true
    execution:
      signal_check_interval: 10      # 信号检测间隔（秒）
      max_concurrent_orders: 5       # 最大并发订单数
      order_timeout: 30              # 订单超时时间（秒）
    active_strategies:               # 已启用的策略列表
      - base_cushion                  # 基础安全垫策略
      - trend_following              # 趋势跟踪策略
    signal_filter:                   # 信号过滤条件
      min_confidence: 0.6            # 最低置信度阈值
      min_volume: 100                # 最小成交量要求

  order_executor:             # 订单执行模块
    enabled: true
    clob:                          # CLOB API 配置
      host: https://clob.polymarket.com  # CLOB 服务器地址
      chain_id: 137                       # Polygon 主网 Chain ID
      api_timeout: 30                     # API 请求超时（秒）
    order_management:              # 订单管理
      default_order_type: GTC           # 默认订单类型：Good-Til-Cancelled
      max_order_age: 3600               # 订单最大存活时间（秒）
      cancel_on_error: true             # 出错时自动取消挂单
    gas:                           # Gas 费设置
      max_gas_price: 100               # 最大 Gas 价格（Gwei）
      gas_limit_multiplier: 1.2         # Gas Limit 倍率

  settlement_worker:          # 结算工作模块
    enabled: true
    settlement:
      check_interval: 60             # 结算检查间隔（秒）
      batch_size: 50                 # 每批处理数量
    position:
      track_history: true            # 是否跟踪持仓历史
      max_history_days: 30           # 历史保留天数

# -------------------- 外部 API 配置 --------------------
api:
  polymarket:                   # Polymarket CLOB API 凭证
    api_key: ${POLYMARKET_API_KEY}
    api_secret: ${POLYMARKET_API_SECRET}
    api_passphrase: ${POLYMARKET_API_PASSPHRASE}
  polygon:                      # Polygon 区块链 RPC
    rpc_url: ${POLYGON_RPC_URL:https://polygon-rpc.com}
  gamma:                        # Gamma 市场 API
    base_url: https://gamma-api.polymarket.com
    timeout: 30                  # 请求超时（秒）

# -------------------- 通知配置 --------------------
notifications:
  email:                        # 邮件通知
    enabled: false
    smtp_server: ${SMTP_SERVER:smtp.gmail.com}
    smtp_port: ${SMTP_PORT:587}
    smtp_username: ${SMTP_USERNAME}
    smtp_password: ${SMTP_PASSWORD}
    alert_email: ${ALERT_EMAIL}
  webhook:                      # Webhook 通知（Slack/钉钉等）
    enabled: false
    url: ${WEBHOOK_URL}
  triggers:                     # 触发条件
    on_order_filled: true        # 订单成交时通知
    on_position_closed: true     # 持仓关闭时通知
    on_error: true               # 出错时通知
    on_large_loss: true          # 大额亏损时通知
    large_loss_threshold: 100    # 大额亏损阈值（$）

# -------------------- 系统全局设置 --------------------
system:
  environment: development       # 运行环境：development / production
  log_level: INFO               # 日志级别：DEBUG / INFO / WARNING / ERROR
  monitoring:                   # 监控配置
    enabled: true
    metrics_port: 9090           # Prometheus 指标端口
    health_check_port: 8080      # 健康检查端口
  persistence:                  # 数据持久化
    data_dir: ./data             # 数据存储目录
    backup_enabled: true         # 是否启用自动备份
    backup_interval: 86400       # 备份间隔（秒），默认每天一次
```

### B.2 .env.example 完整版

```bash
# ========================================
# SimplePolyBot 环境变量配置模板
# 复制为 .env 后填入真实值：cp .env.example .env
# ========================================

# ---- Polymarket API 凭证（必填）----
POLYMARKET_API_KEY=your_api_key_here
POLYMARKET_API_SECRET=your_api_secret_here
POLYMARKET_API_PASSPHRASE=your_api_passphrase_here

# ---- 钱包配置（必填）----
PRIVATE_KEY=your_private_key_here
WALLET_ADDRESS=your_wallet_address_here

# ---- Redis 配置 ----
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# ---- Polygon RPC（可选，有默认值）----
POLYGON_RPC_URL=https://polygon-rpc.com

# ---- 邮件告警（可选）----
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_email_password
ALERT_EMAIL=alert_recipient@gmail.com

# ---- Webhook 告警（可选）----
WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### B.3 conservative.yaml — 保守型预设

适用场景：新手用户、高波动市场、学习阶段。特点：低仓位、高缓冲、严格风控。

```yaml
# ========================================
# SimplePolyBot 保守型配置方案
# 适用场景：新手用户、高波动市场、学习阶段
# 特点：低仓位、高缓冲、严格风控
# ========================================

strategy:
  base_cushion: 0.03           # 较高的基础缓冲（3%）
  alpha: 0.3                   # 低价格调整系数，反应迟钝但稳健

  max_buy_prices:
    default: 0.90              # 限制最大买入价为 90 分
    high_confidence: 0.93      # 高确信度也只到 93 分
    low_volatility: 0.88       # 低波动市场更保守
    fast_market: 0.85          # 快速市场最保守，85 分封顶

  order_sizes:
    default: 50                 # 小仓位起步，每笔 $50
    min: 10
    max: 500                    # 单笔最多 $500

  risk_management:
    max_position_size: 2000    # 单仓严格控制在 $2000 以内
    max_total_exposure: 8000   # 总敞口不超过 $8000
    max_daily_loss: 200        # 日亏限额仅 $200
    max_drawdown: 0.10          # 回撤超过 10% 即触发熔断
    min_balance: 200            # 高保留余额 $200

  stop_loss_take_profit:
    enabled: true
    stop_loss_percentage: 0.08  # 早止损：亏 8% 就跑
    take_profit_percentage: 0.15  # 早止盈：赚 15% 就落袋
```

### B.4 balanced.yaml — 平衡型预设（推荐）

适用场景：大多数用户、一般市场条件。特点：中等仓位、适中缓冲、均衡风控。

```yaml
# ========================================
# SimplePolyBot 平衡型配置方案
# 适用场景：大多数用户、一般市场条件 [推荐]
# 特点：中等仓位、适中缓冲、均衡风控
# ========================================

strategy:
  base_cushion: 0.02           # 标准基础缓冲（2%）
  alpha: 0.5                   # 标准价格调整系数，平衡灵敏度与稳定性

  max_buy_prices:
    default: 0.95              # 标准最大买入价 95 分
    high_confidence: 0.98      # 高确信度可到 98 分
    low_volatility: 0.92       # 低波动市场 92 分
    fast_market: 0.90          # 快速市场 90 分

  order_sizes:
    default: 100               # 中等仓位，每笔 $100
    min: 10
    max: 1000                   # 单笔最多 $1000

  risk_management:
    max_position_size: 5000    # 标准单仓限制 $5000
    max_total_exposure: 20000  # 标准总敞口 $20000
    max_daily_loss: 500        # 标准日亏损限额 $500
    max_drawdown: 0.15          # 标准回撤容忍 15%
    min_balance: 100            # 标准保留余额 $100

  stop_loss_take_profit:
    enabled: true
    stop_loss_percentage: 0.10  # 标准止损：亏 10%
    take_profit_percentage: 0.20  # 标准止盈：赚 20%
```

### B.5 aggressive.yaml — 激进型预设

适用场景：经验丰富的交易者、低波动市场、高确信度信号。特点：大仓位、低缓冲、激进风控。

```yaml
# ========================================
# SimplePolyBot 激进型配置方案
# 适用场景：经验丰富的交易者、低波动市场、高确信度
# 特点：大仓位、低缓冲、激进风控
# ========================================

strategy:
  base_cushion: 0.01           # 低基础缓冲（1%），接近市价入场
  alpha: 0.7                   # 高价格调整系数，快速响应市场变化

  max_buy_prices:
    default: 0.98              # 允许高价买入，最高 98 分
    high_confidence: 0.99      # 极高确信度可到 99 分
    low_volatility: 0.96       # 低波动市场 96 分
    fast_market: 0.95          # 快速市场也敢出到 95 分

  order_sizes:
    default: 200                # 大仓位，每笔 $200
    min: 10
    max: 2000                   # 单笔最多 $2000

  risk_management:
    max_position_size: 8000    # 放宽单仓至 $8000
    max_total_exposure: 30000  # 提高总敞口至 $30000
    max_daily_loss: 1000       # 高日亏损限额 $1000
    max_drawdown: 0.20          # 高回撤容忍 20%
    min_balance: 50             # 低保留余额 $50，更多资金参与交易

  stop_loss_take_profit:
    enabled: true
    stop_loss_percentage: 0.15  # 宽止损：给更多空间，亏 15% 才跑
    take_profit_percentage: 0.30  # 高止盈目标：赚 30% 才平仓
```

<!-- APPENDIX_B_CONTENT_END -->

---

## 附录 C：术语表

<!-- APPENDIX_C_CONTENT_START -->

以下术语按字母顺序排列，涵盖 Polymarket 生态、区块链、量化交易和系统运维四大领域。

| 术语 | 英文全称 / 别名 | 通俗解释 |
|------|-----------------|----------|
| **API** | Application Programming Interface | 程序之间的"接口"或"对话协议"。就像餐厅里服务员把顾客的点菜单传给厨房——我们的机器人通过 API 与 Polymarket 服务器对话来下单、查询行情 |
| **API Key / Secret / Passphrase** | — | 调用 API 时证明身份的三件套，类似于 **身份证 + 密码 + 验证码**。Key 是账号标识，Secret 是签名密钥，Passphrase 是额外验证层 |
| **alpha (α)** | — | 价格调整系数（取值 0~1）。控制安全缓冲垫对市场价格波动的敏感程度。α 越高，系统越积极追涨；α 越低，越保守观望 |
| **Base Cushion** | 基础安全垫 | 买入价格的基础安全距离。比如当前价 50¢，base_cushion=0.05 表示至少要比市场价低 5% 才考虑买入，防止买在高位 |
| **base_cushion** | — | 同 Base Cushion，配置文件中的参数名。表示固定不变的基础安全距离百分比 |
| **Binary Market** | 二元预测市场 | 只有 Yes / No 两种结果的预测市场。例如"比特币下周会突破 10 万吗？"——答案只有是或否 |
| **CLOB** | Central Order Book | 中央订单簿，Polymarket 的核心撮合引擎。所有买卖订单都汇集在这里，按价格优先、时间优先的原则匹配成交 |
| **confidence (置信度)** | Confidence Score | 信号可信程度的评分，范围 0%~100%。80% 以上为高置信度，系统会更积极地执行交易 |
| **CTF** | Conditional Token Framework | 条件代币框架，Polymarket 底层使用的代币标准。每种预测市场的结果都对应一种"条件代币"，结算后可按 1:1 兑换 USDC.e |
| **EIP-712** | Ethereum Improvement Proposal 712 | 以太坊签名标准规范。用于对链下订单数据进行防篡改数字签名，确保订单确实来自钱包持有者且未被篡改 |
| **FAK** | Fill-And-Kill | 一种订单类型：**部分成交后取消剩余**。适合做市商——能成交多少先成交，剩下的立即撤销，不留在订单簿上 |
| **Fast Market** | 快速结算市场 | 每几分钟就滚动创建新实例的市场，典型代表是"Bitcoin Up or Down - 5 Minutes"。由 Chainlink Oracle 提供价格数据，高频滚动 |
| **FOK** | Fill-Or-Kill | 一种订单类型：**要么全部成交，要么全部取消**。适合需要精确执行的场景——不允许部分成交 |
| **Gas** | — | 区块链上的"手续费"。每次链上操作（转账、下单确认等）都需要支付 Gas 给 Polygon 网络的验证者，单位通常用 Gwei 或 MATIC 表示 |
| **GTC** | Good-Til-Cancelled | 一直有效直到手动取消的限价单。最常用的订单类型，挂在订单簿上等待匹配 |
| **GTD** | Good-Til-Date | 到指定时间自动取消的限价单。适用于"我只愿意在这个时间段内以这个价格买入"的场景 |
| **JSON** | JavaScript Object Notation | 一种轻量级数据交换格式。像结构化的记事本——用 `{键: 值}` 的方式组织数据，机器和人都容易读写 |
| **MATIC** | — | Polygon 网络的原生代币（现更名为 POL），用于支付链上交易的 Gas 费用 |
| **max_buy_price** | 最大买入价 | 你愿意为一个预测代币付出的最高价格。设得太高可能买到贵了，设得太低会错过机会 |
| **OLS** | Ordinary Least Squares | 普通最小二乘法。一种统计学方法，给一堆散点画一条"最贴合"的直线，用来判断价格趋势的方向和强度 |
| **order_size** | 订单大小 | 单笔交易的金额（USDC.e）。新手建议从小额开始，熟悉后再逐步加大 |
| **orderbook** | Order Book | 订单簿。记录市场上所有未成交的买单和卖单，按价格排序。深度越厚（挂单越多），流动性越好 |
| **Polymarket** | — | 全球最大的去中心化预测市场平台，运行在 Polygon 链上。用户可以对各种事件（政治、体育、加密货币等）的结果下注交易 |
| **position (持仓)** | Position | 当前持有的某种代币数量。正数表示做多（持有 Yes 代币），负数或零表示空仓 |
| **Pub/Sub** | Publish/Subscribe | 发布/订阅消息模式。像广播电台和电台的关系——Redis 充当广播塔，各模块是收音机，只接收自己关心的频道消息 |
| **Python venv** | Virtual Environment | Python 虚拟环境。项目的独立"药箱"——每个项目有自己的依赖包版本，互不干扰，避免"这个项目装了新库导致另一个项目崩了"的问题 |
| **R² (R-squared)** | 决定系数 | 衡量趋势线拟合好坏的评分（0~1 分）。1.0 表示完美拟合，0.0 表示毫无关系。策略中用于判断价格趋势的可信度 |
| **Redis** | REmote DIctionary Server | 开源内存数据库。在本系统中充当**消息中间件**（Pub/Sub）和数据缓存，特点是极快的读写速度 |
| **Safety Cushion** | 安全垫 | 防止买贵的保护机制。根据市场波动动态计算一个"安全买入价"，只有当市场价格低于这个安全价时才触发买入信号 |
| **Signal (信号)** | Trading Signal | 交易决策建议，通常有三种：**BUY**（买入）、**WAIT**（等待）、**HOLD**（持仓不动）。由策略引擎根据市场数据计算得出 |
| **Slope K** | 回归斜率 | OLS 回归直线的斜率 K，代表价格变化的**速度和方向**。K > 0 表示上涨趋势，K < 0 表示下跌趋势，绝对值越大趋势越强 |
| **stop-loss** | 止损 | 当亏损达到预设阈值时自动卖出的保护机制。"截断亏损，让利润奔跑"的前半句 |
| **systemd** | System Daemon | Linux 系统的服务管理器。负责开机自启、崩溃自动重启、日志收集等——是生产环境中保持机器人 24 小时运行的关键组件 |
| **take-profit** | 止盈 | 当盈利达到预设阈值时自动卖出的机制。"截断亏损，让利润奔跑"的后半句 |
| **tick size** | 最小价格变动单位 | 价格的最小刻度。比如 tick size = 0.01，那么价格只能是 0.50、0.51、0.52……不能出现 0.515 |
| **TLS/SSL** | Transport Layer Security | 加密通信协议。让数据在网络上传输时像走在密封管道中，防止被窃听或篡改 |
| **Ubuntu** | — | 流行的 Linux 发行版操作系统。本项目部署目标为 **Ubuntu 24.04 LTS**（长期支持版），稳定可靠且有 5 年官方维护 |
| **USDC.e** | USD Coin (bridged) | Polygon 网络上的桥接版 USD Circle 稳定币，与美元 1:1 锚定。Polymarket 上所有交易的计价和结算单位 |
| **Vultr** | — | 云服务器/VPS 提供商。本项目使用的服务器托管平台，IP 为 216.238.91.89 |
| **volatility (波动率)** | Volatility | 价格变动的剧烈程度。高波动意味着价格上蹿下跳，低波动意味着价格平稳。策略会据此调整安全垫的大小 |
| **WebSocket** | — | 全双工通信协议。像一根随时可以双向通话的电话线——服务器可以主动推送实时行情数据给客户端，不需要客户端反复询问 |
| **YAML** | YAML Ain't Markup Language | 配置文件格式。用缩进来表达层级关系，比 JSON 更易读。settings.yaml 就是这种格式 |

<!-- APPENDIX_C_CONTENT_END -->

---

> **📖 文档信息**
> 
> - **文档名称**: SimplePolyBot 完整使用手册（百科全书版）
> - **适用版本**: v1.0
> - **目标服务器**: Vultr Ubuntu 24.04 LTS (216.238.91.89)
> - **总章节数**: 10 章 + 3 个附录
> - **最后更新**: 2026年
> 
> ---
> 
> **✅ 文档到此结束**
> 
> 如有疑问或发现问题，请查阅 [第 7 章 FAQ](#第七章--常见问题-faq) 或 [第 8 章 故障排除](#第八章--异常处理与故障排除)
