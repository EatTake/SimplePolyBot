"""
SniperBot 主循环

单进程异步事件驱动架构的入口。
协调所有模块的初始化、生命周期和优雅关机。

启动命令: python -m sniper_bot.app.main
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone
from typing import Optional

# 确保项目根目录在路径中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv

from sniper_bot.core.models import AccountState, RiskLimits
from sniper_bot.core.volatility import VolatilityEstimator
from sniper_bot.core.brownian_bridge import analyze_reversal, minimum_delta_for_confidence
from sniper_bot.core.fee_model import dynamic_max_price
from sniper_bot.core.momentum import ols_regression
from sniper_bot.engine.cycle_manager import CycleManager
from sniper_bot.engine.price_engine import PriceEngine
from sniper_bot.engine.signal_arbiter import SignalArbiter
from sniper_bot.engine.risk_governor import RiskGovernor
from sniper_bot.infra.binance_ws import BinanceWS
from sniper_bot.infra.chainlink_rtds import ChainlinkRTDS
from sniper_bot.infra.clob_client import ClobClient
from sniper_bot.infra.gamma_client import GammaClient
from sniper_bot.infra.ctf_client import CTFClient
from sniper_bot.infra.logger import setup_logging
from sniper_bot.app.pnl_tracker import PnLTracker
from sniper_bot.app.settlement import SettlementDaemon


logger = logging.getLogger(__name__)


class SniperBot:
    """
    SniperBot 主控制器

    生命周期：
      1. __init__: 加载配置
      2. run(): 初始化所有组件 → 启动并发任务 → 等待关机信号
    """

    def __init__(self) -> None:
        load_dotenv()
        setup_logging(level=os.getenv("LOG_LEVEL", "INFO"))

        logger.info("=" * 60)
        logger.info("  SniperBot v1.0 — 布朗桥反转概率交易系统")
        logger.info("=" * 60)

        # ── 从环境变量加载配置 ──
        self._private_key = os.getenv("PRIVATE_KEY", "")
        self._clob_host = os.getenv("CLOB_HOST", "https://clob.polymarket.com")
        self._chain_id = int(os.getenv("CHAIN_ID", "137"))
        self._rpc_url = os.getenv("POLYGON_RPC_URL", "https://polygon-rpc.com")
        self._funder = os.getenv("FUNDER_ADDRESS", "")
        self._api_key = os.getenv("CLOB_API_KEY", "")
        self._api_secret = os.getenv("CLOB_API_SECRET", "")
        self._api_passphrase = os.getenv("CLOB_API_PASSPHRASE", "")
        self._initial_balance = float(os.getenv("INITIAL_BALANCE", "1000"))

        if not self._private_key:
            raise ValueError("PRIVATE_KEY 环境变量未设置")

        # ── 初始化组件 ──
        # Core
        self._volatility = VolatilityEstimator()
        self._price_engine = PriceEngine(window_seconds=180)

        # Engine
        self._cycle_manager = CycleManager(
            on_cycle_reset=self._on_cycle_reset,
        )
        self._arbiter = SignalArbiter()
        self._risk_governor = RiskGovernor(RiskLimits())

        # App
        self._pnl = PnLTracker(initial_balance=self._initial_balance)

        # Infra (延迟初始化)
        self._binance_ws: Optional[BinanceWS] = None
        self._chainlink_ws: Optional[ChainlinkRTDS] = None
        self._gamma: Optional[GammaClient] = None
        self._clob: Optional[ClobClient] = None
        self._ctf: Optional[CTFClient] = None
        self._settlement: Optional[SettlementDaemon] = None

        self._running = False
        self._last_log_time: float = 0.0  # 每 10 秒输出一次状态行

    async def run(self) -> None:
        """主入口：初始化 → 并发运行 → 优雅关机"""
        self._running = True
        self._setup_signal_handlers()

        try:
            await self._initialize_infra()

            # 并发启动所有子任务
            await asyncio.gather(
                self._binance_ws.run_forever(),
                self._chainlink_ws.run_forever(),
                self._strategy_loop(),
                self._settlement.run_forever(),
                return_exceptions=True,
            )

        except asyncio.CancelledError:
            logger.info("收到取消信号")
        except Exception as e:
            logger.error("主循环致命异常: %s", e, exc_info=True)
        finally:
            await self._shutdown()

    async def _initialize_infra(self) -> None:
        """初始化所有基础设施组件"""
        logger.info("初始化基础设施...")

        # Binance WS
        self._binance_ws = BinanceWS(
            on_price=lambda p, t: self._price_engine.push_binance(p, t),
        )

        # Chainlink RTDS
        self._chainlink_ws = ChainlinkRTDS(
            on_price=lambda p, t: self._price_engine.push_chainlink(p, t),
        )

        # Gamma API
        self._gamma = GammaClient()

        # CLOB
        self._clob = ClobClient(
            host=self._clob_host,
            chain_id=self._chain_id,
            private_key=self._private_key,
            api_key=self._api_key,
            api_secret=self._api_secret,
            api_passphrase=self._api_passphrase,
            funder=self._funder,
        )
        await self._clob.initialize()

        # CTF
        self._ctf = CTFClient(
            rpc_url=self._rpc_url,
            private_key=self._private_key,
        )
        await self._ctf.initialize()

        # 赎回守护
        self._settlement = SettlementDaemon(
            gamma=self._gamma,
            ctf=self._ctf,
            wallet_address=self._funder,
        )

        # 初始余额同步
        balance = await self._clob.get_balance()
        if balance > 0:
            self._pnl.account.usdc_balance = balance
            self._pnl.account.peak_balance = max(
                self._pnl.account.peak_balance, balance
            )
            logger.info("账户余额: $%.2f", balance)

        logger.info("✅ 所有组件初始化完成")

    async def _strategy_loop(self) -> None:
        """
        策略主循环 — 每秒执行一次

        流程：
          1. 更新周期状态
          2. 在 DISCOVERY 阶段查找市场
          3. 在 ACCUMULATING 阶段设置 start_price
          4. 在 SNIPING 阶段执行完整分析和决策
          5. FIRE 信号通过风控 → 执行订单
        """
        logger.info("🎯 策略循环启动")

        while self._running:
            try:
                cycle = self._cycle_manager.tick()

                match cycle.phase.value:
                    case "DISCOVERY":
                        await self._handle_discovery()

                    case "ACCUMULATING":
                        self._handle_accumulating(cycle)

                    case "SNIPING":
                        await self._handle_sniping(cycle)

                    case "FIRED":
                        pass  # 等待下一周期

                    case "IDLE":
                        pass

                    case "COOLDOWN":
                        pass

            except Exception as e:
                logger.error("策略循环异常: %s", e, exc_info=True)

            await asyncio.sleep(1.0)

    async def _handle_discovery(self) -> None:
        """
        DISCOVERY: 通过 slug 精确发现当前 5 分钟市场

        策略：
          1. 从周期起始时间计算 slug: btc-updown-5m-{aligned_ts}
          2. 调用 gamma.find_market_by_slug() 精确查询
          3. 失败时降级到模糊匹配 find_active_btc_5m_market()
        """
        if self._cycle_manager.market is not None:
            return  # 已发现

        cycle = self._cycle_manager.tick()
        cycle_ts = int(cycle.start_timestamp)
        aligned_ts = cycle_ts - (cycle_ts % 300)
        slug = f"btc-updown-5m-{aligned_ts}"

        # 策略 1：精确 slug 查询
        result = await self._gamma.find_market_by_slug(slug)
        if result:
            self._cycle_manager.set_market(result.market)

            # 输出真实市场 ID
            m = result.market
            status_icon = "✅" if result.accepting_orders and not result.closed else "⚠️"
            logger.info(
                "%s 市场已发现: %s (ID=%s)",
                status_icon, slug, m.event_id,
            )
            logger.info(
                "  condition=%s  UP=%s...  DOWN=%s...",
                m.condition_id[:24], m.up_token_id[:20], m.down_token_id[:20],
            )
            if not result.accepting_orders or result.closed:
                logger.warning(
                    "⚠️ 市场未开放交易 (accepting=%s, closed=%s)",
                    result.accepting_orders, result.closed,
                )
            return

        # 策略 2：降级到模糊匹配
        logger.debug("slug 查询无结果，尝试模糊匹配...")
        market = await self._gamma.find_active_btc_5m_market()
        if market:
            self._cycle_manager.set_market(market)

    def _handle_accumulating(self, cycle) -> None:
        """
        ACCUMULATING: 设置起始价格 + 每 10 秒行情概览
        """
        if cycle.start_price is None:
            # 优先使用 Chainlink 价格
            price = self._price_engine.chainlink.earliest_price()
            if price is None:
                price = self._price_engine.binance.earliest_price()
            if price:
                self._cycle_manager.set_start_price(price)
                self._volatility.update(price, time.time())
            return

        # 每 10 秒输出行情概览
        now = time.time()
        if now - self._last_log_time >= 10:
            self._last_log_time = now
            chainlink_price = self._price_engine.chainlink.latest_price()
            if chainlink_price:
                delta = abs(chainlink_price - cycle.start_price)
                direction = "UP" if chainlink_price >= cycle.start_price else "DOWN"
                vol = self._volatility.estimate()
                sigma = vol.sigma_dollar_per_sqrt_sec if vol else 0.0
                n_pts = self._price_engine.binance.size
                logger.info(
                    "  T-%3.0fs │ BTC $%,.2f │ Δ $%6.2f │ %s │ σ $%.4f │ 样本 %d │ 📡 数据积累中",
                    cycle.time_remaining, chainlink_price, delta,
                    direction, sigma, n_pts,
                )

    async def _handle_sniping(self, cycle) -> None:
        """
        SNIPING: 每秒执行完整的分析→决策→执行链

        增强：每 10 秒输出详细状态行（包含垫厚系数、动态限价）
        """
        if cycle.market is None or cycle.start_price is None:
            return

        market = cycle.market
        start_price = cycle.start_price

        # 更新波动率
        binance_ts, binance_prices = self._price_engine.binance.get_arrays()
        vol_estimate = self._volatility.estimate()

        # Chainlink 当前价格
        chainlink_price = self._price_engine.chainlink.latest_price()
        if chainlink_price is None:
            return

        # 获取合约最优卖价
        direction = self._price_engine.get_direction(start_price)
        if direction is None:
            return

        token_id = market.token_id_for_direction(direction)
        best_ask, ask_depth = await self._clob.get_best_ask(token_id)

        # 多因子仲裁
        decision = self._arbiter.evaluate(
            chainlink_price=chainlink_price,
            start_price=start_price,
            time_remaining=cycle.time_remaining,
            volatility=vol_estimate,
            binance_timestamps=binance_ts,
            binance_prices=binance_prices,
            directions_agree=self._price_engine.directions_agree(start_price),
            best_ask=best_ask,
            ask_depth=ask_depth,
            market=market,
            account=self._pnl.account,
            already_fired=self._cycle_manager.has_fired,
        )

        # ── 每 10 秒打印详细状态行 ──
        now = time.time()
        should_log = (now - self._last_log_time >= 10) or decision.action == "FIRE"
        if should_log:
            self._last_log_time = now
            delta = abs(chainlink_price - start_price)
            sigma = vol_estimate.sigma_dollar_per_sqrt_sec if vol_estimate else 0.0
            regression = ols_regression(binance_ts, binance_prices) if len(binance_prices) >= 10 else None

            # 安全垫计算
            min_delta = minimum_delta_for_confidence(sigma, cycle.time_remaining, 0.97) if sigma > 0 else float('inf')
            cushion = delta / min_delta if 0 < min_delta < 9999 else 0.0
            dyn_limit = dynamic_max_price(cycle.time_remaining, delta, min_delta)

            # 反转概率
            if sigma > 0 and delta > 0 and cycle.time_remaining > 0:
                rev = analyze_reversal(chainlink_price, start_price, sigma, cycle.time_remaining)
                p_rev_str = f"{rev.p_reversal:.2%}"
            else:
                p_rev_str = " --- "

            r2_str = f"{regression.r_squared:.2f}" if regression else " --- "
            slope_dir = ("↑" if regression and regression.slope > 0 else "↓") if regression else "?"

            status = (
                f"  T-{cycle.time_remaining:3.0f}s │ "
                f"BTC ${chainlink_price:,.2f} │ "
                f"Δ ${delta:6.2f} │ "
                f"垫{cushion:4.1f}x │ "
                f"σ ${sigma:.4f} │ "
                f"R² {r2_str}{slope_dir} │ "
                f"P_rev {p_rev_str:7s} │ "
                f"{direction:4s} │ "
                f"Ask ${best_ask:.2f} 限 ${dyn_limit:.2f}"
            )

            if decision.action == "FIRE":
                logger.info("🔫 %s │ FIRE!", status)
            else:
                reason = decision.reasons[0] if decision.reasons else ""
                logger.info("%s │ ⏸ %s", status, reason[:35])

        if decision.action != "FIRE":
            return

        # ===== FIRE → 风控审批 =====
        verdict = self._risk_governor.approve(decision, self._pnl.account)

        if not verdict.approved:
            logger.info("🚫 风控拒绝: %s", verdict.reason)
            return

        # 使用风控调整后的仓位
        decision.recommended_size = verdict.adjusted_size

        # ===== 执行 FAK 订单 =====
        result = await self._clob.place_fak_order(
            token_id=decision.token_id,
            price=decision.max_buy_price,
            size=decision.recommended_size,
        )

        # 记录交易
        self._pnl.record_trade(decision, result)
        self._cycle_manager.mark_fired()

        logger.info(
            "🎯 订单执行完成: status=%s order_id=%s",
            result.status.value, result.order_id[:16] if result.order_id else "N/A",
        )

    def _on_cycle_reset(self) -> None:
        """周期切换回调：清空所有分析状态"""
        self._price_engine.clear_all()
        self._volatility.clear()
        self._pnl.on_new_cycle()
        logger.debug("已清空价格队列和波动率数据")

    def _setup_signal_handlers(self) -> None:
        """注册系统信号处理器"""
        loop = asyncio.get_event_loop()

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, self._request_shutdown)
            except NotImplementedError:
                # Windows 不支持 add_signal_handler
                signal.signal(sig, lambda s, f: self._request_shutdown())

    def _request_shutdown(self) -> None:
        """请求优雅关机"""
        logger.info("收到关机信号，准备停止...")
        self._running = False

        if self._binance_ws:
            self._binance_ws.stop()
        if self._chainlink_ws:
            self._chainlink_ws.stop()
        if self._settlement:
            self._settlement.stop()

    async def _shutdown(self) -> None:
        """优雅关机"""
        logger.info("执行优雅关机...")

        if self._gamma:
            await self._gamma.close()

        # 打印最终统计
        stats = self._pnl.get_stats()
        logger.info("=" * 60)
        logger.info("  📊 最终统计")
        logger.info("  余额: $%.2f", stats["balance"])
        logger.info("  总 PnL: $%.2f", stats["total_pnl"])
        logger.info("  今日交易: %d", stats["trades_today"])
        logger.info("  胜率: %.1f%%", stats["win_rate"] * 100)
        logger.info("=" * 60)


def main() -> None:
    """CLI 入口"""
    bot = SniperBot()
    asyncio.run(bot.run())


if __name__ == "__main__":
    main()
