"""
SniperBot 模拟交易运行器 v2

使用真实的 Binance BTC/USDT 行情数据，
执行完整的策略分析链，但在最后下单时刻不真正下单，仅记录模拟结果。

v2 修复:
  1. P_rev 列独立计算，不依赖 decision 对象（修复 N/A bug）
  2. Windows Ctrl+C 优雅退出
  3. 跳过首个不完整周期
  4. 提供两套阈值（strict / relaxed），方便测试观察

启动: python -m sniper_bot.app.sim_runner
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# 确保项目根目录在路径中
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

import numpy as np
import httpx

from sniper_bot.core.brownian_bridge import analyze_reversal, minimum_delta_for_confidence
from sniper_bot.core.fee_model import net_expected_value, taker_fee, time_based_max_price, dynamic_max_price
from sniper_bot.core.kelly import calculate_position
from sniper_bot.core.momentum import ols_regression
from sniper_bot.core.volatility import VolatilityEstimator
from sniper_bot.core.models import (
    AccountState, CyclePhase, FastMarket, RiskLimits, hold_decision,
)
from sniper_bot.engine.cycle_manager import CycleManager
from sniper_bot.engine.price_engine import PriceEngine
from sniper_bot.engine.signal_arbiter import SignalArbiter
from sniper_bot.engine.risk_governor import RiskGovernor


logger = logging.getLogger("sim_runner")

# ── 颜色常量 ──
_RESET = "\033[0m"
_GREEN = "\033[92m"
_RED = "\033[91m"
_YELLOW = "\033[93m"
_CYAN = "\033[96m"
_BOLD = "\033[1m"
_DIM = "\033[2m"


# ──────────────────────────────────────────────
# 两套阈值：strict（生产）和 relaxed（测试用）
# ──────────────────────────────────────────────
PROFILES = {
    "strict": {
        "max_reversal_prob": 0.03,   # 3% — 要求 97% 信心
        "min_r_squared": 0.60,
        "min_data_points": 30,
        "desc": "生产级 (P<3%, R²>0.60)",
    },
    "relaxed": {
        "max_reversal_prob": 0.20,   # 20% — 放宽到 80% 信心
        "min_r_squared": 0.20,
        "min_data_points": 15,
        "desc": "测试级 (P<20%, R²>0.20)",
    },
}


class SimulatedMarketBook:
    """
    模拟 Polymarket 订单簿

    根据 BTC 价格偏移和剩余时间，模拟合约的 best_ask 和 depth。
    """

    def estimate_contract_price(
        self,
        delta: float,
        sigma: float,
        time_remaining: float,
    ) -> tuple[float, float]:
        """
        模拟 Polymarket 合约的真实市场价格

        真实市场特征（与理论价格的差异）：
          1. 延迟效应: 合约价格滞后于理论值 ~15-25%
          2. 锚定效应: 市场惯性使价格在 $0.50 附近停留更久
          3. 流动性溢价: 流动性不足时 ask 更高
          4. 尾盘加速: T<30s 时价格追赶理论值

        Returns:
            (estimated_best_ask, simulated_depth)
        """
        if sigma <= 0 or time_remaining <= 0:
            return 0.50, 500.0

        if delta <= 0:
            p_win = 0.50
        else:
            p_rev = math.exp(-2.0 * delta ** 2 / (sigma ** 2 * time_remaining))
            p_win = 1.0 - p_rev

        # ── 模拟市场低效：合约价格滞后于理论概率 ──
        # 真实市场中，即使 P_win=95%，合约可能只到 $0.80
        # 越接近结束，市场追赶越快（做市商套利）
        if time_remaining > 60:
            # 早期：大幅滞后（合约反应慢）
            # 映射: p_win → best_ask = 0.10 + p_win * 0.75
            # 例: P_win=0.97 → ask=$0.83, P_win=0.80 → ask=$0.70
            best_ask = 0.10 + p_win * 0.75
        elif time_remaining > 30:
            # 中期：逐渐追赶
            # 映射: p_win → best_ask = 0.08 + p_win * 0.82
            best_ask = 0.08 + p_win * 0.82
        else:
            # 尾盘：快速收敛
            # 映射: p_win → best_ask = 0.03 + p_win * 0.92
            best_ask = 0.03 + p_win * 0.92

        best_ask = max(0.02, min(0.98, best_ask))

        # ── 模拟深度（尾盘流动性衰减）──
        base_depth = 500.0
        time_factor = max(0.1, time_remaining / 100.0)
        depth = base_depth * time_factor

        return round(best_ask, 2), round(depth, 0)


class SimRunner:
    """
    模拟交易主控制器

    真实数据:
      - Binance WS: 实时 BTC/USDT 价格 ✅
      - 合约价格: 布朗桥模拟订单簿

    模拟:
      - 下单: 记录但不提交 ✅
      - 结算: 根据 5 分钟结束时 BTC 价格判断胜负 ✅
    """

    def __init__(self, sim_balance: float = 1000.0, profile: str = "relaxed"):
        self._setup_logging()

        # ── 选择阈值 profile ──
        prof = PROFILES.get(profile, PROFILES["relaxed"])
        self._profile_name = profile
        self._profile_desc = prof["desc"]

        # ── 分析组件 ──
        self._volatility = VolatilityEstimator()
        self._price_engine = PriceEngine(window_seconds=180)
        self._cycle_manager = CycleManager(on_cycle_reset=self._on_cycle_reset)
        self._arbiter = SignalArbiter(
            max_reversal_prob=prof["max_reversal_prob"],
            min_r_squared=prof["min_r_squared"],
            min_data_points=prof["min_data_points"],
        )
        self._risk_governor = RiskGovernor(RiskLimits())
        self._sim_book = SimulatedMarketBook()

        # ── 模拟账户 ──
        self._account = AccountState(
            usdc_balance=sim_balance,
            peak_balance=sim_balance,
        )

        # ── 交易记录 ──
        self._data_dir = Path("data")
        self._data_dir.mkdir(exist_ok=True)
        self._sim_file = self._data_dir / f"sim_{profile}_{int(time.time())}.jsonl"

        # ── 状态 ──
        self._running = False
        self._cycles_seen = 0
        self._total_signals = 0
        self._fire_count = 0
        self._last_cycle_id = -1
        self._skipped_first_cycle = False

        # ── Gamma API 市场发现 ──
        self._http_client = httpx.AsyncClient(
            base_url="https://gamma-api.polymarket.com",
            timeout=8.0,
            headers={"Accept": "application/json"},
        )
        self._current_market: Optional[FastMarket] = None
        self._market_slug: str = ""   # 当前周期的 slug (如 btc-updown-5m-1775177700)
        self._market_id: str = ""     # Gamma event.id

        # 周期结算追踪
        self._pending_bet: Optional[dict] = None
        self._cycle_start_price: Optional[float] = None

    def _setup_logging(self) -> None:
        """配置控制台日志"""
        fmt = "%(asctime)s | %(message)s"
        logging.basicConfig(
            level=logging.INFO,
            format=fmt,
            datefmt="%H:%M:%S",
            handlers=[logging.StreamHandler(sys.stdout)],
            force=True,
        )
        for name in ("websockets", "urllib3", "httpx", "asyncio", "httpcore"):
            logging.getLogger(name).setLevel(logging.WARNING)

    async def run(self) -> None:
        """启动模拟交易"""
        self._running = True

        logger.info(f"{_BOLD}{'='*65}{_RESET}")
        logger.info(f"{_BOLD}{_CYAN}  SniperBot 模拟交易 v2 (Paper Trading){_RESET}")
        logger.info(f"{_BOLD}{_CYAN}  真实 BTC 行情 · 模拟下单 · 自动结算{_RESET}")
        logger.info(f"{_BOLD}{'='*65}{_RESET}")
        logger.info(f"  余额: ${self._account.usdc_balance:.2f}")
        logger.info(f"  数据源: Binance WS (btcusdt@trade)")
        logger.info(f"  阈值档位: {_YELLOW}{self._profile_desc}{_RESET}")
        logger.info(f"  记录: {self._sim_file}")
        logger.info(f"  退出: 按 Ctrl+C 优雅退出")
        logger.info(f"{_BOLD}{'='*65}{_RESET}")
        logger.info("")

        # ── Windows Ctrl+C 优雅处理 ──
        loop = asyncio.get_event_loop()
        try:
            loop.add_signal_handler(signal.SIGINT, self._graceful_stop)
        except NotImplementedError:
            # Windows: 用 signal.signal 做兜底
            signal.signal(signal.SIGINT, lambda s, f: self._graceful_stop())

        try:
            # 用 create_task 而不是 gather 来控制取消
            binance_task = asyncio.create_task(self._binance_stream())
            strategy_task = asyncio.create_task(self._strategy_loop())

            # 等待优雅关机
            while self._running:
                await asyncio.sleep(0.5)

        except asyncio.CancelledError:
            pass
        finally:
            # 取消子任务
            for task in [binance_task, strategy_task]:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except (asyncio.CancelledError, Exception):
                        pass

            self._print_final_stats()

    def _graceful_stop(self) -> None:
        """优雅停止 — 无堆栈打印"""
        logger.info(f"\n{_YELLOW}收到 Ctrl+C，正在优雅退出...{_RESET}")
        self._running = False

    async def _binance_stream(self) -> None:
        """连接 Binance WebSocket 获取实时 BTC 价格"""
        import websockets
        from websockets.exceptions import ConnectionClosed

        url = "wss://stream.binance.com:9443/ws/btcusdt@trade"
        reconnect_delay = 1

        while self._running:
            try:
                async with websockets.connect(
                    url, ping_interval=20, ping_timeout=10, close_timeout=5,
                ) as ws:
                    logger.info(f"{_GREEN}✅ Binance WS 已连接 — 实时 BTC 行情就绪{_RESET}")
                    reconnect_delay = 1

                    async for raw in ws:
                        if not self._running:
                            break
                        try:
                            data = json.loads(raw)
                            if data.get("e") != "trade":
                                continue
                            price = float(data["p"])
                            ts = data["T"] / 1000.0

                            # 双轨推送
                            self._price_engine.push_binance(price, ts)
                            self._price_engine.push_chainlink(price, ts)

                            # 更新波动率
                            self._volatility.update(price, ts)

                        except (json.JSONDecodeError, KeyError):
                            pass

            except ConnectionClosed:
                if self._running:
                    logger.warning("Binance WS 断开，重连中...")
            except asyncio.CancelledError:
                return
            except Exception as e:
                if self._running:
                    logger.error(f"Binance WS 错误: {e}")

            if self._running:
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, 30)

    async def _strategy_loop(self) -> None:
        """每秒执行一次策略分析"""
        logger.info(f"{_DIM}等待 Binance 数据流...{_RESET}")
        while self._running and self._price_engine.binance.size < 5:
            await asyncio.sleep(0.5)

        logger.info(f"{_GREEN}数据流就绪，开始策略循环{_RESET}")
        logger.info("")

        while self._running:
            try:
                await self._tick()
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.error(f"策略异常: {e}", exc_info=True)

            await asyncio.sleep(1.0)

    async def _tick(self) -> None:
        """单次策略 tick"""
        now = time.time()
        cycle = self._cycle_manager.tick(now)

        # ── 检测周期切换 ──
        if cycle.cycle_id != self._last_cycle_id:
            self._handle_new_cycle(cycle)
            self._last_cycle_id = cycle.cycle_id

        # ── FIX#3: 跳过首个不完整周期 ──
        if not self._skipped_first_cycle:
            if cycle.time_remaining < 200:
                # 启动时已过半，跳过
                return
            self._skipped_first_cycle = True

        # ── DISCOVERY: 通过 Gamma API 发现真实市场 ──
        if cycle.phase == CyclePhase.DISCOVERY:
            await self._discover_real_market(cycle)

        # ── ACCUMULATING: 设置起始价格 + 每 10 秒输出 ──
        if cycle.phase == CyclePhase.ACCUMULATING:
            if cycle.start_price is None:
                price = self._price_engine.chainlink.latest_price()
                if price:
                    self._cycle_manager.set_start_price(price)
                    self._cycle_start_price = price
                    logger.info(
                        f"{_CYAN}📌 周期 #{cycle.cycle_id} 起始价 "
                        f"${price:,.2f}{_RESET}"
                    )
            else:
                # 需求4: ACCUMULATING 阶段也每 10 秒输出
                t_rem = int(cycle.time_remaining)
                if t_rem % 10 == 0:
                    self._print_accumulating_status(cycle)

        # ── SNIPING: 策略评估 ──
        if cycle.phase == CyclePhase.SNIPING:
            await self._evaluate_signal(cycle)

    def _handle_new_cycle(self, cycle) -> None:
        """处理新周期"""
        self._cycles_seen += 1

        # 结算上一周期
        self._settle_pending_bet()

        if self._cycles_seen > 1:
            logger.info("")
            logger.info(f"{_BOLD}{'─'*65}{_RESET}")

        cycle_start_utc = datetime.fromtimestamp(cycle.start_timestamp, tz=timezone.utc).strftime("%H:%M")
        cycle_end_utc = datetime.fromtimestamp(cycle.end_timestamp, tz=timezone.utc).strftime("%H:%M")
        logger.info(
            f"{_BOLD}🔄 周期 #{cycle.cycle_id} "
            f"(UTC {cycle_start_utc}-{cycle_end_utc}) "
            f"余额 ${self._account.usdc_balance:.2f} "
            f"PnL ${self._account.total_pnl:+.2f}{_RESET}"
        )

    async def _discover_real_market(self, cycle) -> None:
        """
        通过 Gamma API 发现当前 5 分钟周期的真实 Polymarket 市场

        slug 格式: btc-updown-5m-{5分钟对齐的 Unix 时间戳}
        例: btc-updown-5m-1775177700

        API: GET https://gamma-api.polymarket.com/events?slug={slug}
        """
        # 计算当前周期的 5 分钟对齐时间戳
        cycle_ts = int(cycle.start_timestamp)
        aligned_ts = cycle_ts - (cycle_ts % 300)
        slug = f"btc-updown-5m-{aligned_ts}"

        try:
            resp = await self._http_client.get("/events", params={"slug": slug})
            resp.raise_for_status()
            events = resp.json()

            if events and isinstance(events, list) and len(events) > 0:
                event = events[0]
                markets = event.get("markets", [])

                if markets:
                    market_data = markets[0]
                    clob_ids_raw = market_data.get("clobTokenIds", "[]")

                    # clobTokenIds 可能是 JSON 字符串
                    if isinstance(clob_ids_raw, str):
                        clob_ids = json.loads(clob_ids_raw)
                    else:
                        clob_ids = clob_ids_raw

                    if len(clob_ids) >= 2:
                        condition_id = market_data.get("conditionId", "")
                        event_id = event.get("id", "")

                        # 解析 eventStartTime
                        start_time_str = event.get("startTime", "")
                        end_ts = cycle.start_timestamp + 300
                        if start_time_str:
                            try:
                                dt = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
                                end_ts = dt.timestamp() + 300
                            except (ValueError, TypeError):
                                pass

                        self._current_market = FastMarket(
                            event_id=event_id,
                            condition_id=condition_id,
                            up_token_id=clob_ids[0],
                            down_token_id=clob_ids[1],
                            end_timestamp=end_ts,
                            slug=slug,
                        )
                        self._market_slug = slug
                        self._market_id = event_id

                        self._cycle_manager.set_market(self._current_market)

                        # 检查市场是否接受订单
                        accepting = market_data.get("acceptingOrders", False)
                        closed = market_data.get("closed", False)
                        status_icon = "✅" if accepting and not closed else "⚠️"

                        logger.info(
                            f"{_CYAN}  {status_icon} 市场已发现: {slug}{_RESET}"
                        )
                        logger.info(
                            f"{_CYAN}  📋 ID={event_id}  condition={condition_id[:24]}...{_RESET}"
                        )
                        logger.info(
                            f"{_DIM}  UP  token={clob_ids[0][:24]}...{_RESET}"
                        )
                        logger.info(
                            f"{_DIM}  DOWN token={clob_ids[1][:24]}...{_RESET}"
                        )
                        if not accepting or closed:
                            logger.info(
                                f"{_YELLOW}  ⚠️ 市场未开放交易 (accepting={accepting}, closed={closed}){_RESET}"
                            )
                        return

            # API 无结果 → 使用备用（市场可能还没创建）
            logger.info(
                f"{_YELLOW}  ⚠️ Gamma API 未找到: {slug} — 使用本地模拟{_RESET}"
            )

        except Exception as e:
            logger.warning(
                f"{_YELLOW}  ⚠️ Gamma API 查询失败: {e} — 使用本地模拟{_RESET}"
            )

        # 兜底：使用本地模拟市场
        self._current_market = FastMarket(
            event_id=f"sim-{aligned_ts}",
            condition_id=f"sim_cond_{aligned_ts}",
            up_token_id="sim_up_token",
            down_token_id="sim_down_token",
            end_timestamp=cycle.start_timestamp + 300,
            slug=slug,
        )
        self._market_slug = slug
        self._market_id = f"sim-{aligned_ts}"
        self._cycle_manager.set_market(self._current_market)

    async def _evaluate_signal(self, cycle) -> None:
        """在狙击窗口内评估信号"""
        if cycle.start_price is None or cycle.market is None:
            return

        start_price = cycle.start_price
        chainlink_price = self._price_engine.chainlink.latest_price()
        if chainlink_price is None:
            return

        # ── 收集数据 ──
        binance_ts, binance_prices = self._price_engine.binance.get_arrays()
        vol = self._volatility.estimate()

        delta = abs(chainlink_price - start_price)
        direction = "UP" if chainlink_price >= start_price else "DOWN"

        regression = ols_regression(binance_ts, binance_prices) if len(binance_prices) >= 10 else None
        sigma = vol.sigma_dollar_per_sqrt_sec if vol else 0.0

        # ── 模拟合约定价 ──
        best_ask, ask_depth = self._sim_book.estimate_contract_price(
            delta, sigma, cycle.time_remaining,
        )

        dirs_agree = self._price_engine.directions_agree(start_price)
        self._total_signals += 1

        # ── 独立计算 P_reversal 用于显示 ──
        if sigma > 0 and delta > 0 and cycle.time_remaining > 0:
            reversal = analyze_reversal(
                chainlink_price, start_price, sigma, cycle.time_remaining
            )
            display_p_rev = reversal.p_reversal
        else:
            display_p_rev = None

        # ── 完整仲裁 ──
        decision = self._arbiter.evaluate(
            chainlink_price=chainlink_price,
            start_price=start_price,
            time_remaining=cycle.time_remaining,
            volatility=vol,
            binance_timestamps=binance_ts,
            binance_prices=binance_prices,
            directions_agree=dirs_agree,
            best_ask=best_ask,
            ask_depth=ask_depth,
            market=cycle.market,
            account=self._account,
            already_fired=self._cycle_manager.has_fired,
        )

        # ── 每 10 秒打印状态行 ──
        t_rem = int(cycle.time_remaining)
        if t_rem % 10 == 0 or decision.action == "FIRE":
            if display_p_rev is not None:
                p_rev_str = f"{display_p_rev:.2%}"
            else:
                p_rev_str = " --- "

            r2_str = f"{regression.r_squared:.2f}" if regression else " --- "

            # 计算安全垫系数和动态限价
            min_delta = (
                minimum_delta_for_confidence(sigma, cycle.time_remaining, 0.97)
                if sigma > 0 else float('inf')
            )
            cushion = delta / min_delta if min_delta > 0 and min_delta < 9999 else 0.0
            dyn_limit = dynamic_max_price(cycle.time_remaining, delta, min_delta)
            min_d_str = f"${min_delta:6.2f}" if min_delta < 9999 else "$  inf"

            # 斜率方向标记
            if regression and cycle.start_price:
                slope_dir = "↑" if regression.slope > 0 else "↓"
            else:
                slope_dir = "?"

            status_line = (
                f"  T-{t_rem:3d}s │ "
                f"BTC ${chainlink_price:,.2f} │ "
                f"Δ ${delta:6.2f} │ "
                f"需 {min_d_str} │ "
                f"垫{cushion:4.1f}x │ "
                f"σ ${sigma:.4f} │ "
                f"R² {r2_str:5s}{slope_dir} │ "
                f"P_rev {p_rev_str:7s} │ "
                f"{direction:4s} │ "
                f"Ask ${best_ask:.2f} 限 ${dyn_limit:.2f}"
            )

            if decision.action == "FIRE":
                logger.info(f"{_GREEN}{_BOLD}{status_line} │ 🔫 FIRE!{_RESET}")
            else:
                reason = decision.reasons[0] if decision.reasons else ""
                logger.info(f"{_DIM}{status_line} │ ⏸ {reason[:30]}{_RESET}")

        # ── FIRE → 模拟下单 ──
        if decision.action == "FIRE":
            self._execute_paper_trade(decision, cycle)

    def _print_accumulating_status(self, cycle) -> None:
        """
        ACCUMULATING 阶段每 10 秒输出行情概览

        此阶段不执行仲裁，仅展示行情变化和波动率积累状态，
        让操作者对当前周期的市场特征有直观认知。
        """
        if cycle.start_price is None:
            return

        start_price = cycle.start_price
        chainlink_price = self._price_engine.chainlink.latest_price()
        if chainlink_price is None:
            return

        delta = abs(chainlink_price - start_price)
        direction = "UP" if chainlink_price >= start_price else "DOWN"
        vol = self._volatility.estimate()
        sigma = vol.sigma_dollar_per_sqrt_sec if vol and vol.sigma_dollar_per_sqrt_sec > 0 else 0.0
        n_points = self._price_engine.binance.size

        t_rem = int(cycle.time_remaining)

        # 简版状态行
        logger.info(
            f"{_DIM}  T-{t_rem:3d}s │ "
            f"BTC ${chainlink_price:,.2f} │ "
            f"Δ ${delta:6.2f} │ "
            f"{direction:4s} │ "
            f"σ ${sigma:.4f} │ "
            f"样本 {n_points:4d} │ "
            f"📡 数据积累中...{_RESET}"
        )

    def _execute_paper_trade(self, decision, cycle) -> None:
        """模拟下单（记录，不提交）"""
        verdict = self._risk_governor.approve(decision, self._account)
        if not verdict.approved:
            logger.info(f"{_RED}🚫 风控拒绝: {verdict.reason}{_RESET}")
            return

        size = verdict.adjusted_size
        cost = size * decision.best_ask
        fee = taker_fee(size, decision.best_ask, "crypto")

        trade = {
            "signal_id": decision.signal_id,
            "timestamp": time.time(),
            "utc_time": datetime.now(timezone.utc).isoformat(),
            "direction": decision.direction,
            "btc_price": decision.chainlink_price,
            "start_price": decision.start_price,
            "delta": decision.delta,
            "sigma": decision.sigma,
            "p_reversal": decision.p_reversal,
            "confidence": decision.confidence,
            "slope_k": decision.slope_k,
            "r_squared": decision.r_squared,
            "time_remaining": decision.time_remaining,
            "contract_ask": decision.best_ask,
            "size": size,
            "cost": cost,
            "fee": fee,
            "max_buy_price": decision.max_buy_price,
            "ev": decision.expected_value,
            "reasons": decision.reasons,
            "outcome": "PENDING",
        }

        self._pending_bet = trade
        self._account.usdc_balance -= cost
        self._fire_count += 1
        self._cycle_manager.mark_fired()

        logger.info("")
        logger.info(f"{_GREEN}{_BOLD}{'━'*65}{_RESET}")
        logger.info(f"{_GREEN}{_BOLD}  📋 模拟下单 #{self._fire_count}{_RESET}")
        logger.info(f"{_GREEN}  方向: {decision.direction:<5} 信号: {decision.signal_id[:8]}{_RESET}")
        logger.info(f"{_GREEN}  BTC : ${decision.chainlink_price:,.2f}  起始: ${decision.start_price:,.2f}  Δ=${decision.delta:.2f}{_RESET}")
        logger.info(f"{_GREEN}  合约: ${decision.best_ask:.2f}  份额: {size:.0f}  成本: ${cost:.2f}  手续费: ${fee:.2f}{_RESET}")
        logger.info(f"{_GREEN}  胜率: {decision.confidence:.2%}  EV: ${decision.expected_value:.2f}  P_rev: {decision.p_reversal:.4%}{_RESET}")
        logger.info(f"{_GREEN}  σ={decision.sigma:.4f}/√s  R²={decision.r_squared:.2f}  K={decision.slope_k:.6f}{_RESET}")
        logger.info(f"{_GREEN}{_BOLD}{'━'*65}{_RESET}")
        logger.info("")

        self._persist_trade(trade)

    def _settle_pending_bet(self) -> None:
        """结算上一周期的模拟交易"""
        if self._pending_bet is None:
            return

        bet = self._pending_bet
        self._pending_bet = None

        # 用当前价格判断上一周期结果
        current_price = self._price_engine.binance.latest_price()
        start_price = bet["start_price"]

        if current_price is None or start_price is None:
            bet["outcome"] = "UNKNOWN"
            self._persist_trade(bet)
            return

        actual_direction = "UP" if current_price >= start_price else "DOWN"
        won = actual_direction == bet["direction"]

        size = bet["size"]
        cost = bet["cost"]

        if won:
            pnl = size - cost
            self._account.usdc_balance += size
            self._account.wins_today += 1
            self._account.consecutive_losses = 0
            bet["outcome"] = "WIN"
            bet["pnl"] = pnl
            bet["settle_price"] = current_price

            logger.info(
                f"{_GREEN}{_BOLD}  ✅ 结算: WIN! "
                f"方向={bet['direction']} 实际={actual_direction} "
                f"BTC=${current_price:,.2f} "
                f"PnL=${pnl:+.2f} "
                f"余额=${self._account.usdc_balance + pnl:.2f}{_RESET}"
            )
        else:
            pnl = -cost
            self._account.losses_today += 1
            self._account.consecutive_losses += 1
            bet["outcome"] = "LOSS"
            bet["pnl"] = pnl
            bet["settle_price"] = current_price

            logger.info(
                f"{_RED}{_BOLD}  ❌ 结算: LOSS "
                f"方向={bet['direction']} 实际={actual_direction} "
                f"BTC=${current_price:,.2f} "
                f"PnL=${pnl:+.2f}{_RESET}"
            )

        self._account.daily_pnl += pnl
        self._account.total_pnl += pnl
        self._account.trades_today += 1

        if self._account.usdc_balance > self._account.peak_balance:
            self._account.peak_balance = self._account.usdc_balance

        self._persist_trade(bet)

    def _on_cycle_reset(self) -> None:
        """周期重置回调"""
        self._price_engine.clear_all()
        self._volatility.clear()

    def _persist_trade(self, trade: dict) -> None:
        """追加写入 JSONL"""
        try:
            with open(self._sim_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(trade, ensure_ascii=False, default=str) + "\n")
        except Exception as e:
            logger.error(f"写入交易记录失败: {e}")

    def _print_final_stats(self) -> None:
        """打印最终统计"""
        logger.info("")
        logger.info(f"{_BOLD}{'='*65}{_RESET}")
        logger.info(f"{_BOLD}{_CYAN}  📊 模拟交易统计 [{self._profile_name}]{_RESET}")
        logger.info(f"{_BOLD}{'='*65}{_RESET}")
        logger.info(f"  运行周期: {self._cycles_seen}")
        logger.info(f"  信号评估: {self._total_signals}")
        logger.info(f"  模拟下单: {self._fire_count}")

        total = self._account.wins_today + self._account.losses_today
        wr = (self._account.wins_today / total * 100) if total > 0 else 0

        logger.info(f"  胜/负: {self._account.wins_today}/{self._account.losses_today} ({wr:.1f}%)")
        logger.info(f"  总 PnL: ${self._account.total_pnl:+.2f}")
        logger.info(f"  最终余额: ${self._account.usdc_balance:.2f}")
        logger.info(f"  最大回撤: {self._account.drawdown_pct:.1%}")
        logger.info(f"  记录文件: {self._sim_file}")
        logger.info(f"{_BOLD}{'='*65}{_RESET}")

    def stop(self) -> None:
        self._running = False


async def main():
    # 选择测试档位: "relaxed" 或 "strict"
    profile = "relaxed"

    # 检查命令行参数
    if len(sys.argv) > 1 and sys.argv[1] in PROFILES:
        profile = sys.argv[1]

    runner = SimRunner(sim_balance=1000.0, profile=profile)
    await runner.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass  # 已经在 _graceful_stop 中处理
