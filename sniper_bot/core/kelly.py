"""
凯利公式仓位计算模块

基于 Kelly Criterion 计算每笔交易的最优仓位大小。
使用半凯利（Half-Kelly）作为保守策略，
并叠加流动性约束和风控上限。

与 SimplePolyBot 的区别：
  SimplePolyBot 使用固定份额（如 100 份/笔），
  本模块根据获胜概率和赔率动态计算最优仓位。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PositionSizing:
    """仓位计算结果"""
    kelly_fraction: float       # 完整凯利比例
    half_kelly_fraction: float  # 半凯利比例
    recommended_shares: float   # 推荐份额数
    max_by_balance: float       # 余额约束上限
    max_by_depth: float         # 流动性约束上限
    limiting_factor: str        # 限制因素名称


def kelly_fraction(
    p_win: float,
    buy_price: float,
) -> float:
    """
    计算凯利比例

    对于二元期权（赢赚 1-price，输亏 price）：
      f* = (P_win × (1/price - 1) - P_loss) / (1/price - 1)
         = P_win - P_loss × price / (1 - price)

    Args:
        p_win: 获胜概率
        buy_price: 买入价格（0~1）

    Returns:
        凯利比例 f*，可能为负（说明不应下注）
    """
    if buy_price <= 0 or buy_price >= 1 or p_win <= 0:
        return 0.0

    p_loss = 1.0 - p_win
    odds = (1.0 / buy_price) - 1.0  # 赔率 b

    if odds <= 0:
        return 0.0

    # Kelly: f* = (p × b - q) / b
    f = (p_win * odds - p_loss) / odds

    return f


def calculate_position(
    p_win: float,
    buy_price: float,
    usdc_balance: float,
    available_depth: float,
    max_bet_usd: float = 200.0,
    balance_fraction: float = 0.20,
    depth_fraction: float = 0.50,
    min_shares: float = 10.0,
    max_shares: float = 1000.0,
) -> PositionSizing:
    """
    计算最终推荐仓位（多重约束叠加）

    约束链（取最小值）：
      1. 半凯利公式 → 理论最优
      2. 余额 × 20% → 资金安全
      3. 订单簿深度 × 50% → 流动性保护
      4. 硬上限 1000 份 → 尾部风险
      5. 硬下限 10 份 → 最小可操作量

    Args:
        p_win: 获胜概率
        buy_price: 买入价格
        usdc_balance: 可用 USDC 余额
        available_depth: 目标价位的订单簿深度（份）
        max_bet_usd: 单笔最大 USDC 投入
        balance_fraction: 最大余额占比
        depth_fraction: 最大深度占比
        min_shares: 最小份额
        max_shares: 最大份额

    Returns:
        PositionSizing 完整计算结果
    """
    f_full = kelly_fraction(p_win, buy_price)
    f_half = max(0.0, f_full * 0.5)

    if buy_price <= 0:
        return PositionSizing(
            kelly_fraction=0.0,
            half_kelly_fraction=0.0,
            recommended_shares=0.0,
            max_by_balance=0.0,
            max_by_depth=0.0,
            limiting_factor="invalid_price",
        )

    # 各约束下的最大份额
    kelly_shares = f_half * usdc_balance / buy_price
    balance_shares = usdc_balance * balance_fraction / buy_price
    bet_shares = max_bet_usd / buy_price
    depth_shares = available_depth * depth_fraction

    # 取所有约束的最小值
    candidates = {
        "kelly": kelly_shares,
        "balance": balance_shares,
        "max_bet": bet_shares,
        "depth": depth_shares,
        "hard_max": max_shares,
    }

    limiting = min(candidates, key=candidates.get)  # type: ignore[arg-type]
    recommended = max(0.0, min(candidates.values()))

    # 下限检查
    if recommended < min_shares:
        recommended = 0.0  # 不满足最小量，不交易
        limiting = "below_minimum"

    return PositionSizing(
        kelly_fraction=f_full,
        half_kelly_fraction=f_half,
        recommended_shares=recommended,
        max_by_balance=balance_shares,
        max_by_depth=depth_shares,
        limiting_factor=limiting,
    )
